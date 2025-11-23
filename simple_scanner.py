#!/usr/bin/env python3
"""
Simple Spectrum Scanner with Anomaly Detection
Scans real RF spectrum, builds baseline, detects anomalies
"""

import sys
import time
import numpy as np
from rtlsdr import RtlSdr
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleScanner:
    def __init__(self):
        self.sdr = None
        self.baseline = {}  # {freq: mean_power}
        self.signal_history = defaultdict(list)  # {freq: [power_readings]}
        
        # Interesting frequency bands (Hz)
        self.scan_bands = [
            {'name': '2m Amateur', 'start': 144e6, 'end': 148e6, 'step': 100e3},
            {'name': '70cm Amateur', 'start': 420e6, 'end': 450e6, 'step': 100e3},
            {'name': 'ISM 433 MHz', 'start': 433e6, 'end': 435e6, 'step': 50e3},
            {'name': 'ISM 915 MHz', 'start': 902e6, 'end': 928e6, 'step': 100e3},
        ]
        
    def init_sdr(self):
        """Initialize the RTL-SDR"""
        try:
            self.sdr = RtlSdr()
            self.sdr.sample_rate = 2.4e6  # 2.4 MHz
            self.sdr.gain = 'auto'
            logger.info("RTL-SDR initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize SDR: {e}")
            return False
    
    def scan_frequency(self, freq):
        """Scan a single frequency and return power level"""
        try:
            self.sdr.center_freq = freq
            time.sleep(0.05)  # Let SDR settle
            
            # Read samples
            samples = self.sdr.read_samples(256 * 1024)
            
            # Calculate power (dBm)
            power = 10 * np.log10(np.mean(np.abs(samples)**2))
            
            return power
        except Exception as e:
            logger.warning(f"Error scanning {freq/1e6:.3f} MHz: {e}")
            return None
    
    def build_baseline(self, num_passes=3):
        """Build baseline by scanning all bands multiple times"""
        print("\n" + "="*60)
        print("BUILDING BASELINE - Scanning your RF environment...")
        print("="*60)
        
        all_readings = defaultdict(list)
        
        for pass_num in range(num_passes):
            print(f"\nBaseline Pass {pass_num + 1}/{num_passes}...")
            
            for band in self.scan_bands:
                print(f"  Scanning {band['name']}...", end='', flush=True)
                
                freq = band['start']
                scanned = 0
                while freq <= band['end']:
                    power = self.scan_frequency(freq)
                    if power is not None:
                        all_readings[freq].append(power)
                        scanned += 1
                    freq += band['step']
                
                print(f" {scanned} frequencies")
        
        # Calculate baseline (average power per frequency)
        print("\nCalculating baseline statistics...")
        for freq, powers in all_readings.items():
            self.baseline[freq] = {
                'mean': np.mean(powers),
                'std': np.std(powers),
                'max': np.max(powers)
            }
        
        # Find and display strongest baseline signals
        print("\n" + "="*60)
        print("BASELINE ESTABLISHED - Top 10 Signals:")
        print("="*60)
        
        sorted_signals = sorted(self.baseline.items(), 
                               key=lambda x: x[1]['mean'], 
                               reverse=True)[:10]
        
        for freq, stats in sorted_signals:
            print(f"  {freq/1e6:>8.3f} MHz: {stats['mean']:>6.1f} dBm (std: {stats['std']:.1f})")
        
        print(f"\nBaseline contains {len(self.baseline)} frequencies")
        return len(self.baseline) > 0
    
    def detect_anomalies(self):
        """Scan and detect anomalies compared to baseline"""
        print("\n" + "="*60)
        print("MONITORING FOR ANOMALIES - Press Ctrl+C to stop")
        print("="*60)
        
        scan_count = 0
        anomaly_count = 0
        
        try:
            while True:
                scan_count += 1
                print(f"\n[Scan #{scan_count}] {time.strftime('%H:%M:%S')}")
                
                anomalies_this_scan = []
                
                for band in self.scan_bands:
                    freq = band['start']
                    while freq <= band['end']:
                        # Only scan frequencies in our baseline
                        if freq in self.baseline:
                            power = self.scan_frequency(freq)
                            
                            if power is not None:
                                baseline_stats = self.baseline[freq]
                                
                                # Check for anomalies
                                # 1. Power surge (>10 dB above baseline mean)
                                if power > baseline_stats['mean'] + 10:
                                    anomalies_this_scan.append({
                                        'type': 'POWER SURGE',
                                        'freq': freq,
                                        'power': power,
                                        'baseline': baseline_stats['mean'],
                                        'delta': power - baseline_stats['mean']
                                    })
                                
                                # 2. Strong signal (>3 std devs above mean)
                                elif power > baseline_stats['mean'] + (3 * baseline_stats['std']):
                                    anomalies_this_scan.append({
                                        'type': 'STRONG SIGNAL',
                                        'freq': freq,
                                        'power': power,
                                        'baseline': baseline_stats['mean'],
                                        'delta': power - baseline_stats['mean']
                                    })
                                
                                # Update signal history
                                self.signal_history[freq].append(power)
                                if len(self.signal_history[freq]) > 10:
                                    self.signal_history[freq].pop(0)
                        
                        freq += band['step']
                
                # Display anomalies
                if anomalies_this_scan:
                    anomaly_count += len(anomalies_this_scan)
                    print(f"\n  *** {len(anomalies_this_scan)} ANOMALY(IES) DETECTED ***")
                    for anom in anomalies_this_scan:
                        print(f"  [{anom['type']}] {anom['freq']/1e6:.3f} MHz")
                        print(f"    Current: {anom['power']:.1f} dBm | Baseline: {anom['baseline']:.1f} dBm | Delta: +{anom['delta']:.1f} dB")
                else:
                    print("  No anomalies detected - environment stable")
                
                print(f"  Total anomalies found: {anomaly_count}")
                
                # Brief pause between scans
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user.")
            print(f"Summary: {scan_count} scans completed, {anomaly_count} total anomalies detected")
    
    def close(self):
        """Clean up"""
        if self.sdr:
            self.sdr.close()
            logger.info("SDR closed")

def main():
    print("\n" + "#"*60)
    print("# ReconRaven - Simple Spectrum Scanner")
    print("# Real RF with Anomaly Detection")
    print("#"*60)
    
    scanner = SimpleScanner()
    
    try:
        # Initialize hardware
        if not scanner.init_sdr():
            print("\nERROR: Could not initialize RTL-SDR")
            print("Make sure no other program is using it.")
            sys.exit(1)
        
        # Build baseline (3 passes through all bands)
        if not scanner.build_baseline(num_passes=3):
            print("\nERROR: Failed to build baseline")
            sys.exit(1)
        
        # Monitor for anomalies
        scanner.detect_anomalies()
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scanner.close()

if __name__ == "__main__":
    main()


