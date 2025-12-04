"""
Signal Logger Module
Records IQ samples, audio, and metadata with GPS timestamps.
"""

import json
import logging
import os
import time
import wave
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np

from reconraven.core.debug_helper import DebugHelper


try:
    import gpsd

    GPS_AVAILABLE = True
except ImportError:
    GPS_AVAILABLE = False
    logging.warning('gpsd not available - GPS features disabled')


class GPSInterface:
    """Interface for GPS data acquisition."""

    def __init__(self, config: dict = None):
        """Initialize GPS interface."""
        self.config = config or {}
        self.connected = False
        self.current_position = None

        if GPS_AVAILABLE and self.config.get('enabled', True):
            try:
                gpsd.connect()
                self.connected = True
                self.log_info('GPS connected')
            except Exception as e:
                self.log_warning(f'Could not connect to GPS: {e}')

    def get_position(self) -> Optional[Dict[str, Any]]:
        """Get current GPS position.

        Returns:
            Dictionary with GPS data or None
        """
        if not self.connected or not GPS_AVAILABLE:
            return None

        try:
            packet = gpsd.get_current()

            if packet.mode >= 2:  # 2D fix or better
                position = {
                    'latitude': packet.lat,
                    'longitude': packet.lon,
                    'altitude_m': getattr(packet, 'alt', 0),
                    'speed_mps': getattr(packet, 'speed', 0),
                    'track_degrees': getattr(packet, 'track', 0),
                    'satellites': getattr(packet, 'sats', 0),
                    'mode': packet.mode,
                    'timestamp': time.time(),
                }

                self.current_position = position
                return position

        except Exception as e:
            self.log_debug(f'Error reading GPS: {e}')

        return self.current_position  # Return last known position

    def wait_for_fix(self, timeout_s: float = 30) -> bool:
        """Wait for GPS fix.

        Args:
            timeout_s: Maximum time to wait

        Returns:
            True if fix acquired
        """
        if not self.connected:
            return False

        start_time = time.time()

        while time.time() - start_time < timeout_s:
            position = self.get_position()
            if position and position['mode'] >= 2:
                self.log_info('GPS fix acquired')
                return True
            time.sleep(1)

        self.log_warning('GPS fix timeout')
        return False


class SignalLogger(DebugHelper):
    """Records signal data with GPS timestamps."""

    def __init__(self, config: dict = None):
        super().__init__(component_name='SignalLogger')
        self.debug_enabled = True
        """Initialize signal logger."""
        self.config = config or {}
        self.output_dir = self.config.get('output_dir', './recordings')
        self.gps = GPSInterface(self.config.get('gps', {}))

        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

    def log_signal_detection(
        self, signal_hit, bearing: Optional[Dict] = None, metadata: Optional[Dict] = None
    ) -> str:
        """Log a signal detection event.

        Args:
            signal_hit: SignalHit object
            bearing: Optional bearing information
            metadata: Optional additional metadata

        Returns:
            Path to log file
        """
        timestamp = datetime.now()
        filename = f"signal_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.output_dir, filename)

        # Get GPS position
        gps_data = self.gps.get_position()

        # Build log entry
        log_entry = {
            'timestamp': timestamp.isoformat(),
            'unix_time': time.time(),
            'signal': signal_hit.to_dict() if hasattr(signal_hit, 'to_dict') else str(signal_hit),
            'gps': gps_data,
            'bearing': bearing,
            'metadata': metadata or {},
        }

        # Write to file
        try:
            with open(filepath, 'w') as f:
                json.dump(log_entry, f, indent=2)

            self.log_debug(f'Signal logged to {filepath}')
            return filepath

        except Exception as e:
            self.log_error(f'Error logging signal: {e}')
            return ''

    def record_iq_samples(
        self,
        samples: np.ndarray,
        frequency_hz: float,
        sample_rate: int,
        duration_s: Optional[float] = None,
    ) -> str:
        """Record IQ samples to file.

        Args:
            samples: Complex IQ samples
            frequency_hz: Center frequency
            sample_rate: Sample rate
            duration_s: Recording duration (if None, record all samples)

        Returns:
            Path to recording file
        """
        timestamp = datetime.now()
        filename = f"iq_{int(frequency_hz/1e6)}MHz_{timestamp.strftime('%Y%m%d_%H%M%S')}.dat"
        filepath = os.path.join(self.output_dir, filename)

        try:
            # Limit samples if duration specified
            if duration_s:
                max_samples = int(sample_rate * duration_s)
                samples = samples[:max_samples]

            # Save as complex64
            samples.astype(np.complex64).tofile(filepath)

            # Save metadata
            meta_file = filepath + '.json'
            metadata = {
                'frequency_hz': frequency_hz,
                'sample_rate': sample_rate,
                'num_samples': len(samples),
                'duration_s': len(samples) / sample_rate,
                'timestamp': timestamp.isoformat(),
                'gps': self.gps.get_position(),
            }

            with open(meta_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            self.log_info(f'IQ samples recorded to {filepath}')
            return filepath

        except Exception as e:
            self.log_error(f'Error recording IQ samples: {e}')
            return ''

    def record_audio(
        self, audio_data: bytes, frequency_hz: float, sample_rate: int = 48000, mode: str = 'FM'
    ) -> str:
        """Record demodulated audio to WAV file.

        Args:
            audio_data: Audio data bytes
            frequency_hz: Signal frequency
            sample_rate: Audio sample rate
            mode: Demodulation mode

        Returns:
            Path to WAV file
        """
        timestamp = datetime.now()
        filename = (
            f"audio_{int(frequency_hz/1e6)}MHz_{mode}_{timestamp.strftime('%Y%m%d_%H%M%S')}.wav"
        )
        filepath = os.path.join(self.output_dir, filename)

        try:
            # Write WAV file
            with wave.open(filepath, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data)

            # Save metadata
            meta_file = filepath + '.json'
            metadata = {
                'frequency_hz': frequency_hz,
                'sample_rate': sample_rate,
                'mode': mode,
                'duration_s': len(audio_data) / (sample_rate * 2),  # 2 bytes per sample
                'timestamp': timestamp.isoformat(),
                'gps': self.gps.get_position(),
            }

            with open(meta_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            self.log_info(f'Audio recorded to {filepath}')
            return filepath

        except Exception as e:
            self.log_error(f'Error recording audio: {e}')
            return ''

    def create_session_log(self, session_data: Dict[str, Any]) -> str:
        """Create a session summary log.

        Args:
            session_data: Session information dictionary

        Returns:
            Path to session log file
        """
        timestamp = datetime.now()
        filename = f"session_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.output_dir, filename)

        try:
            session_log = {
                'session_start': timestamp.isoformat(),
                'gps_start': self.gps.get_position(),
                **session_data,
            }

            with open(filepath, 'w') as f:
                json.dump(session_log, f, indent=2)

            self.log_info(f'Session log created: {filepath}')
            return filepath

        except Exception as e:
            self.log_error(f'Error creating session log: {e}')
            return ''

    def get_gps_position(self) -> Optional[Dict[str, Any]]:
        """Get current GPS position.

        Returns:
            GPS position dictionary or None
        """
        return self.gps.get_position()
