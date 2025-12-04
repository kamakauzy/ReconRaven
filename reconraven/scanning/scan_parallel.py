"""
Parallel Spectrum Scanner Module
Uses multiple SDRs to scan different frequency bands simultaneously.
"""

import queue
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np

from reconraven.core.debug_helper import DebugHelper


@dataclass
class BandAssignment:
    """Band assignment for a specific SDR."""

    sdr_index: int
    band_name: str
    start_hz: float
    end_hz: float
    priority: int = 2


class ParallelScanner(DebugHelper):
    """Parallel scanner using multiple SDRs for simultaneous band coverage."""

    def __init__(self, sdr_controller, config: dict = None):
        super().__init__(component_name='ParallelScanner')
        self.debug_enabled = True
        """Initialize parallel scanner.

        Args:
            sdr_controller: SDRController instance with multiple SDRs
            config: Configuration dictionary
        """
        self.sdr = sdr_controller
        self.config = config or {}
        self.num_sdrs = len(self.sdr.sdrs)
        self.band_assignments = self._load_band_assignments()
        self.running = False
        self.results_queue = queue.Queue()
        self.scan_threads = []

        self.log_info(f'Parallel scanner initialized with {self.num_sdrs} SDRs')

    def _load_band_assignments(self) -> List[BandAssignment]:
        """Load band assignments from configuration.

        Returns:
            List of BandAssignment objects
        """
        assignments = []
        parallel_config = self.config.get('parallel_scan_assignments', {})

        # Default assignments if not configured
        if not parallel_config and self.num_sdrs >= 4:
            # Default 4-SDR assignment
            defaults = [
                {'bands': ['2m Amateur Band'], 'priority': 3},
                {'bands': ['70cm Amateur Band'], 'priority': 3},
                {'bands': ['ISM 433 MHz', 'ISM 868 MHz (EU)'], 'priority': 4},
                {'bands': ['ISM 915 MHz (US)'], 'priority': 4},
            ]
            parallel_config = {f'sdr{i}': defaults[i] for i in range(min(4, self.num_sdrs))}

        # Convert to BandAssignment objects
        from config import get_config

        all_bands = get_config().get_scan_bands()

        for sdr_idx in range(self.num_sdrs):
            sdr_key = f'sdr{sdr_idx}'
            if sdr_key in parallel_config:
                assigned_band_names = parallel_config[sdr_key].get('bands', [])
                priority = parallel_config[sdr_key].get('priority', 2)

                # Find matching bands
                for band_name in assigned_band_names:
                    for band in all_bands:
                        if band.get('name') == band_name:
                            assignment = BandAssignment(
                                sdr_index=sdr_idx,
                                band_name=band_name,
                                start_hz=band['start_hz'],
                                end_hz=band['end_hz'],
                                priority=priority,
                            )
                            assignments.append(assignment)
                            break

        self.log_info(f'Loaded {len(assignments)} band assignments across {self.num_sdrs} SDRs')
        return assignments

    def start_parallel_scan(self):
        """Start parallel scanning threads."""
        if self.running:
            self.log_warning('Parallel scan already running')
            return

        self.running = True

        # Group assignments by SDR
        sdr_bands = {}
        for assignment in self.band_assignments:
            if assignment.sdr_index not in sdr_bands:
                sdr_bands[assignment.sdr_index] = []
            sdr_bands[assignment.sdr_index].append(assignment)

        # Start thread for each SDR
        for sdr_idx, bands in sdr_bands.items():
            thread = threading.Thread(
                target=self._scan_worker,
                args=(sdr_idx, bands),
                daemon=True,
                name=f'Scanner-SDR{sdr_idx}',
            )
            thread.start()
            self.scan_threads.append(thread)

        self.log_info(f'Started {len(self.scan_threads)} parallel scan threads')

    def stop_parallel_scan(self):
        """Stop all parallel scanning threads."""
        self.log_info('Stopping parallel scan threads...')
        self.running = False

        # Wait for threads to finish
        for thread in self.scan_threads:
            thread.join(timeout=5)

        self.scan_threads = []
        self.log_info('Parallel scan stopped')

    def _scan_worker(self, sdr_idx: int, bands: List[BandAssignment]):
        """Worker thread for scanning assigned bands on one SDR.

        Args:
            sdr_idx: SDR index
            bands: List of bands to scan
        """
        self.log_info(f'SDR{sdr_idx} worker started with {len(bands)} bands')

        while self.running:
            try:
                for band in bands:
                    if not self.running:
                        break

                    # Use rtl_power for fast sweep
                    results = self._rtl_power_scan(sdr_idx, band)

                    if results:
                        # Put results in queue for processing
                        for result in results:
                            self.results_queue.put(result)

                # Brief pause between full cycles
                time.sleep(0.1)

            except Exception as e:
                self.log_error(f'Error in SDR{sdr_idx} scan worker: {e}')
                time.sleep(1)

        self.log_info(f'SDR{sdr_idx} worker stopped')

    def _rtl_power_scan(self, sdr_idx: int, band: BandAssignment) -> List[Dict[str, Any]]:
        """Perform rtl_power scan on a band.

        Args:
            sdr_idx: SDR device index
            band: Band to scan

        Returns:
            List of detected signals
        """
        try:
            # Use rtl_power for fast FFT sweep
            # Output format: date, time, Hz low, Hz high, Hz step, samples, dB, dB, dB...
            cmd = [
                'rtl_power',
                '-d',
                str(sdr_idx),
                '-f',
                f'{int(band.start_hz)}:{int(band.end_hz)}:25k',
                '-i',
                '0.5',  # 0.5 second integration
                '-1',  # Single sweep
                '-',  # Output to stdout
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=False)

            if result.returncode != 0:
                self.log_debug(f'rtl_power error on SDR{sdr_idx}: {result.stderr}')
                return []

            # Parse rtl_power output
            return self._parse_rtl_power_output(result.stdout, band)

        except subprocess.TimeoutExpired:
            self.log_warning(f'rtl_power timeout on SDR{sdr_idx}')
            return []
        except FileNotFoundError:
            # rtl_power not available, fallback to pyrtlsdr
            self.log_debug(f'rtl_power not found, using pyrtlsdr for SDR{sdr_idx}')
            return self._pyrtlsdr_scan(sdr_idx, band)
        except Exception as e:
            self.log_error(f'Error in rtl_power scan: {e}')
            return []

    def _parse_rtl_power_output(self, output: str, band: BandAssignment) -> List[Dict[str, Any]]:
        """Parse rtl_power output and detect peaks.

        Args:
            output: rtl_power output text
            band: Band information

        Returns:
            List of detected signals
        """
        signals = []
        threshold = self.config.get('detection_threshold_dbm', -60)

        try:
            for line in output.strip().split('\n'):
                if not line:
                    continue

                parts = line.split(',')
                if len(parts) < 7:
                    continue

                # Extract frequency range and power values
                freq_low = float(parts[2])
                freq_high = float(parts[3])
                freq_step = float(parts[4])
                power_values = [float(p) for p in parts[6:]]

                # Find peaks above threshold
                for i, power in enumerate(power_values):
                    if power > threshold:
                        freq = freq_low + (i * freq_step)

                        signals.append(
                            {
                                'sdr_index': band.sdr_index,
                                'band_name': band.band_name,
                                'frequency_hz': freq,
                                'power_dbm': power,
                                'bandwidth_hz': 25000,  # Approximate
                                'timestamp': time.time(),
                                'source': 'rtl_power',
                            }
                        )

        except Exception as e:
            self.log_error(f'Error parsing rtl_power output: {e}')

        return signals

    def _pyrtlsdr_scan(self, sdr_idx: int, band: BandAssignment) -> List[Dict[str, Any]]:
        """Fallback scan using pyrtlsdr.

        Args:
            sdr_idx: SDR device index
            band: Band to scan

        Returns:
            List of detected signals
        """
        signals = []

        try:
            if sdr_idx >= len(self.sdr.sdrs):
                return []

            sdr = self.sdr.sdrs[sdr_idx]
            threshold = self.config.get('detection_threshold_dbm', -60)

            # Quick sweep
            bandwidth = sdr.sample_rate
            num_steps = int((band.end_hz - band.start_hz) / (bandwidth * 0.8))

            for step in range(min(num_steps, 10)):  # Limit steps for speed
                if not self.running:
                    break

                center_freq = band.start_hz + (step * bandwidth * 0.8)
                sdr.center_freq = int(center_freq)

                # Quick sample
                samples = sdr.read_samples(8192)

                # FFT
                fft = np.fft.fft(samples)
                fft_shifted = np.fft.fftshift(fft)
                power = np.abs(fft_shifted) ** 2
                power_db = 10 * np.log10(power + 1e-10) - 60

                # Find peaks
                peaks = np.where(power_db > threshold)[0]

                for peak_idx in peaks:
                    freq_offset = (peak_idx - len(power_db) / 2) * (bandwidth / len(power_db))
                    freq = center_freq + freq_offset

                    if band.start_hz <= freq <= band.end_hz:
                        signals.append(
                            {
                                'sdr_index': sdr_idx,
                                'band_name': band.band_name,
                                'frequency_hz': freq,
                                'power_dbm': float(power_db[peak_idx]),
                                'bandwidth_hz': 25000,
                                'timestamp': time.time(),
                                'source': 'pyrtlsdr',
                            }
                        )

        except Exception as e:
            self.log_error(f'Error in pyrtlsdr scan: {e}')

        return signals

    def get_results(self, timeout: float = 0.1) -> List[Dict[str, Any]]:
        """Get scan results from queue.

        Args:
            timeout: Timeout for queue get

        Returns:
            List of signal detections
        """
        results = []

        try:
            while True:
                result = self.results_queue.get(timeout=timeout)
                results.append(result)
        except queue.Empty:
            pass

        return results

    def get_coverage_status(self) -> Dict[str, Any]:
        """Get status of parallel scan coverage.

        Returns:
            Dictionary with coverage information
        """
        status = {
            'num_sdrs': self.num_sdrs,
            'running': self.running,
            'active_threads': sum(1 for t in self.scan_threads if t.is_alive()),
            'bands_covered': [],
        }

        for assignment in self.band_assignments:
            status['bands_covered'].append(
                {
                    'sdr': assignment.sdr_index,
                    'band': assignment.band_name,
                    'start_mhz': assignment.start_hz / 1e6,
                    'end_mhz': assignment.end_hz / 1e6,
                    'priority': assignment.priority,
                }
            )

        return status
