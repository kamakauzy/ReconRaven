#!/usr/bin/env python3
"""
Voice Traffic Monitor
Real-time monitoring and recording of voice transmissions (FM/AM/DMR/P25)
"""

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from reconraven.core.database import get_db
from reconraven.core.debug_helper import DebugHelper
from reconraven.demodulation.analog import AnalogDemodulator, AnalogMode


class VoiceMonitor(DebugHelper):
    """Monitors and records voice transmissions"""

    def __init__(self, sdr_device_id: int = 0):
        super().__init__(component_name='VoiceMonitor')
        self.debug_enabled = True
        self.sdr_device_id = sdr_device_id
        self.db = get_db()
        self.is_monitoring = False
        self.current_frequency = None
        self.demodulator = None
        self.recording_dir = 'recordings/voice'
        Path(self.recording_dir).mkdir(parents=True, exist_ok=True)

        # Voice-optimized squelch/detection
        self.squelch_threshold_dbm = -80  # Typical voice signal
        self.voice_activity_threshold = 0.02  # Audio level to detect voice

    def start_monitoring_frequency(
        self,
        frequency_hz: float,
        mode: str = 'FM',
        duration_sec: Optional[int] = None,
        auto_record: bool = True,
    ) -> bool:
        """Start monitoring a specific frequency for voice

        Args:
            frequency_hz: Frequency to monitor
            mode: Demod mode ('FM', 'AM', 'NFM', 'WFM')
            duration_sec: Optional duration (None = continuous)
            auto_record: Automatically record when voice detected

        Returns:
            True if started successfully
        """
        if self.is_monitoring:
            self.log_warning('Already monitoring. Stop current session first.')
            return False

        try:
            # Map mode string to enum
            mode_map = {
                'FM': AnalogMode.FM,
                'NFM': AnalogMode.FM,
                'WFM': AnalogMode.FM_WIDE,
                'AM': AnalogMode.AM,
                'USB': AnalogMode.USB,
                'LSB': AnalogMode.LSB,
            }

            analog_mode = mode_map.get(mode.upper(), AnalogMode.FM)

            # Create demodulator
            self.demodulator = AnalogDemodulator()

            # Setup output file if auto-recording
            output_file = None
            if auto_record:
                timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                freq_mhz = frequency_hz / 1e6
                output_file = str(Path(self.recording_dir) / f'voice_{freq_mhz:.3f}MHz_{timestamp}.wav')
                self.log_info(f'Auto-recording to: {output_file}')

            # Start demodulation
            success = self.demodulator.start_demodulation(
                frequency_hz=frequency_hz,
                mode=analog_mode,
                output_file=output_file,
                audio_callback=self._audio_callback,
            )

            if not success:
                return False

            self.is_monitoring = True
            self.current_frequency = frequency_hz

            # Log to database
            device = self.db.get_device_by_frequency(frequency_hz)
            device_name = (
                device.get('name', f'{freq_mhz:.3f} MHz') if device else f'{freq_mhz:.3f} MHz'
            )

            self.log_info(f"\n{'='*70}")
            self.log_info(f'VOICE MONITOR: {device_name}')
            self.log_info(f"{'='*70}")
            self.log_info(f'Frequency: {freq_mhz:.3f} MHz')
            self.log_info(f'Mode: {mode}')
            self.log_info(f"Recording: {'Yes' if auto_record else 'No'}")
            if output_file:
                self.log_info(f'Output: {output_file}')
            self.log_debug('\nListening... Press Ctrl+C to stop')
            self.log_info(f"{'='*70}\n")

            # Run for duration or until interrupted
            if duration_sec:
                time.sleep(duration_sec)
                self.stop_monitoring()
            else:
                # Continuous monitoring - let it run
                pass

            return True

        except Exception as e:
            self.log_error(f'Error starting voice monitor: {e}')
            return False

    def _audio_callback(self, audio_data: bytes):
        """Called when audio data is received"""
        # Could add:
        # - Voice activity detection
        # - Silence suppression
        # - Audio level metering
        # - Real-time streaming to web dashboard

    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_monitoring = False
        if self.demodulator:
            self.demodulator.stop_demodulation()
            self.demodulator = None

        self.log_info('\nMonitoring stopped.')

    def scan_voice_bands(self, band: str = '2m', dwell_time_sec: int = 5):
        """Scan a band looking for voice activity

        Args:
            band: Band name ('2m', '70cm', 'gmrs', 'frs', 'marine')
            dwell_time_sec: How long to listen to each frequency
        """
        # Define common voice frequencies by band
        voice_freqs = {
            '2m': [  # 2-meter ham band (FM voice)
                146.520,  # National simplex
                146.400,
                146.420,
                146.440,
                146.460,
                146.480,
                146.500,  # Simplex
                # Add repeater freqs from database
            ],
            '70cm': [  # 70cm ham band
                446.000,  # National simplex
                # Add repeater freqs
            ],
            'gmrs': [  # GMRS channels
                462.550,
                462.575,
                462.600,
                462.625,
                462.650,
                462.675,
                462.700,
                462.725,
                467.550,
                467.575,
                467.600,
                467.625,
                467.650,
                467.675,
                467.700,
                467.725,
            ],
            'frs': [  # FRS channels (overlap with GMRS)
                462.5625,
                462.5875,
                462.6125,
                462.6375,
                462.6625,
                462.6875,
                462.7125,
                467.5625,
                467.5875,
                467.6125,
                467.6375,
                467.6625,
                467.6875,
                467.7125,
            ],
            'marine': [  # Marine VHF
                156.300,
                156.400,
                156.450,
                156.500,  # Common channels
                156.550,
                156.600,
                156.650,
                156.700,
                156.750,
                156.800,
                156.850,
                156.900,
            ],
        }

        frequencies = voice_freqs.get(band.lower(), [])

        if not frequencies:
            self.log_info(f'Unknown band: {band}')
            return

        # Add repeater frequencies from database
        if band.lower() in ['2m', '70cm']:
            freq_info = self.db.get_frequency_ranges()
            for freq_range in freq_info:
                if freq_range['name'].lower() == band.lower():
                    # Get known repeaters in this band
                    cursor = self.db.conn.cursor()
                    cursor.execute(
                        """
                        SELECT DISTINCT frequency_hz
                        FROM devices
                        WHERE frequency_hz BETWEEN ? AND ?
                          AND (device_type LIKE '%repeater%' OR name LIKE '%repeater%')
                    """,
                        (freq_range['start_hz'], freq_range['end_hz']),
                    )

                    for row in cursor.fetchall():
                        freq_mhz = row[0] / 1e6
                        if freq_mhz not in frequencies:
                            frequencies.append(freq_mhz)

        self.log_info(f"\n{'='*70}")
        self.log_info(f'VOICE BAND SCAN: {band.upper()}')
        self.log_info(f"{'='*70}")
        self.log_info(f'Frequencies: {len(frequencies)}')
        self.log_info(f'Dwell Time: {dwell_time_sec}s per frequency')
        self.log_info(f'Total Scan Time: {len(frequencies) * dwell_time_sec / 60:.1f} minutes')
        self.log_info(f"{'='*70}\n")

        try:
            for freq_mhz in frequencies:
                freq_hz = freq_mhz * 1e6
                self.log_debug(f'[{freq_mhz:.4f} MHz] Listening...')

                # Start monitoring this frequency
                self.start_monitoring_frequency(
                    frequency_hz=freq_hz,
                    mode='FM',
                    duration_sec=dwell_time_sec,
                    auto_record=False,  # Don't record during scan
                )

                # Wait for dwell time
                time.sleep(dwell_time_sec)

                # Stop monitoring
                self.stop_monitoring()

                self.log_info()

        except KeyboardInterrupt:
            self.log_info('\n\nScan interrupted.')
            self.stop_monitoring()

    def monitor_multiple_frequencies(
        self, frequencies_mhz: list[float], mode: str = 'FM', auto_record: bool = True
    ):
        """Monitor multiple frequencies (requires multiple SDRs or rapid scanning)

        Args:
            frequencies_mhz: List of frequencies in MHz
            mode: Demodulation mode
            auto_record: Auto-record voice activity
        """
        self.log_info(f"\n{'='*70}")
        self.log_info('MULTI-FREQUENCY VOICE MONITOR')
        self.log_info(f"{'='*70}")
        self.log_info(f'Monitoring {len(frequencies_mhz)} frequencies')
        self.log_info(f'Mode: {mode}')
        self.log_info(f"Recording: {'Enabled' if auto_record else 'Disabled'}")
        self.log_info(f"{'='*70}\n")

        for freq_mhz in frequencies_mhz:
            self.log_info(f'  {freq_mhz:.4f} MHz')

        self.log_info('\nPress Ctrl+C to stop\n')

        try:
            # Rapid scanning approach (switches between freqs)
            while True:
                for freq_mhz in frequencies_mhz:
                    if not self.is_monitoring:
                        break

                    freq_hz = freq_mhz * 1e6

                    # Monitor each freq for short period
                    self.start_monitoring_frequency(
                        frequency_hz=freq_hz,
                        mode=mode,
                        duration_sec=2,  # 2 second dwell
                        auto_record=False,  # Manual record on activity
                    )

                    time.sleep(2)
                    self.stop_monitoring()

        except KeyboardInterrupt:
            self.log_info('\n\nMonitoring stopped.')
            self.stop_monitoring()


