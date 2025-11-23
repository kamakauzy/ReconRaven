#!/usr/bin/env python3
"""
Quick RF Scanner - Fast baseline and anomaly detection
Scans key frequencies only for speed
"""

import sys
import time
import numpy as np
from rtlsdr import RtlSdr
from collections import defaultdict

class QuickScanner:
    def __init__(self):
        self.sdr = None
        self.baseline = {}
        
        # Quick scan: just sample key frequencies per band (not every 100 kHz)
        self.scan_freqs = [
            # 2m Amateur (sample every 1 MHz)
            144.0e6, 145.0e6, 146.0e6, 147.0e6, 148.0e6,
            # 70cm Amateur (sample every 3 MHz)
            420e6, 423e6, 426e6, 429e6, 432e6, 435e6, 438e6, 441e6, 444e6, 447e6, 450e6,
            # ISM 433 (key freqs)
            433.05e6, 433.92e6, 434.5e6,
            # ISM 915 (key freqs)
            915e6, 920e6, 925e6,
        ]
        
        self.band_names = {
            144e6: '2m', 145e6: '2m', 146e6: '2m', 147e6: '2m', 148e6: '2m',
            420e6: '70cm', 423e6: '70cm', 426e6: '70cm', 429e6: '70cm', 432e6: '70cm',
            435e6: '70cm', 438e6: '70cm', 441e6: '70cm', 444e6: '70cm', 447e6: '70cm', 450e6: '70cm',
            433.05e6: 'ISM433', 433.92e6: 'ISM433', 434.5e6: 'ISM433',
            915e6: 'ISM915', 920e6: 'ISM915', 925e6: 'ISM915',
        }
        
    def init_sdr(self):
        """Initialize RTL-SDR"""
        try:
            print("Initializing RTL-SDR...", end='', flush=True)
            self.sdr = RtlSdr()
            self.sdr.sample_rate = 2.4e6
            self.sdr.gain = 'auto'
            print(" OK")
            return True
        except Exception as e:
            print(f" FAILED: {e}")
            return False
    
    def scan_frequency(self, freq):
        """Scan single frequency, return power in dBm"""
        try:
            self.sdr.center_freq = freq
            time.sleep(0.05)  # Let tuner settle
            samples = self.sdr.read_samples(128 * 1024)  # Smaller sample for speed
            power = 10 * np.log10(np.mean(np.abs(samples)**2))
            return power
        except Exception as e:
            return None
    
    def build_baseline(self):
        """Quick baseline - scan all frequencies 3 times"""
        print("\n" + "="*70)
        print("BUILDING BASELINE")
        print("="*70)
        print(f"Scanning {len(self.scan_freqs)} key frequencies x 3 passes...")
        
        all_readings = defaultdict(list)
        total = len(self.scan_freqs) * 3
        count = 0
        
        for pass_num in range(3):
            print(f"\nPass {pass_num + 1}/3:", end='', flush=True)
            for freq in self.scan_freqs:
                power = self.scan_frequency(freq)
                if power:
                    all_readings[freq].append(power)
                count += 1
                if count % 10 == 0:
                    print('.', end='', flush=True)
            print(" done")
        
        # Calculate baseline stats
        for freq, powers in all_readings.items():
            self.baseline[freq] = {
                'mean': np.mean(powers),
                'std': np.std(powers),
                'max': np.max(powers),
                'band': self.band_names.get(freq, '?')
            }
        
        # Show top signals
        print("\n" + "="*70)
        print("TOP 10 STRONGEST BASELINE SIGNALS")
        print("="*70)
        sorted_sigs = sorted(self.baseline.items(), key=lambda x: x[1]['mean'], reverse=True)[:10]
        
        print(f"{'Freq (MHz)':<12} {'Band':<8} {'Power':<10} {'Std Dev':<10}")
        print("-"*70)
        for freq, stats in sorted_sigs:
            print(f"{freq/1e6:<12.3f} {stats['band']:<8} {stats['mean']:<10.1f} {stats['std']:<10.2f}")
        
        print(f"\nBaseline complete: {len(self.baseline)} frequencies")
        return True
    
    def monitor_anomalies(self):
        """Continuous monitoring for anomalies"""
        print("\n" + "="*70)
        print("MONITORING FOR ANOMALIES - Press Ctrl+C to stop")
        print("="*70)
        
        scan_num = 0
        total_anomalies = 0
        
        try:
            while True:
                scan_num += 1
                print(f"\n[Scan #{scan_num}] {time.strftime('%H:%M:%S')} - ", end='', flush=True)
                
                anomalies = []
                for freq in self.scan_freqs:
                    power = self.scan_frequency(freq)
                    if power:
                        baseline = self.baseline[freq]
                        
                        # Anomaly: >10 dB above baseline
                        if power > baseline['mean'] + 10:
                            anomalies.append({
                                'freq': freq,
                                'power': power,
                                'baseline': baseline['mean'],
                                'delta': power - baseline['mean'],
                                'band': baseline['band']
                            })
                        # Strong signal: >3 std devs
                        elif power > baseline['mean'] + (3 * baseline['std']):
                            anomalies.append({
                                'freq': freq,
                                'power': power,
                                'baseline': baseline['mean'],
                                'delta': power - baseline['mean'],
                                'band': baseline['band']
                            })
                
                if anomalies:
                    total_anomalies += len(anomalies)
                    print(f"*** {len(anomalies)} ANOMALY(IES) ***")
                    for a in anomalies:
                        print(f"  [{a['band']}] {a['freq']/1e6:.3f} MHz: {a['power']:.1f} dBm "
                              f"(baseline {a['baseline']:.1f}, +{a['delta']:.1f} dB)")
                else:
                    print("Clean - no anomalies")
                
                print(f"  Total anomalies so far: {total_anomalies}")
                time.sleep(3)
                
        except KeyboardInterrupt:
            print(f"\n\nStopped. Completed {scan_num} scans, detected {total_anomalies} anomalies.")
    
    def close(self):
        if self.sdr:
            self.sdr.close()

def main():
    print("\n" + "#"*70)
    print("# ReconRaven - Quick RF Scanner with Anomaly Detection")
    print("# Scanning real RF environment with your RTL-SDR V4")
    print("#"*70)
    
    scanner = QuickScanner()
    
    try:
        if not scanner.init_sdr():
            sys.exit(1)
        
        scanner.build_baseline()
        scanner.monitor_anomalies()
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scanner.close()
        print("\nSDR closed. Goodbye!")

if __name__ == "__main__":
    main()


