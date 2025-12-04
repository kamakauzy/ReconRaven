#!/usr/bin/env python3
"""
Advanced Scanner with Demodulation & Recording
Can decode analog signals (FM/AM) and record ham/433 MHz traffic
"""

import signal
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from rtlsdr import RtlSdr
from web.server import SDRDashboardServer

from database import get_db
from recording_manager import RecordingManager


class AdvancedScanner:
    def __init__(self, dashboard_server=None, num_sdrs=None):
        """
        Initialize scanner with optional multi-SDR support.

        Args:
            dashboard_server: Optional dashboard for real-time updates
            num_sdrs: Number of SDRs to use (None = auto-detect, 1 = single mode, 4+ = concurrent mode)
        """
        self.sdr = None
        self.sdrs = []  # Multiple SDRs for concurrent scanning
        self.num_sdrs = num_sdrs
        self.concurrent_mode = False
        self.baseline = {}
        self.recording = False
        self.demod_process = None
        self.db = get_db()
        self.dashboard = dashboard_server
        self.recording_manager = RecordingManager(self.db)

        # Voice detection and transcription
        from voice_detector import VoiceDetector

        self.voice_detector = VoiceDetector()
        self.voice_transcriber = None  # Lazy load when needed

        # Output directories
        self.output_dir = Path('recordings')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'audio').mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'logs').mkdir(parents=True, exist_ok=True)

        # Register cleanup handlers
        import atexit

        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Comprehensive frequency scanning - ALL bands
        self.scan_freqs = []

        # 2m Amateur Band (144-148 MHz) - every 100 kHz
        for freq in range(144000000, 148000000, 100000):
            self.scan_freqs.append(freq)

        # Add important 2m simplex/calling frequencies for guaranteed detection
        important_2m = [
            146.400e6,  # Calling frequency (some regions)
            146.460e6,  # Simplex
            146.520e6,  # National simplex calling frequency
            146.550e6,  # Simplex
            146.562e6,  # User test frequency
            146.580e6,  # Common simplex
            147.420e6,  # Simplex
            147.450e6,  # Simplex
            147.480e6,  # Simplex
            147.510e6,  # Simplex
            147.540e6,  # Simplex
        ]
        self.scan_freqs.extend([f for f in important_2m if f not in self.scan_freqs])

        # 70cm Amateur Band (420-450 MHz) - every 100 kHz
        for freq in range(420000000, 450000000, 100000):
            self.scan_freqs.append(freq)

        # Add important 70cm simplex/calling frequencies
        important_70cm = [
            446.000e6,  # National simplex calling
            446.500e6,  # Simplex
            447.000e6,  # Simplex
            433.500e6,  # ISM/Ham crossover (common for data)
        ]
        self.scan_freqs.extend([f for f in important_70cm if f not in self.scan_freqs])

        # 433 MHz ISM Band (433.05-434.79 MHz) - every 25 kHz for high resolution
        for freq in range(433050000, 434790000, 25000):
            self.scan_freqs.append(freq)

        # 915 MHz ISM Band (902-928 MHz) - every 100 kHz
        for freq in range(902000000, 928000000, 100000):
            self.scan_freqs.append(freq)

        # Sort frequencies for efficient scanning (avoid large jumps)
        self.scan_freqs.sort()

        print(f'Loaded {len(self.scan_freqs)} scan frequencies')
        print(f'  - 2m band: {sum(1 for f in self.scan_freqs if 144e6 <= f <= 148e6)} freqs')
        print(f'  - 70cm band: {sum(1 for f in self.scan_freqs if 420e6 <= f <= 450e6)} freqs')
        print(
            f'  - ISM bands: {sum(1 for f in self.scan_freqs if 433e6 <= f <= 435e6 or 902e6 <= f <= 928e6)} freqs'
        )

        # Dynamically determine band names
        self.band_names = {}

        # Signal type detection
        self.signal_types = {
            '2m': 'FM',  # Narrowband FM for ham voice
            '70cm': 'FM',  # Narrowband FM for ham voice
            'ISM433': 'ASK',  # Usually ASK/OOK for remotes
            'ISM915': 'FSK',  # Often FSK for data
        }

    def init_sdr(self):
        """Initialize RTL-SDR(s) - auto-detects and uses multiple if available"""
        try:
            # Detect how many SDRs are available
            from rtlsdr import librtlsdr

            available_sdrs = librtlsdr.rtlsdr_get_device_count()

            if available_sdrs == 0:
                print('No RTL-SDR devices found!')
                return False

            # Determine mode
            if self.num_sdrs is None:
                # Auto-detect: use all available SDRs if 3+, otherwise single mode
                if available_sdrs >= 3:  # Changed from 4 to 3
                    self.num_sdrs = available_sdrs
                    self.concurrent_mode = True
                else:
                    self.num_sdrs = 1
                    self.concurrent_mode = False
            elif self.num_sdrs > 1:
                self.concurrent_mode = True
                if self.num_sdrs > available_sdrs:
                    print(
                        f'Warning: Requested {self.num_sdrs} SDRs but only {available_sdrs} available'
                    )
                    self.num_sdrs = available_sdrs

            # Initialize SDR(s)
            if self.concurrent_mode:
                print(f'Initializing {self.num_sdrs} RTL-SDRs for CONCURRENT scanning...')
                successful_sdrs = 0
                for i in range(self.num_sdrs):
                    try:
                        print(f'  SDR #{i}...', end='', flush=True)

                        # Use threading with timeout to prevent hangs
                        sdr_obj = [None]
                        error_obj = [None]

                        def init_sdr_thread(device_idx=i, sdr_container=sdr_obj, error_container=error_obj):
                            try:
                                sdr = RtlSdr(device_index=device_idx)
                                sdr.sample_rate = (
                                    2.8e6  # Increased from 2.4 to 2.8 Msps for better coverage
                                )
                                sdr.gain = 'auto'
                                sdr_container[0] = sdr
                            except Exception as e:
                                error_container[0] = e

                        thread = threading.Thread(target=init_sdr_thread)
                        thread.daemon = True
                        thread.start()
                        thread.join(timeout=15.0)  # 15 second timeout

                        if thread.is_alive():
                            print(' TIMEOUT (hung, skipping)')
                            # Don't wait for it, just continue with other SDRs
                            continue

                        if error_obj[0]:
                            raise error_obj[0]

                        if sdr_obj[0]:
                            self.sdrs.append(sdr_obj[0])
                            successful_sdrs += 1
                            print(' OK', flush=True)
                        else:
                            print(' FAILED (unknown error)')
                            continue

                    except Exception as e:
                        print(f' FAILED: {e}')
                        # Continue with other SDRs instead of failing completely
                        continue

                if successful_sdrs == 0:
                    print('ERROR: No SDRs could be initialized!')
                    return False

                print(f'[+] Concurrent mode enabled with {successful_sdrs} SDRs!', flush=True)
                self.num_sdrs = successful_sdrs  # Update to actual count

                # Update dashboard with mode
                if self.dashboard:
                    self.dashboard.update_status(
                        'CONCURRENT', f'Scanning with {successful_sdrs} SDRs'
                    )
            else:
                print('Initializing RTL-SDR (single mode)...', end='', flush=True)
                self.sdr = RtlSdr()
                self.sdr.sample_rate = 2.8e6  # Increased from 2.4 to 2.8 Msps for better coverage
                self.sdr.gain = 'auto'
                print(' OK')

                # Update dashboard
                if self.dashboard:
                    self.dashboard.update_status('MOBILE', 'Single SDR scanning')

            return True

        except Exception as e:
            print(f' FAILED: {e}')
            return False

    def get_band_name(self, freq):
        """Determine band name from frequency"""
        if 144e6 <= freq <= 148e6:
            return '2m'
        if 420e6 <= freq <= 450e6:
            return '70cm'
        if 433e6 <= freq <= 435e6:
            return 'ISM433'
        if 902e6 <= freq <= 928e6:
            return 'ISM915'
        return 'Unknown'

    def scan_frequency(self, freq):
        """Scan single frequency, return power in dBm"""
        try:
            # Use appropriate SDR (single or first from array)
            active_sdr = self.sdr if self.sdr else (self.sdrs[0] if self.sdrs else None)
            if not active_sdr:
                return None

            active_sdr.center_freq = freq
            time.sleep(0.03)  # Faster scanning
            samples = active_sdr.read_samples(128 * 1024)
            return 10 * np.log10(np.mean(np.abs(samples) ** 2))
        except Exception:
            return None

    def build_baseline(self):
        """Quick baseline - 3 passes"""
        print('\n' + '=' * 70)
        print('BUILDING BASELINE')
        print('=' * 70)
        print(f'Scanning {len(self.scan_freqs)} frequencies x 3 passes...')

        all_readings = defaultdict(list)

        for pass_num in range(3):
            print(f'\nPass {pass_num + 1}/3:', end='', flush=True)
            count = 0
            for freq in self.scan_freqs:
                power = self.scan_frequency(freq)
                if power:
                    all_readings[freq].append(power)
                count += 1
                if count % 50 == 0:
                    print('.', end='', flush=True)
            print(f' done ({count} frequencies)')

        # Calculate baseline and save to database
        for freq, powers in all_readings.items():
            baseline_data = {
                'mean': np.mean(powers),
                'std': np.std(powers),
                'max': np.max(powers),
                'band': self.get_band_name(freq),
            }
            self.baseline[freq] = baseline_data

            # Add to database
            self.db.add_baseline_frequency(
                freq=freq,
                band=baseline_data['band'],
                power=baseline_data['mean'],
                std=baseline_data['std'],
            )

        print(f'\nBaseline complete: {len(self.baseline)} frequencies')
        return True

    def record_signal(self, freq, duration=3):
        """Record raw IQ samples"""
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        band = self.get_band_name(freq)
        signal_type = self.signal_types.get(band, 'FM')

        # Filenames
        iq_file = f'{self.output_dir}/audio/{band}_{freq/1e6:.3f}MHz_{timestamp}_{signal_type}.npy'
        log_file = f'{self.output_dir}/logs/signal_log.txt'

        print(f"\n{'='*70}")
        print(f'RECORDING: {freq/1e6:.3f} MHz ({band}) - {signal_type}')
        print(f'Duration: {duration} seconds')
        print(f"{'='*70}")

        # Log to file
        with open(log_file, 'a') as f:
            f.write(f'{timestamp},{freq},{band},{signal_type},recording_start\n')

        try:
            # Capture IQ samples directly
            print('Capturing raw IQ samples...')

            # Use first available SDR (either single or from array)
            active_sdr = self.sdr if self.sdr else self.sdrs[0]

            active_sdr.center_freq = freq
            time.sleep(0.1)

            # Record for specified duration - read in chunks to avoid USB memory issues
            samples_per_sec = int(active_sdr.sample_rate)
            total_samples = samples_per_sec * duration

            # Read in smaller chunks (256K samples at a time) for WSL USB compatibility
            chunk_size = 256 * 1024
            num_chunks = int(total_samples / chunk_size)

            print(
                f'Reading {total_samples / 1e6:.1f}M samples in {num_chunks} chunks @ {samples_per_sec/1e6:.1f} Msps...'
            )

            all_samples = []
            for i in range(num_chunks):
                try:
                    chunk = active_sdr.read_samples(chunk_size)
                    all_samples.append(chunk)
                    if (i + 1) % 5 == 0:
                        print(f'  Progress: {(i+1)/num_chunks*100:.0f}%', end='\r', flush=True)
                except Exception:
                    print(f'\n  Warning: Chunk {i+1} failed, continuing...')
                    break

            if not all_samples:
                raise Exception('Failed to read any samples')

            samples = np.concatenate(all_samples)

            # Save as numpy array
            np.save(iq_file, samples)

            iq_path = Path(iq_file)
            size = iq_path.stat().st_size / (1024 * 1024)  # MB
            print(f'SUCCESS! IQ recording saved: {iq_file}')
            print(f'File size: {size:.1f} MB')
            print('To replay: Use GQRX, URH, or Inspectrum')

            # Add to database
            try:
                filename = iq_path.name
                self.db.add_recording(
                    filename=filename, freq=freq, band=band, duration=duration, file_size_mb=size
                )

                # Update dashboard if connected
                if self.dashboard:
                    self.dashboard.update_state(
                        {'recording_count': self.db.get_statistics()['total_recordings']}
                    )
            except Exception as e:
                print(f'Database error: {e}')

            with open(log_file, 'a') as f:
                f.write(f'{timestamp},{freq},{band},{signal_type},iq_complete,{size:.1f}MB\n')

            return iq_path.name  # Return filename

        except Exception as e:
            print(f'RECORDING ERROR: {e}')
            import traceback

            traceback.print_exc()
            with open(log_file, 'a') as f:
                f.write(f'{timestamp},{freq},{band},{signal_type},error,{e!s}\n')
            return None  # Return None on error

    def analyze_recording(self, filepath):
        """Quick auto-analysis of recording to identify device"""
        try:
            # Use field_analyzer for comprehensive analysis
            import subprocess

            result = subprocess.run(
                [sys.executable, 'field_analyzer.py', filepath],
                capture_output=True,
                text=True,
                timeout=180,
                check=False,  # 3 minute timeout - reduced recording size should complete faster
            )

            if result.returncode == 0:
                # Parse output for device identification
                output = result.stdout

                # Look for identification patterns
                device_name = 'Unknown Device'
                manufacturer = 'Unknown'
                device_type = 'Unknown Type'
                confidence = 0.5

                # Simple parsing - look for common patterns
                if 'Weather Station' in output:
                    device_name = 'Weather Station'
                    device_type = 'weather_sensor'
                    confidence = 0.8
                elif 'Garage Door' in output or 'Remote Control' in output:
                    device_name = 'Remote Control'
                    device_type = 'remote'
                    confidence = 0.7
                elif 'TPMS' in output:
                    device_name = 'TPMS Sensor'
                    device_type = 'automotive'
                    confidence = 0.75
                elif 'sensor' in output.lower():
                    device_name = 'Wireless Sensor'
                    device_type = 'sensor'
                    confidence = 0.6

                print(
                    f'[Analysis] Identified as: {device_name} (Confidence: {confidence*100:.0f}%)'
                )

                return {
                    'name': device_name,
                    'manufacturer': manufacturer,
                    'device_type': device_type,
                    'confidence': confidence,
                }
            print(f'[Analysis] Failed: {result.stderr[:100]}')
            return None

        except subprocess.TimeoutExpired:
            print('[Analysis] Timeout - skipping')
            return None
        except Exception as e:
            print(f'[Analysis] Error: {e}')
            return None

    def monitor_with_recording(self):
        """Monitor for anomalies and record strong signals"""
        print('\n' + '=' * 70)
        print('MONITORING MODE - Will record strong signals')
        print('Commands:')
        print('  - Anomalies >15 dB above baseline = AUTO-RECORD 3 seconds')
        print('  - Press Ctrl+C to stop')
        print('=' * 70)

        # Ensure baseline exists
        if not self.baseline:
            print('\nERROR: No baseline available. Run build_baseline() first.')
            return

        # Update dashboard with initial state
        if self.dashboard:
            mode = 'CONCURRENT' if self.concurrent_mode else 'MOBILE'
            self.dashboard.update_state({'mode': mode, 'status': 'scanning', 'scanning': True})

        scan_num = 0

        # If concurrent mode, use threaded scanning
        if self.concurrent_mode:
            self._concurrent_monitor_with_recording()
            return

        try:
            while True:
                scan_num += 1
                print(f"\n[Scan #{scan_num}] {time.strftime('%H:%M:%S')} - ", end='', flush=True)

                strong_signals = []

                for freq in self.scan_freqs:
                    power = self.scan_frequency(freq)
                    if power and freq in self.baseline:
                        baseline = self.baseline[freq]
                        delta = power - baseline['mean']

                        # Check for strong anomaly (worth recording)
                        if delta > 15:
                            strong_signals.append(
                                {
                                    'freq': freq,
                                    'power': power,
                                    'baseline': baseline['mean'],
                                    'delta': delta,
                                    'band': baseline['band'],
                                }
                            )

                if strong_signals:
                    print(f'*** {len(strong_signals)} STRONG SIGNAL(S) - RECORDING ***')

                    for sig in strong_signals:
                        print(
                            f"  [{sig['band']}] {sig['freq']/1e6:.3f} MHz: {sig['power']:.1f} dBm (+{sig['delta']:.1f} dB)"
                        )

                        # Record this signal FIRST
                        recording_file = self.record_signal(sig['freq'], duration=3)

                        # Auto-analyze the recording
                        device_info = None
                        recording_id = None
                        if recording_file:
                            # Get recording ID from database
                            recordings = self.db.get_recordings()
                            for rec in recordings:
                                if rec['filename'] == recording_file:
                                    recording_id = rec['id']
                                    break

                            print(f'\n[Auto-Analysis] Analyzing {recording_file}...')
                            device_info = self.analyze_recording(
                                f'{self.output_dir}/audio/{recording_file}'
                            )

                            # Auto-cleanup based on band
                            if device_info and recording_id:
                                self.recording_manager.cleanup_after_analysis(
                                    recording_id, device_info
                                )

                        # Add to database as anomaly AFTER recording WITH analysis results
                        signal_kwargs = {}
                        if device_info:
                            signal_kwargs.update(
                                {
                                    'device_name': device_info.get('name'),
                                    'device_type': device_info.get('device_type'),
                                    'manufacturer': device_info.get('manufacturer'),
                                    'confidence': device_info.get('confidence'),
                                }
                            )

                        self.db.add_signal(
                            freq=sig['freq'],
                            band=sig['band'],
                            power=sig['power'],
                            baseline_power=sig['baseline'],
                            is_anomaly=True,
                            recording_file=recording_file,
                            **signal_kwargs,
                        )

                        # Notify dashboard of new signal with filename
                        if self.dashboard:
                            signal_data = {
                                'frequency_hz': sig['freq'],
                                'band': sig['band'],
                                'power_dbm': sig['power'],
                                'baseline_power_dbm': sig['baseline'],
                                'delta_db': sig['delta'],
                                'detected_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                                'filename': recording_file,
                            }

                            # If identified, add device info
                            if device_info:
                                signal_data.update(device_info)

                            self.dashboard.add_signal(signal_data)

                    # Update dashboard stats
                    if self.dashboard:
                        stats = self.db.get_statistics()
                        self.dashboard.update_state(
                            {
                                'anomaly_count': stats['anomalies'],
                                'recording_count': stats['total_recordings'],
                                'device_count': stats['identified_devices'],
                            }
                        )

                else:
                    print('Monitoring - no strong signals')

                time.sleep(3)

        except KeyboardInterrupt:
            print(f'\n\nStopped after {scan_num} scans')

    def _concurrent_monitor_with_recording(self):
        """Monitor with 4 SDRs scanning in parallel"""
        print(f'\n[CONCURRENT MODE] Using {self.num_sdrs} SDRs for real-time coverage!\n')

        # Split frequencies by BAND for efficient scanning (no constant retuning)
        # Group frequencies by band first
        band_freqs = {'2m': [], '70cm': [], 'ISM433': [], 'ISM915': []}

        for freq in self.scan_freqs:
            band = self.get_band_name(freq)
            if band in band_freqs:
                band_freqs[band].append(freq)

        # Assign bands to SDRs based on how many we have
        freq_chunks = [[] for _ in range(self.num_sdrs)]

        if self.num_sdrs == 3:
            # 3 SDRs: SDR0=2m, SDR1=70cm, SDR2=ISM (both 433+915)
            freq_chunks[0] = band_freqs['2m']
            freq_chunks[1] = band_freqs['70cm']
            freq_chunks[2] = band_freqs['ISM433'] + band_freqs['ISM915']
        elif self.num_sdrs >= 4:
            # 4+ SDRs: SDR0=2m, SDR1=70cm, SDR2=433MHz, SDR3=915MHz
            freq_chunks[0] = band_freqs['2m']
            freq_chunks[1] = band_freqs['70cm']
            freq_chunks[2] = band_freqs['ISM433']
            freq_chunks[3] = band_freqs['ISM915']
            # Any additional SDRs can help with the largest band
            if self.num_sdrs > 4:
                # Split 70cm across extra SDRs (it's the largest)
                largest_band = band_freqs['70cm']
                split_size = len(largest_band) // (self.num_sdrs - 3)
                for i in range(4, self.num_sdrs):
                    start = (i - 4) * split_size
                    freq_chunks[i] = largest_band[start : start + split_size]
        else:
            # Fallback: round-robin if unexpected SDR count
            for i, freq in enumerate(self.scan_freqs):
                freq_chunks[i % self.num_sdrs].append(freq)

        # Display SDR assignments
        print('=' * 70)
        print('SDR FREQUENCY ASSIGNMENTS')
        print('=' * 70)
        for i, chunk in enumerate(freq_chunks):
            if chunk:
                # Group by band
                band_ranges = {}
                for freq in chunk:
                    band = self.get_band_name(freq)
                    if band not in band_ranges:
                        band_ranges[band] = []
                    band_ranges[band].append(freq)

                # Display summary
                print(f'SDR #{i} ({len(chunk)} freqs):')
                for band, freqs in sorted(band_ranges.items()):
                    min_freq = min(freqs) / 1e6
                    max_freq = max(freqs) / 1e6
                    print(
                        f'  {band:12s}: {min_freq:>7.2f} - {max_freq:>7.2f} MHz ({len(freqs)} freqs)'
                    )
        print('=' * 70 + '\n')

        # Update dashboard with SDR assignments
        if self.dashboard:
            sdr_info = []
            for i, chunk in enumerate(freq_chunks):
                if chunk:
                    band_ranges = {}
                    for freq in chunk:
                        band = self.get_band_name(freq)
                        if band not in band_ranges:
                            band_ranges[band] = {'min': freq, 'max': freq, 'count': 0}
                        band_ranges[band]['min'] = min(band_ranges[band]['min'], freq)
                        band_ranges[band]['max'] = max(band_ranges[band]['max'], freq)
                        band_ranges[band]['count'] += 1

                    sdr_info.append({'index': i, 'freq_count': len(chunk), 'bands': band_ranges})

            self.dashboard.update_state(
                {'mode': 'CONCURRENT', 'num_sdrs': self.num_sdrs, 'sdr_assignments': sdr_info}
            )

        scan_num = 0

        try:
            while True:
                scan_num += 1
                scan_time = time.strftime('%H:%M:%S')

                # Scan all frequencies in parallel using all SDRs
                results = {}
                threads = []

                def scan_chunk(sdr_idx, freqs, result_dict=results):
                    sdr = self.sdrs[sdr_idx]
                    for freq in freqs:
                        try:
                            sdr.center_freq = freq
                            time.sleep(0.01)  # Let SDR settle
                            samples = sdr.read_samples(256 * 1024)
                            power_dbm = 10 * np.log10(np.mean(np.abs(samples) ** 2) + 1e-10)
                            result_dict[freq] = power_dbm
                        except Exception:
                            pass

                # Start all SDRs scanning in parallel
                for i, chunk in enumerate(freq_chunks):
                    t = threading.Thread(target=scan_chunk, args=(i, chunk))
                    t.start()
                    threads.append(t)

                # Wait for all to complete
                for t in threads:
                    t.join()

                # Check for anomalies
                strong_signals = []
                for freq, power in results.items():
                    if freq in self.baseline:
                        baseline = self.baseline[freq]
                        delta = power - baseline['mean']

                        if delta > 15:  # Strong anomaly
                            strong_signals.append(
                                {
                                    'freq': freq,
                                    'power': power,
                                    'delta': delta,
                                    'band': self.get_band_name(freq),
                                    'baseline': baseline['mean'],
                                }
                            )

                # Display results and record
                if strong_signals:
                    print(
                        f'[Scan #{scan_num}] {scan_time} - [!] {len(strong_signals)} ANOMALIES DETECTED!'
                    )
                    for sig in strong_signals[:3]:  # Show top 3
                        print(
                            f"  - {sig['freq']/1e6:.3f} MHz ({sig['band']}) - {sig['power']:.1f} dBm (+{sig['delta']:.1f} dB)"
                        )

                    # Record strongest signal FIRST
                    strongest = max(strong_signals, key=lambda x: x['delta'])
                    print(f"\n  [REC] Recording strongest: {strongest['freq']/1e6:.3f} MHz...")
                    recording_file = self.record_signal(strongest['freq'], duration=3)

                    # Now save to database WITH the recording filename
                    self.db.add_signal(
                        freq=strongest['freq'],
                        band=strongest['band'],
                        power=strongest['power'],
                        baseline_power=strongest['baseline'],
                        is_anomaly=True,
                        recording_file=recording_file,
                    )
                else:
                    print(
                        f'[Scan #{scan_num}] {scan_time} - Monitoring ({len(results)} freqs checked)'
                    )

                # Update dashboard
                if self.dashboard and strong_signals:
                    for sig in strong_signals:
                        self.dashboard.add_signal(
                            {
                                'frequency_hz': sig['freq'],
                                'power_dbm': sig['power'],
                                'delta_db': sig['delta'],
                                'band': sig['band'],
                                'is_anomaly': True,
                            }
                        )

                time.sleep(3)  # Scan every 3 seconds

        except KeyboardInterrupt:
            print(f'\n\nStopped after {scan_num} scans')

    def _signal_handler(self, signum, frame):
        """Handle signals for graceful shutdown"""
        print(f'\n[CLEANUP] Received signal {signum}, cleaning up...')
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        """Clean up all SDR resources - ALWAYS called on exit"""
        try:
            print('[CLEANUP] Releasing SDR devices...')

            # Close concurrent SDRs
            if self.sdrs:
                for i, sdr in enumerate(self.sdrs):
                    try:
                        print(f'[CLEANUP] Closing SDR #{i}...')
                        sdr.close()
                    except Exception as e:
                        print(f'[CLEANUP] Error closing SDR #{i}: {e}')
                self.sdrs = []

            # Close single SDR
            if self.sdr:
                try:
                    print('[CLEANUP] Closing primary SDR...')
                    self.sdr.close()
                    self.sdr = None
                except Exception as e:
                    print(f'[CLEANUP] Error closing primary SDR: {e}')

            print('[CLEANUP] All SDRs released!')

        except Exception as e:
            print(f'[CLEANUP] Error during cleanup: {e}')

    def close(self):
        """Legacy close method - calls cleanup"""
        self.cleanup()