# ========== CLI INTERFACE ==========

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Voice Traffic Monitor')
    parser.add_argument('--freq', type=float, help='Frequency to monitor (MHz)')
    parser.add_argument(
        '--mode',
        type=str,
        default='FM',
        choices=['FM', 'NFM', 'WFM', 'AM', 'USB', 'LSB'],
        help='Demodulation mode',
    )
    parser.add_argument('--duration', type=int, help='Duration in seconds (default: continuous)')
    parser.add_argument('--record', action='store_true', help='Auto-record audio')
    parser.add_argument(
        '--scan',
        type=str,
        choices=['2m', '70cm', 'gmrs', 'frs', 'marine'],
        help='Scan a voice band',
    )
    parser.add_argument(
        '--dwell', type=int, default=5, help='Dwell time per frequency when scanning (seconds)'
    )

    args = parser.parse_args()

    monitor = VoiceMonitor()

    try:
        if args.scan:
            monitor.scan_voice_bands(band=args.scan, dwell_time_sec=args.dwell)
        elif args.freq:
            monitor.start_monitoring_frequency(
                frequency_hz=args.freq * 1e6,
                mode=args.mode,
                duration_sec=args.duration,
                auto_record=args.record,
            )

            # If continuous, wait for Ctrl+C
            if not args.duration:
                try:
                    while monitor.is_monitoring:
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
        else:
            parser.print_help()

    finally:
        monitor.stop_monitoring()
