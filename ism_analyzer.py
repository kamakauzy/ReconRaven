#!/usr/bin/env python3
"""
ISM Band Analyzer
Specialized decoder for 433/868/915 MHz ISM devices
Identifies common protocols: TPMS, weather stations, remotes, etc.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
import os

class ISMAnalyzer:
    def __init__(self, filepath):
        self.filepath = filepath
        self.samples = None
        self.sample_rate = 2.4e6
        
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
        """Load IQ samples"""
        print("Loading IQ samples...", end='', flush=True)
        self.samples = np.load(self.filepath)
        print(f" OK ({len(self.samples):,} samples)")
        
    def detect_bursts(self):
        """Detect transmission bursts"""
        print("\n" + "="*70)
        print("BURST DETECTION")
        print("="*70)
        
        # Get amplitude envelope
        envelope = np.abs(self.samples)
        
        # Smooth envelope
        window = int(self.sample_rate * 0.001)  # 1ms window
        envelope_smooth = np.convolve(envelope, np.ones(window)/window, mode='same')
        
        # Detect bursts above threshold
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
            
            num_bursts = min(len(burst_starts), len(burst_ends))
            
            print(f"\nDetected {num_bursts} transmission bursts")
            print(f"\n{'Burst':<8} {'Start (ms)':<12} {'Duration (ms)':<15} {'Peak Power':<12}")
            print("-"*70)
            
            burst_info = []
            for i in range(min(10, num_bursts)):  # Show first 10
                start_ms = burst_starts[i] / self.sample_rate * 1000
                duration_ms = (burst_ends[i] - burst_starts[i]) / self.sample_rate * 1000
                peak = np.max(envelope[burst_starts[i]:burst_ends[i]])
                
                print(f"{i+1:<8} {start_ms:<12.2f} {duration_ms:<15.2f} {peak:<12.4f}")
                
                burst_info.append({
                    'start': burst_starts[i],
                    'end': burst_ends[i],
                    'duration_ms': duration_ms,
                    'peak': peak
                })
                
            if num_bursts > 10:
                print(f"... and {num_bursts - 10} more bursts")
                
            return burst_info
        else:
            print("No clear bursts detected - signal may be continuous")
            return []
            
    def identify_protocol(self, burst_info):
        """Try to identify the protocol based on burst characteristics"""
        print("\n" + "="*70)
        print("PROTOCOL IDENTIFICATION")
        print("="*70)
        
        if not burst_info:
            print("No burst data available for identification")
            return
            
        avg_duration = np.mean([b['duration_ms'] for b in burst_info])
        
        print(f"Frequency: {self.frequency} MHz")
        print(f"Average burst duration: {avg_duration:.1f} ms")
        
        # Protocol database for 915 MHz
        if 910 <= self.frequency <= 930:
            print("\n>>> 915 MHz ISM Band - North America")
            
            if 50 < avg_duration < 150:
                print("\nLikely Protocol: TIRE PRESSURE MONITOR (TPMS)")
                print("  - Typical burst: 50-100 ms")
                print("  - Usually FSK modulated")
                print("  - Contains: Tire ID, Pressure, Temperature, Battery")
                print("  - Transmits every 60-90 seconds while driving")
                
            elif avg_duration < 20:
                print("\nLikely Protocol: GARAGE DOOR OPENER / REMOTE CONTROL")
                print("  - Typical burst: 5-20 ms")
                print("  - Usually OOK/ASK modulated")
                print("  - Contains: Rolling code or fixed code")
                print("  - Very short transmissions on button press")
                
            elif 20 < avg_duration < 50:
                print("\nLikely Protocol: WIRELESS SENSOR")
                print("  - Could be: Temperature sensor, door sensor, motion detector")
                print("  - Typical burst: 20-50 ms")
                print("  - Usually FSK or OOK")
                print("  - Periodic transmissions (every few seconds to minutes)")
                
            elif avg_duration > 200:
                print("\nLikely Protocol: LoRa or LONG-RANGE DATA")
                print("  - Typical burst: 200+ ms")
                print("  - CSS (Chirp Spread Spectrum) modulation")
                print("  - Used for: IoT devices, smart city sensors")
                
            else:
                print("\nUnknown protocol - could be:")
                print("  - Utility meter (smart meter)")
                print("  - Industrial telemetry")
                print("  - Weather station")
                
        elif 430 <= self.frequency <= 440:
            print("\n>>> 433 MHz ISM Band - Europe/Asia")
            print("Common devices: Car remotes, weather stations, doorbells, outlets")
            
        elif 860 <= self.frequency <= 870:
            print("\n>>> 868 MHz ISM Band - Europe")
            print("Common devices: Smart home, Z-Wave, industrial sensors")
            
    def plot_bursts(self, burst_info):
        """Visualize bursts"""
        print("\n" + "="*70)
        print("GENERATING BURST VISUALIZATION")
        print("="*70)
        
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))
        
        # Full signal overview
        envelope = np.abs(self.samples)
        time_sec = np.arange(len(envelope)) / self.sample_rate
        
        axes[0].plot(time_sec, envelope, linewidth=0.5, alpha=0.7)
        axes[0].set_xlabel('Time (seconds)')
        axes[0].set_ylabel('Amplitude')
        axes[0].set_title(f'Full Capture - {self.frequency} MHz - {len(burst_info)} bursts detected')
        axes[0].grid(True, alpha=0.3)
        
        # Mark bursts
        for burst in burst_info[:20]:  # Show first 20
            start_sec = burst['start'] / self.sample_rate
            end_sec = burst['end'] / self.sample_rate
            axes[0].axvspan(start_sec, end_sec, alpha=0.3, color='red')
        
        # Zoom on first burst
        if burst_info:
            burst = burst_info[0]
            burst_samples = self.samples[burst['start']:burst['end']]
            burst_time_ms = np.arange(len(burst_samples)) / self.sample_rate * 1000
            
            axes[1].plot(burst_time_ms, np.abs(burst_samples), linewidth=0.8)
            axes[1].set_xlabel('Time (ms)')
            axes[1].set_ylabel('Amplitude')
            axes[1].set_title('First Burst - Detail View')
            axes[1].grid(True, alpha=0.3)
            
            # Spectrogram of first burst
            if len(burst_samples) > 512:
                f, t, Sxx = signal.spectrogram(burst_samples, 
                                               fs=self.sample_rate,
                                               nperseg=min(512, len(burst_samples)//4),
                                               noverlap=256)
                
                axes[2].pcolormesh(t*1000, f/1e3, 10*np.log10(Sxx + 1e-10),
                                  shading='gouraud', cmap='viridis')
                axes[2].set_xlabel('Time (ms)')
                axes[2].set_ylabel('Frequency Offset (kHz)')
                axes[2].set_title('First Burst - Spectrogram')
        
        plt.tight_layout()
        
        plot_file = self.filepath.replace('.npy', '_bursts.png')
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        print(f"Saved: {plot_file}")
        
        plt.show()
        
    def analyze(self):
        """Run complete analysis"""
        print("\n" + "#"*70)
        print("# ReconRaven - ISM Band Analyzer")
        print("# Specialized for 433/868/915 MHz devices")
        print("#"*70)
        print(f"\nAnalyzing: {os.path.basename(self.filepath)}")
        
        self.load()
        burst_info = self.detect_bursts()
        self.identify_protocol(burst_info)
        
        if burst_info:
            self.plot_bursts(burst_info)
        
        print("\n" + "="*70)
        print("NEXT STEPS")
        print("="*70)
        print("\n1. Use rtl_433 to decode known protocols:")
        print("   rtl_433 -f 915M -s 2.4M -g 40")
        print("\n2. Use Universal Radio Hacker (URH) for deep analysis:")
        print("   - Load the .npy file")
        print("   - Auto-detect modulation")
        print("   - Extract and analyze protocol")
        print("\n3. Compare with protocol databases:")
        print("   - https://github.com/merbanan/rtl_433")
        print("   - https://fccid.io/ (search by frequency)")
        print("="*70)

def main():
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python ism_analyzer.py <file.npy>")
        print("\nExample:")
        print("  python ism_analyzer.py recordings/audio/ISM915_925.000MHz_20251122_173249_FSK.npy")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not os.path.exists(filepath):
        print(f"\nError: File not found: {filepath}")
        sys.exit(1)
    
    try:
        analyzer = ISMAnalyzer(filepath)
        analyzer.analyze()
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

