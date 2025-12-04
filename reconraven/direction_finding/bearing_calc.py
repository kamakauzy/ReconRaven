"""
Bearing Calculation Module
Implements MUSIC algorithm for direction finding.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


logger = logging.getLogger(__name__)


class BearingCalculator:
    """Calculates bearings using MUSIC algorithm."""

    def __init__(self, array_sync, config: dict = None):
        """Initialize bearing calculator."""
        self.array_sync = array_sync
        self.config = config or {}
        self.num_sources = self.config.get('num_sources', 1)
        self.angle_resolution = 1  # degrees

    def calculate_bearing(
        self, frequency_hz: float, num_samples: int = 16384
    ) -> Optional[Dict[str, Any]]:
        """Calculate bearing to signal source.

        Args:
            frequency_hz: Signal frequency
            num_samples: Number of samples to acquire

        Returns:
            Dictionary with bearing information or None
        """
        try:
            # Acquire phase-coherent samples
            samples = self.array_sync.acquire_coherent_samples(frequency_hz, num_samples)

            if len(samples) < 2:
                logger.error('Insufficient array elements for bearing calculation')
                return None

            # Calculate covariance matrix
            R = self.array_sync.get_covariance_matrix(samples)

            # Get array geometry
            array_positions = self.array_sync.get_array_geometry()

            # Run MUSIC algorithm
            bearing, confidence = self._music_algorithm(R, array_positions, frequency_hz)

            if bearing is not None:
                result = {
                    'bearing_degrees': bearing,
                    'confidence': confidence,
                    'frequency_hz': frequency_hz,
                    'num_elements': len(samples),
                    'timestamp': __import__('time').time(),
                }

                logger.info(f'Bearing calculated: {bearing:.1f}° (confidence: {confidence:.2f})')
                return result

        except Exception as e:
            logger.error(f'Error calculating bearing: {e}')

        return None

    def _music_algorithm(
        self, R: np.ndarray, array_positions: np.ndarray, frequency_hz: float
    ) -> Tuple[Optional[float], float]:
        """MUSIC (Multiple Signal Classification) algorithm.

        Args:
            R: Spatial covariance matrix
            array_positions: Array element positions
            frequency_hz: Signal frequency

        Returns:
            Tuple of (bearing in degrees, confidence)
        """
        try:
            # Eigenvalue decomposition
            eigenvalues, eigenvectors = np.linalg.eigh(R)

            # Sort by eigenvalue (descending)
            idx = eigenvalues.argsort()[::-1]
            eigenvalues = eigenvalues[idx]
            eigenvectors = eigenvectors[:, idx]

            # Separate signal and noise subspaces
            num_elements = len(eigenvalues)
            noise_subspace = eigenvectors[:, self.num_sources :]

            # Calculate wavelength
            c = 3e8  # Speed of light
            wavelength = c / frequency_hz

            # Sweep angles and calculate MUSIC spectrum
            angles = np.arange(0, 360, self.angle_resolution)
            spectrum = np.zeros(len(angles))

            for i, angle in enumerate(angles):
                # Calculate steering vector for this angle
                a = self._steering_vector(angle, array_positions, wavelength)

                # Calculate MUSIC pseudo-spectrum
                numerator = 1.0
                denominator = np.abs(a.conj().T @ noise_subspace @ noise_subspace.conj().T @ a)

                if denominator > 1e-10:
                    spectrum[i] = numerator / denominator
                else:
                    spectrum[i] = 0.0

            # Find peak in spectrum
            peak_idx = np.argmax(spectrum)
            bearing = angles[peak_idx]

            # Calculate confidence based on peak prominence
            peak_value = spectrum[peak_idx]
            mean_value = np.mean(spectrum)

            if mean_value > 0:
                confidence = min(1.0, (peak_value / mean_value) / 10.0)
            else:
                confidence = 0.0

            return float(bearing), float(confidence)

        except Exception as e:
            logger.error(f'Error in MUSIC algorithm: {e}')
            return None, 0.0

    def _steering_vector(
        self, angle_degrees: float, array_positions: np.ndarray, wavelength: float
    ) -> np.ndarray:
        """Calculate steering vector for given angle.

        Args:
            angle_degrees: Angle in degrees (0° = North, clockwise)
            array_positions: Array element positions [[x1,y1], [x2,y2], ...]
            wavelength: Signal wavelength in meters

        Returns:
            Steering vector
        """
        # Convert angle to radians
        angle_rad = np.deg2rad(angle_degrees)

        # Wave vector direction
        k = 2 * np.pi / wavelength
        kx = k * np.sin(angle_rad)
        ky = k * np.cos(angle_rad)

        # Calculate phase at each element
        num_elements = len(array_positions)
        a = np.zeros(num_elements, dtype=complex)

        for i in range(num_elements):
            x, y = array_positions[i]
            phase = kx * x + ky * y
            a[i] = np.exp(1j * phase)

        # Normalize
        a /= np.sqrt(num_elements)

        return a

    def calculate_bearing_from_samples(
        self, samples: List[np.ndarray], frequency_hz: float
    ) -> Optional[Dict[str, Any]]:
        """Calculate bearing from pre-acquired samples.

        Args:
            samples: List of sample arrays
            frequency_hz: Signal frequency

        Returns:
            Dictionary with bearing information
        """
        try:
            R = self.array_sync.get_covariance_matrix(samples)
            array_positions = self.array_sync.get_array_geometry()

            bearing, confidence = self._music_algorithm(R, array_positions, frequency_hz)

            if bearing is not None:
                return {
                    'bearing_degrees': bearing,
                    'confidence': confidence,
                    'frequency_hz': frequency_hz,
                    'timestamp': __import__('time').time(),
                }

        except Exception as e:
            logger.error(f'Error calculating bearing from samples: {e}')

        return None
