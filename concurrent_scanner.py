#!/usr/bin/env python3
"""
Concurrent Multi-SDR Scanner
Scans multiple frequency ranges simultaneously using 4 RTL-SDRs
"""

import threading
import time
import queue
import signal
import sys
import atexit
from rtlsdr import RtlSdr
from database import get_db
import numpy as np
from datetime import datetime

class ConcurrentScanner:
    def __init__(self, num_sdrs=4):
        """Initialize concurrent scanner with multiple SDRs."""
        self.num_sdrs = num_sdrs
        self.sdrs = []
        self.threads = []
        self.result_queue = queue.Queue()
        self.running = False
        self.db = get_db()
        
        print(f"[*] Initializing {num_sdrs} RTL-SDRs for concurrent scanning...")
        
        # Register cleanup handlers
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def init_sdrs(self):
        """Initialize all SDR devices."""
        try:
            for i in range(self.num_sdrs):
                print(f"  Initializing SDR #{i}...")
                sdr = RtlSdr(device_index=i)
                sdr.sample_rate = 2.048e6
                sdr.gain = 'auto'
                self.sdrs.append(sdr)
                print(f"  ✓ SDR #{i} ready")
            
            print(f"[+] All {self.num_sdrs} SDRs initialized!")
            return True
            
        except Exception as e:
            print(f"[-] Error initializing SDRs: {e}")
            return False
    
    def scan_range(self, sdr_index, start_freq, end_freq, step=0.25e6):
        """Scan a frequency range with a specific SDR."""
        sdr = self.sdrs[sdr_index]
        thread_name = f"SDR-{sdr_index}"
        
        print(f"[{thread_name}] Starting scan: {start_freq/1e6:.2f} - {end_freq/1e6:.2f} MHz")
        
        signals_found = 0
        scan_start = time.time()
        
        try:
            freq = start_freq
            while freq <= end_freq and self.running:
                # Set center frequency
                sdr.center_freq = freq
                time.sleep(0.01)  # Let SDR settle
                
                # Read samples
                samples = sdr.read_samples(256 * 1024)
                
                # Compute FFT
                fft = np.fft.fft(samples)
                fft_mag = np.abs(fft)
                fft_mag_db = 20 * np.log10(fft_mag + 1e-10)
                
                # Find peaks
                threshold = np.mean(fft_mag_db) + 10  # 10dB above mean
                peaks = np.where(fft_mag_db > threshold)[0]
                
                if len(peaks) > 0:
                    # Found signals!
                    for peak_idx in peaks[:5]:  # Limit to top 5 peaks
                        # Calculate actual frequency
                        freq_offset = (peak_idx - len(fft)/2) * (sdr.sample_rate / len(fft))
                        actual_freq = freq + freq_offset
                        power_dbm = fft_mag_db[peak_idx] - 60  # Rough calibration
                        
                        # Determine band
                        band = self._get_band(actual_freq)
                        
                        signal_data = {
                            'sdr_index': sdr_index,
                            'frequency_hz': actual_freq,
                            'power_dbm': power_dbm,
                            'band': band,
                            'detected_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        self.result_queue.put(signal_data)
                        signals_found += 1
                
                # Move to next frequency
                freq += step
            
            scan_time = time.time() - scan_start
            print(f"[{thread_name}] ✓ Scan complete! Found {signals_found} signals in {scan_time:.1f}s")
            
        except Exception as e:
            print(f"[{thread_name}] ❌ Error: {e}")
    
    def _get_band(self, freq_hz):
        """Determine which band a frequency belongs to."""
        if 144e6 <= freq_hz <= 148e6:
            return '2m'
        elif 420e6 <= freq_hz <= 450e6:
            return '70cm'
        elif 433e6 <= freq_hz <= 435e6:
            return 'ISM433'
        elif 902e6 <= freq_hz <= 928e6:
            return 'ISM915'
        else:
            return 'Unknown'
    
    def start_concurrent_scan(self):
        """Start concurrent scanning on all SDRs."""
        if not self.init_sdrs():
            return False
        
        # Define frequency ranges for each SDR
        # Split the spectrum across 4 SDRs
        scan_ranges = [
            (144e6, 148e6),     # SDR 0: 2m band
            (420e6, 435e6),     # SDR 1: 70cm + ISM433
            (433e6, 450e6),     # SDR 2: ISM433 + 70cm upper
            (902e6, 928e6),     # SDR 3: ISM915
        ]
        
        self.running = True
        
        print("\n🚀 Starting concurrent scan on 4 SDRs...")
        print("=" * 60)
        
        # Start a thread for each SDR
        for i, (start, end) in enumerate(scan_ranges):
            thread = threading.Thread(
                target=self.scan_range,
                args=(i, start, end),
                name=f"SDR-{i}"
            )
            thread.daemon = True
            thread.start()
            self.threads.append(thread)
        
        # Process results in main thread
        print("\n📊 Real-time signal detection:")
        print("-" * 60)
        
        try:
            while self.running:
                try:
                    signal = self.result_queue.get(timeout=1)
                    
                    # Print signal
                    print(f"[SDR-{signal['sdr_index']}] "
                          f"{signal['frequency_hz']/1e6:.4f} MHz | "
                          f"{signal['power_dbm']:.1f} dBm | "
                          f"{signal['band']}")
                    
                    # Check if anomaly (not in baseline)
                    cursor = self.db.conn.cursor()
                    cursor.execute('''
                        SELECT COUNT(*) FROM baseline 
                        WHERE ABS(frequency_hz - ?) < 100000
                    ''', (signal['frequency_hz'],))
                    
                    is_baseline = cursor.fetchone()[0] > 0
                    
                    if not is_baseline:
                        # Add to signals table as anomaly
                        cursor.execute('''
                            INSERT INTO signals 
                            (frequency_hz, power_dbm, band, is_anomaly, detected_at)
                            VALUES (?, ?, ?, 1, ?)
                        ''', (signal['frequency_hz'], signal['power_dbm'], 
                              signal['band'], signal['detected_at']))
                        self.db.conn.commit()
                    
                except queue.Empty:
                    # Check if all threads are done
                    if not any(t.is_alive() for t in self.threads):
                        break
                    continue
        
        except KeyboardInterrupt:
            print("\n⚠️  Stopping scan...")
            self.running = False
        
        # Wait for threads to finish
        for thread in self.threads:
            thread.join(timeout=2)
        
        print("\n" + "=" * 60)
        print("✅ Concurrent scan complete!")
        
        # Cleanup
        for sdr in self.sdrs:
            sdr.close()
    
    def quick_test(self):
        """Quick test to verify all 4 SDRs are working."""
        print("🔧 Quick Test: Verifying all SDRs...")
        print("-" * 60)
        
        if not self.init_sdrs():
            return False
        
        # Test each SDR by tuning to a different frequency
        test_freqs = [146e6, 433.92e6, 440e6, 915e6]
        
        for i, freq in enumerate(test_freqs):
            try:
                sdr = self.sdrs[i]
                sdr.center_freq = freq
                time.sleep(0.1)
                samples = sdr.read_samples(1024)
                power = 10 * np.log10(np.mean(np.abs(samples)**2))
                
                print(f"✓ SDR #{i}: Tuned to {freq/1e6:.2f} MHz, Power: {power:.1f} dB")
                
            except Exception as e:
                print(f"✗ SDR #{i}: ERROR - {e}")
                return False
        
        # Cleanup
        for sdr in self.sdrs:
            sdr.close()
        
        print("-" * 60)
        print("✅ All SDRs working perfectly!")
        return True
    
    def _signal_handler(self, signum, frame):
        """Handle signals for graceful shutdown"""
        print(f"\n[CLEANUP] Received signal {signum}, stopping scan...")
        self.running = False
        self.cleanup()
        sys.exit(0)
    
    def cleanup(self):
        """Clean up all SDR resources - ALWAYS called on exit"""
        try:
            print("[CLEANUP] Releasing all SDR devices...")
            self.running = False
            
            # Close all SDRs
            for i, sdr in enumerate(self.sdrs):
                try:
                    print(f"[CLEANUP] Closing SDR #{i}...")
                    sdr.close()
                except Exception as e:
                    print(f"[CLEANUP] Error closing SDR #{i}: {e}")
            
            self.sdrs = []
            print("[CLEANUP] All SDRs released!")
            
        except Exception as e:
            print(f"[CLEANUP] Error during cleanup: {e}")


if __name__ == "__main__":
    import sys
    
    scanner = ConcurrentScanner(num_sdrs=4)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        # Quick test mode
        scanner.quick_test()
    else:
        # Full concurrent scan
        scanner.start_concurrent_scan()

