#!/usr/bin/env python3
"""
RF Signal Fingerprinting Tool
Identifies specific brands, models, and device types from RF signatures
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
from collections import Counter
import os

class SignalFingerprinter:
    def __init__(self, filepath):
        self.filepath = filepath
        self.samples = None
        self.sample_rate = 2.4e6
        self.fingerprint = {
            'frequency': None,
            'modulation': None,
            'bit_rate': None,
            'burst_count': 0,
            'burst_duration_ms': [],
            'burst_spacing_ms': [],
            'preamble': None,
            'data_length': None,
            'manchester': False,
            'carrier_offset': None,
            'bandwidth': None
        }
        
        # Extract frequency from filename
        self.frequency = self._extract_freq()
        
    def _extract_freq(self):
        """Extract frequency from filename"""
        import re
        match = re.search(r'(\d+\.\d+)MHz', self.filepath)
        if match:
            return float(match.group(1))
        return None
        
    def load(self):
        """Load IQ samples (only first 2 seconds for speed)"""
        print("Loading IQ samples...", end='', flush=True)
        # Only load first 5M samples (2 seconds) for faster analysis
        all_samples = np.load(self.filepath)
        self.samples = all_samples[:5000000]  # 2 seconds at 2.4 Msps
        print(f" OK ({len(self.samples):,} samples, first 2 seconds)")
        
    def analyze_bursts(self):
        """Detailed burst analysis"""
        print("\n" + "="*70)
        print("BURST PATTERN ANALYSIS")
        print("="*70)
        
        envelope = np.abs(self.samples)
        window = int(self.sample_rate * 0.0001)
        envelope_smooth = np.convolve(envelope, np.ones(window)/window, mode='same')
        
        threshold = np.mean(envelope_smooth) + 3*np.std(envelope_smooth)
        above_threshold = envelope_smooth > threshold
        
        transitions = np.diff(above_threshold.astype(int))
        burst_starts = np.where(transitions == 1)[0]
        burst_ends = np.where(transitions == -1)[0]
        
        if len(burst_starts) > 0 and len(burst_ends) > 0:
            if burst_ends[0] < burst_starts[0]:
                burst_ends = burst_ends[1:]
            
            # Calculate burst durations
            for i in range(min(len(burst_starts), len(burst_ends))):
                duration = (burst_ends[i] - burst_starts[i]) / self.sample_rate * 1000
                if duration > 1:  # Filter noise
                    self.fingerprint['burst_duration_ms'].append(duration)
            
            # Calculate burst spacing (time between bursts)
            for i in range(len(burst_starts) - 1):
                spacing = (burst_starts[i+1] - burst_ends[i]) / self.sample_rate * 1000
                if spacing > 0:
                    self.fingerprint['burst_spacing_ms'].append(spacing)
            
            self.fingerprint['burst_count'] = len(self.fingerprint['burst_duration_ms'])
            
            print(f"Total bursts: {self.fingerprint['burst_count']}")
            
            if self.fingerprint['burst_duration_ms']:
                avg_duration = np.mean(self.fingerprint['burst_duration_ms'])
                std_duration = np.std(self.fingerprint['burst_duration_ms'])
                print(f"Burst duration: {avg_duration:.2f} ± {std_duration:.2f} ms")
                
            if self.fingerprint['burst_spacing_ms']:
                avg_spacing = np.mean(self.fingerprint['burst_spacing_ms'])
                print(f"Burst spacing: {avg_spacing:.2f} ms (time between transmissions)")
        
    def analyze_modulation(self):
        """Detailed modulation analysis"""
        print("\n" + "="*70)
        print("MODULATION FINGERPRINTING")
        print("="*70)
        
        magnitude = np.abs(self.samples[:100000])  # Use first portion
        phase = np.angle(self.samples[:100000])
        inst_freq = np.diff(np.unwrap(phase))
        
        # Amplitude statistics
        mag_std = np.std(magnitude)
        mag_range = np.max(magnitude) - np.min(magnitude)
        
        # Frequency statistics
        freq_std = np.std(inst_freq)
        
        # Carrier offset (center frequency error)
        fft = np.fft.fftshift(np.fft.fft(self.samples[:4096]))
        freqs = np.fft.fftshift(np.fft.fftfreq(4096, 1/self.sample_rate))
        peak_idx = np.argmax(np.abs(fft))
        carrier_offset = freqs[peak_idx]
        
        # 3dB bandwidth
        power_spectrum = np.abs(fft)**2
        peak_power = np.max(power_spectrum)
        half_power = peak_power / 2
        above_half = power_spectrum > half_power
        bandwidth = np.sum(above_half) * (self.sample_rate / 4096)
        
        self.fingerprint['carrier_offset'] = carrier_offset
        self.fingerprint['bandwidth'] = bandwidth
        
        print(f"Carrier offset: {carrier_offset/1e3:.2f} kHz")
        print(f"3dB Bandwidth: {bandwidth/1e3:.1f} kHz")
        print(f"Amplitude modulation depth: {mag_range:.4f}")
        print(f"Frequency deviation: {freq_std:.4f}")
        
        # Classify modulation
        if mag_std > 0.05 and freq_std < 0.3:
            self.fingerprint['modulation'] = 'OOK/ASK'
            print(">>> Modulation: OOK/ASK (On-Off Keying)")
        elif freq_std > 0.5:
            self.fingerprint['modulation'] = 'FSK'
            print(">>> Modulation: FSK (Frequency Shift Keying)")
        else:
            self.fingerprint['modulation'] = 'Unknown'
            
    def analyze_bit_rate(self):
        """Estimate bit rate with high precision"""
        print("\n" + "="*70)
        print("BIT RATE ANALYSIS")
        print("="*70)
        
        envelope = np.abs(self.samples[:500000])
        
        # High-pass filter
        b, a = signal.butter(4, 1000, 'highpass', fs=self.sample_rate)
        envelope_filt = signal.filtfilt(b, a, envelope)
        
        # Autocorrelation
        autocorr = np.correlate(envelope_filt, envelope_filt, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        
        # Find peaks
        peaks, properties = signal.find_peaks(autocorr[:int(self.sample_rate*0.01)], 
                                             height=np.max(autocorr)*0.1,
                                             distance=10)
        
        if len(peaks) > 1:
            # Calculate from multiple peaks for accuracy
            bit_rates = []
            for i in range(min(5, len(peaks)-1)):
                period = peaks[i+1] - peaks[i]
                rate = self.sample_rate / period
                bit_rates.append(rate)
            
            if bit_rates:
                self.fingerprint['bit_rate'] = np.mean(bit_rates)
                print(f"Estimated bit rate: {self.fingerprint['bit_rate']:.0f} baud")
                
                # Check against common rates
                common_rates = {
                    300: "Very old systems",
                    600: "Legacy pagers",
                    1200: "APRS, older telemetry",
                    2400: "Some car remotes",
                    4800: "Weather stations",
                    9600: "Some sensors",
                    19200: "Modern sensors",
                    38400: "High-speed data",
                    100000: "Keeloq/HCS rolling code",
                    200000: "Modern car key fobs",
                    250000: "Garage door openers"
                }
                
                closest_rate = min(common_rates.keys(), 
                                  key=lambda x: abs(x - self.fingerprint['bit_rate']))
                
                if abs(closest_rate - self.fingerprint['bit_rate']) < self.fingerprint['bit_rate'] * 0.2:
                    print(f"Closest standard: {closest_rate} baud ({common_rates[closest_rate]})")
        
    def identify_device(self):
        """Match against known device signatures"""
        print("\n" + "="*70)
        print("DEVICE IDENTIFICATION")
        print("="*70)
        
        freq = self.frequency
        mod = self.fingerprint['modulation']
        rate = self.fingerprint['bit_rate']
        duration = np.mean(self.fingerprint['burst_duration_ms']) if self.fingerprint['burst_duration_ms'] else 0
        
        print(f"\nSignature Summary:")
        print(f"  Frequency: {freq} MHz")
        print(f"  Modulation: {mod}")
        print(f"  Bit rate: {rate:.0f} baud" if rate else "  Bit rate: Unknown")
        print(f"  Burst duration: {duration:.1f} ms")
        print(f"  Burst count: {self.fingerprint['burst_count']}")
        
        # Device database
        matches = []
        confidence = 0
        
        # 915 MHz ISM Band Signatures
        if 910 <= freq <= 930:
            print("\n>>> Region: North America (915 MHz ISM)")
            
            # Keeloq/HCS (Microchip) - Most common garage door system
            if mod == 'OOK/ASK' and rate and 50000 <= rate <= 150000:
                if 3 <= duration <= 20:
                    matches.append({
                        'device': 'Garage Door Opener Remote',
                        'brand': 'Chamberlain/LiftMaster',
                        'protocol': 'Keeloq (Microchip HCS301)',
                        'confidence': 85,
                        'notes': 'Rolling code, Security+ or Security+ 2.0'
                    })
                    confidence = 85
                    
            # Car key fob signatures
            if mod == 'OOK/ASK' and rate and 150000 <= rate <= 300000:
                if 5 <= duration <= 50:
                    matches.append({
                        'device': 'Automotive Key Fob',
                        'brand': 'GM/Ford/Chrysler (likely)',
                        'protocol': 'Proprietary rolling code',
                        'confidence': 75,
                        'notes': 'High bit rate suggests modern vehicle'
                    })
                    confidence = 75
                    
            # TPMS (Tire Pressure Monitoring)
            if mod in ['FSK', 'OOK/ASK'] and rate and 10000 <= rate <= 40000:
                if 50 <= duration <= 150:
                    matches.append({
                        'device': 'Tire Pressure Monitor',
                        'brand': 'Schrader/Continental/TRW',
                        'protocol': 'TPMS proprietary',
                        'confidence': 80,
                        'notes': 'Transmits tire ID, pressure, temperature'
                    })
                    confidence = 80
                    
            # Genie garage door (different from Chamberlain)
            if mod == 'OOK/ASK' and duration < 15 and self.fingerprint['burst_count'] >= 2:
                matches.append({
                    'device': 'Garage Door Opener',
                    'brand': 'Genie (Overhead Door)',
                    'protocol': 'Intellicode (rolling)',
                    'confidence': 70,
                    'notes': 'Different encoding than Chamberlain'
                })
                
            # Wireless sensors
            if 20 <= duration <= 50 and rate and rate < 10000:
                matches.append({
                    'device': 'Wireless Sensor',
                    'brand': 'Generic (Honeywell/2GIG/Others)',
                    'protocol': 'ASK/OOK basic',
                    'confidence': 60,
                    'notes': 'Could be door/window sensor, motion detector'
                })
                
        # 433 MHz signatures
        elif 430 <= freq <= 440:
            print("\n>>> Region: Europe/Asia (433 MHz ISM)")
            matches.append({
                'device': 'European Car Remote or Weather Station',
                'brand': 'Various',
                'protocol': 'Multiple possibilities',
                'confidence': 50,
                'notes': 'Common in Europe for car remotes, weather stations'
            })
            
        # Print matches
        if matches:
            print("\n" + "-"*70)
            print("POSSIBLE MATCHES (sorted by confidence):")
            print("-"*70)
            
            matches.sort(key=lambda x: x['confidence'], reverse=True)
            
            for i, match in enumerate(matches, 1):
                print(f"\n{i}. {match['device']}")
                print(f"   Brand/Manufacturer: {match['brand']}")
                print(f"   Protocol: {match['protocol']}")
                print(f"   Confidence: {match['confidence']}%")
                print(f"   Notes: {match['notes']}")
                
            # Best match
            best = matches[0]
            if best['confidence'] >= 75:
                print("\n" + "="*70)
                print(f">>> MOST LIKELY: {best['device']}")
                print(f">>> Brand: {best['brand']}")
                print(f">>> Protocol: {best['protocol']}")
                print("="*70)
        else:
            print("\n>>> No strong matches in database")
            print("    This could be a proprietary or uncommon system")
            
    def generate_report(self):
        """Generate comprehensive fingerprint report"""
        print("\n" + "="*70)
        print("COMPLETE FINGERPRINT REPORT")
        print("="*70)
        
        print("\n[RF CHARACTERISTICS]")
        print(f"  Frequency: {self.frequency} MHz")
        print(f"  Carrier offset: {self.fingerprint['carrier_offset']/1e3:.2f} kHz")
        print(f"  Bandwidth: {self.fingerprint['bandwidth']/1e3:.1f} kHz")
        
        print("\n[MODULATION]")
        print(f"  Type: {self.fingerprint['modulation']}")
        if self.fingerprint['bit_rate']:
            print(f"  Bit rate: {self.fingerprint['bit_rate']:.0f} baud")
        
        print("\n[TRANSMISSION PATTERN]")
        print(f"  Burst count: {self.fingerprint['burst_count']}")
        if self.fingerprint['burst_duration_ms']:
            print(f"  Avg burst duration: {np.mean(self.fingerprint['burst_duration_ms']):.2f} ms")
        if self.fingerprint['burst_spacing_ms']:
            print(f"  Avg burst spacing: {np.mean(self.fingerprint['burst_spacing_ms']):.2f} ms")
        
        print("\n[SECURITY ASSESSMENT]")
        if self.fingerprint['burst_count'] >= 2:
            print("  Multiple bursts detected (likely rolling code)")
            print("  Security: GOOD (modern rolling code system)")
        else:
            print("  Single or fixed transmission")
            print("  Security: UNKNOWN (need more samples)")
        
        # Save fingerprint to file
        report_file = self.filepath.replace('.npy', '_fingerprint.txt')
        with open(report_file, 'w') as f:
            f.write("="*70 + "\n")
            f.write("RF SIGNAL FINGERPRINT REPORT\n")
            f.write("="*70 + "\n\n")
            f.write(f"File: {os.path.basename(self.filepath)}\n\n")
            f.write(f"Frequency: {self.frequency} MHz\n")
            f.write(f"Modulation: {self.fingerprint['modulation']}\n")
            f.write(f"Bit rate: {self.fingerprint['bit_rate']:.0f} baud\n" if self.fingerprint['bit_rate'] else "")
            f.write(f"Burst count: {self.fingerprint['burst_count']}\n")
            f.write(f"Carrier offset: {self.fingerprint['carrier_offset']/1e3:.2f} kHz\n")
            f.write(f"Bandwidth: {self.fingerprint['bandwidth']/1e3:.1f} kHz\n")
        
        print(f"\n[REPORT] Saved: {report_file}")
        
    def analyze(self):
        """Run complete fingerprinting analysis"""
        print("\n" + "#"*70)
        print("# ReconRaven - RF Signal Fingerprinting")
        print("# Brand/Model/Device Type Identification")
        print("#"*70)
        
        self.load()
        self.analyze_bursts()
        self.analyze_modulation()
        self.analyze_bit_rate()
        self.identify_device()
        self.generate_report()
        
        print("\n" + "="*70)
        print("RECOMMENDATIONS")
        print("="*70)
        print("\n1. Compare with FCC database: https://fccid.io/")
        print("   Search by frequency (925 MHz) to find registered devices")
        print("\n2. Use Universal Radio Hacker for deeper protocol analysis")
        print("\n3. Capture more samples for better confidence")
        print("\n4. If car key fob: Check year/make/model compatibility databases")
        print("="*70)

def main():
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python fingerprint_signal.py <file.npy>")
        print("\nExample:")
        print("  python fingerprint_signal.py recordings/audio/ISM915_925.000MHz_20251122_173249_FSK.npy")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not os.path.exists(filepath):
        print(f"\nError: File not found: {filepath}")
        sys.exit(1)
    
    try:
        fingerprinter = SignalFingerprinter(filepath)
        fingerprinter.analyze()
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