def main():
    print('\n' + '#' * 70)
    print('# ReconRaven - Advanced Scanner with Recording')
    print('# Detects, demodulates, and records ham/433/915 MHz signals')
    print('#' * 70)

    # Start dashboard in background
    print('\nStarting dashboard...')
    # Kill any existing dashboard processes
    import psutil

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and any(
                'server.py' in str(c) or 'dashboard' in str(c).lower() for c in cmdline
            ):
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    time.sleep(1)

    dashboard = SDRDashboardServer({'host': '0.0.0.0', 'port': 5000})
    dashboard.run_threaded()
    time.sleep(2)

    # Load database stats
    db = get_db()
    stats = db.get_statistics()

    # Initialize dashboard state
    dashboard.update_state(
        {
            'mode': 'scanning',
            'status': 'initializing',
            'baseline_count': stats['baseline_frequencies'],
            'device_count': 0,  # Start at 0 - will increment as devices are detected
            'recording_count': stats['total_recordings'],
            'anomaly_count': 0,  # Start at 0 - will increment as anomalies detected
            'identified_devices': [],  # Empty - will populate as signals detected
            'signals': [],  # Empty - will populate as anomalies detected
        }
    )

    print('Dashboard: http://localhost:5000')
    print(
        f"Database: {stats['total_recordings']} recordings, {stats['identified_devices']} devices"
    )

    # Create scanner with dashboard integration
    scanner = AdvancedScanner(dashboard_server=dashboard)

    try:
        if not scanner.init_sdr():
            sys.exit(1)

        # Build or load baseline
        if stats['baseline_frequencies'] == 0:
            print('\nNo baseline found. Building baseline...')
            scanner.build_baseline()
        else:
            print(f"\nLoading existing baseline ({stats['baseline_frequencies']} frequencies)...")
            for entry in db.get_baseline():
                scanner.baseline[entry['frequency_hz']] = {
                    'mean': entry['power_dbm'],
                    'std': entry['std_dbm'] or 5.0,
                    'max': entry['power_dbm'] + 10,
                    'band': entry['band'],
                }
            print(f'Loaded {len(scanner.baseline)} frequencies')

        dashboard.update_state({'status': 'monitoring', 'baseline_count': len(scanner.baseline)})
        scanner.monitor_with_recording()

    except Exception as e:
        print(f'\nError: {e}')
        import traceback

        traceback.print_exc()
    finally:
        scanner.close()
        dashboard.update_state({'status': 'stopped', 'mode': 'idle'})
        print("\nSDR closed. Check 'recordings/' folder for captured audio!")
        print('Dashboard still running at http://localhost:5000')


if __name__ == '__main__':
    main()
