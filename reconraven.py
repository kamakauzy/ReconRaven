#!/usr/bin/env python3
"""
ReconRaven - Unified Command-Line Interface

All-in-one tool for scanning, analysis, and database management.
"""

import argparse
import contextlib
import os
import sys
import time

import numpy as np

from database import get_db


def cmd_voice(args):
    """Voice monitoring and transcription operations"""
    from reconraven.core.database import get_db
    from reconraven.voice.monitor import VoiceMonitor
    from reconraven.voice.transcriber import VoiceTranscriber

    if args.voice_action == 'monitor':
        # Monitor a specific frequency for voice
        if not args.freq:
            print('ERROR: --freq required for monitor')
            return 1

        monitor = VoiceMonitor()
        print(f'Monitoring {args.freq} MHz in {args.mode} mode...')

        try:
            monitor.start_monitoring_frequency(
                frequency_hz=args.freq * 1e6,
                mode=args.mode,
                duration_sec=args.duration,
                auto_record=args.record,
            )
        except KeyboardInterrupt:
            print('\nStopped')

        return 0

    if args.voice_action == 'scan':
        # Scan a band for voice activity
        monitor = VoiceMonitor()
        print(f'Scanning {args.band} band for voice activity...')

        try:
            monitor.scan_band(band=args.band, dwell_time_sec=args.dwell, auto_record=True)
        except KeyboardInterrupt:
            print('\nStopped')

        return 0

    if args.voice_action == 'transcribe':
        # Transcribe a single recording
        if not args.file:
            print('ERROR: --file required for transcribe')
            return 1

        transcriber = VoiceTranscriber(model_size=args.model)
        result = transcriber.transcribe_file(args.file)

        if result:
            print(f'\nTranscription:\n{result["text"]}\n')
            print(f'Language: {result.get("language", "unknown")}')
            print(f'Confidence: {result.get("confidence", 0):.2%}')
        else:
            print('Transcription failed')
            return 1

        return 0

    if args.voice_action == 'batch-transcribe':
        # Batch transcribe untranscribed recordings
        db = get_db()
        transcriber = VoiceTranscriber(model_size=args.model)

        untranscribed = db.get_untranscribed_recordings()
        print(f'Found {len(untranscribed)} untranscribed recordings')

        for i, rec in enumerate(untranscribed, 1):
            print(f'[{i}/{len(untranscribed)}] Transcribing {rec["filename"]}...')
            # Transcription logic here

        return 0
    return None


def cmd_analyze_extended(args):
    """Extended analysis operations (correlation, network, profile)"""
    from reconraven.analysis.correlation import CorrelationEngine
    from reconraven.analysis.field import FieldAnalyzer

    engine = CorrelationEngine()

    if args.analyze_type == 'correlation':
        # Find temporal correlations
        print(f'Finding temporal correlations (window: {args.time_window}s)...')
        correlations = engine.find_temporal_correlations(time_window_seconds=args.time_window)

        print(f'\nFound {len(correlations)} correlated signal pairs:')
        for corr in correlations[:20]:  # Show top 20
            print(f'{corr["frequency1_mhz"]:.3f} MHz ↔ {corr["frequency2_mhz"]:.3f} MHz')
            print(f'  Occurrences: {corr["occurrences"]}, Avg delay: {corr["avg_delay_sec"]:.2f}s')

        return 0

    if args.analyze_type == 'sequences':
        # Find sequential patterns
        print('Finding sequential patterns...')
        sequences = engine.find_sequential_patterns(max_sequence_length=args.max_length)

        print(f'\nFound {len(sequences)} sequences:')
        for seq in sequences[:10]:
            print(f'Sequence: {seq}')

        return 0

    if args.analyze_type == 'profile':
        # Get behavioral profile for a frequency
        if not args.freq:
            print('ERROR: --freq required for profile')
            return 1

        profile = engine.get_device_profile(args.freq * 1e6)
        print(f'\nBehavioral Profile for {args.freq} MHz:')
        print(f'  Transmissions: {profile.get("transmission_count", 0)}')
        print(f'  Pattern: {profile.get("pattern", "unknown")}')

        return 0

    if args.analyze_type == 'network':
        # Build network map
        print('Building device network map...')
        network = engine.build_network_graph()

        if args.output:
            import json

            with open(args.output, 'w') as f:
                json.dump(network, f, indent=2)
            print(f'Network saved to {args.output}')
        else:
            print(f'Network has {len(network.get("nodes", []))} nodes')

        return 0

    if args.analyze_type == 'field':
        # Field analysis
        if not args.file:
            print('ERROR: --file required for field analysis')
            return 1

        analyzer = FieldAnalyzer()
        results = analyzer.analyze_signal(args.file)

        print('\n=== Field Analysis Results ===')
        print(f'File: {results.get("file")}')
        print(f'Identification: {results.get("identification", "Unknown")}')
        print(f'Confidence: {results.get("confidence", 0):.2%}')

        return 0
    return None


