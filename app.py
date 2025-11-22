#!/usr/bin/env python3
"""
SDR SIGINT Platform - Main Application
Dual-mode SDR platform for signal intelligence with direction finding.
"""

import logging
import argparse
import signal
import sys
import time
import threading
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import platform modules
from config import get_config
from hardware import SDRController, OperatingMode
from scanning import (
    SpectrumScanner, DroneDetector,
    ParallelScanner, AnomalyDetector, ModeSwitcher
)
from demodulation import AnalogDemodulator, DigitalDemodulator
from direction_finding import SDRArraySync, BearingCalculator
from recording import SignalLogger
from visualization import BearingMapper
from web import start_server


class SDRPlatform:
    """Main SDR SIGINT Platform controller."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """Initialize SDR platform."""
        self.config = get_config(config_dir)
        self.running = False
        self.sdr: Optional[SDRController] = None
        self.scanner: Optional[SpectrumScanner] = None
        self.parallel_scanner: Optional[ParallelScanner] = None
        self.anomaly_detector: Optional[AnomalyDetector] = None
        self.mode_switcher: Optional[ModeSwitcher] = None
        self.drone_detector: Optional[DroneDetector] = None
        self.analog_demod: Optional[AnalogDemodulator] = None
        self.digital_demod: Optional[DigitalDemodulator] = None
        self.df_array: Optional[SDRArraySync] = None
        self.bearing_calc: Optional[BearingCalculator] = None
        self.logger: Optional[SignalLogger] = None
        self.mapper: Optional[BearingMapper] = None
        self.web_server = None
        
        # Performance tracking
        self.scan_count = 0
        self.anomaly_count = 0
        self.df_count = 0
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def initialize(self) -> bool:
        """Initialize all platform components."""
        logger.info("Initializing SDR SIGINT Platform...")
        
        try:
            # Initialize hardware
            sdr_config = self.config.hardware_config.get('sdr', {})
            self.sdr = SDRController(sdr_config)
            
            if not self.sdr.initialize():
                logger.error("Failed to initialize SDR hardware")
                return False
            
            # Initialize based on mode
            if self.sdr.mode == OperatingMode.MOBILE:
                logger.info("Initializing MOBILE mode components")
                self._init_mobile_mode()
            elif self.sdr.mode == OperatingMode.MOBILE_MULTI:
                logger.info("Initializing MOBILE_MULTI mode components")
                self._init_mobile_multi_mode()
            elif self.sdr.mode == OperatingMode.PARALLEL_SCAN:
                logger.info("Initializing PARALLEL_SCAN mode components")
                self._init_parallel_scan_mode()
            elif self.sdr.mode == OperatingMode.DF:
                logger.info("Initializing DF mode components")
                self._init_df_mode()
            else:
                logger.error("Unknown operating mode")
                return False
            
            # Initialize common components
            self._init_common_components()
            
            # Start web dashboard if enabled
            if self.config.hardware_config.get('dashboard', {}).get('enabled', True):
                dashboard_config = self.config.hardware_config.get('dashboard', {})
                self.web_server = start_server(dashboard_config)
                
                # Update dashboard with initial state
                if self.web_server:
                    self.web_server.update_state({
                        'mode': self.sdr.mode.value,
                        'status': 'initialized'
                    })
            
            logger.info("Platform initialized successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            return False
    
    def _init_mobile_mode(self):
        """Initialize mobile mode components."""
        # Spectrum scanner
        scan_config = self.config.hardware_config.get('scanning', {})
        self.scanner = SpectrumScanner(self.sdr, scan_config)
        self.scanner.calibrate_noise_floor()
        
        # Drone detector
        self.drone_detector = DroneDetector(self.config.bands)
    
    def _init_mobile_multi_mode(self):
        """Initialize mobile multi mode (2-4 SDRs for faster sequential scanning)."""
        # Same components as mobile but scanner knows about multiple SDRs
        scan_config = self.config.hardware_config.get('scanning', {})
        self.scanner = SpectrumScanner(self.sdr, scan_config)
        
        # Calibrate first SDR only (faster)
        logger.info("Calibrating noise floor on SDR 0...")
        self.scanner.calibrate_noise_floor()
        
        # Drone detector
        self.drone_detector = DroneDetector(self.config.bands)
        
        logger.info(f"Mobile Multi mode: {len(self.sdr.sdrs)} SDRs will divide scanning work")
    
    def _init_parallel_scan_mode(self):
        """Initialize parallel scan mode (4-SDR simultaneous scanning with DF capability)."""
        # All mobile mode components
        self._init_mobile_mode()
        
        # Parallel scanner
        scan_config = self.config.hardware_config.get('scanning', {})
        parallel_config = {
            **scan_config,
            'parallel_scan_assignments': self.config.bands.get('parallel_scan_assignments', {})
        }
        self.parallel_scanner = ParallelScanner(self.sdr, parallel_config)
        
        # Anomaly detector
        anomaly_config = self.config.hardware_config.get('anomaly_detection', {})
        self.anomaly_detector = AnomalyDetector(anomaly_config)
        
        # DF components for switching
        df_config = self.config.hardware_config.get('df_array', {})
        self.df_array = SDRArraySync(self.sdr, df_config)
        self.bearing_calc = BearingCalculator(self.df_array, df_config.get('music', {}))
        
        # Mode switcher
        self.mode_switcher = ModeSwitcher(self.sdr, self.parallel_scanner, self.df_array)
        
        logger.info("Parallel scan mode initialized with DF capability")
    
    def _init_df_mode(self):
        """Initialize direction finding mode components."""
        # All mobile mode components
        self._init_mobile_mode()
        
        # DF-specific components
        df_config = self.config.hardware_config.get('df_array', {})
        self.df_array = SDRArraySync(self.sdr, df_config)
        self.bearing_calc = BearingCalculator(self.df_array, df_config.get('music', {}))
        
        # Calibrate array
        cal_freq = df_config.get('calibration', {}).get('cal_frequency_hz', 434000000)
        logger.info(f"Calibrating DF array at {cal_freq/1e6:.3f} MHz...")
        self.df_array.calibrate_phase(cal_freq)
    
    def _init_common_components(self):
        """Initialize components common to all modes."""
        # Demodulators
        self.analog_demod = AnalogDemodulator(self.config.demod_params)
        self.digital_demod = DigitalDemodulator(self.config.demod_params)
        
        # Logger
        recording_config = self.config.hardware_config.get('recording', {})
        self.logger = SignalLogger(recording_config)
        
        # Mapper
        self.mapper = BearingMapper()
    
    def run(self):
        """Run the platform main loop."""
        if not self.initialize():
            logger.error("Initialization failed")
            return
        
        self.running = True
        logger.info("Starting main loop...")
        
        # Start background threads based on mode
        if self.sdr.mode in [OperatingMode.MOBILE, OperatingMode.MOBILE_MULTI]:
            scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
            scan_thread.start()
        elif self.sdr.mode == OperatingMode.PARALLEL_SCAN:
            parallel_thread = threading.Thread(target=self._parallel_scan_loop, daemon=True)
            parallel_thread.start()
        elif self.sdr.mode == OperatingMode.DF:
            df_thread = threading.Thread(target=self._df_loop, daemon=True)
            df_thread.start()
        
        # Main monitoring loop
        try:
            while self.running:
                self._update_status()
                time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        
        finally:
            self.stop()
    
    def _scan_loop(self):
        """Background scanning loop (mobile mode)."""
        while self.running:
            try:
                # Get scan bands from config
                bands = self.config.get_scan_bands()
                
                logger.info("Starting spectrum scan...")
                self.scan_count += 1
                results = self.scanner.scan_band_list(bands)
                
                # Process detected signals
                for band_name, signals in results.items():
                    for signal in signals:
                        self._process_signal(signal)
                
                # Wait before next scan
                time.sleep(5)
            
            except Exception as e:
                logger.error(f"Error in scan loop: {e}")
                time.sleep(10)
    
    def _parallel_scan_loop(self):
        """Background parallel scanning loop with anomaly-triggered DF."""
        if not self.parallel_scanner or not self.anomaly_detector or not self.mode_switcher:
            logger.error("Parallel scan components not initialized")
            return
        
        # Start parallel scanning
        self.parallel_scanner.start_parallel_scan()
        
        # Get config
        parallel_config = self.config.hardware_config.get('modes', {}).get('parallel_scan', {})
        enable_df = parallel_config.get('enable_df_on_anomaly', True)
        df_dwell_time = parallel_config.get('df_dwell_time_s', 3)
        max_df_per_cycle = parallel_config.get('max_df_per_cycle', 3)
        
        logger.info(f"Parallel scan loop started (DF on anomaly: {enable_df})")
        
        while self.running:
            try:
                self.scan_count += 1
                
                # Collect results from parallel scanners
                scan_results = self.parallel_scanner.get_results(timeout=0.5)
                
                if scan_results:
                    logger.debug(f"Scan #{self.scan_count}: {len(scan_results)} signals detected")
                    
                    # Check for anomalies
                    anomalies = self.anomaly_detector.check_anomalies(
                        scan_results,
                        enable_df_trigger=enable_df
                    )
                    
                    if anomalies:
                        self.anomaly_count += len(anomalies)
                        logger.info(f"Detected {len(anomalies)} anomalies")
                        
                        # Process high-priority anomalies with DF
                        df_performed = 0
                        for anomaly in anomalies:
                            if not self.running:
                                break
                            
                            # Process anomaly
                            self._process_anomaly(anomaly)
                            
                            # Perform DF if triggered and haven't hit limit
                            if (anomaly.get('trigger_df') and 
                                df_performed < max_df_per_cycle):
                                
                                self._perform_df_on_anomaly(anomaly, df_dwell_time)
                                df_performed += 1
                    
                    # Process all signals for logging/dashboard
                    for signal in scan_results:
                        self._process_signal(signal)
                
                # Brief pause
                time.sleep(0.1)
            
            except Exception as e:
                logger.error(f"Error in parallel scan loop: {e}")
                time.sleep(1)
        
        # Cleanup
        self.parallel_scanner.stop_parallel_scan()
    
    def _perform_df_on_anomaly(self, anomaly: Dict[str, Any], dwell_time: float):
        """Perform DF operation on detected anomaly.
        
        Args:
            anomaly: Anomaly dictionary
            dwell_time: How long to spend in DF mode
        """
        try:
            freq = anomaly['frequency_hz']
            logger.info(f"Performing DF on anomaly: {freq/1e6:.3f} MHz")
            
            # Switch to DF mode
            if not self.mode_switcher.switch_to_df(freq):
                logger.error("Failed to switch to DF mode")
                return
            
            # Brief stabilization
            time.sleep(0.5)
            
            # Calculate bearing
            bearing = self.bearing_calc.calculate_bearing(freq)
            
            if bearing:
                self.df_count += 1
                logger.info(
                    f"DF result: {bearing['bearing_degrees']:.1f}° "
                    f"(confidence: {bearing['confidence']:.2f})"
                )
                
                # Log with bearing
                if self.logger:
                    self.logger.log_signal_detection(anomaly, bearing=bearing)
                
                # Update dashboard
                if self.web_server:
                    self.web_server.add_bearing(bearing)
            
            # Dwell in DF mode
            time.sleep(dwell_time)
            
            # Switch back to parallel scan
            self.mode_switcher.switch_to_parallel()
            
        except Exception as e:
            logger.error(f"Error performing DF on anomaly: {e}")
            # Ensure we return to parallel scan
            if self.mode_switcher:
                self.mode_switcher.force_parallel_scan()
    
    def _process_anomaly(self, anomaly: Dict[str, Any]):
        """Process a detected anomaly.
        
        Args:
            anomaly: Anomaly dictionary
        """
        try:
            logger.warning(
                f"ANOMALY: {anomaly['frequency_hz']/1e6:.3f} MHz, "
                f"{anomaly['power_dbm']:.1f} dBm, "
                f"reasons: {', '.join(anomaly['reasons'])}"
            )
            
            # Update dashboard
            if self.web_server:
                self.web_server.add_signal({
                    **anomaly,
                    'anomaly': True,
                    'priority': anomaly.get('priority', 0)
                })
        
        except Exception as e:
            logger.error(f"Error processing anomaly: {e}")
    
    def _df_loop(self):
        """Background direction finding loop."""
        if not self.bearing_calc:
            return
        
        while self.running:
            try:
                # Get recent signals to calculate bearings for
                # This is a simplified version - in practice you'd maintain
                # a list of signals of interest
                time.sleep(10)  # DF calculations every 10 seconds
            
            except Exception as e:
                logger.error(f"Error in DF loop: {e}")
                time.sleep(10)
    
    def _process_signal(self, signal_hit):
        """Process a detected signal."""
        try:
            # Check for drone signatures
            if self.drone_detector:
                drone_result = self.drone_detector.analyze_signal(signal_hit)
                if drone_result:
                    logger.warning(f"DRONE DETECTED: {drone_result['signature']}")
                    
                    # Update web dashboard
                    if self.web_server:
                        self.web_server.add_signal({
                            **signal_hit.to_dict(),
                            'drone': True,
                            'drone_type': drone_result['signature']
                        })
            
            # Calculate bearing if in DF mode
            bearing = None
            if self.sdr.mode == OperatingMode.DF and self.bearing_calc:
                bearing = self.bearing_calc.calculate_bearing(
                    signal_hit.frequency_hz
                )
                
                if bearing and self.web_server:
                    self.web_server.add_bearing(bearing)
            
            # Log signal
            if self.logger:
                self.logger.log_signal_detection(
                    signal_hit,
                    bearing=bearing
                )
            
            # Update dashboard
            if self.web_server:
                self.web_server.add_signal(signal_hit.to_dict())
        
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
    
    def _update_status(self):
        """Update platform status."""
        try:
            # Update GPS
            if self.logger:
                gps = self.logger.get_gps_position()
                if gps and self.web_server:
                    self.web_server.update_gps(gps)
        
        except Exception as e:
            logger.error(f"Error updating status: {e}")
    
    def stop(self):
        """Stop the platform."""
        logger.info("Stopping platform...")
        self.running = False
        
        # Stop parallel scanner if running
        if self.parallel_scanner:
            self.parallel_scanner.stop_parallel_scan()
        
        # Stop demodulators
        if self.analog_demod:
            self.analog_demod.stop_demodulation()
        if self.digital_demod:
            self.digital_demod.stop_demodulation()
        
        # Close SDR
        if self.sdr:
            self.sdr.close()
        
        # Print statistics
        logger.info(f"Session statistics:")
        logger.info(f"  Scan cycles: {self.scan_count}")
        logger.info(f"  Anomalies detected: {self.anomaly_count}")
        logger.info(f"  DF operations: {self.df_count}")
        
        logger.info("Platform stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='SDR SIGINT Platform - Dual-mode signal intelligence system'
    )
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration directory'
    )
    parser.add_argument(
        '--mode',
        choices=['mobile', 'mobile_multi', 'parallel_scan', 'df', 'auto'],
        default='auto',
        help='Force operating mode (default: auto-detect)'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create and run platform
    platform = SDRPlatform(config_dir=args.config)
    platform.run()


if __name__ == '__main__':
    main()

