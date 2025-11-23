#!/usr/bin/env python3
"""
Advanced Scanner with Demodulation & Recording
Can decode analog signals (FM/AM) and record ham/433 MHz traffic
"""

import sys
import time
import os
import numpy as np
import subprocess
from rtlsdr import RtlSdr
from collections import defaultdict
from datetime import datetime
import threading
import signal

class AdvancedScanner:
    def __init__(self):
        self.sdr = None
        self.baseline = {}
        self.recording = False
        self.demod_process = None
        
        # Output directories
        self.output_dir = "recordings"
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(f"{self.output_dir}/audio", exist_ok=True)
        os.makedirs(f"{self.output_dir}/logs", exist_ok=True)
        
        # Key frequencies to monitor
        self.scan_freqs = [
            # 2m Amateur repeaters
            144.0e6, 145.0e6, 146.0e6, 147.0e6, 148.0e6,
            # 70cm Amateur
            420e6, 423e6, 426e6, 429e6, 432e6, 435e6, 438e6, 441e6, 444e6, 447e6, 450e6,
            # ISM 433 MHz (remotes, sensors)
            433.05e6, 433.92e6, 434.5e6,
            # ISM 915 MHz
            915e6, 920e6, 925e6,
        ]
        
        self.band_names = {
            144e6: '2m', 145e6: '2m', 146e6: '2m', 147e6: '2m', 148e6: '2m',
            420e6: '70cm', 423e6: '70cm', 426e6: '70cm', 429e6: '70cm', 432e6: '70cm',
            435e6: '70cm', 438e6: '70cm', 441e6: '70cm', 444e6: '70cm', 447e6: '70cm', 450e6: '70cm',
            433.05e6: 'ISM433', 433.92e6: 'ISM433', 434.5e6: 'ISM433',
            915e6: 'ISM915', 920e6: 'ISM915', 925e6: 'ISM915',
        }
        
        # Signal type detection
        self.signal_types = {
            '2m': 'FM',      # Narrowband FM for ham voice
            '70cm': 'FM',    # Narrowband FM for ham voice
            'ISM433': 'ASK', # Usually ASK/OOK for remotes
            'ISM915': 'FSK', # Often FSK for data
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
            time.sleep(0.05)
            samples = self.sdr.read_samples(128 * 1024)
            power = 10 * np.log10(np.mean(np.abs(samples)**2))
            return power
        except Exception as e:
            return None
    
    def build_baseline(self):
        """Quick baseline - 3 passes"""
        print("\n" + "="*70)
        print("BUILDING BASELINE")
        print("="*70)
        print(f"Scanning {len(self.scan_freqs)} frequencies x 3 passes...")
        
        all_readings = defaultdict(list)
        
        for pass_num in range(3):
            print(f"\nPass {pass_num + 1}/3:")
            for freq in self.scan_freqs:
                band = self.band_names.get(freq, '?')
                print(f"  [{band:>7}] {freq/1e6:>8.3f} MHz", end='', flush=True)
                power = self.scan_frequency(freq)
                if power:
                    all_readings[freq].append(power)
                    print(f" ... {power:>6.1f} dBm")
                else:
                    print(" ... FAIL")
            print("  Pass complete")
        
        # Calculate baseline
        for freq, powers in all_readings.items():
            self.baseline[freq] = {
                'mean': np.mean(powers),
                'std': np.std(powers),
                'max': np.max(powers),
                'band': self.band_names.get(freq, '?')
            }
        
        print(f"\nBaseline complete: {len(self.baseline)} frequencies")
        return True
    
    def record_signal(self, freq, duration=10):
        """Record raw IQ samples"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        band = self.baseline[freq]['band']
        signal_type = self.signal_types.get(band, 'FM')
        
        # Filenames
        iq_file = f"{self.output_dir}/audio/{band}_{freq/1e6:.3f}MHz_{timestamp}_{signal_type}.npy"
        log_file = f"{self.output_dir}/logs/signal_log.txt"
        
        print(f"\n{'='*70}")
        print(f"RECORDING: {freq/1e6:.3f} MHz ({band}) - {signal_type}")
        print(f"Duration: {duration} seconds")
        print(f"{'='*70}")
        
        # Log to file
        with open(log_file, 'a') as f:
            f.write(f"{timestamp},{freq},{band},{signal_type},recording_start\n")
        
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
            print(f"To replay: Use GQRX, URH, or Inspectrum")
            
            with open(log_file, 'a') as f:
                f.write(f"{timestamp},{freq},{band},{signal_type},iq_complete,{size:.1f}MB\n")
                
        except Exception as e:
            print(f"RECORDING ERROR: {e}")
            import traceback
            traceback.print_exc()
            with open(log_file, 'a') as f:
                f.write(f"{timestamp},{freq},{band},{signal_type},error,{str(e)}\n")
    
    def monitor_with_recording(self):
        """Monitor for anomalies and record strong signals"""
        print("\n" + "="*70)
        print("MONITORING MODE - Will record strong signals")
        print("Commands:")
        print("  - Anomalies >15 dB above baseline = AUTO-RECORD 10 seconds")
        print("  - Press Ctrl+C to stop")
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
                                'delta': delta,
                                'band': baseline['band']
                            })
                
                if strong_signals:
                    print(f"*** {len(strong_signals)} STRONG SIGNAL(S) - RECORDING ***")
                    
                    for sig in strong_signals:
                        print(f"  [{sig['band']}] {sig['freq']/1e6:.3f} MHz: {sig['power']:.1f} dBm (+{sig['delta']:.1f} dB)")
                        
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
    print("# ReconRaven - Advanced Scanner with Recording")
    print("# Detects, demodulates, and records ham/433/915 MHz signals")
    print("#"*70)
    
    scanner = AdvancedScanner()
    
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
        print("\nSDR closed. Check 'recordings/' folder for captured audio!")

if __name__ == "__main__":
    main()

