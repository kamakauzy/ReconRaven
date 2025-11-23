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
from database import get_db
from web.server import SDRDashboardServer

class AdvancedScanner:
    def __init__(self, dashboard_server=None):
        self.sdr = None
        self.baseline = {}
        self.recording = False
        self.demod_process = None
        self.db = get_db()
        self.dashboard = dashboard_server
        
        # Output directories
        self.output_dir = "recordings"
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(f"{self.output_dir}/audio", exist_ok=True)
        os.makedirs(f"{self.output_dir}/logs", exist_ok=True)
        
        # Comprehensive frequency scanning - ALL bands
        self.scan_freqs = []
        
        # 2m Amateur Band (144-148 MHz) - every 100 kHz
        for freq in range(144000000, 148000000, 100000):
            self.scan_freqs.append(freq)
        
        # 70cm Amateur Band (420-450 MHz) - every 100 kHz  
        for freq in range(420000000, 450000000, 100000):
            self.scan_freqs.append(freq)
        
        # 433 MHz ISM Band (433.05-434.79 MHz) - every 25 kHz for high resolution
        for freq in range(433050000, 434790000, 25000):
            self.scan_freqs.append(freq)
        
        # 915 MHz ISM Band (902-928 MHz) - every 100 kHz
        for freq in range(902000000, 928000000, 100000):
            self.scan_freqs.append(freq)
        
        # Dynamically determine band names
        self.band_names = {}
        
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
    
    def get_band_name(self, freq):
        """Determine band name from frequency"""
        if 144e6 <= freq <= 148e6:
            return '2m'
        elif 420e6 <= freq <= 450e6:
            return '70cm'
        elif 433e6 <= freq <= 435e6:
            return 'ISM433'
        elif 902e6 <= freq <= 928e6:
            return 'ISM915'
        else:
            return 'Unknown'
    
    def scan_frequency(self, freq):
        """Scan single frequency, return power in dBm"""
        try:
            self.sdr.center_freq = freq
            time.sleep(0.03)  # Faster scanning
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
            print(f"\nPass {pass_num + 1}/3:", end='', flush=True)
            count = 0
            for freq in self.scan_freqs:
                power = self.scan_frequency(freq)
                if power:
                    all_readings[freq].append(power)
                count += 1
                if count % 50 == 0:
                    print('.', end='', flush=True)
            print(f" done ({count} frequencies)")
        
        # Calculate baseline and save to database
        for freq, powers in all_readings.items():
            baseline_data = {
                'mean': np.mean(powers),
                'std': np.std(powers),
                'max': np.max(powers),
                'band': self.get_band_name(freq)
            }
            self.baseline[freq] = baseline_data
            
            # Add to database
            self.db.add_baseline_frequency(
                freq=freq,
                band=baseline_data['band'],
                power=baseline_data['mean'],
                std=baseline_data['std']
            )
        
        print(f"\nBaseline complete: {len(self.baseline)} frequencies")
        return True
    
    def record_signal(self, freq, duration=10):
        """Record raw IQ samples"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        band = self.get_band_name(freq)
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
            
            # Add to database
            try:
                filename = os.path.basename(iq_file)
                self.db.add_recording(
                    filename=filename,
                    freq=freq,
                    band=band,
                    duration=duration,
                    file_size_mb=size
                )
                
                # Update dashboard if connected
                if self.dashboard:
                    self.dashboard.update_state({'recording_count': self.db.get_statistics()['total_recordings']})
            except Exception as e:
                print(f"Database error: {e}")
            
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
        
        # Ensure baseline exists
        if not self.baseline:
            print("\nERROR: No baseline available. Run build_baseline() first.")
            return
        
        scan_num = 0
        
        try:
            while True:
                scan_num += 1
                print(f"\n[Scan #{scan_num}] {time.strftime('%H:%M:%S')} - ", end='', flush=True)
                
                strong_signals = []
                
                for freq in self.scan_freqs:
                    power = self.scan_frequency(freq)
                    if power and freq in self.baseline:
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
    
    # Start dashboard in background
    print("\nStarting dashboard...")
    from kill_dashboard import kill_dashboard_processes
    kill_dashboard_processes()
    time.sleep(1)
    
    dashboard = SDRDashboardServer({'host': '0.0.0.0', 'port': 5000})
    dashboard.run_threaded()
    time.sleep(2)
    
    # Load database stats
    db = get_db()
    stats = db.get_statistics()
    
    # Initialize dashboard state
    dashboard.update_state({
        'mode': 'scanning',
        'status': 'initializing',
        'baseline_count': stats['baseline_frequencies'],
        'device_count': stats['identified_devices'],
        'recording_count': stats['total_recordings'],
        'anomaly_count': stats['anomalies']
    })
    
    print(f"Dashboard: http://localhost:5000")
    print(f"Database: {stats['total_recordings']} recordings, {stats['identified_devices']} devices")
    
    # Create scanner with dashboard integration
    scanner = AdvancedScanner(dashboard_server=dashboard)
    
    try:
        if not scanner.init_sdr():
            sys.exit(1)
        
        # Build or load baseline
        if stats['baseline_frequencies'] == 0:
            print("\nNo baseline found. Building baseline...")
            scanner.build_baseline()
        else:
            print(f"\nLoading existing baseline ({stats['baseline_frequencies']} frequencies)...")
            for entry in db.get_baseline():
                scanner.baseline[entry['frequency_hz']] = {
                    'mean': entry['power_dbm'],
                    'std': entry['std_dbm'] or 5.0,
                    'max': entry['power_dbm'] + 10,
                    'band': entry['band']
                }
            print(f"Loaded {len(scanner.baseline)} frequencies")
        
        dashboard.update_state({'status': 'monitoring', 'baseline_count': len(scanner.baseline)})
        scanner.monitor_with_recording()
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scanner.close()
        dashboard.update_state({'status': 'stopped', 'mode': 'idle'})
        print("\nSDR closed. Check 'recordings/' folder for captured audio!")
        print("Dashboard still running at http://localhost:5000")

if __name__ == "__main__":
    main()

