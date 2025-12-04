#!/usr/bin/env python3
"""
Voice Signal Detector
Automatically detects voice transmissions and triggers recording
"""

from typing import Optional

import numpy as np
from scipy import signal

from reconraven.core.debug_helper import DebugHelper


class VoiceDetector(DebugHelper):
    """Detects voice signals from RF characteristics"""

    def __init__(self):
        super().__init__(component_name='VoiceDetector')
        self.debug_enabled = True
        # Voice signal characteristics
        self.voice_bandwidths = {
            'NFM': (8000, 16000),  # Narrow FM (ham, public safety)
            'FM': (12500, 25000),  # Standard FM
            'WFM': (150000, 200000),  # Broadcast FM
            'AM': (6000, 10000),  # AM voice (aviation)
            'SSB': (2400, 3000),  # SSB (ham HF)
        }

        # Known voice frequencies (MHz)
        self.known_voice_bands = [
            (144.0, 148.0),  # 2m ham
            (420.0, 450.0),  # 70cm ham
            (462.5, 467.7),  # GMRS/FRS
            (156.0, 162.0),  # Marine VHF
            (118.0, 137.0),  # Aviation
            (150.0, 174.0),  # VHF public safety
        ]

    def is_voice_signal(
        self, frequency_hz: float, power_dbm: float, iq_samples: Optional[np.ndarray] = None
    ) -> tuple[bool, float, str]:
        """Determine if a signal is likely voice

        Args:
            frequency_hz: Center frequency
            power_dbm: Signal power
            iq_samples: Optional IQ samples for analysis

        Returns:
            (is_voice, confidence, mode_guess)
        """
        confidence = 0.0
        mode_guess = 'Unknown'

        # Check if frequency is in known voice band
        freq_mhz = frequency_hz / 1e6

        for start, end in self.known_voice_bands:
            if start <= freq_mhz <= end:
                confidence += 0.3

                # Guess mode based on band
                if 144 <= freq_mhz <= 148 or 420 <= freq_mhz <= 450:
                    mode_guess = 'FM'  # Ham bands
                elif 462.5 <= freq_mhz <= 467.7:
                    mode_guess = 'FM'  # GMRS/FRS
                elif 156 <= freq_mhz <= 162:
                    mode_guess = 'FM'  # Marine VHF
                elif 118 <= freq_mhz <= 137:
                    mode_guess = 'AM'  # Aviation
                break

        # Analyze IQ samples if available
        if iq_samples is not None and len(iq_samples) > 0:
            # Detect modulation type
            mod_type, mod_confidence = self._detect_modulation(iq_samples)

            if mod_type in ['FM', 'AM', 'SSB']:
                confidence += 0.4 * mod_confidence
                mode_guess = mod_type

            # Analyze spectral characteristics
            is_voice_like = self._analyze_spectral_features(iq_samples)
            if is_voice_like:
                confidence += 0.3

        # Power threshold (voice signals typically > -90 dBm)
        if power_dbm > -90:
            confidence += 0.1

        is_voice = confidence > 0.5

        return is_voice, min(confidence, 1.0), mode_guess

    def _detect_modulation(self, iq_samples: np.ndarray) -> tuple[str, float]:
        """Detect modulation type from IQ samples"""
        try:
            # Calculate instantaneous frequency for FM detection
            phase = np.unwrap(np.angle(iq_samples))
            inst_freq = np.diff(phase)
            fm_deviation = np.std(inst_freq)

            # Calculate amplitude for AM detection
            amplitude = np.abs(iq_samples)
            am_depth = (np.max(amplitude) - np.min(amplitude)) / np.mean(amplitude)

            # Classify based on characteristics
            if fm_deviation > 0.1:
                if fm_deviation > 0.5:
                    return 'WFM', 0.8  # Wide FM (broadcast)
                return 'FM', 0.7  # Narrow FM
            if am_depth > 0.3:
                return 'AM', 0.7
            if am_depth > 0.1:
                return 'SSB', 0.6

            return 'Unknown', 0.0

        except Exception:
            return 'Unknown', 0.0

    def _analyze_spectral_features(self, iq_samples: np.ndarray) -> bool:
        """Analyze spectral characteristics typical of voice"""
        try:
            # Calculate power spectral density
            freqs, psd = signal.welch(iq_samples, fs=2.4e6, nperseg=1024)

            # Voice energy is typically concentrated in 300-3400 Hz band
            # Look for peak in this range
            voice_range_mask = (freqs > 300) & (freqs < 3400)
            voice_energy = np.sum(psd[voice_range_mask])
            total_energy = np.sum(psd)

            # Voice typically has 20-40% of energy in voice band
            voice_ratio = voice_energy / total_energy if total_energy > 0 else 0

            return 0.15 < voice_ratio < 0.5

        except Exception:
            return False

    def should_monitor_for_voice(self, frequency_hz: float) -> bool:
        """Quick check if we should monitor this frequency for voice"""
        freq_mhz = frequency_hz / 1e6

        return any(start <= freq_mhz <= end for start, end in self.known_voice_bands)

    def get_optimal_voice_mode(self, frequency_hz: float) -> str:
        """Get the optimal demodulation mode for a frequency"""
        freq_mhz = frequency_hz / 1e6

        if 144 <= freq_mhz <= 148 or 420 <= freq_mhz <= 450:
            return 'FM'  # Ham bands
        if 462.5 <= freq_mhz <= 467.7:
            return 'FM'  # GMRS/FRS
        if 156 <= freq_mhz <= 162:
            return 'FM'  # Marine VHF
        if 150 <= freq_mhz <= 174:
            return 'FM'  # VHF public safety
        if 118 <= freq_mhz <= 137:
            return 'AM'  # Aviation
        if freq_mhz < 30:
            return 'USB'  # HF ham (assume USB)

        return 'FM'  # Default to FM


if __name__ == '__main__':
    # Test voice detection
    detector = VoiceDetector()

    test_frequencies = [
        (146.52e6, '2m calling frequency'),
        (146.94e6, '2m repeater'),
        (434.5e6, '70cm data'),
        (462.5625e6, 'GMRS channel 1'),
        (156.8e6, 'Marine channel 16'),
        (121.5e6, 'Aviation emergency'),
    ]

    print('\n' + '=' * 70)
    print('VOICE SIGNAL DETECTION TEST')
    print('=' * 70)

    for freq_hz, description in test_frequencies:
        should_monitor = detector.should_monitor_for_voice(freq_hz)
        mode = detector.get_optimal_voice_mode(freq_hz)

        print(f'\n{freq_hz/1e6:.4f} MHz - {description}')
        print(f"  Monitor for voice: {'YES' if should_monitor else 'NO'}")
        print(f'  Optimal mode: {mode}')
