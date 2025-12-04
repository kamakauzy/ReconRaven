"""
SDR Hardware Controller
Manages RTL-SDR devices, auto-detects mode, and provides hardware abstraction.
"""

import logging
import subprocess
from enum import Enum
from typing import List

import numpy as np


try:
    from rtlsdr import RtlSdr

    RTLSDR_AVAILABLE = True
except ImportError:
    RTLSDR_AVAILABLE = False
    logging.warning('pyrtlsdr not available - running in simulation mode')

logger = logging.getLogger(__name__)


class OperatingMode(Enum):
    """Operating modes for the SDR platform."""

    MOBILE = 'mobile'  # Single SDR for mobile scanning
    MOBILE_MULTI = (
        'mobile_multi'  # Multiple SDRs for faster mobile scanning (sequential but distributed)
    )
    PARALLEL_SCAN = 'parallel_scan'  # 4 SDRs scanning different bands simultaneously
    DF = 'df'  # Multiple SDRs for direction finding (switched from parallel)
    UNKNOWN = 'unknown'  # Mode not yet determined


def detect_sdr_devices() -> int:
    """Detect number of connected RTL-SDR devices.

    Returns:
        Number of RTL-SDR devices found
    """
    if not RTLSDR_AVAILABLE:
        logger.warning('RTL-SDR library not available, returning 0 devices')
        return 0

    try:
        # Try to detect devices using rtl_test
        result = subprocess.run(
            ['rtl_test', '-t'], capture_output=True, text=True, timeout=5, check=False
        )

        # Parse output to count devices
        count = 0
        for line in result.stderr.split('\n'):
            if 'Found' in line and 'device' in line:
                # Extract number from line like "Found 1 device(s):"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'Found' and i + 1 < len(parts):
                        try:
                            count = int(parts[i + 1])
                            break
                        except ValueError:
                            pass

        logger.info(f'Detected {count} RTL-SDR device(s)')
        return count

    except FileNotFoundError:
        # rtl_test not found, try pyrtlsdr detection
        logger.warning('rtl_test not found, using pyrtlsdr detection')
        try:
            # Try to enumerate devices
            count = 0
            while True:
                try:
                    sdr = RtlSdr(device_index=count)
                    sdr.close()
                    count += 1
                except Exception:
                    break

            logger.info(f'Detected {count} RTL-SDR device(s) via pyrtlsdr')
            return count

        except Exception as e:
            logger.error(f'Error detecting SDR devices: {e}')
            return 0

    except subprocess.TimeoutExpired:
        logger.error('Timeout detecting SDR devices')
        return 0
    except Exception as e:
        logger.error(f'Error detecting SDR devices: {e}')
        return 0


def detect_sdr_mode() -> OperatingMode:
    """Auto-detect operating mode based on number of connected SDRs.

    Returns:
        OperatingMode enum value
    """
    num_devices = detect_sdr_devices()

    if num_devices == 0:
        logger.warning('No SDR devices detected')
        return OperatingMode.UNKNOWN
    if num_devices == 1:
        logger.info('Single SDR detected - MOBILE mode')
        return OperatingMode.MOBILE
    if num_devices >= 4:
        logger.info(f'{num_devices} SDRs detected - PARALLEL_SCAN mode (DF available)')
        return OperatingMode.PARALLEL_SCAN
    logger.warning(
        f'{num_devices} SDRs detected - insufficient for parallel/DF (need 4), using MOBILE mode'
    )
    return OperatingMode.MOBILE


