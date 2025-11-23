#!/usr/bin/env python3
"""
ReconRaven - URH Integration
Lightweight signal analysis using URH-inspired techniques
"""

import sys
import numpy as np
from scipy import signal
import os

class SignalAnalyzer:
    """URH-inspired signal analysis"""
    
    def __init__(self, filepath):
        self.filepath = filepath
        self.samples = None
        self.sample_rate = 2.4e6
        
    def load(self, max_samples=5000000):
        """Load signal (first 2 seconds)"""
        print(f"Loading signal from {os.path.basename(self.filepath)}...")
        all_samples = np.load(self.filepath)
        self.samples = all_samples[:max_samples]
        print(f"Loaded {len(self.samples):,} samples ({len(self.samples)/self.sample_rate:.1f}s)")
        
    def detect_modulation(self):
        """Auto-detect modulation type"""
        print("\n" + "="*70)
        print("MODULATION AUTO-DETECTION")
        print("="*70)
        
        # Analyze amplitude and phase characteristics
        magnitude = np.abs(self.samples[:100000])
        phase = np.angle(self.samples[:100000])
        inst_freq = np.diff(np.unwrap(phase))
        
        mag_std = np.std(magnitude)
        freq_std = np.std(inst_freq)
        
        # Decision tree
        modulations = []
        
        if mag_std > 0.05:
            confidence = min(int(mag_std * 200), 95)
            modulations.append(('ASK/OOK', confidence, 'Amplitude varies significantly'))
            
        if freq_std > 0.5:
            confidence = min(int(freq_std * 100), 95)
            modulations.append(('FSK', confidence, 'Frequency varies significantly'))
            
        if mag_std < 0.02 and freq_std < 0.2:
            modulations.append(('PSK', 60, 'Constant amplitude and frequency'))
            
        if not modulations:
            modulations.append(('Unknown', 30, 'No clear modulation pattern'))
            
        # Sort by confidence
        modulations.sort(key=lambda x: x[1], reverse=True)
        
        print("\nDetected modulations (by confidence):")
        for mod, conf, reason in modulations:
            print(f"  {mod}: {conf}% - {reason}")
            
        return modulations[0]  # Return best match
        
    def extract_symbols(self):
        """Extract digital symbols from signal"""
        print("\n" + "="*70)
        print("SYMBOL EXTRACTION")
        print("="*70)
        
        # Demodulate to baseband
        envelope = np.abs(self.samples)
        
        # Detect symbol rate via autocorrelation
        window_size = min(500000, len(envelope))
        test_signal = envelope[:window_size]
        
        # High-pass filter
        b, a = signal.butter(4, 1000, 'highpass', fs=self.sample_rate)
        filtered = signal.filtfilt(b, a, test_signal)
        
        # Autocorrelation
        autocorr = np.correlate(filtered, filtered, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        
        # Find symbol period
        peaks, _ = signal.find_peaks(autocorr[:int(self.sample_rate*0.01)], 
                                    height=np.max(autocorr)*0.1,
                                    distance=10)
        
        if len(peaks) > 1:
            symbol_period = peaks[1] - peaks[0]
            symbol_rate = self.sample_rate / symbol_period
            
            print(f"Symbol rate: {symbol_rate:.0f} symbols/sec")
            print(f"Symbol period: {symbol_period/self.sample_rate*1000:.2f} ms")
            
            return symbol_rate, symbol_period
        else:
            print("Could not determine symbol rate")
            return None, None
            
    def find_preamble(self):
        """Look for sync/preamble patterns"""
        print("\n" + "="*70)
        print("PREAMBLE DETECTION")
        print("="*70)
        
        envelope = np.abs(self.samples[:500000])
        
        # Threshold detection
        threshold = np.mean(envelope) + 2*np.std(envelope)
        digital = (envelope > threshold).astype(int)
        
        # Look for alternating patterns (common preambles)
        patterns = {
            '10101010': 'Alternating (standard preamble)',
            '11110000': 'Block pattern',
            '10011001': 'Manchester-like',
        }
        
        # Convert to bit string (sample every 100 samples for speed)
        bit_string = ''.join(str(digital[i]) for i in range(0, min(10000, len(digital)), 100))
        
        found_patterns = []
        for pattern, desc in patterns.items():
            if pattern in bit_string:
                index = bit_string.index(pattern)
                found_patterns.append((pattern, desc, index))
                
        if found_patterns:
            print("\nFound preamble patterns:")
            for pattern, desc, idx in found_patterns:
                print(f"  {pattern} - {desc} (at position {idx})")
        else:
            print("No standard preamble patterns detected")
            print("Signal may use:")
            print("  - No preamble")
            print("  - Custom preamble")
            print("  - Continuous transmission")
            
    def protocol_analysis(self):
        """Analyze protocol structure"""
        print("\n" + "="*70)
        print("PROTOCOL STRUCTURE ANALYSIS")
        print("="*70)
        
        # Find bursts
        envelope = np.abs(self.samples)
        threshold = np.mean(envelope) + 3*np.std(envelope)
        above = envelope > threshold
        
        transitions = np.diff(above.astype(int))
        starts = np.where(transitions == 1)[0]
        ends = np.where(transitions == -1)[0]
        
        if len(starts) > 0 and len(ends) > 0:
            if ends[0] < starts[0]:
                ends = ends[1:]
                
            bursts = []
            for i in range(min(len(starts), len(ends))):
                duration = (ends[i] - starts[i]) / self.sample_rate * 1000
                if duration > 1:
                    bursts.append({
                        'start': starts[i],
                        'end': ends[i],
                        'duration_ms': duration
                    })
                    
            print(f"\nFound {len(bursts)} bursts")
            
            if bursts:
                durations = [b['duration_ms'] for b in bursts]
                print(f"Average burst duration: {np.mean(durations):.2f} ms")
                print(f"Duration range: {np.min(durations):.2f} - {np.max(durations):.2f} ms")
                
                # Analyze spacing
                if len(bursts) > 1:
                    spacings = []
                    for i in range(len(bursts)-1):
                        spacing = (bursts[i+1]['start'] - bursts[i]['end']) / self.sample_rate * 1000
                        spacings.append(spacing)
                    
                    if spacings:
                        print(f"\nBurst spacing: {np.mean(spacings):.2f} ms average")
                        
                        # Classify transmission type
                        if np.std(spacings) < np.mean(spacings) * 0.2:
                            print(">>> Regular periodic transmission (likely sensor)")
                        else:
                            print(">>> Irregular timing (likely user-triggered remote)")
                            
    def compare_to_database(self):
        """Compare signal characteristics to known protocols"""
        print("\n" + "="*70)
        print("PROTOCOL DATABASE COMPARISON")
        print("="*70)
        
        # Extract key characteristics
        freq = float(os.path.basename(self.filepath).split('_')[1].replace('MHz', ''))
        
        envelope = np.abs(self.samples[:100000])
        magnitude_std = np.std(envelope)
        
        # Simple database of known protocols
        protocols = [
            {
                'name': 'Keeloq (Microchip HCS301)',
                'freq_range': (310, 315, 390, 434, 868, 915),
                'modulation': 'ASK/OOK',
                'bit_rate': 1000,
                'typical_devices': 'Garage doors (Chamberlain, LiftMaster, Genie)'
            },
            {
                'name': 'Acurite Weather Station',
                'freq_range': (433, 915),
                'modulation': 'OOK',
                'bit_rate': 1000,
                'typical_devices': 'Temperature/humidity sensors'
            },
            {
                'name': 'Oregon Scientific',
                'freq_range': (433,),
                'modulation': 'OOK/Manchester',
                'bit_rate': 1024,
                'typical_devices': 'Weather stations'
            },
            {
                'name': 'Honeywell Security',
                'freq_range': (345, 915),
                'modulation': 'FSK',
                'bit_rate': 4800,
                'typical_devices': 'Door/window sensors, motion detectors'
            },
        ]
        
        print("\nChecking against known protocols...")
        
        matches = []
        for proto in protocols:
            # Check frequency match
            freq_match = any(abs(freq - f) < 50 for f in proto['freq_range'])
            
            if freq_match:
                score = 50  # Base score for frequency match
                matches.append((proto['name'], score, proto))
                
        if matches:
            print(f"\nFound {len(matches)} potential matches:")
            for name, score, proto in matches:
                print(f"\n  {name} (Match: {score}%)")
                print(f"    Typical devices: {proto['typical_devices']}")
                print(f"    Modulation: {proto['modulation']}")
                print(f"    Bit rate: {proto['bit_rate']} baud")
        else:
            print("\nNo matches in database")
            print("This may be:")
            print("  - A proprietary protocol")
            print("  - A newer device not in database")
            print("  - A custom/industrial system")
            
    def generate_report(self):
        """Generate comprehensive analysis report"""
        print("\n" + "="*70)
        print("ANALYSIS COMPLETE")
        print("="*70)
        
        report_file = self.filepath.replace('.npy', '_urh_analysis.txt')
        
        with open(report_file, 'w') as f:
            f.write("="*70 + "\n")
            f.write("URH-STYLE SIGNAL ANALYSIS REPORT\n")
            f.write("="*70 + "\n\n")
            f.write(f"File: {os.path.basename(self.filepath)}\n")
            f.write(f"Sample rate: {self.sample_rate/1e6:.1f} Msps\n")
            f.write(f"Duration: {len(self.samples)/self.sample_rate:.1f} seconds\n")
            f.write(f"Samples: {len(self.samples):,}\n")
            f.write("\nAnalysis completed with URH-inspired techniques\n")
            
        print(f"\nReport saved: {report_file}")
        print("\nRECOMMENDATIONS:")
        print("  1. Install full URH GUI for visual analysis:")
        print("     Download from: https://github.com/jopohl/urh/releases")
        print("  2. Use rtl_433 for automatic decoding:")
        print("     Download from: https://github.com/merbanan/rtl_433/releases")
        print("  3. Check SigIDWiki: https://www.sigidwiki.com/")
        
    def analyze(self):
        """Run complete analysis"""
        print("\n" + "#"*70)
        print("# ReconRaven - URH-Style Signal Analysis")
        print("# Automatic protocol detection and classification")
        print("#"*70)
        
        self.load()
        mod = self.detect_modulation()
        symbol_rate, symbol_period = self.extract_symbols()
        self.find_preamble()
        self.protocol_analysis()
        self.compare_to_database()
        self.generate_report()

def main():
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python urh_analyze.py <file.npy>")
        print("\nExample:")
        print("  python urh_analyze.py recordings/audio/ISM915_925.000MHz_20251122_173249_FSK.npy")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not os.path.exists(filepath):
        print(f"\nError: File not found: {filepath}")
        sys.exit(1)
    
    try:
        analyzer = SignalAnalyzer(filepath)
        analyzer.analyze()
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

