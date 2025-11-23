#!/usr/bin/env python3
"""
433 MHz Scanner - Specialized for European ISM band
Optimized for car remotes, weather stations, wireless sensors
"""

import sys
import time
import os
import numpy as np
from rtlsdr import RtlSdr
from collections import defaultdict
from datetime import datetime

class Scanner433:
    def __init__(self):
        self.sdr = None
        self.baseline = {}
        
        # Output directories
        self.output_dir = "recordings"
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(f"{self.output_dir}/audio", exist_ok=True)
        os.makedirs(f"{self.output_dir}/logs", exist_ok=True)
        
        # 433 MHz ISM Band - Common frequencies
        self.scan_freqs = [
            433.050e6,  # Lower edge
            433.075e6,
            433.100e6,
            433.125e6,
            433.150e6,
            433.175e6,
            433.200e6,
            433.225e6,
            433.250e6,
            433.275e6,
            433.300e6,
            433.325e6,
            433.350e6,
            433.375e6,
            433.400e6,
            433.425e6,
            433.450e6,
            433.475e6,
            433.500e6,
            433.525e6,
            433.550e6,
            433.575e6,
            433.600e6,
            433.625e6,
            433.650e6,
            433.675e6,
            433.700e6,
            433.725e6,
            433.750e6,
            433.775e6,
            433.800e6,
            433.825e6,
            433.850e6,
            433.875e6,
            433.900e6,  # Very common (433.92 MHz)
            433.920e6,  # Standard channel
            433.925e6,
            433.950e6,
            433.975e6,
            434.000e6,
            434.025e6,
            434.050e6,
            434.075e6,
            434.100e6,
            434.125e6,
            434.150e6,
            434.175e6,
            434.200e6,
            434.225e6,
            434.250e6,
            434.275e6,
            434.300e6,
            434.325e6,
            434.350e6,
            434.375e6,
            434.400e6,
            434.425e6,
            434.450e6,
            434.475e6,
            434.500e6,
            434.525e6,
            434.550e6,
            434.575e6,
            434.600e6,
            434.625e6,
            434.650e6,
            434.675e6,
            434.700e6,
            434.725e6,
            434.750e6,  # Upper edge
            434.775e6,
            434.790e6,
        ]
        
    def init_sdr(self):
        """Initialize RTL-SDR"""
        try:
            print("Initializing RTL-SDR for 433 MHz...", end='', flush=True)
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
            time.sleep(0.03)  # Shorter settle time for ISM
            samples = self.sdr.read_samples(128 * 1024)
            power = 10 * np.log10(np.mean(np.abs(samples)**2))
            return power
        except Exception as e:
            return None
    
    def build_baseline(self):
        """Quick baseline - 3 passes"""
        print("\n" + "="*70)
        print("BUILDING 433 MHz BASELINE")
        print("="*70)
        print(f"Scanning {len(self.scan_freqs)} frequencies (433.05-434.79 MHz)")
        print("Common devices: Car remotes, weather stations, doorbells, sensors")
        
        all_readings = defaultdict(list)
        
        for pass_num in range(3):
            print(f"\nPass {pass_num + 1}/3:", end='', flush=True)
            for freq in self.scan_freqs:
                power = self.scan_frequency(freq)
                if power:
                    all_readings[freq].append(power)
                if len(all_readings) % 10 == 0:
                    print('.', end='', flush=True)
            print(" done")
        
        # Calculate baseline
        for freq, powers in all_readings.items():
            self.baseline[freq] = {
                'mean': np.mean(powers),
                'std': np.std(powers),
                'max': np.max(powers),
            }
        
        # Show top signals
        print("\n" + "="*70)
        print("TOP 10 STRONGEST SIGNALS IN 433 MHz BAND")
        print("="*70)
        sorted_sigs = sorted(self.baseline.items(), key=lambda x: x[1]['mean'], reverse=True)[:10]
        
        print(f"{'Freq (MHz)':<12} {'Power (dBm)':<12} {'Std Dev':<10}")
        print("-"*70)
        for freq, stats in sorted_sigs:
            print(f"{freq/1e6:<12.3f} {stats['mean']:<12.1f} {stats['std']:<10.2f}")
        
        print(f"\nBaseline complete: {len(self.baseline)} frequencies")
        return True
    
    def record_signal(self, freq, duration=10):
        """Record raw IQ samples"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Filenames
        iq_file = f"{self.output_dir}/audio/ISM433_{freq/1e6:.3f}MHz_{timestamp}.npy"
        log_file = f"{self.output_dir}/logs/signal_log.txt"
        
        print(f"\n{'='*70}")
        print(f"RECORDING: {freq/1e6:.3f} MHz (433 MHz ISM)")
        print(f"Duration: {duration} seconds")
        print(f"{'='*70}")
        
        # Log to file
        with open(log_file, 'a') as f:
            f.write(f"{timestamp},{freq},ISM433,recording_start\n")
        
        try:
            # Capture IQ samples directly
            print(f"Capturing raw IQ samples...")
            self.sdr.center_freq = freq
            time.sleep(0.1)
            
            # Record for specified duration
            samples_per_sec = int(self.sdr.sample_rate)
            total_samples = samples_per_sec * duration
            
            print(f"Reading {total_samples / 1e6:.1f}M samples @ {samples_per_sec/1e6:.1f} Msps...")
            samples = self.sdr.read_samples(total_samples)
            
            # Save as numpy array
            np.save(iq_file, samples)
            
            size = os.path.getsize(iq_file) / (1024 * 1024)  # MB
            print(f"SUCCESS! IQ recording saved: {iq_file}")
            print(f"File size: {size:.1f} MB")
            
            with open(log_file, 'a') as f:
                f.write(f"{timestamp},{freq},ISM433,iq_complete,{size:.1f}MB\n")
                
        except Exception as e:
            print(f"RECORDING ERROR: {e}")
            import traceback
            traceback.print_exc()
            with open(log_file, 'a') as f:
                f.write(f"{timestamp},{freq},ISM433,error,{str(e)}\n")
    
    def monitor_with_recording(self):
        """Monitor for anomalies and record strong signals"""
        print("\n" + "="*70)
        print("MONITORING 433 MHz - Will record strong signals")
        print("Expected devices:")
        print("  - Car key fobs (European vehicles)")
        print("  - Weather stations")
        print("  - Wireless doorbells")
        print("  - Security sensors")
        print("  - Remote controls")
        print("="*70)
        
        scan_num = 0
        
        try:
            while True:
                scan_num += 1
                print(f"\n[Scan #{scan_num}] {time.strftime('%H:%M:%S')} - ", end='', flush=True)
                
                strong_signals = []
                
                for freq in self.scan_freqs:
                    power = self.scan_frequency(freq)
                    if power:
                        baseline = self.baseline[freq]
                        delta = power - baseline['mean']
                        
                        # Check for strong anomaly (worth recording)
                        if delta > 15:
                            strong_signals.append({
                                'freq': freq,
                                'power': power,
                                'baseline': baseline['mean'],
                                'delta': delta
                            })
                
                if strong_signals:
                    print(f"*** {len(strong_signals)} STRONG SIGNAL(S) - RECORDING ***")
                    
                    for sig in strong_signals:
                        print(f"  433 MHz: {sig['freq']/1e6:.3f} MHz: {sig['power']:.1f} dBm (+{sig['delta']:.1f} dB)")
                        
                        # Record this signal
                        self.record_signal(sig['freq'], duration=10)
                        
                else:
                    print("Monitoring - no strong signals")
                
                time.sleep(3)
                
        except KeyboardInterrupt:
            print(f"\n\nStopped after {scan_num} scans")
    
    def close(self):
        if self.sdr:
            self.sdr.close()

def main():
    print("\n" + "#"*70)
    print("# ReconRaven - 433 MHz ISM Scanner")
    print("# European/Asian ISM band monitoring")
    print("# Press CTRL+C to stop")
    print("#"*70)
    
    scanner = Scanner433()
    
    try:
        if not scanner.init_sdr():
            sys.exit(1)
        
        scanner.build_baseline()
        scanner.monitor_with_recording()
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scanner.close()
        print("\nSDR closed. Check 'recordings/' folder for captured signals!")

if __name__ == "__main__":
    main()

