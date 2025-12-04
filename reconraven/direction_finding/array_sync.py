"""
SDR Array Synchronization Module
Manages phase-coherent sampling for direction finding.
"""

import logging
from typing import List

import numpy as np


logger = logging.getLogger(__name__)


class SDRArraySync:
    """Manages synchronization of multiple SDRs for direction finding."""

    def __init__(self, sdr_controller, config: dict = None):
        """Initialize array synchronization."""
        self.sdr = sdr_controller
        self.config = config or {}
        self.num_elements = self.config.get('num_elements', 4)
        self.reference_element = self.config.get('reference_element', 0)
        self.phase_offsets = np.zeros(self.num_elements)
        self.is_calibrated = False

        # Antenna configuration
        self.antenna_type = self.config.get('antenna_type', 'omnidirectional')
        self.element_spacing_m = self.config.get('element_spacing_m', 0.5)

        # Load saved calibration if available
        self._load_calibration()

    def _load_calibration(self):
        """Load saved calibration from database"""
        try:
            from database import get_db

            db = get_db()
            cal = db.get_active_df_calibration()

            if cal and cal['num_sdrs'] == self.num_elements:
                self.phase_offsets = np.array(cal['phase_offsets'])
                self.antenna_type = cal.get('antenna_type', 'omnidirectional')
                self.element_spacing_m = cal.get('element_spacing_m', 0.5)
                self.is_calibrated = True
                logger.info(
                    f"Loaded DF calibration: {cal['calibration_method']} from {cal['created_at']}"
                )
                logger.info(f'Phase offsets: {self.phase_offsets}')
            else:
                logger.info('No valid calibration found, array needs calibration')
        except Exception as e:
            logger.warning(f'Could not load calibration: {e}')

    def calibrate_phase(
        self,
        frequency_hz: float,
        num_samples: int = 10000,
        known_bearing: float = None,
        save_to_db: bool = True,
    ) -> bool:
        """Calibrate phase offsets between array elements.

        Args:
            frequency_hz: Calibration frequency
            num_samples: Number of samples for calibration
            known_bearing: If provided, calibrate using signal from known direction
            save_to_db: Save calibration to database

        Returns:
            True if calibration successful
        """
        logger.info(f'Calibrating array phase at {frequency_hz/1e6:.3f} MHz...')

        if known_bearing is not None:
            logger.info(f'Using known bearing: {known_bearing}° for calibration')

        try:
            # Set all SDRs to calibration frequency
            self.sdr.set_frequency(int(frequency_hz))

            # Collect samples from all elements
            samples = self.sdr.read_samples_sync(num_samples)

            if len(samples) < self.num_elements:
                logger.error(f'Expected {self.num_elements} SDRs, got {len(samples)}')
                return False

            # Calculate phase offsets relative to reference element
            reference_samples = samples[self.reference_element]

            # Calculate SNR for quality metric
            snr_db = self._calculate_snr(reference_samples)

            for i in range(self.num_elements):
                if i == self.reference_element:
                    self.phase_offsets[i] = 0.0
                else:
                    # Calculate cross-correlation to find phase offset
                    phase_diff = self._calculate_phase_difference(reference_samples, samples[i])
                    self.phase_offsets[i] = phase_diff

            # Calculate coherence score (how well arrays are synchronized)
            coherence = self._calculate_coherence(samples)

            self.is_calibrated = True
            logger.info('Phase calibration complete!')
            logger.info(f'  Phase offsets: {self.phase_offsets}')
            logger.info(f'  Coherence: {coherence:.3f}')
            logger.info(f'  SNR: {snr_db:.1f} dB')

            # Save to database
            if save_to_db:
                try:
                    from database import get_db

                    db = get_db()

                    array_geometry = {
                        'type': self.config.get('geometry', 'square'),
                        'element_positions': self.get_array_geometry().tolist(),
                    }

                    cal_method = 'Cross-correlation'
                    if known_bearing is not None:
                        cal_method += f' with known bearing {known_bearing}°'

                    notes = f'Antenna: {self.antenna_type}, Spacing: {self.element_spacing_m}m'

                    db.save_df_calibration(
                        num_sdrs=self.num_elements,
                        calibration_freq_hz=frequency_hz,
                        phase_offsets=self.phase_offsets.tolist(),
                        array_geometry=array_geometry,
                        antenna_type=self.antenna_type,
                        element_spacing_m=self.element_spacing_m,
                        coherence_score=coherence,
                        snr_db=snr_db,
                        calibration_method=cal_method,
                        notes=notes,
                    )
                    logger.info('Calibration saved to database')
                except Exception as e:
                    logger.warning(f'Could not save calibration to database: {e}')

            return True

        except Exception as e:
            logger.error(f'Error during phase calibration: {e}')
            import traceback

            traceback.print_exc()
            return False

    def _calculate_phase_difference(self, reference: np.ndarray, signal: np.ndarray) -> float:
        """Calculate phase difference between two signals.

        Args:
            reference: Reference signal
            signal: Signal to compare

        Returns:
            Phase difference in radians
        """
        # Cross-correlation in frequency domain
        fft_ref = np.fft.fft(reference)
        fft_sig = np.fft.fft(signal)

        # Calculate cross-power spectrum
        cross_power = fft_ref * np.conj(fft_sig)

        # Find peak in cross-correlation
        cross_corr = np.fft.ifft(cross_power)
        peak_idx = np.argmax(np.abs(cross_corr))

        # Phase at peak is the phase offset
        phase_offset = np.angle(cross_corr[peak_idx])

        return phase_offset

    def _calculate_snr(self, samples: np.ndarray) -> float:
        """Calculate signal-to-noise ratio.

        Args:
            samples: Complex sample array

        Returns:
            SNR in dB
        """
        # Calculate power spectrum
        spectrum = np.abs(np.fft.fft(samples)) ** 2

        # Signal power (peak)
        signal_power = np.max(spectrum)

        # Noise power (median, excluding peak)
        sorted_spectrum = np.sort(spectrum)
        noise_power = np.median(sorted_spectrum[: len(sorted_spectrum) // 2])

        if noise_power > 0:
            snr_db = 10 * np.log10(signal_power / noise_power)
        else:
            snr_db = 0.0

        return snr_db

    def _calculate_coherence(self, samples: List[np.ndarray]) -> float:
        """Calculate array coherence (0.0-1.0).

        Higher values indicate better synchronization.

        Args:
            samples: List of sample arrays from each element

        Returns:
            Coherence score
        """
        if len(samples) < 2:
            return 0.0

        # Calculate cross-correlation between all pairs
        coherence_sum = 0.0
        pair_count = 0

        for i in range(len(samples)):
            for j in range(i + 1, len(samples)):
                # Normalized cross-correlation
                corr = np.correlate(samples[i], samples[j], mode='valid')
                max_corr = np.max(np.abs(corr))

                # Normalize by auto-correlations
                auto_i = np.correlate(samples[i], samples[i], mode='valid')[0]
                auto_j = np.correlate(samples[j], samples[j], mode='valid')[0]

                if auto_i > 0 and auto_j > 0:
                    normalized_corr = max_corr / np.sqrt(auto_i * auto_j)
                    coherence_sum += min(1.0, abs(normalized_corr))
                    pair_count += 1

        if pair_count > 0:
            return coherence_sum / pair_count
        return 0.0

    def acquire_coherent_samples(
        self, frequency_hz: float, num_samples: int = 16384
    ) -> List[np.ndarray]:
        """Acquire phase-coherent samples from all array elements.

        Args:
            frequency_hz: Frequency to sample
            num_samples: Number of samples to acquire

        Returns:
            List of phase-corrected sample arrays
        """
        if not self.is_calibrated:
            logger.warning('Array not calibrated, results may be inaccurate')

        # Set frequency
        self.sdr.set_frequency(int(frequency_hz))

        # Acquire samples
        samples = self.sdr.read_samples_sync(num_samples)

        # Apply phase corrections
        corrected_samples = []
        for i, sample_array in enumerate(samples):
            if i < len(self.phase_offsets):
                # Apply phase correction
                correction = np.exp(-1j * self.phase_offsets[i])
                corrected = sample_array * correction
                corrected_samples.append(corrected)
            else:
                corrected_samples.append(sample_array)

        return corrected_samples

    def get_covariance_matrix(
        self, samples: List[np.ndarray], num_snapshots: int = 100
    ) -> np.ndarray:
        """Calculate spatial covariance matrix for MUSIC algorithm.

        Args:
            samples: List of sample arrays from each element
            num_snapshots: Number of snapshots for covariance estimation

        Returns:
            Covariance matrix
        """
        num_elements = len(samples)

        # Create snapshot matrix
        snapshot_length = len(samples[0]) // num_snapshots

        # Initialize covariance matrix
        R = np.zeros((num_elements, num_elements), dtype=complex)

        # Calculate covariance over snapshots
        for snapshot in range(num_snapshots):
            start_idx = snapshot * snapshot_length
            end_idx = start_idx + snapshot_length

            # Get snapshot vector (one sample from each element)
            snapshot_vector = np.array(
                [samples[i][start_idx:end_idx].mean() for i in range(num_elements)]
            )

            # Add to covariance matrix
            R += np.outer(snapshot_vector, snapshot_vector.conj())

        # Normalize
        R /= num_snapshots

        return R

    def get_array_geometry(self) -> np.ndarray:
        """Get array element positions.

        Returns:
            Array of element positions [x, y] in meters
        """
        positions = self.config.get(
            'element_positions', [[0.0, 0.0], [0.5, 0.0], [0.5, 0.5], [0.0, 0.5]]
        )

        return np.array(positions[: self.num_elements])
