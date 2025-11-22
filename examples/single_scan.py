#!/usr/bin/env python3
"""
Example: Single Spectrum Scan
Demonstrates mobile mode scanning of frequency bands.
"""

import logging
import sys
sys.path.insert(0, '..')

from hardware import SDRController
from scanning import SpectrumScanner
from config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Run a single spectrum scan."""
    # Load configuration
    config = get_config()
    
    # Initialize SDR
    logger.info("Initializing SDR...")
    sdr = SDRController(config.hardware_config.get('sdr', {}))
    
    if not sdr.initialize():
        logger.error("Failed to initialize SDR")
        return
    
    try:
        # Create scanner
        scanner = SpectrumScanner(sdr, config.hardware_config.get('scanning', {}))
        
        # Calibrate noise floor
        logger.info("Calibrating noise floor...")
        scanner.calibrate_noise_floor()
        
        # Scan 2m amateur band
        logger.info("Scanning 2m amateur band (144-148 MHz)...")
        signals = scanner.scan_frequency_range(144e6, 148e6)
        
        # Display results
        print(f"\n{'='*70}")
        print(f"Scan Results: {len(signals)} signals detected")
        print(f"{'='*70}")
        
        for i, signal in enumerate(signals, 1):
            print(f"\nSignal {i}:")
            print(f"  Frequency: {signal.frequency_hz/1e6:.6f} MHz")
            print(f"  Power:     {signal.power_dbm:.1f} dBm")
            print(f"  Bandwidth: {signal.bandwidth_hz/1e3:.1f} kHz")
            print(f"  Confidence: {signal.confidence:.2f}")
        
        print(f"\n{'='*70}")
    
    finally:
        sdr.close()
        logger.info("SDR closed")


if __name__ == '__main__':
    main()

