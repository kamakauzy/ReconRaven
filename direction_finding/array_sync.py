"""
SDR Array Synchronization Module
Manages phase-coherent sampling for direction finding.
"""

import logging
import numpy as np
from typing import List, Dict, Any

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
        
    def calibrate_phase(self, frequency_hz: float, num_samples: int = 10000) -> bool:
        """Calibrate phase offsets between array elements.
        
        Args:
            frequency_hz: Calibration frequency
            num_samples: Number of samples for calibration
            
        Returns:
            True if calibration successful
        """
        logger.info(f"Calibrating array phase at {frequency_hz/1e6:.3f} MHz...")
        
        try:
            # Set all SDRs to calibration frequency
            self.sdr.set_frequency(int(frequency_hz))
            
            # Collect samples from all elements
            samples = self.sdr.read_samples_sync(num_samples)
            
            if len(samples) < self.num_elements:
                logger.error(f"Expected {self.num_elements} SDRs, got {len(samples)}")
                return False
            
            # Calculate phase offsets relative to reference element
            reference_samples = samples[self.reference_element]
            
            for i in range(self.num_elements):
                if i == self.reference_element:
                    self.phase_offsets[i] = 0.0
                else:
                    # Calculate cross-correlation to find phase offset
                    phase_diff = self._calculate_phase_difference(
                        reference_samples,
                        samples[i]
                    )
                    self.phase_offsets[i] = phase_diff
            
            self.is_calibrated = True
            logger.info(f"Phase calibration complete: {self.phase_offsets}")
            return True
            
        except Exception as e:
            logger.error(f"Error during phase calibration: {e}")
            return False
    
    def _calculate_phase_difference(
        self,
        reference: np.ndarray,
        signal: np.ndarray
    ) -> float:
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
    
    def acquire_coherent_samples(
        self,
        frequency_hz: float,
        num_samples: int = 16384
    ) -> List[np.ndarray]:
        """Acquire phase-coherent samples from all array elements.
        
        Args:
            frequency_hz: Frequency to sample
            num_samples: Number of samples to acquire
            
        Returns:
            List of phase-corrected sample arrays
        """
        if not self.is_calibrated:
            logger.warning("Array not calibrated, results may be inaccurate")
        
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
        self,
        samples: List[np.ndarray],
        num_snapshots: int = 100
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
            snapshot_vector = np.array([
                samples[i][start_idx:end_idx].mean()
                for i in range(num_elements)
            ])
            
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
        positions = self.config.get('element_positions', [
            [0.0, 0.0],
            [0.5, 0.0],
            [0.5, 0.5],
            [0.0, 0.5]
        ])
        
        return np.array(positions[:self.num_elements])