def cmd_recording(args):
    """Recording management operations"""
    from reconraven.core.database import get_db
    from reconraven.utils.recording_manager import RecordingManager

    db = get_db()
    RecordingManager(db)

    if args.recording_action == 'list':
        # List recordings
        recordings = db.get_recordings(limit=args.limit or 100)

        print(f'\n{"ID":<6} {"Frequency":<12} {"Band":<8} {"Created":<20}')
        print('=' * 60)

        for rec in recordings:
            freq_mhz = rec['frequency_hz'] / 1e6
            print(
                f'{rec["id"]:<6} {freq_mhz:<12.3f} {rec.get("band", "N/A"):<8} {rec["created_at"]:<20}'
            )

        return 0

    if args.recording_action == 'export':
        # Export recording
        if not args.id:
            print('ERROR: --id required for export')
            return 1

        # Export logic here
        print(f'Exporting recording {args.id} as {args.format}...')
        return 0

    if args.recording_action == 'cleanup':
        # Call existing cleanup logic
        return cmd_cleanup(args)
    return None


def cmd_scan(args):
    """Run scanner with optional dashboard"""
    try:
        import os

        # Kill any existing dashboard processes (but not ourselves!)
        import psutil

        from reconraven.core.scanner import AdvancedScanner

        current_pid = os.getpid()
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.pid == current_pid:
                    continue  # Don't kill ourselves!
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('server.py' in str(c) for c in cmdline):
                    print(f'Killing old dashboard process {proc.pid}')
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        print('Initializing scanner...')
        scanner = AdvancedScanner()

        print('Initializing SDR...')
        if not scanner.init_sdr():
            print('ERROR: Failed to initialize SDR!')
            return 1

        print('[SUCCESS] All SDRs initialized!')

    except Exception as e:
        print(f'FATAL ERROR during initialization: {e}')
        import traceback

        traceback.print_exc()
        return 1

    # Build or load baseline
    db = get_db()
    stats = db.get_statistics()

    if args.rebuild_baseline or stats['baseline_frequencies'] == 0:
        print('Building baseline...')
        scanner.build_baseline()
    else:
        print(f"Loading baseline ({stats['baseline_frequencies']} frequencies)...")
        for entry in db.get_baseline():
            scanner.baseline[entry['frequency_hz']] = {
                'mean': entry['power_dbm'],
                'std': entry['std_dbm'] or 5.0,
                'max': entry['power_dbm'] + 10,
                'band': entry['band'],
            }

    # Start dashboard AFTER SDRs are fully initialized
    dashboard = None
    if args.dashboard:
        from reconraven.web.server import SDRDashboardServer

        print('Starting dashboard...')
        # Dashboard cleanup already done above
        time.sleep(1)
        dashboard = SDRDashboardServer({'host': '0.0.0.0', 'port': 5000})
        dashboard.run_threaded()
        time.sleep(2)
        scanner.dashboard = dashboard
        print('Dashboard: http://localhost:5000')

    # Run scanner
    try:
        if args.quick:
            scanner.build_baseline()
        else:
            scanner.monitor_with_recording()
    except KeyboardInterrupt:
        print('\nStopping...')
    finally:
        scanner.cleanup()  # Use cleanup instead of direct sdr.close()

    return 0


