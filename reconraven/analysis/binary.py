#!/usr/bin/env python3
"""
Binary Decoder Module
Extracts clean binary data from IQ samples for protocol analysis
"""

import logging


logger = logging.getLogger(__name__)

import sys

import numpy as np
from scipy import signal


class BinaryDecoder:
    """Extract binary data from modulated signals"""

    def __init__(self, samples, sample_rate=2.4e6):
        self.samples = samples
        self.sample_rate = sample_rate
        self.modulation = None
        self.symbol_rate = None

    def detect_modulation_type(self):
        """Determine modulation type (OOK/ASK/FSK)"""
        magnitude = np.abs(self.samples[:100000])
        phase = np.angle(self.samples[:100000])
        inst_freq = np.diff(np.unwrap(phase))

        mag_std = np.std(magnitude)
        freq_std = np.std(inst_freq)

        if mag_std > 0.05:
            self.modulation = 'OOK/ASK'
        elif freq_std > 0.5:
            self.modulation = 'FSK'
        else:
            self.modulation = 'Unknown'

        return self.modulation

    def estimate_symbol_rate(self):
        """Estimate symbol rate via autocorrelation"""
        if self.modulation == 'OOK/ASK':
            sig = np.abs(self.samples[:500000])
        else:
            phase = np.angle(self.samples[:500000])
            sig = np.diff(np.unwrap(phase))

        # High-pass filter
        b, a = signal.butter(4, 1000, 'highpass', fs=self.sample_rate)
        sig_filtered = signal.filtfilt(b, a, sig)

        # Autocorrelation
        autocorr = np.correlate(sig_filtered, sig_filtered, mode='full')
        autocorr = autocorr[len(autocorr) // 2 :]

        # Find symbol period
        peaks, _ = signal.find_peaks(
            autocorr[: int(self.sample_rate * 0.01)], height=np.max(autocorr) * 0.1, distance=10
        )

        if len(peaks) > 1:
            symbol_period = peaks[1] - peaks[0]
            self.symbol_rate = self.sample_rate / symbol_period
            return self.symbol_rate

        return None

    def decode_ook(self):
        """Decode OOK/ASK to binary"""
        logger.info('Decoding OOK/ASK signal...')

        # Get amplitude envelope
        envelope = np.abs(self.samples)

        # Smooth envelope
        if self.symbol_rate:
            window_size = int(self.sample_rate / (self.symbol_rate * 4))
        else:
            window_size = 100

        envelope_smooth = np.convolve(envelope, np.ones(window_size) / window_size, mode='same')

        # Threshold detection
        threshold = np.mean(envelope_smooth) + 1.5 * np.std(envelope_smooth)
        digital = (envelope_smooth > threshold).astype(int)

        # Sample at symbol rate
        if self.symbol_rate:
            samples_per_symbol = int(self.sample_rate / self.symbol_rate)
            bits = []

            for i in range(0, len(digital) - samples_per_symbol, samples_per_symbol):
                # Sample middle of symbol
                sample_idx = i + samples_per_symbol // 2
                if sample_idx < len(digital):
                    bits.append(digital[sample_idx])

            return np.array(bits)

        return digital

    def decode_fsk(self):
        """Decode FSK to binary"""
        logger.info('Decoding FSK signal...')

        # Calculate instantaneous frequency
        phase = np.unwrap(np.angle(self.samples))
        inst_freq = np.diff(phase)

        # Smooth
        if self.symbol_rate:
            window_size = int(self.sample_rate / (self.symbol_rate * 4))
        else:
            window_size = 100

        inst_freq_smooth = np.convolve(inst_freq, np.ones(window_size) / window_size, mode='same')

        # Find mark and space frequencies
        hist, bins = np.histogram(inst_freq_smooth, bins=100)
        peaks, _ = signal.find_peaks(hist, height=np.max(hist) * 0.3)

        if len(peaks) >= 2:
            # Get two strongest peaks
            peak_heights = hist[peaks]
            top_peaks = peaks[np.argsort(peak_heights)[-2:]]

            freq_mark = bins[max(top_peaks)]
            freq_space = bins[min(top_peaks)]
            threshold = (freq_mark + freq_space) / 2

            # Decode
            digital = (inst_freq_smooth > threshold).astype(int)

            # Sample at symbol rate
            if self.symbol_rate:
                samples_per_symbol = int(self.sample_rate / self.symbol_rate)
                bits = []

                for i in range(0, len(digital) - samples_per_symbol, samples_per_symbol):
                    sample_idx = i + samples_per_symbol // 2
                    if sample_idx < len(digital):
                        bits.append(digital[sample_idx])

                return np.array(bits)

            return digital

        return None

    def decode_to_binary(self):
        """Main decode function - returns binary array"""
        # Detect modulation
        mod = self.detect_modulation_type()
        logger.info(f'Detected modulation: {mod}')

        # Estimate symbol rate
        rate = self.estimate_symbol_rate()
        if rate:
            logger.info(f'Symbol rate: {rate:.0f} baud')
        else:
            logger.info('Symbol rate: Unknown (using default)')

        # Decode based on modulation
        if mod == 'OOK/ASK':
            bits = self.decode_ook()
        elif mod == 'FSK':
            bits = self.decode_fsk()
        else:
            logger.info('Unknown modulation - cannot decode')
            return None

        if bits is not None:
            logger.info(f'Decoded {len(bits)} bits')
            return bits

        return None

    def bits_to_hex(self, bits):
        """Convert bit array to hex string"""
        # Group into bytes
        hex_string = ''
        for i in range(0, len(bits), 8):
            byte = bits[i : i + 8]
            if len(byte) == 8:
                byte_val = int(''.join(map(str, byte)), 2)
                hex_string += f'{byte_val:02X} '

        return hex_string.strip()

    def find_preamble(self, bits, common_preambles=None):
        """Find known preambles in bit stream"""
        if common_preambles is None:
            common_preambles = [
                '10101010',  # Standard alternating
                '01010101',  # Inverted alternating
                '11110000',  # Keeloq
                '10011001',  # Manchester-like
            ]

        bit_string = ''.join(map(str, bits[: min(1000, len(bits))]))

        found = []
        for preamble in common_preambles:
            if preamble in bit_string:
                idx = bit_string.index(preamble)
                found.append(
                    {
                        'pattern': preamble,
                        'position': idx,
                        'description': self._describe_preamble(preamble),
                    }
                )

        return found

    def _describe_preamble(self, pattern):
        """Describe what a preamble pattern is"""
        if pattern == '10101010' or pattern == '01010101':
            return 'Standard sync/preamble'
        if pattern == '11110000':
            return 'Keeloq garage door opener'
        if pattern == '10011001':
            return 'Manchester encoding marker'
        return 'Unknown preamble'


def decode_file(filepath):
    """Decode a recording file"""
    logger.info(f'\nLoading: {filepath}')
    samples = np.load(filepath)
    logger.info(f'Loaded {len(samples):,} samples')

    # Use first 5 seconds for faster processing
    samples = samples[: int(2.4e6 * 5)]

    decoder = BinaryDecoder(samples)
    bits = decoder.decode_to_binary()

    if bits is not None and len(bits) > 0:
        logger.info('\n' + '=' * 70)
        logger.info('BINARY DECODE RESULTS')
        logger.info('=' * 70)

        # Show first 1000 bits
        display_bits = bits[: min(1000, len(bits))]

        logger.info('\nBit stream (first 1000 bits):')
        bit_string = ''.join(map(str, display_bits))
        for i in range(0, len(bit_string), 64):
            logger.info(f'  {bit_string[i:i+64]}')

        # Convert to hex
        logger.info('\nHex representation:')
        hex_str = decoder.bits_to_hex(display_bits)
        words = hex_str.split()
        for i in range(0, len(words), 16):
            logger.info(f"  {' '.join(words[i:i+16])}")

        # Find preambles
        logger.info('\nPreamble search:')
        preambles = decoder.find_preamble(bits)
        if preambles:
            for p in preambles:
                logger.info(
                    f"  Found: {p['pattern']} at position {p['position']} - {p['description']}"
                )
        else:
            logger.info('  No known preambles found')

        # Statistics
        logger.info('\nStatistics:')
        ones = np.sum(bits)
        zeros = len(bits) - ones
        logger.info(f'  Total bits: {len(bits)}')
        logger.info(f'  Ones: {ones} ({ones/len(bits)*100:.1f}%)')
        logger.info(f'  Zeros: {zeros} ({zeros/len(bits)*100:.1f}%)')

        # Save to file
        output_file = filepath.replace('.npy', '_decoded.txt')
        with open(output_file, 'w') as f:
            f.write('BINARY DECODE\n')
            f.write('=' * 70 + '\n\n')
            f.write(f'File: {filepath}\n')
            f.write(f'Modulation: {decoder.modulation}\n')
            f.write(
                f'Symbol rate: {decoder.symbol_rate:.0f} baud\n'
                if decoder.symbol_rate
                else 'Symbol rate: Unknown\n'
            )
            f.write(f'Total bits: {len(bits)}\n\n')
            f.write('Bit stream:\n')
            bit_string = ''.join(map(str, bits))
            for i in range(0, len(bit_string), 64):
                f.write(bit_string[i : i + 64] + '\n')

        logger.info(f'\nFull decode saved to: {output_file}')

        return bits, decoder

    return None, decoder


if __name__ == '__main__':
    if len(sys.argv) < 2:
        logger.info('Usage: python binary_decoder.py <file.npy>')
        sys.exit(1)

    decode_file(sys.argv[1])
