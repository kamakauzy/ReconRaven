#!/usr/bin/env python3
"""
Example: Parallel Scan with Anomaly Detection
Demonstrates 4-SDR parallel scanning with automatic anomaly detection.
"""

import logging
import sys
import time
sys.path.insert(0, '..')

from hardware import SDRController, OperatingMode
from scanning import ParallelScanner, AnomalyDetector
from config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Run parallel scan example."""
    # Load configuration
    config = get_config()
    
    # Initialize SDR
    logger.info("Initializing SDR array for parallel scanning...")
    sdr = SDRController(config.hardware_config.get('sdr', {}))
    
    if not sdr.initialize():
        logger.error("Failed to initialize SDR")
        return
    
    if sdr.mode != OperatingMode.PARALLEL_SCAN:
        logger.error(f"Parallel scan requires 4 SDRs. Detected: {len(sdr.sdrs)}")
        logger.info("Connect 4 RTL-SDR devices for parallel scan mode")
        sdr.close()
        return
    
    try:
        # Initialize parallel scanner
        scan_config = config.hardware_config.get('scanning', {})
        parallel_config = {
            **scan_config,
            'parallel_scan_assignments': config.bands.get('parallel_scan_assignments', {})
        }
        scanner = ParallelScanner(sdr, parallel_config)
        
        # Initialize anomaly detector
        anomaly_config = config.hardware_config.get('anomaly_detection', {})
        detector = AnomalyDetector(anomaly_config)
        
        # Get coverage status
        coverage = scanner.get_coverage_status()
        
        print(f"\n{'='*70}")
        print(f"Parallel Scan Configuration")
        print(f"{'='*70}")
        print(f"Number of SDRs: {coverage['num_sdrs']}")
        print(f"\nBand Assignments:")
        for band_info in coverage['bands_covered']:
            print(f"  SDR{band_info['sdr']}: {band_info['band']}")
            print(f"    Range: {band_info['start_mhz']:.2f} - {band_info['end_mhz']:.2f} MHz")
            print(f"    Priority: {band_info['priority']}")
        print(f"{'='*70}\n")
        
        # Start parallel scanning
        logger.info("Starting parallel scan...")
        scanner.start_parallel_scan()
        
        # Monitor for signals
        print("Monitoring signals (Press Ctrl+C to stop)...\n")
        
        cycle = 0
        total_signals = 0
        total_anomalies = 0
        
        try:
            while True:
                cycle += 1
                
                # Get scan results
                results = scanner.get_results(timeout=0.5)
                
                if results:
                    total_signals += len(results)
                    print(f"\n[Cycle #{cycle}] Detected {len(results)} signals:")
                    
                    # Display signals
                    for i, signal in enumerate(results[:5], 1):  # Show first 5
                        print(f"  {i}. {signal['frequency_hz']/1e6:.3f} MHz | "
                              f"{signal['power_dbm']:.1f} dBm | "
                              f"SDR{signal['sdr_index']} | "
                              f"{signal['band_name']}")
                    
                    if len(results) > 5:
                        print(f"  ... and {len(results)-5} more")
                    
                    # Check for anomalies
                    anomalies = detector.check_anomalies(results)
                    
                    if anomalies:
                        total_anomalies += len(anomalies)
                        print(f"\n  🚨 ANOMALIES DETECTED: {len(anomalies)}")
                        
                        for anomaly in anomalies[:3]:  # Show top 3
                            print(f"    • {anomaly['frequency_hz']/1e6:.3f} MHz | "
                                  f"{anomaly['power_dbm']:.1f} dBm | "
                                  f"Priority: {anomaly['priority']} | "
                                  f"Reasons: {', '.join(anomaly['reasons'])}")
                            
                            if anomaly.get('trigger_df'):
                                print(f"      → Would trigger DF operation")
                
                # Show statistics every 10 cycles
                if cycle % 10 == 0:
                    stats = detector.get_statistics()
                    print(f"\n--- Statistics (Cycle #{cycle}) ---")
                    print(f"Total signals: {total_signals}")
                    print(f"Total anomalies: {total_anomalies}")
                    print(f"Tracked signals: {stats['tracked_signals']}")
                    print(f"Persistent signals: {stats['persistent_signals']}")
                
                time.sleep(0.5)
        
        except KeyboardInterrupt:
            print("\n\nStopping parallel scan...")
            
            # Final statistics
            stats = detector.get_statistics()
            print(f"\n{'='*70}")
            print(f"Final Statistics")
            print(f"{'='*70}")
            print(f"Scan cycles: {cycle}")
            print(f"Total signals detected: {total_signals}")
            print(f"Total anomalies: {total_anomalies}")
            print(f"Tracked signals: {stats['tracked_signals']}")
            print(f"Persistent signals: {stats['persistent_signals']}")
            
            if stats['persistent_list']:
                print(f"\nTop Persistent Signals:")
                for i, sig in enumerate(stats['persistent_list'][:5], 1):
                    print(f"  {i}. {sig['frequency_hz']/1e6:.3f} MHz | "
                          f"Avg: {sig['avg_power_dbm']:.1f} dBm | "
                          f"Detections: {sig['detections']}")
            
            print(f"{'='*70}\n")
    
    finally:
        scanner.stop_parallel_scan()
        sdr.close()
        logger.info("SDR closed")


if __name__ == '__main__':
    main()