def cmd_analyze(args):
    """Analyze captured signals"""
    import glob
    import subprocess

    # Get files to analyze
    if args.file:
        files = [args.file]
    elif args.all:
        files = glob.glob('recordings/audio/*.npy')
    else:
        print('ERROR: Specify --file <path> or --all')
        return 1

    if not files:
        print('No files found to analyze')
        return 0

    print(f'Analyzing {len(files)} file(s)...')

    for filepath in files:
        print(f"\n{'='*70}")
        print(f'File: {os.path.basename(filepath)}')
        print('=' * 70)

        # Run analysis based on type
        if args.type in ('all', 'ism'):
            print('\n[ISM Analysis]')
            subprocess.run([sys.executable, 'ism_analyzer.py', filepath], check=False)

        if args.type in ('all', 'remote'):
            print('\n[Remote Decoder]')
            subprocess.run([sys.executable, 'decode_remote.py', filepath], check=False)

        if args.type in ('all', 'protocol'):
            print('\n[Protocol Analysis]')
            subprocess.run([sys.executable, 'urh_analyze.py', filepath], check=False)

        if args.type == 'fingerprint':
            print('\n[Device Fingerprinting]')
            subprocess.run([sys.executable, 'fingerprint_signal.py', filepath], check=False)

    return 0


def cmd_dashboard(args):
    """Start web dashboard"""
    # Kill any existing dashboard processes
    import psutil

    from reconraven.web.server import SDRDashboardServer

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and any(
                'server.py' in str(c) or 'dashboard' in str(c).lower() for c in cmdline
            ):
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    print('Starting ReconRaven Dashboard...')
    time.sleep(1)

    # Load database data
    db = get_db()
    stats = db.get_statistics()
    print(
        f"Database: {stats['total_recordings']} recordings, {stats['identified_devices']} devices"
    )

    dashboard = SDRDashboardServer({'host': '0.0.0.0', 'port': args.port})

    # Initialize with data
    dashboard.update_state(
        {
            'mode': 'idle',
            'status': 'ready',
            'baseline_count': stats['baseline_frequencies'],
            'device_count': stats['identified_devices'],
            'recording_count': stats['total_recordings'],
            'anomaly_count': stats['anomalies'],
        }
    )

    print(f'\nDashboard running at: http://localhost:{args.port}')
    print('Press Ctrl+C to stop')

    try:
        dashboard.run()
    except KeyboardInterrupt:
        print('\nStopping dashboard...')

    return 0


