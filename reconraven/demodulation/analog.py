"""
Analog Demodulation Module
Handles FM, AM, and SSB demodulation using rtl_fm.
"""

import queue
import subprocess
import threading
import wave
from enum import Enum
from typing import Callable, Optional

from reconraven.core.debug_helper import DebugHelper


class AnalogMode(Enum):
    """Analog demodulation modes."""

    FM = 'fm'
    FM_WIDE = 'wbfm'
    AM = 'am'
    USB = 'usb'
    LSB = 'lsb'


class AnalogDemodulator(DebugHelper):
    """Demodulates analog signals using rtl_fm."""

    def __init__(self, config: Optional[dict] = None):
        super().__init__(component_name='AnalogDemodulator')
        self.debug_enabled = True
        """Initialize analog demodulator.

        Args:
            config: Demodulation configuration dictionary
        """
        self.config = config or {}
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.audio_callback: Optional[Callable] = None
        self.audio_queue = queue.Queue(maxsize=100)

    def start_demodulation(
        self,
        frequency_hz: float,
        mode: AnalogMode = AnalogMode.FM,
        output_file: Optional[str] = None,
        audio_callback: Optional[Callable] = None,
    ) -> bool:
        """Start demodulating a signal.

        Args:
            frequency_hz: Frequency to demodulate
            mode: Demodulation mode
            output_file: Optional WAV file to record to
            audio_callback: Optional callback for audio data

        Returns:
            True if started successfully
        """
        if self.is_running:
            self.log_warning('Demodulator already running')
            return False

        try:
            # Get mode configuration
            mode_config = self.config.get(mode.value.upper(), {})
            sample_rate = mode_config.get('sample_rate', 240000)
            audio_rate = mode_config.get('audio_rate', 48000)

            # Build rtl_fm command
            cmd = [
                'rtl_fm',
                '-f',
                str(int(frequency_hz)),
                '-M',
                mode.value,
                '-s',
                str(sample_rate),
                '-r',
                str(audio_rate),
                '-',  # Output to stdout
            ]

            # Add any additional args from config
            extra_args = mode_config.get('args', [])
            if extra_args:
                cmd.extend(extra_args)

            self.log_info(f"Starting demodulation: {' '.join(cmd)}")

            # Start rtl_fm process
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0
            )

            self.is_running = True
            self.audio_callback = audio_callback

            # Start audio processing thread
            audio_thread = threading.Thread(
                target=self._process_audio, args=(audio_rate, output_file), daemon=True
            )
            audio_thread.start()

            self.log_info(f'Demodulation started: {frequency_hz/1e6:.6f} MHz, mode: {mode.value}')
            return True

        except FileNotFoundError:
            self.log_error('rtl_fm not found. Please install rtl-sdr tools.')
            return False
        except Exception as e:
            self.log_error(f'Error starting demodulation: {e}')
            return False

    def _process_audio(self, sample_rate: int, output_file: Optional[str]):
        """Process audio data from rtl_fm."""
        wav_file = None

        try:
            if output_file:
                wav_file = wave.open(output_file, 'wb')
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)

            chunk_size = 4096

            while self.is_running and self.process:
                try:
                    data = self.process.stdout.read(chunk_size)
                    if not data:
                        break

                    if wav_file:
                        wav_file.writeframes(data)

                    if self.audio_callback:
                        self.audio_callback(data)

                    try:
                        self.audio_queue.put_nowait(data)
                    except queue.Full:
                        try:
                            self.audio_queue.get_nowait()
                            self.audio_queue.put_nowait(data)
                        except Exception:
                            pass

                except Exception as e:
                    self.log_error(f'Error processing audio: {e}')
                    break

        finally:
            if wav_file:
                wav_file.close()

    def stop_demodulation(self):
        """Stop demodulation."""
        self.is_running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()
            self.process = None

    def __del__(self):
        self.stop_demodulation()
