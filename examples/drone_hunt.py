#!/usr/bin/env python3
"""
Example: Drone Hunting
Demonstrates drone detection and tracking.
"""

import logging
import sys
import time
sys.path.insert(0, '..')

from hardware import SDRController
from scanning import SpectrumScanner, DroneDetector
from config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Run drone hunting example."""
    # Load configuration
    config = get_config()
    
    # Initialize SDR
    logger.info("Initializing SDR for drone detection...")
    sdr = SDRController(config.hardware_config.get('sdr', {}))
    
    if not sdr.initialize():
        logger.error("Failed to initialize SDR")
        return
    
    try:
        # Create scanner and drone detector
        scanner = SpectrumScanner(sdr, config.hardware_config.get('scanning', {}))
        drone_detector = DroneDetector(config.bands)
        
        # Calibrate noise floor
        logger.info("Calibrating noise floor...")
        scanner.calibrate_noise_floor()
        
        # Get drone bands
        drone_bands = config.get_drone_bands()
        logger.info(f"Monitoring {len(drone_bands)} drone bands...")
        
        # Continuous monitoring
        print(f"\n{'='*70}")
        print("DRONE HUNTING MODE - Press Ctrl+C to stop")
        print(f"{'='*70}\n")
        
        scan_count = 0
        detections = 0
        
        while True:
            scan_count += 1
            logger.info(f"Scan #{scan_count}...")
            
            # Scan drone bands
            for band in drone_bands:
                if not band.get('detectable', False):
                    continue
                
                band_name = band.get('name', 'Unknown')
                start_hz = band.get('start_hz')
                end_hz = band.get('end_hz')
                
                logger.info(f"  Scanning {band_name}...")
                signals = scanner.scan_frequency_range(start_hz, end_hz)
                
                # Check each signal for drone signatures
                for signal in signals:
                    drone_result = drone_detector.analyze_signal(signal)
                    
                    if drone_result:
                        detections += 1
                        print(f"\n🚨 DRONE DETECTED! 🚨")
                        print(f"  Signature:  {drone_result['signature']}")
                        print(f"  Frequency:  {drone_result['frequency_hz']/1e6:.3f} MHz")
                        print(f"  Power:      {drone_result['power_dbm']:.1f} dBm")
                        print(f"  Confidence: {drone_result['confidence']:.2f}")
                        print(f"  Pattern:    {drone_result['pattern_type']}")
                        print(f"  Total detections: {detections}\n")
            
            # Display summary
            summary = drone_detector.get_detection_summary()
            if summary['total_detections'] > 0:
                print(f"Recent detections (last 5 min): {summary['total_detections']}")
                print(f"Signatures: {summary['signatures']}\n")
            
            # Wait before next scan
            time.sleep(2)
    
    except KeyboardInterrupt:
        print(f"\n\nStopping drone hunting...")
        print(f"Total scans: {scan_count}")
        print(f"Total detections: {detections}")
    
    finally:
        sdr.close()
        logger.info("SDR closed")


if __name__ == '__main__':
    main()