def cmd_db(args):
    """Database management"""
    db = get_db()

    if args.action == 'stats':
        stats = db.get_statistics()
        print('\nReconRaven Database Statistics')
        print('=' * 50)
        print(f"Baseline Frequencies: {stats['baseline_frequencies']}")
        print(f"Total Signals:        {stats['total_signals']}")
        print(f"Anomalies:            {stats['anomalies']}")
        print(f"Identified Devices:   {stats['identified_devices']}")
        print(f"Total Recordings:     {stats['total_recordings']}")
        print(f"Analyzed Recordings:  {stats['analyzed_recordings']}")
        print(f"Storage Used:         {stats['total_storage_mb']:.1f} MB")

    elif args.action == 'devices':
        devices = db.get_devices()
        print(f'\nIdentified Devices ({len(devices)})')
        print('=' * 70)
        for dev in devices:
            freq_mhz = dev['frequency_hz'] / 1e6
            print(f"{freq_mhz:>8.3f} MHz - {dev['name']}")
            print(
                f"             {dev['manufacturer']} | {dev['device_type']} | Conf: {dev['confidence']*100:.0f}%"
            )

    elif args.action == 'anomalies':
        anomalies = db.get_anomalies(limit=args.limit or 20)
        print(f'\nRecent Anomalies ({len(anomalies)})')
        print('=' * 70)
        for sig in anomalies:
            freq_mhz = sig['frequency_hz'] / 1e6
            delta = sig['delta_db'] if sig['delta_db'] else 0
            print(
                f"{freq_mhz:>8.3f} MHz | {sig['band']:>6} | +{delta:>5.1f} dB | {sig['detected_at']}"
            )

    elif args.action == 'promote':
        devices = db.get_devices()
        print(f'Promoting {len(devices)} devices to baseline...')
        for dev in devices:
            freq_info = db.get_frequency_range_info(dev['frequency_hz'])
            band_name = freq_info['name'] if freq_info else 'Unknown'
            db.add_baseline_frequency(
                freq=dev['frequency_hz'], band=band_name, power=-60.0, std=5.0
            )
        print(f'Done! {len(devices)} devices promoted to baseline.')

    elif args.action == 'import':
        print('ERROR: Import functionality removed. Recordings auto-import on scan.')
        return 1

    elif args.action == 'export':
        import json

        data = db.get_dashboard_data()
        with open(args.output or 'reconraven_export.json', 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Exported to {args.output or 'reconraven_export.json'}")

    return 0


def cmd_setup(args):
    """Setup location-specific frequencies"""
    print('ERROR: Setup functionality being redesigned.')
    print('For now, baseline frequencies are auto-built during first scan.')
    return 1


def cmd_play(args):
    """Play/convert IQ recording"""
    print('ERROR: Play functionality removed.')
    print('Use external tools like inspectrum or URH to view .npy IQ files.')
    print('Voice recordings are auto-converted to .wav files.')
    return 1


def cmd_cleanup(args):
    """Cleanup recordings to save disk space"""
    db = get_db()

    # Show current status
    recordings = db.get_recordings()
    audio_dir = 'recordings/audio'
    total_mb = 0
    file_count = 0

    if os.path.exists(audio_dir):
        for filename in os.listdir(audio_dir):
            filepath = os.path.join(audio_dir, filename)
            if os.path.isfile(filepath):
                total_mb += os.path.getsize(filepath) / (1024 * 1024)
                file_count += 1

    print('\nReconRaven Disk Usage')
    print('=' * 50)
    print(f'Total Files:     {file_count}')
    print(f'Disk Usage:      {total_mb:.1f} MB ({total_mb/1024:.2f} GB)')
    print(f'Recordings (DB): {len(recordings)}')
    print(f"Analyzed:        {sum(1 for r in recordings if r['analyzed'])}")

    if args.type == 'ism':
        print('\nDeleting ISM band recordings (433/915 MHz)...')
        deleted = 0
        saved_mb = 0

        for rec in recordings:
            band = rec.get('band', '')
            if 'ISM' in band:
                filename = rec['filename']
                filepath = os.path.join(audio_dir, filename)
                if os.path.exists(filepath) and filename.endswith('.npy'):
                    size_mb = os.path.getsize(filepath) / (1024 * 1024)
                    os.remove(filepath)
                    saved_mb += size_mb
                    deleted += 1
                    if deleted % 10 == 0:
                        print(f'  Deleted {deleted} files, freed {saved_mb:.1f} MB...')

        print(
            f'\n[SUCCESS] Deleted {deleted} ISM recordings, freed {saved_mb:.1f} MB ({saved_mb/1024:.2f} GB)'
        )

    elif args.type == 'old':
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(days=args.days or 7)

        deleted = 0
        saved_mb = 0

        for rec in recordings:
            if not rec['analyzed']:
                captured = datetime.fromisoformat(rec['captured_at'])
                if captured < cutoff:
                    filename = rec['filename']
                    filepath = os.path.join(audio_dir, filename)
                    if os.path.exists(filepath):
                        size_mb = os.path.getsize(filepath) / (1024 * 1024)
                        os.remove(filepath)
                        saved_mb += size_mb
                        deleted += 1

        print(f'\n[SUCCESS] Deleted {deleted} old recordings, freed {saved_mb:.1f} MB')

    elif args.type == 'voice':
        from reconraven.utils.recording_manager import RecordingManager

        manager = RecordingManager(db)

        print('\nConverting voice recordings to WAV...')
        converted = 0
        saved_mb = 0

        for rec in recordings:
            band = rec.get('band', '')
            if band in ['2m', '70cm']:
                filename = rec['filename']
                if filename.endswith('.npy'):
                    filepath = os.path.join(audio_dir, filename)
                    if os.path.exists(filepath):
                        print(f'  Converting: {filename}')
                        wav_file = manager.demodulate_to_wav(filepath)
                        if wav_file:
                            npy_size = os.path.getsize(filepath) / (1024 * 1024)
                            os.remove(filepath)
                            saved_mb += npy_size
                            converted += 1
                            db.update_recording_audio(rec['id'], os.path.basename(wav_file))

        print(f'\n[SUCCESS] Converted {converted} voice recordings, freed {saved_mb:.1f} MB')

    else:
        print('\nNo cleanup type specified. Use --type ism|old|voice')

    return 0


def cmd_test(args):
    """Run diagnostic tests"""
    # Import test modules
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tests'))

    try:
        from test_hardware import (
            test_multi_sdr_initialization,
            test_sdr_detection,
            test_sdr_initialization,
        )
        from test_rf_environment import test_band_scan, test_frequency_monitoring, test_noise_floor
    except ImportError as e:
        print(f'ERROR: Could not import test modules: {e}')
        print(
            'Make sure the tests/ directory exists with test_hardware.py and test_rf_environment.py'
        )
        return 1

    if args.mode == 'sdr':
        return 0 if test_sdr_detection() else 1

    if args.mode == 'noise':
        return 0 if test_noise_floor() else 1

    if args.mode == 'freq':
        if not args.freq:
            print('ERROR: --freq required for freq mode')
            print('Example: reconraven.py test freq --freq 146.52 --duration 60')
            return 1
        return 0 if test_frequency_monitoring(args.freq, args.duration) else 1

    if args.mode == 'rf':
        if not args.band:
            print('ERROR: --band required for rf mode')
            print('Example: reconraven.py test rf --band 2m')
            return 1
        return 0 if test_band_scan(args.band) else 1

    if args.mode == 'df-cal':
        return cmd_df_calibrate(args)

    return 1


def cmd_df_calibrate(args):
    """Calibrate DF array"""
    import yaml
    from direction_finding.array_sync import SDRArraySync
    from rtlsdr import RtlSdr

    print('=' * 70)
    print('DIRECTION FINDING ARRAY CALIBRATION')
    print('=' * 70)

    # Detect SDRs
    try:
        num_sdrs = RtlSdr.get_device_count()
        print(f'\nDetected SDRs: {num_sdrs}')

        if num_sdrs < 2:
            print('ERROR: Need at least 2 SDRs for DF calibration!')
            print('Please connect multiple RTL-SDR devices.')
            return 1

        if num_sdrs < 4:
            print(f'WARNING: Only {num_sdrs} SDRs detected.')
            print('For best DF performance, use 4 SDRs in a square/circular array.')
            response = input('Continue with calibration? (y/n): ')
            if response.lower() != 'y':
                return 1

    except Exception as e:
        print(f'ERROR: Could not detect SDRs: {e}')
        return 1

    # Load hardware config
    try:
        with open('config/hardware.yaml') as f:
            hw_config = yaml.safe_load(f)
        df_config = hw_config.get('df_array', {})
        df_config['num_elements'] = num_sdrs
    except Exception as e:
        print(f'WARNING: Could not load hardware.yaml: {e}')
        df_config = {'num_elements': num_sdrs}

    # Get calibration parameters
    cal_freq = args.freq or df_config.get('calibration', {}).get('cal_frequency_hz', 146.52e6)
    cal_freq_mhz = cal_freq / 1e6 if cal_freq > 1e6 else cal_freq
    cal_freq_hz = cal_freq_mhz * 1e6

    known_bearing = args.bearing

    print('\nCalibration Settings:')
    print(f'  Number of SDRs: {num_sdrs}')
    print(f'  Calibration Frequency: {cal_freq_mhz:.3f} MHz')
    print(f"  Antenna Type: {df_config.get('antenna_type', 'omnidirectional')}")
    print(f"  Array Spacing: {df_config.get('spacing_m', 0.5)} meters")

    if known_bearing is not None:
        print(f'  Known Bearing: {known_bearing}°')
        print('\n  USING KNOWN BEARING MODE:')
        print('  Place a transmitter at the specified bearing before continuing.')
        print('  This provides the most accurate calibration.')
    else:
        print('\n  USING AMBIENT NOISE MODE:')
        print('  Calibration will use ambient RF or a broadcast signal.')
        print('  For best results, tune to a strong local FM broadcast or')
        print('  amateur repeater.')

    input('\nPress Enter when ready to calibrate...')

    # Initialize SDR controller (simplified for calibration)
    class SimpleSDRController:
        def __init__(self, num_sdrs):
            self.sdrs = [RtlSdr(i) for i in range(num_sdrs)]
            for sdr in self.sdrs:
                sdr.sample_rate = 2.4e6
                sdr.gain = 'auto'

        def set_frequency(self, freq_hz):
            for sdr in self.sdrs:
                sdr.center_freq = freq_hz

        def read_samples_sync(self, num_samples):
            return [sdr.read_samples(num_samples) for sdr in self.sdrs]

        def close(self):
            for sdr in self.sdrs:
                sdr.close()

    try:
        print('\nInitializing SDRs...')
        sdr_controller = SimpleSDRController(num_sdrs)

        print('Creating array sync object...')
        array_sync = SDRArraySync(sdr_controller, df_config)

        print(f'\nCalibrating at {cal_freq_mhz:.3f} MHz...')
        print('This will take 10-15 seconds...')

        success = array_sync.calibrate_phase(
            frequency_hz=cal_freq_hz,
            num_samples=20000,
            known_bearing=known_bearing,
            save_to_db=True,
        )

        if success:
            print('\n' + '=' * 70)
            print('CALIBRATION SUCCESSFUL!')
            print('=' * 70)

            # Get calibration from database
            from reconraven.core.database import get_db

            db = get_db()
            cal = db.get_active_df_calibration()

            if cal:
                print(f"\nCalibration saved to database (ID: {cal['id']})")
                print(f"  Method: {cal['calibration_method']}")
                print(f"  Coherence: {cal['coherence_score']:.3f} (>0.7 is good)")
                print(f"  SNR: {cal['snr_db']:.1f} dB")
                print('\nPhase Offsets (radians):')
                for i, offset in enumerate(cal['phase_offsets']):
                    print(f'  SDR #{i}: {offset:+.4f} rad ({np.rad2deg(offset):+.1f}°)')

                # Quality assessment
                if cal['coherence_score'] >= 0.8:
                    print('\n✓ EXCELLENT coherence - Array is well synchronized')
                elif cal['coherence_score'] >= 0.7:
                    print('\n✓ GOOD coherence - Array should work well for DF')
                else:
                    print('\n⚠ WARNING: Low coherence - Check antenna connections and spacing')

                if cal['snr_db'] >= 15:
                    print('✓ STRONG signal - Calibration very reliable')
                elif cal['snr_db'] >= 10:
                    print('✓ GOOD signal - Calibration reliable')
                else:
                    print('⚠ WARNING: Weak signal - Consider recalibrating with stronger source')

            print('\nThe array is now calibrated and ready for direction finding!')
            print('Start scanning with DF enabled:')
            print('  python reconraven.py scan --dashboard')

            return 0
        print('\n' + '=' * 70)
        print('CALIBRATION FAILED')
        print('=' * 70)
        print('\nPossible issues:')
        print('  - SDRs not receiving signal')
        print('  - Antennas not connected')
        print('  - Frequency has no signal (try FM broadcast)')
        print('  - SDRs too close together (RF coupling)')
        return 1

    except Exception as e:
        print(f'\nERROR during calibration: {e}')
        import traceback

        traceback.print_exc()
        return 1

    finally:
        with contextlib.suppress(Exception):
            sdr_controller.close()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='ReconRaven - SIGINT Signal Analysis Platform',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start scanning with dashboard
  reconraven.py scan --dashboard

  # Quick scan (baseline only)
  reconraven.py scan --quick

  # Analyze all recordings
  reconraven.py analyze --all

  # Analyze specific file
  reconraven.py analyze --file recording.npy --type ism

  # Start dashboard only
  reconraven.py dashboard

  # Database stats
  reconraven.py db stats

  # Test SDR detection
  reconraven.py test sdr

  # Test noise floor
  reconraven.py test noise

  # Monitor specific frequency
  reconraven.py test freq --freq 146.52 --duration 60

  # Scan band for signals
  reconraven.py test rf --band 2m

  # Calibrate DF array (auto mode)
  reconraven.py test df-cal --freq 146.52

  # Calibrate DF array with known bearing
  reconraven.py test df-cal --freq 146.52 --bearing 45

  # Setup location
  reconraven.py setup --state AL --city Huntsville
        """,
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Start RF scanning')
    scan_parser.add_argument('--dashboard', action='store_true', help='Start web dashboard')
    scan_parser.add_argument('--quick', action='store_true', help='Quick scan (baseline only)')
    scan_parser.add_argument('--rebuild-baseline', action='store_true', help='Rebuild baseline')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze recordings')
    analyze_parser.add_argument('--file', help='Specific file to analyze')
    analyze_parser.add_argument('--all', action='store_true', help='Analyze all recordings')
    analyze_parser.add_argument(
        '--type',
        default='all',
        choices=['all', 'ism', 'remote', 'protocol', 'fingerprint'],
        help='Analysis type',
    )

    # Dashboard command
    dash_parser = subparsers.add_parser('dashboard', help='Start web dashboard')
    dash_parser.add_argument('--port', type=int, default=5000, help='Port number')

    # Database command
    db_parser = subparsers.add_parser('db', help='Database management')
    db_parser.add_argument(
        'action',
        choices=['stats', 'devices', 'anomalies', 'promote', 'import', 'export'],
        help='Database action',
    )
    db_parser.add_argument('--limit', type=int, help='Limit for list queries')
    db_parser.add_argument('--output', help='Output file for export')

    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Setup location frequencies')
    setup_parser.add_argument('--auto', action='store_true', help='Auto-detect location')
    setup_parser.add_argument('--state', help='State code (e.g., AL)')
    setup_parser.add_argument('--city', help='City name')
    setup_parser.add_argument('--lat', type=float, help='Latitude')
    setup_parser.add_argument('--lon', type=float, help='Longitude')

    # Play command
    play_parser = subparsers.add_parser('play', help='Play/convert IQ recording')
    play_parser.add_argument('file', help='IQ file to play')
    play_parser.add_argument('--mode', default='fm', choices=['fm', 'am'], help='Demodulation mode')
    play_parser.add_argument('--no-plot', action='store_true', help='Skip plotting')

    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup recordings to save disk space')
    cleanup_parser.add_argument(
        '--type',
        choices=['ism', 'old', 'voice'],
        help='Cleanup type: ism=delete ISM recordings, old=delete old unanalyzed, voice=convert to WAV',
    )
    cleanup_parser.add_argument(
        '--days', type=int, default=7, help='Days for old cleanup (default: 7)'
    )

    # Voice command
    voice_parser = subparsers.add_parser('voice', help='Voice monitoring and transcription')
    voice_subparsers = voice_parser.add_subparsers(dest='voice_action', help='Voice action')

    voice_monitor = voice_subparsers.add_parser('monitor', help='Monitor frequency for voice')
    voice_monitor.add_argument('--freq', type=float, required=True, help='Frequency in MHz')
    voice_monitor.add_argument(
        '--mode', default='FM', choices=['FM', 'AM', 'USB', 'LSB'], help='Demod mode'
    )
    voice_monitor.add_argument('--duration', type=int, help='Duration in seconds')
    voice_monitor.add_argument('--record', action='store_true', help='Auto-record')

    voice_scan = voice_subparsers.add_parser('scan', help='Scan band for voice')
    voice_scan.add_argument(
        '--band',
        required=True,
        choices=['2m', '70cm', 'gmrs', 'frs', 'marine'],
        help='Band to scan',
    )
    voice_scan.add_argument(
        '--dwell', type=int, default=5, help='Dwell time per frequency (seconds)'
    )

    voice_transcribe = voice_subparsers.add_parser('transcribe', help='Transcribe recording')
    voice_transcribe.add_argument('--file', required=True, help='Audio file to transcribe')
    voice_transcribe.add_argument(
        '--model',
        default='base',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        help='Whisper model size',
    )

    voice_batch = voice_subparsers.add_parser(
        'batch-transcribe', help='Batch transcribe recordings'
    )
    voice_batch.add_argument(
        '--model',
        default='base',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        help='Whisper model size',
    )
    voice_batch.add_argument(
        '--untranscribed-only', action='store_true', help='Only untranscribed recordings'
    )

    # Extended analyze command
    analyze_extended_parser = subparsers.add_parser('analyze', help='Extended analysis operations')
    analyze_extended_subparsers = analyze_extended_parser.add_subparsers(
        dest='analyze_type', help='Analysis type'
    )

    analyze_corr = analyze_extended_subparsers.add_parser(
        'correlation', help='Find temporal correlations'
    )
    analyze_corr.add_argument('--time-window', type=int, default=10, help='Time window in seconds')
    analyze_corr.add_argument('--min-occurrences', type=int, default=3, help='Minimum occurrences')

    analyze_seq = analyze_extended_subparsers.add_parser(
        'sequences', help='Find sequential patterns'
    )
    analyze_seq.add_argument('--max-length', type=int, default=5, help='Maximum sequence length')

    analyze_prof = analyze_extended_subparsers.add_parser(
        'profile', help='Get device behavioral profile'
    )
    analyze_prof.add_argument('--freq', type=float, required=True, help='Frequency in MHz')

    analyze_net = analyze_extended_subparsers.add_parser('network', help='Build network graph')
    analyze_net.add_argument('--output', help='Output file (JSON)')

    analyze_field = analyze_extended_subparsers.add_parser('field', help='Field signal analysis')
    analyze_field.add_argument('--file', required=True, help='Recording file to analyze')
    analyze_field.add_argument('--offline', action='store_true', help='Offline mode')

    # Recording command
    recording_parser = subparsers.add_parser('recording', help='Recording management')
    recording_subparsers = recording_parser.add_subparsers(
        dest='recording_action', help='Recording action'
    )

    recording_list = recording_subparsers.add_parser('list', help='List recordings')
    recording_list.add_argument('--limit', type=int, default=100, help='Limit results')
    recording_list.add_argument(
        '--format', choices=['table', 'json'], default='table', help='Output format'
    )

    recording_export = recording_subparsers.add_parser('export', help='Export recording')
    recording_export.add_argument('--id', type=int, required=True, help='Recording ID')
    recording_export.add_argument(
        '--format', choices=['wav', 'npy'], default='wav', help='Export format'
    )

    recording_cleanup = recording_subparsers.add_parser('cleanup', help='Cleanup recordings')
    recording_cleanup.add_argument('--type', choices=['ism', 'old', 'voice'], help='Cleanup type')
    recording_cleanup.add_argument('--days', type=int, default=7, help='Days for old cleanup')

    # Test command (diagnostics)
    test_parser = subparsers.add_parser('test', help='Run diagnostic tests')
    test_parser.add_argument(
        'mode',
        choices=['sdr', 'rf', 'noise', 'freq', 'df-cal'],
        help='Test mode: sdr=detect SDRs, rf=scan band, noise=check noise floor, freq=test specific frequency, df-cal=calibrate DF array',
    )
    test_parser.add_argument('--freq', type=float, help='Frequency in MHz (for freq/df-cal mode)')
    test_parser.add_argument(
        '--band', choices=['2m', '70cm', '433', '915'], help='Band to scan (for rf mode)'
    )
    test_parser.add_argument('--duration', type=int, default=30, help='Test duration in seconds')
    test_parser.add_argument(
        '--bearing',
        type=float,
        help='Known bearing in degrees (for df-cal with reference transmitter)',
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Route to command handler
    commands = {
        'scan': cmd_scan,
        'analyze': cmd_analyze_extended,
        'dashboard': cmd_dashboard,
        'db': cmd_db,
        'setup': cmd_setup,
        'play': cmd_play,
        'cleanup': cmd_cleanup,
        'test': cmd_test,
        'voice': cmd_voice,
        'recording': cmd_recording,
    }

    return commands[args.command](args)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n{'='*70}")
        print(f'FATAL ERROR: {e}')
        print(f"{'='*70}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
