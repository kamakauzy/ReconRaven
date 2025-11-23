#!/usr/bin/env python3
"""
Signal Decoder & Classifier
Identifies modulation type and attempts to decode signals
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
from scipy.stats import kurtosis
import os

class SignalDecoder:
    def __init__(self, filepath):
        self.filepath = filepath
        self.samples = None
        self.sample_rate = 2.4e6
        self.modulation_type = None
        self.symbol_rate = None
        
    def load(self):
        """Load IQ samples"""
        print("Loading IQ samples...", end='', flush=True)
        self.samples = np.load(self.filepath)
        print(f" OK ({len(self.samples):,} samples)")
        
    def detect_modulation(self):
        """Detect modulation type"""
        print("\n" + "="*70)
        print("MODULATION DETECTION")
        print("="*70)
        
        # Calculate various metrics
        magnitude = np.abs(self.samples)
        phase = np.angle(self.samples)
        instantaneous_freq = np.diff(np.unwrap(phase))
        
        # Normalize
        mag_normalized = (magnitude - np.mean(magnitude)) / np.std(magnitude)
        freq_normalized = (instantaneous_freq - np.mean(instantaneous_freq)) / np.std(instantaneous_freq)
        
        # Calculate statistics
        mag_std = np.std(magnitude)
        mag_kurt = kurtosis(mag_normalized)
        freq_std = np.std(instantaneous_freq)
        
        # Peak-to-average ratio
        par = np.max(magnitude) / np.mean(magnitude)
        
        print(f"Magnitude std dev: {mag_std:.4f}")
        print(f"Magnitude kurtosis: {mag_kurt:.2f}")
        print(f"Freq std dev: {freq_std:.4f}")
        print(f"Peak-to-average ratio: {par:.2f}")
        
        # Classification logic
        if mag_kurt > 2.0 and mag_std > 0.05:
            self.modulation_type = "OOK/ASK"
            print("\n>>> DETECTED: OOK/ASK (On-Off Keying / Amplitude Shift Keying)")
            print("    Common for: garage remotes, doorbells, car key fobs")
        elif freq_std > 0.5 and mag_std < 0.03:
            self.modulation_type = "FSK"
            print("\n>>> DETECTED: FSK (Frequency Shift Keying)")
            print("    Common for: wireless sensors, weather stations, tire pressure monitors")
        elif freq_std > 0.3:
            self.modulation_type = "FM"
            print("\n>>> DETECTED: FM (Frequency Modulation)")
            print("    Common for: voice communications, analog transmissions")
        elif mag_std < 0.02:
            self.modulation_type = "PSK/QAM"
            print("\n>>> DETECTED: PSK or QAM (Phase modulation)")
            print("    Common for: digital data, WiFi, cellular")
        else:
            self.modulation_type = "UNKNOWN"
            print("\n>>> DETECTED: Unknown modulation")
            
    def estimate_symbol_rate(self):
        """Estimate symbol/baud rate"""
        print("\n" + "="*70)
        print("SYMBOL RATE ESTIMATION")
        print("="*70)
        
        # Use magnitude envelope for OOK/ASK
        if self.modulation_type in ["OOK/ASK", "FSK"]:
            if self.modulation_type == "OOK/ASK":
                sig = np.abs(self.samples)
            else:
                # For FSK, use instantaneous frequency
                sig = np.diff(np.unwrap(np.angle(self.samples)))
            
            # High-pass filter to remove DC
            b, a = signal.butter(4, 1000, 'highpass', fs=self.sample_rate)
            sig_filtered = signal.filtfilt(b, a, sig[:len(sig)//2])
            
            # Autocorrelation to find repetition rate
            autocorr = np.correlate(sig_filtered, sig_filtered, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            # Find peaks in autocorrelation
            peaks, _ = signal.find_peaks(autocorr[:int(self.sample_rate*0.01)], 
                                        height=np.max(autocorr)*0.1,
                                        distance=int(self.sample_rate*0.0001))
            
            if len(peaks) > 1:
                # Calculate symbol rate from first peak
                symbol_period_samples = peaks[1] - peaks[0]
                self.symbol_rate = self.sample_rate / symbol_period_samples
                
                print(f"Estimated symbol rate: {self.symbol_rate:.0f} baud")
                print(f"Estimated bit period: {1/self.symbol_rate*1000:.2f} ms")
                
                # Common rates
                common_rates = [300, 600, 1200, 2400, 4800, 9600, 19200, 38400]
                closest = min(common_rates, key=lambda x: abs(x - self.symbol_rate))
                if abs(closest - self.symbol_rate) < self.symbol_rate * 0.15:
                    print(f"Closest standard rate: {closest} baud")
            else:
                print("Could not determine symbol rate (signal may be continuous)")
                
    def decode_ook_ask(self):
        """Attempt to decode OOK/ASK signal"""
        print("\n" + "="*70)
        print("OOK/ASK DECODER")
        print("="*70)
        
        # Get magnitude envelope
        envelope = np.abs(self.samples)
        
        # Smooth envelope
        window_size = int(self.sample_rate / (self.symbol_rate * 10)) if self.symbol_rate else 100
        envelope_smooth = np.convolve(envelope, np.ones(window_size)/window_size, mode='same')
        
        # Threshold detection
        threshold = np.mean(envelope_smooth) + 2*np.std(envelope_smooth)
        digital = (envelope_smooth > threshold).astype(int)
        
        # Find transitions
        transitions = np.diff(digital)
        rising_edges = np.where(transitions == 1)[0]
        falling_edges = np.where(transitions == -1)[0]
        
        print(f"Detected {len(rising_edges)} bursts")
        
        if len(rising_edges) > 0:
            # Analyze burst lengths
            burst_lengths = []
            for i in range(min(len(rising_edges), len(falling_edges))):
                burst_len = falling_edges[i] - rising_edges[i]
                burst_lengths.append(burst_len / self.sample_rate * 1000)  # ms
            
            print(f"Average burst length: {np.mean(burst_lengths):.2f} ms")
            print(f"Burst length range: {np.min(burst_lengths):.2f} - {np.max(burst_lengths):.2f} ms")
            
            # Extract binary data
            print("\nAttempting binary decode...")
            
            # Simple approach: sample at symbol rate
            if self.symbol_rate:
                samples_per_bit = int(self.sample_rate / self.symbol_rate)
                bits = []
                for i in range(0, len(digital) - samples_per_bit, samples_per_bit):
                    bit_value = np.mean(digital[i:i+samples_per_bit])
                    bits.append('1' if bit_value > 0.5 else '0')
                
                # Group into bytes
                bit_string = ''.join(bits[:min(200, len(bits))])  # First 200 bits
                print(f"\nBit stream (first 200 bits):")
                
                # Print in groups of 8
                for i in range(0, len(bit_string), 8):
                    byte = bit_string[i:i+8]
                    if len(byte) == 8:
                        hex_val = hex(int(byte, 2))[2:].upper().zfill(2)
                        print(f"  {byte}  0x{hex_val}  {int(byte, 2):3d}")
                    else:
                        print(f"  {byte}")
                        
                # Look for patterns
                print("\nLooking for patterns...")
                if '1010' in bit_string:
                    print("  - Found 1010 pattern (possible preamble/sync)")
                if '101010' in bit_string:
                    print("  - Found 101010 pattern (likely Manchester encoding)")
                if bit_string.count('1') > len(bit_string) * 0.8:
                    print("  - Mostly 1s (possible idle/carrier)")
                    
    def decode_fsk(self):
        """Attempt to decode FSK signal"""
        print("\n" + "="*70)
        print("FSK DECODER")
        print("="*70)
        
        # Calculate instantaneous frequency
        phase = np.unwrap(np.angle(self.samples))
        inst_freq = np.diff(phase)
        
        # Smooth
        window_size = int(self.sample_rate / (self.symbol_rate * 10)) if self.symbol_rate else 100
        inst_freq_smooth = np.convolve(inst_freq, np.ones(window_size)/window_size, mode='same')
        
        # Find two dominant frequencies (mark and space)
        hist, bins = np.histogram(inst_freq_smooth, bins=100)
        peaks, _ = signal.find_peaks(hist, height=np.max(hist)*0.3)
        
        if len(peaks) >= 2:
            # Get two strongest peaks
            peak_heights = hist[peaks]
            top_peaks = peaks[np.argsort(peak_heights)[-2:]]
            
            freq_mark = bins[top_peaks[0]]
            freq_space = bins[top_peaks[1]]
            
            deviation = abs(freq_mark - freq_space) * self.sample_rate / (2 * np.pi) / 1000  # kHz
            
            print(f"Detected FSK with ~{deviation:.1f} kHz deviation")
            print(f"Mark frequency: {freq_mark:.4f}")
            print(f"Space frequency: {freq_space:.4f}")
            
            # Decode bits
            threshold = (freq_mark + freq_space) / 2
            digital = (inst_freq_smooth > threshold).astype(int)
            
            # Sample at symbol rate
            if self.symbol_rate:
                samples_per_bit = int(self.sample_rate / self.symbol_rate)
                bits = []
                for i in range(0, len(digital) - samples_per_bit, samples_per_bit):
                    bit_value = np.mean(digital[i:i+samples_per_bit])
                    bits.append('1' if bit_value > 0.5 else '0')
                
                bit_string = ''.join(bits[:min(200, len(bits))])
                print(f"\nBit stream (first 200 bits):")
                
                for i in range(0, len(bit_string), 8):
                    byte = bit_string[i:i+8]
                    if len(byte) == 8:
                        hex_val = hex(int(byte, 2))[2:].upper().zfill(2)
                        print(f"  {byte}  0x{hex_val}  {int(byte, 2):3d}")
        else:
            print("Could not identify FSK mark/space frequencies")
            
    def visualize_signal(self):
        """Create detailed visualization"""
        print("\n" + "="*70)
        print("GENERATING VISUALIZATION")
        print("="*70)
        
        fig, axes = plt.subplots(4, 1, figsize=(14, 12))
        
        # 1. Time domain - Amplitude
        plot_samples = min(50000, len(self.samples))
        time_ms = np.arange(plot_samples) / self.sample_rate * 1000
        axes[0].plot(time_ms, np.abs(self.samples[:plot_samples]), linewidth=0.5)
        axes[0].set_xlabel('Time (ms)')
        axes[0].set_ylabel('Amplitude')
        axes[0].set_title(f'Amplitude Envelope - Modulation: {self.modulation_type}')
        axes[0].grid(True, alpha=0.3)
        
        # 2. Instantaneous Frequency
        inst_freq = np.diff(np.unwrap(np.angle(self.samples[:plot_samples])))
        axes[1].plot(time_ms[:-1], inst_freq, linewidth=0.5)
        axes[1].set_xlabel('Time (ms)')
        axes[1].set_ylabel('Instantaneous Freq (rad/sample)')
        axes[1].set_title('Instantaneous Frequency')
        axes[1].grid(True, alpha=0.3)
        
        # 3. FFT
        fft_size = 2048
        freqs = np.fft.fftshift(np.fft.fftfreq(fft_size, 1/self.sample_rate)) / 1e3  # kHz
        spectrum = np.fft.fftshift(np.fft.fft(self.samples[:fft_size]))
        spectrum_db = 20 * np.log10(np.abs(spectrum) + 1e-10)
        
        axes[2].plot(freqs, spectrum_db)
        axes[2].set_xlabel('Frequency Offset (kHz)')
        axes[2].set_ylabel('Power (dB)')
        axes[2].set_title('Frequency Spectrum')
        axes[2].grid(True, alpha=0.3)
        
        # 4. Spectrogram
        spec_samples = min(200000, len(self.samples))
        f, t, Sxx = signal.spectrogram(self.samples[:spec_samples], 
                                       fs=self.sample_rate, 
                                       nperseg=512,
                                       noverlap=256)
        
        axes[3].pcolormesh(t*1000, f/1e3, 10*np.log10(Sxx + 1e-10), 
                          shading='gouraud', cmap='viridis')
        axes[3].set_xlabel('Time (ms)')
        axes[3].set_ylabel('Frequency Offset (kHz)')
        axes[3].set_title('Spectrogram')
        
        plt.tight_layout()
        
        # Save
        plot_file = self.filepath.replace('.npy', '_decoded.png')
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        print(f"Saved: {plot_file}")
        
        plt.show()
        
    def analyze(self):
        """Run complete analysis"""
        self.load()
        self.detect_modulation()
        self.estimate_symbol_rate()
        
        # Attempt decoding based on modulation type
        if self.modulation_type == "OOK/ASK":
            self.decode_ook_ask()
        elif self.modulation_type == "FSK":
            self.decode_fsk()
        
        self.visualize_signal()

def main():
    print("\n" + "#"*70)
    print("# ReconRaven - Signal Decoder & Classifier")
    print("# Automatically identifies modulation and decodes signals")
    print("#"*70)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python decode_signal.py <file.npy>")
        print("\nExample:")
        print("  python decode_signal.py recordings/audio/ISM915_925.000MHz_20251122_173249_FSK.npy")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not os.path.exists(filepath):
        print(f"\nError: File not found: {filepath}")
        sys.exit(1)
    
    try:
        decoder = SignalDecoder(filepath)
        decoder.analyze()
        
        print("\n" + "="*70)
        print("DECODING COMPLETE")
        print("="*70)
        print("\nRECOMMENDATIONS:")
        print("  1. Use Universal Radio Hacker (URH) for more advanced analysis")
        print("  2. Compare patterns with known protocols (e.g., RTL_433 database)")
        print("  3. Look for repeating sequences that might be device IDs")
        print("  4. Check if Manchester or differential encoding is used")
        print("="*70)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