class SDRController:
    """Controller for RTL-SDR hardware with mode management."""

    def __init__(self, config: dict = None):
        """Initialize SDR controller.

        Args:
            config: Hardware configuration dictionary
        """
        self.config = config or {}
        self.mode = OperatingMode.UNKNOWN
        self.sdrs: List[RtlSdr] = []
        self.is_initialized = False

        # Default SDR parameters
        self.sample_rate = self.config.get('sample_rate_hz', 2400000)
        self.center_freq = self.config.get('center_freq_hz', 434000000)
        self.gain = self.config.get('gain', 'auto')
        self.ppm_error = self.config.get('ppm_error', 0)

    def initialize(self) -> bool:
        """Initialize SDR hardware and detect mode.

        Returns:
            True if initialization successful
        """
        try:
            # Detect mode
            self.mode = detect_sdr_mode()

            if self.mode == OperatingMode.UNKNOWN:
                logger.error('No SDR devices available')
                return False

            # Initialize SDRs based on mode
            if self.mode == OperatingMode.MOBILE:
                success = self._init_single_sdr()
            else:  # DF mode
                success = self._init_df_array()

            self.is_initialized = success
            return success

        except Exception as e:
            logger.error(f'Error initializing SDR hardware: {e}')
            return False

    def _init_single_sdr(self) -> bool:
        """Initialize single SDR for mobile mode.

        Returns:
            True if successful
        """
        if not RTLSDR_AVAILABLE:
            logger.error('RTL-SDR library not available')
            return False

        try:
            sdr = RtlSdr(device_index=0)

            # Configure SDR with error handling for Windows
            try:
                sdr.sample_rate = self.sample_rate
            except Exception as e:
                logger.warning(f'Could not set sample_rate (trying default): {e}')
                sdr.sample_rate = 2.048e6  # Default

            try:
                sdr.center_freq = self.center_freq
            except Exception as e:
                logger.warning(f'Could not set center_freq (trying default): {e}')
                sdr.center_freq = 100e6  # Default to 100 MHz

            # Try to set frequency correction (may fail on some Windows setups)
            try:
                sdr.freq_correction = self.ppm_error
            except Exception as e:
                logger.warning(f'Could not set freq_correction (non-critical): {e}')

            # Set gain with error handling
            try:
                if self.gain == 'auto':
                    sdr.gain = 'auto'
                else:
                    sdr.gain = float(self.gain)
            except Exception as e:
                logger.warning(f'Could not set gain (using auto): {e}')
                try:
                    sdr.gain = 'auto'
                except:
                    pass  # Some drivers don't support auto either

            self.sdrs = [sdr]
            logger.info(f'Initialized single SDR: {sdr.sample_rate} Hz, {sdr.center_freq} Hz')
            return True

        except Exception as e:
            logger.error(f'Error initializing SDR: {e}')
            return False

    def _init_df_array(self) -> bool:
        """Initialize multiple SDRs for DF array mode.

        Returns:
            True if successful
        """
        if not RTLSDR_AVAILABLE:
            logger.error('RTL-SDR library not available')
            return False

        try:
            num_devices = detect_sdr_devices()

            if num_devices < 4:
                logger.error(f'Insufficient SDRs for DF mode: {num_devices} < 4')
                return False

            # Initialize 4 SDRs for the array
            for i in range(4):
                sdr = RtlSdr(device_index=i)

                # Configure each SDR identically
                sdr.sample_rate = self.sample_rate
                sdr.center_freq = self.center_freq
                sdr.freq_correction = self.ppm_error

                if self.gain == 'auto':
                    sdr.gain = 'auto'
                else:
                    sdr.gain = float(self.gain)

                self.sdrs.append(sdr)
                logger.info(f'Initialized SDR {i} for DF array')

            logger.info(f'DF array initialized with {len(self.sdrs)} SDRs')
            return True

        except Exception as e:
            logger.error(f'Error initializing DF array: {e}')
            return False

    def set_frequency(self, freq_hz: int):
        """Set center frequency for all SDRs.

        Args:
            freq_hz: Frequency in Hz
        """
        for sdr in self.sdrs:
            sdr.center_freq = freq_hz
        self.center_freq = freq_hz
        logger.debug(f'Set frequency to {freq_hz} Hz')

    def set_sample_rate(self, rate_hz: int):
        """Set sample rate for all SDRs.

        Args:
            rate_hz: Sample rate in Hz
        """
        for sdr in self.sdrs:
            sdr.sample_rate = rate_hz
        self.sample_rate = rate_hz
        logger.debug(f'Set sample rate to {rate_hz} Hz')

    def set_gain(self, gain):
        """Set gain for all SDRs.

        Args:
            gain: Gain value or 'auto'
        """
        for sdr in self.sdrs:
            if gain == 'auto':
                sdr.gain = 'auto'
            else:
                sdr.gain = float(gain)
        self.gain = gain
        logger.debug(f'Set gain to {gain}')

    def read_samples(self, num_samples: int = 256 * 1024) -> List[np.ndarray]:
        """Read samples from all SDRs.

        Args:
            num_samples: Number of samples to read

        Returns:
            List of sample arrays (one per SDR)
        """
        import numpy as np

        if not self.is_initialized:
            logger.error('SDR not initialized')
            return []

        samples = []
        for i, sdr in enumerate(self.sdrs):
            try:
                data = sdr.read_samples(num_samples)
                samples.append(data)
            except Exception as e:
                logger.error(f'Error reading from SDR {i}: {e}')
                samples.append(np.array([]))

        return samples

    def read_samples_sync(self, num_samples: int = 256 * 1024) -> List[np.ndarray]:
        """Read phase-synchronized samples from all SDRs (for DF mode).

        Note: True phase coherence requires external clock synchronization.
        This method attempts to read samples simultaneously.

        Args:
            num_samples: Number of samples to read

        Returns:
            List of sample arrays (one per SDR)
        """
        # TODO: Implement true phase-coherent sampling with external clock
        # For now, just read samples as quickly as possible
        return self.read_samples(num_samples)

    def close(self):
        """Close all SDR devices."""
        for i, sdr in enumerate(self.sdrs):
            try:
                sdr.close()
                logger.debug(f'Closed SDR {i}')
            except Exception as e:
                logger.error(f'Error closing SDR {i}: {e}')

        self.sdrs = []
        self.is_initialized = False
        logger.info('All SDRs closed')

    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def get_status(self) -> dict:
        """Get status information about the SDR hardware.

        Returns:
            Dictionary with status information
        """
        return {
            'mode': self.mode.value,
            'num_sdrs': len(self.sdrs),
            'initialized': self.is_initialized,
            'sample_rate': self.sample_rate,
            'center_freq': self.center_freq,
            'gain': self.gain,
        }
