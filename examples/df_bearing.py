#!/usr/bin/env python3
"""
Example: Direction Finding
Demonstrates DF mode with bearing calculations.
"""

import logging
import sys
sys.path.insert(0, '..')

from hardware import SDRController, OperatingMode
from direction_finding import SDRArraySync, BearingCalculator
from config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Run direction finding example."""
    # Load configuration
    config = get_config()
    
    # Initialize SDR
    logger.info("Initializing SDR in DF mode...")
    sdr = SDRController(config.hardware_config.get('sdr', {}))
    
    if not sdr.initialize():
        logger.error("Failed to initialize SDR")
        return
    
    if sdr.mode != OperatingMode.DF:
        logger.error("DF mode requires 4 SDRs. Only found {}".format(len(sdr.sdrs)))
        logger.info("Connect 4 RTL-SDR devices for DF mode")
        sdr.close()
        return
    
    try:
        # Initialize DF array
        df_config = config.hardware_config.get('df_array', {})
        df_array = SDRArraySync(sdr, df_config)
        bearing_calc = BearingCalculator(df_array, df_config.get('music', {}))
        
        # Calibrate array
        cal_freq = 434e6  # 434 MHz
        logger.info(f"Calibrating array at {cal_freq/1e6:.1f} MHz...")
        
        if not df_array.calibrate_phase(cal_freq):
            logger.error("Array calibration failed")
            return
        
        # Calculate bearing to a signal
        # In real use, you would first scan to find signals
        test_freq = 434.5e6  # 434.5 MHz
        
        logger.info(f"Calculating bearing for {test_freq/1e6:.3f} MHz...")
        bearing = bearing_calc.calculate_bearing(test_freq)
        
        if bearing:
            print(f"\n{'='*70}")
            print(f"Bearing Results")
            print(f"{'='*70}")
            print(f"  Frequency:   {bearing['frequency_hz']/1e6:.3f} MHz")
            print(f"  Bearing:     {bearing['bearing_degrees']:.1f}°")
            print(f"  Confidence:  {bearing['confidence']:.2f}")
            print(f"  Elements:    {bearing['num_elements']}")
            print(f"{'='*70}\n")
        else:
            logger.warning("Failed to calculate bearing")
    
    finally:
        sdr.close()
        logger.info("SDR closed")


if __name__ == '__main__':
    main()

