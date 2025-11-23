#!/usr/bin/env python3
"""
Remote Control Decoder
Extracts and decodes binary data from garage door openers, car remotes, etc.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
import os

class RemoteDecoder:
    def __init__(self, filepath):
        self.filepath = filepath
        self.samples = None
        self.sample_rate = 2.4e6
        self.bursts = []
        
    def load(self):
        """Load IQ samples"""
        print("Loading IQ samples...", end='', flush=True)
        self.samples = np.load(self.filepath)
        print(f" OK ({len(self.samples):,} samples)")
        
    def extract_bursts(self):
        """Extract individual transmission bursts"""
        print("\n" + "="*70)
        print("EXTRACTING BURSTS")
        print("="*70)
        
        # Get amplitude envelope
        envelope = np.abs(self.samples)
        
        # Smooth envelope
        window = int(self.sample_rate * 0.0001)  # 0.1ms window
        envelope_smooth = np.convolve(envelope, np.ones(window)/window, mode='same')
        
        # Detect bursts
        threshold = np.mean(envelope_smooth) + 3*np.std(envelope_smooth)
        above_threshold = envelope_smooth > threshold
        
        # Find burst boundaries
        transitions = np.diff(above_threshold.astype(int))
        burst_starts = np.where(transitions == 1)[0]
        burst_ends = np.where(transitions == -1)[0]
        
        # Match starts with ends
        if len(burst_starts) > 0 and len(burst_ends) > 0:
            if burst_ends[0] < burst_starts[0]:
                burst_ends = burst_ends[1:]
            
            for i in range(min(len(burst_starts), len(burst_ends))):
                start = burst_starts[i]
                end = burst_ends[i]
                duration_ms = (end - start) / self.sample_rate * 1000
                
                # Only keep bursts > 1ms (filter noise)
                if duration_ms > 1:
                    self.bursts.append({
                        'id': i+1,
                        'samples': self.samples[start:end],
                        'start': start,
                        'end': end,
                        'duration_ms': duration_ms
                    })
            
            print(f"Extracted {len(self.bursts)} valid bursts")
        else:
            print("No bursts found")
            
    def decode_ook_burst(self, burst):
        """Decode OOK/ASK modulated burst to binary"""
        samples = burst['samples']
        
        # Get amplitude envelope
        envelope = np.abs(samples)
        
        # Smooth slightly
        window = 10
        envelope_smooth = np.convolve(envelope, np.ones(window)/window, mode='same')
        
        # Try to estimate symbol rate
        # Look for transitions in the envelope
        threshold = np.mean(envelope_smooth) + 0.5*np.std(envelope_smooth)
        digital = (envelope_smooth > threshold).astype(int)
        
        # Find edges (bit transitions)
        edges = np.diff(digital)
        edge_indices = np.where(np.abs(edges) > 0)[0]
        
        if len(edge_indices) > 1:
            # Calculate typical bit period from edge spacing
            edge_diffs = np.diff(edge_indices)
            
            # Filter out very short glitches
            edge_diffs_filtered = edge_diffs[edge_diffs > 10]
            
            if len(edge_diffs_filtered) > 0:
                # Find the most common short pulse (likely one bit)
                hist, bins = np.histogram(edge_diffs_filtered, bins=50)
                peak_idx = np.argmax(hist)
                bit_period = bins[peak_idx]
                
                # Decode bits by sampling at bit period intervals
                bits = []
                for i in range(0, len(digital), int(bit_period)):
                    if i < len(digital):
                        # Sample in the middle of the bit period
                        sample_idx = int(i + bit_period/2)
                        if sample_idx < len(digital):
                            bits.append(str(digital[sample_idx]))
                
                bit_string = ''.join(bits)
                
                return {
                    'bit_string': bit_string,
                    'bit_period_samples': bit_period,
                    'bit_rate': self.sample_rate / bit_period,
                    'num_bits': len(bits)
                }
        
        return None
        
    def decode_all_bursts(self):
        """Decode all extracted bursts"""
        print("\n" + "="*70)
        print("DECODING BURSTS")
        print("="*70)
        
        decoded_bursts = []
        
        for burst in self.bursts:
            print(f"\n--- Burst #{burst['id']} ({burst['duration_ms']:.1f} ms) ---")
            
            decoded = self.decode_ook_burst(burst)
            
            if decoded and len(decoded['bit_string']) > 8:
                print(f"Bit rate: ~{decoded['bit_rate']:.0f} baud")
                print(f"Total bits: {decoded['num_bits']}")
                print(f"\nBinary stream:")
                
                # Print bits in groups of 8
                bit_str = decoded['bit_string']
                for i in range(0, len(bit_str), 8):
                    byte = bit_str[i:i+8]
                    if len(byte) == 8:
                        hex_val = hex(int(byte, 2))[2:].upper().zfill(2)
                        print(f"  {byte}  0x{hex_val}  {int(byte, 2):3d}")
                    else:
                        print(f"  {byte}")
                
                # Look for patterns
                self.analyze_code(decoded['bit_string'], burst['id'])
                
                decoded_bursts.append({
                    'burst_id': burst['id'],
                    'code': decoded['bit_string']
                })
            else:
                print("Could not decode - signal too weak or noisy")
                
        return decoded_bursts
        
    def analyze_code(self, bit_string, burst_id):
        """Analyze the decoded bit pattern"""
        print(f"\nPattern Analysis:")
        
        # Look for preamble (alternating 1010 pattern)
        if bit_string.startswith('1010') or bit_string.startswith('0101'):
            preamble_len = 0
            for i in range(0, len(bit_string), 4):
                if bit_string[i:i+4] in ['1010', '0101']:
                    preamble_len = i + 4
                else:
                    break
            
            if preamble_len > 0:
                print(f"  - Preamble detected: {preamble_len} bits")
                print(f"    {bit_string[:preamble_len]}")
                data = bit_string[preamble_len:]
                print(f"  - Data payload: {len(data)} bits")
                print(f"    {data}")
        
        # Check for Manchester encoding (equal 0s and 1s, no long runs)
        ones = bit_string.count('1')
        zeros = bit_string.count('0')
        total = len(bit_string)
        
        if total > 0:
            balance = abs(ones - zeros) / total
            if balance < 0.1:
                print(f"  - Possible Manchester encoding (balanced 1s and 0s)")
        
        # Look for repeated patterns
        if len(bit_string) >= 24:
            # Check if pattern repeats
            chunk_size = len(bit_string) // 2
            chunk1 = bit_string[:chunk_size]
            chunk2 = bit_string[chunk_size:chunk_size*2]
            
            # Calculate similarity
            if len(chunk1) == len(chunk2) and chunk1 == chunk2:
                print(f"  - REPEATED PATTERN detected (possible error correction)")
        
        # Count transitions (for complexity assessment)
        transitions = sum(1 for i in range(len(bit_string)-1) 
                         if bit_string[i] != bit_string[i+1])
        print(f"  - Bit transitions: {transitions} ({transitions/len(bit_string)*100:.1f}%)")
        
    def compare_bursts(self, decoded_bursts):
        """Compare multiple bursts to identify rolling codes vs fixed codes"""
        print("\n" + "="*70)
        print("BURST COMPARISON")
        print("="*70)
        
        if len(decoded_bursts) < 2:
            print("Need at least 2 bursts to compare")
            return
            
        print(f"\nComparing {len(decoded_bursts)} bursts...")
        
        # Compare each pair
        all_same = True
        for i in range(len(decoded_bursts)-1):
            code1 = decoded_bursts[i]['code']
            code2 = decoded_bursts[i+1]['code']
            
            if code1 == code2:
                print(f"  Burst {decoded_bursts[i]['burst_id']} == Burst {decoded_bursts[i+1]['burst_id']} (IDENTICAL)")
            else:
                all_same = False
                # Calculate hamming distance
                min_len = min(len(code1), len(code2))
                differences = sum(1 for j in range(min_len) if code1[j] != code2[j])
                similarity = (1 - differences/min_len) * 100
                
                print(f"  Burst {decoded_bursts[i]['burst_id']} vs Burst {decoded_bursts[i+1]['burst_id']}: "
                      f"{similarity:.1f}% similar ({differences} bits different)")
        
        print("\n" + "-"*70)
        if all_same:
            print(">>> FIXED CODE DETECTED")
            print("    All transmissions are identical.")
            print("    This is a simple remote with a static code.")
            print("    WARNING: This code could be replayed (cloned)!")
        else:
            print(">>> ROLLING CODE DETECTED (or noise)")
            print("    Codes are different between transmissions.")
            print("    This uses a secure rolling/hopping code algorithm.")
            print("    Each button press generates a unique code.")
        print("-"*70)
        
    def visualize_burst(self, burst):
        """Visualize a single burst in detail"""
        samples = burst['samples']
        envelope = np.abs(samples)
        phase = np.angle(samples)
        
        fig, axes = plt.subplots(3, 1, figsize=(14, 9))
        
        time_ms = np.arange(len(samples)) / self.sample_rate * 1000
        
        # Amplitude
        axes[0].plot(time_ms, envelope, linewidth=0.8)
        axes[0].set_xlabel('Time (ms)')
        axes[0].set_ylabel('Amplitude')
        axes[0].set_title(f"Burst #{burst['id']} - Amplitude Envelope")
        axes[0].grid(True, alpha=0.3)
        
        # Add threshold line
        threshold = np.mean(envelope) + 0.5*np.std(envelope)
        axes[0].axhline(threshold, color='r', linestyle='--', label='Threshold')
        axes[0].legend()
        
        # Digital signal (demodulated)
        window = 10
        envelope_smooth = np.convolve(envelope, np.ones(window)/window, mode='same')
        digital = (envelope_smooth > threshold).astype(int)
        
        axes[1].plot(time_ms, digital, linewidth=1.5, drawstyle='steps-post')
        axes[1].set_xlabel('Time (ms)')
        axes[1].set_ylabel('Digital Value')
        axes[1].set_title('Demodulated Digital Signal (OOK)')
        axes[1].set_ylim(-0.1, 1.1)
        axes[1].grid(True, alpha=0.3)
        
        # Spectrogram
        if len(samples) > 256:
            f, t, Sxx = signal.spectrogram(samples, 
                                          fs=self.sample_rate,
                                          nperseg=min(256, len(samples)//4))
            
            axes[2].pcolormesh(t*1000, f/1e3, 10*np.log10(Sxx + 1e-10),
                              shading='gouraud', cmap='viridis')
            axes[2].set_xlabel('Time (ms)')
            axes[2].set_ylabel('Frequency Offset (kHz)')
            axes[2].set_title('Spectrogram')
        
        plt.tight_layout()
        
        plot_file = self.filepath.replace('.npy', f'_burst{burst["id"]}_decoded.png')
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        print(f"\nSaved: {plot_file}")
        
        plt.show()
        
    def analyze(self):
        """Run complete analysis"""
        print("\n" + "#"*70)
        print("# ReconRaven - Remote Control Decoder")
        print("# Decodes garage openers, car remotes, and more")
        print("#"*70)
        
        self.load()
        self.extract_bursts()
        
        if self.bursts:
            decoded = self.decode_all_bursts()
            
            if decoded:
                self.compare_bursts(decoded)
                
                # Visualize first burst
                if len(self.bursts) > 0:
                    print("\nGenerating detailed visualization of first burst...")
                    self.visualize_burst(self.bursts[0])
        
        print("\n" + "="*70)
        print("SECURITY NOTES")
        print("="*70)
        print("\n- Fixed codes can be cloned/replayed (security risk)")
        print("- Rolling codes are more secure but still vulnerable to:")
        print("  * Jamming attacks")
        print("  * Code grabbing (if encryption is weak)")
        print("  * Replay attacks (in some implementations)")
        print("\n- Modern systems use encryption + rolling codes")
        print("="*70)

def main():
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python decode_remote.py <file.npy>")
        print("\nExample:")
        print("  python decode_remote.py recordings/audio/ISM915_925.000MHz_20251122_173249_FSK.npy")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not os.path.exists(filepath):
        print(f"\nError: File not found: {filepath}")
        sys.exit(1)
    
    try:
        decoder = RemoteDecoder(filepath)
        decoder.analyze()
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

