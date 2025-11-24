#!/usr/bin/env python3
"""
ReconRaven - Unified Command-Line Interface

All-in-one tool for scanning, analysis, and database management.
"""

import argparse
import sys
import os
import time
from database import get_db

def cmd_scan(args):
    """Run scanner with optional dashboard"""
    try:
        from advanced_scanner import AdvancedScanner
        
        # Kill any existing dashboard processes (but not ourselves!)
        import psutil
        import os
        current_pid = os.getpid()
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.pid == current_pid:
                    continue  # Don't kill ourselves!
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('server.py' in str(c) for c in cmdline):
                    print(f"Killing old dashboard process {proc.pid}")
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        print("Initializing scanner...")
        scanner = AdvancedScanner()
        
        print("Initializing SDR...")
        if not scanner.init_sdr():
            print("ERROR: Failed to initialize SDR!")
            return 1
        
        print("[SUCCESS] All SDRs initialized!")
        
    except Exception as e:
        print(f"FATAL ERROR during initialization: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Build or load baseline
    db = get_db()
    stats = db.get_statistics()
    
    if args.rebuild_baseline or stats['baseline_frequencies'] == 0:
        print("Building baseline...")
        scanner.build_baseline()
    else:
        print(f"Loading baseline ({stats['baseline_frequencies']} frequencies)...")
        for entry in db.get_baseline():
            scanner.baseline[entry['frequency_hz']] = {
                'mean': entry['power_dbm'],
                'std': entry['std_dbm'] or 5.0,
                'max': entry['power_dbm'] + 10,
                'band': entry['band']
            }
    
    # Start dashboard AFTER SDRs are fully initialized
    dashboard = None
    if args.dashboard:
        from web.server import SDRDashboardServer
        print("Starting dashboard...")
        # Dashboard cleanup already done above
        time.sleep(1)
        dashboard = SDRDashboardServer({'host': '0.0.0.0', 'port': 5000})
        dashboard.run_threaded()
        time.sleep(2)
        scanner.dashboard = dashboard
        print("Dashboard: http://localhost:5000")
    
    # Run scanner
    try:
        if args.quick:
            scanner.build_baseline()
        else:
            scanner.monitor_with_recording()
    except KeyboardInterrupt:
        print("\nStopping...")
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
        files = glob.glob("recordings/audio/*.npy")
    else:
        print("ERROR: Specify --file <path> or --all")
        return 1
    
    if not files:
        print("No files found to analyze")
        return 0
    
    print(f"Analyzing {len(files)} file(s)...")
    
    for filepath in files:
        print(f"\n{'='*70}")
        print(f"File: {os.path.basename(filepath)}")
        print('='*70)
        
        # Run analysis based on type
        if args.type == 'all' or args.type == 'ism':
            print("\n[ISM Analysis]")
            subprocess.run([sys.executable, 'ism_analyzer.py', filepath])
        
        if args.type == 'all' or args.type == 'remote':
            print("\n[Remote Decoder]")
            subprocess.run([sys.executable, 'decode_remote.py', filepath])
        
        if args.type == 'all' or args.type == 'protocol':
            print("\n[Protocol Analysis]")
            subprocess.run([sys.executable, 'urh_analyze.py', filepath])
        
        if args.type == 'fingerprint':
            print("\n[Device Fingerprinting]")
            subprocess.run([sys.executable, 'fingerprint_signal.py', filepath])
    
    return 0

def cmd_dashboard(args):
    """Start web dashboard"""
    from web.server import SDRDashboardServer
    
    # Kill any existing dashboard processes
    import psutil
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and any('server.py' in str(c) or 'dashboard' in str(c).lower() for c in cmdline):
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    print("Starting ReconRaven Dashboard...")
    time.sleep(1)
    
    # Load database data
    db = get_db()
    stats = db.get_statistics()
    print(f"Database: {stats['total_recordings']} recordings, {stats['identified_devices']} devices")
    
    dashboard = SDRDashboardServer({'host': '0.0.0.0', 'port': args.port})
    
    # Initialize with data
    dashboard.update_state({
        'mode': 'idle',
        'status': 'ready',
        'baseline_count': stats['baseline_frequencies'],
        'device_count': stats['identified_devices'],
        'recording_count': stats['total_recordings'],
        'anomaly_count': stats['anomalies']
    })
    
    print(f"\nDashboard running at: http://localhost:{args.port}")
    print("Press Ctrl+C to stop")
    
    try:
        dashboard.run()
    except KeyboardInterrupt:
        print("\nStopping dashboard...")
    
    return 0

def cmd_db(args):
    """Database management"""
    db = get_db()
    
    if args.action == 'stats':
        stats = db.get_statistics()
        print("\nReconRaven Database Statistics")
        print("="*50)
        print(f"Baseline Frequencies: {stats['baseline_frequencies']}")
        print(f"Total Signals:        {stats['total_signals']}")
        print(f"Anomalies:            {stats['anomalies']}")
        print(f"Identified Devices:   {stats['identified_devices']}")
        print(f"Total Recordings:     {stats['total_recordings']}")
        print(f"Analyzed Recordings:  {stats['analyzed_recordings']}")
        print(f"Storage Used:         {stats['total_storage_mb']:.1f} MB")
        
    elif args.action == 'devices':
        devices = db.get_devices()
        print(f"\nIdentified Devices ({len(devices)})")
        print("="*70)
        for dev in devices:
            freq_mhz = dev['frequency_hz'] / 1e6
            print(f"{freq_mhz:>8.3f} MHz - {dev['name']}")
            print(f"             {dev['manufacturer']} | {dev['device_type']} | Conf: {dev['confidence']*100:.0f}%")
    
    elif args.action == 'anomalies':
        anomalies = db.get_anomalies(limit=args.limit or 20)
        print(f"\nRecent Anomalies ({len(anomalies)})")
        print("="*70)
        for sig in anomalies:
            freq_mhz = sig['frequency_hz'] / 1e6
            delta = sig['delta_db'] if sig['delta_db'] else 0
            print(f"{freq_mhz:>8.3f} MHz | {sig['band']:>6} | +{delta:>5.1f} dB | {sig['detected_at']}")
    
    elif args.action == 'promote':
        devices = db.get_devices()
        print(f"Promoting {len(devices)} devices to baseline...")
        for dev in devices:
            freq_info = db.get_frequency_range_info(dev['frequency_hz'])
            band_name = freq_info['name'] if freq_info else 'Unknown'
            db.add_baseline_frequency(
                freq=dev['frequency_hz'],
                band=band_name,
                power=-60.0,
                std=5.0
            )
        print(f"Done! {len(devices)} devices promoted to baseline.")
    
    elif args.action == 'import':
        print("ERROR: Import functionality removed. Recordings auto-import on scan.")
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
    print("ERROR: Setup functionality being redesigned.")
    print("For now, baseline frequencies are auto-built during first scan.")
    return 1

def cmd_play(args):
    """Play/convert IQ recording"""
    print("ERROR: Play functionality removed.")
    print("Use external tools like inspectrum or URH to view .npy IQ files.")
    print("Voice recordings are auto-converted to .wav files.")
    return 1

def cmd_cleanup(args):
    """Cleanup recordings to save disk space"""
    db = get_db()
    
    # Show current status
    recordings = db.get_recordings()
    audio_dir = "recordings/audio"
    total_mb = 0
    file_count = 0
    
    if os.path.exists(audio_dir):
        for filename in os.listdir(audio_dir):
            filepath = os.path.join(audio_dir, filename)
            if os.path.isfile(filepath):
                total_mb += os.path.getsize(filepath) / (1024 * 1024)
                file_count += 1
    
    print("\nReconRaven Disk Usage")
    print("="*50)
    print(f"Total Files:     {file_count}")
    print(f"Disk Usage:      {total_mb:.1f} MB ({total_mb/1024:.2f} GB)")
    print(f"Recordings (DB): {len(recordings)}")
    print(f"Analyzed:        {sum(1 for r in recordings if r['analyzed'])}")
    
    if args.type == 'ism':
        print("\nDeleting ISM band recordings (433/915 MHz)...")
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
                        print(f"  Deleted {deleted} files, freed {saved_mb:.1f} MB...")
        
        print(f"\n[SUCCESS] Deleted {deleted} ISM recordings, freed {saved_mb:.1f} MB ({saved_mb/1024:.2f} GB)")
    
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
        
        print(f"\n[SUCCESS] Deleted {deleted} old recordings, freed {saved_mb:.1f} MB")
    
    elif args.type == 'voice':
        from recording_manager import RecordingManager
        manager = RecordingManager(db)
        
        print("\nConverting voice recordings to WAV...")
        converted = 0
        saved_mb = 0
        
        for rec in recordings:
            band = rec.get('band', '')
            if band in ['2m', '70cm']:
                filename = rec['filename']
                if filename.endswith('.npy'):
                    filepath = os.path.join(audio_dir, filename)
                    if os.path.exists(filepath):
                        print(f"  Converting: {filename}")
                        wav_file = manager.demodulate_to_wav(filepath)
                        if wav_file:
                            npy_size = os.path.getsize(filepath) / (1024 * 1024)
                            os.remove(filepath)
                            saved_mb += npy_size
                            converted += 1
                            db.update_recording_audio(rec['id'], os.path.basename(wav_file))
        
        print(f"\n[SUCCESS] Converted {converted} voice recordings, freed {saved_mb:.1f} MB")
    
    else:
        print("\nNo cleanup type specified. Use --type ism|old|voice")
    
    return 0

def cmd_test(args):
    """Run diagnostic tests"""
    from rtlsdr import RtlSdr, librtlsdr
    import numpy as np
    import time
    
    if args.mode == 'sdr':
        # Detect and list all SDRs
        print("\n" + "="*70)
        print("SDR DETECTION TEST")
        print("="*70)
        
        count = librtlsdr.rtlsdr_get_device_count()
        print(f"\nFound {count} RTL-SDR device(s)")
        
        if count == 0:
            print("\nNo SDRs detected!")
            print("Check:")
            print("  - SDRs are plugged into USB")
            print("  - udev rules are installed (Linux)")
            print("  - Drivers are installed (Windows)")
            return 1
        
        for i in range(count):
            try:
                print(f"\n  SDR #{i}:")
                sdr = RtlSdr(device_index=i)
                print(f"    Tuner: {sdr.get_tuner_type()}")
                print(f"    Sample rate: {sdr.sample_rate/1e6:.1f} Msps (default)")
                print(f"    Gain: {sdr.gain} dB")
                sdr.close()
            except Exception as e:
                print(f"    ERROR: {e}")
        
        print("\n" + "="*70)
        return 0
    
    elif args.mode == 'noise':
        # Check noise floor across spectrum
        print("\n" + "="*70)
        print("NOISE FLOOR TEST")
        print("="*70)
        
        sdr = RtlSdr()
        sdr.sample_rate = 2.8e6
        sdr.gain = 'auto'
        
        test_freqs = {
            '2m': 146.5e6,
            '70cm': 435.0e6,
            'ISM433': 433.92e6,
            'ISM915': 915.0e6
        }
        
        print(f"\nTesting noise floor on {len(test_freqs)} bands...")
        print("(Disconnect antennas for true noise floor test)\n")
        
        results = {}
        for band, freq in test_freqs.items():
            sdr.center_freq = freq
            time.sleep(0.1)
            samples = sdr.read_samples(256 * 1024)
            power = 10 * np.log10(np.mean(np.abs(samples)**2) + 1e-10)
            results[band] = power
            status = "GOOD" if power < -20 else "WARNING" if power < -10 else "SATURATED"
            print(f"  {band:8s} ({freq/1e6:>7.2f} MHz): {power:>6.1f} dBm  [{status}]")
        
        sdr.close()
        
        print("\nInterpretation:")
        print("  < -20 dBm: Good noise floor")
        print("  -20 to -10 dBm: Elevated noise (check RF environment)")
        print("  > -10 dBm: Saturated! (move SDR away from interference)")
        print("\n" + "="*70)
        return 0
    
    elif args.mode == 'freq':
        # Test specific frequency
        if not args.freq:
            print("ERROR: --freq required for freq mode")
            return 1
        
        freq_hz = args.freq * 1e6
        duration = args.duration
        
        print("\n" + "="*70)
        print(f"FREQUENCY TEST: {args.freq:.3f} MHz")
        print("="*70)
        print(f"\nMonitoring for {duration} seconds...")
        print("TRANSMIT NOW!\n")
        
        sdr = RtlSdr()
        sdr.sample_rate = 2.8e6
        sdr.gain = 'auto'
        sdr.center_freq = freq_hz
        
        baseline_samples = []
        for i in range(5):
            samples = sdr.read_samples(128 * 1024)
            power = 10 * np.log10(np.mean(np.abs(samples)**2) + 1e-10)
            baseline_samples.append(power)
            time.sleep(0.2)
        
        baseline = np.mean(baseline_samples)
        print(f"Baseline: {baseline:.1f} dBm (avg of 5 samples)\n")
        
        max_power = baseline
        max_delta = 0
        start = time.time()
        
        while time.time() - start < duration:
            samples = sdr.read_samples(128 * 1024)
            power = 10 * np.log10(np.mean(np.abs(samples)**2) + 1e-10)
            delta = power - baseline
            
            if power > max_power:
                max_power = power
                max_delta = delta
            
            status = ""
            if delta > 15:
                status = " <-- STRONG SIGNAL!"
            elif delta > 10:
                status = " <-- Signal detected"
            elif delta > 5:
                status = " <-- Weak signal"
            
            print(f"  {power:>6.1f} dBm (Δ{delta:>+5.1f} dB){status}", flush=True)
            time.sleep(0.5)
        
        sdr.close()
        
        print(f"\nResults:")
        print(f"  Baseline: {baseline:.1f} dBm")
        print(f"  Max power: {max_power:.1f} dBm")
        print(f"  Max delta: +{max_delta:.1f} dB")
        
        if max_delta > 15:
            print(f"  Status: ✓ STRONG transmission detected!")
        elif max_delta > 10:
            print(f"  Status: ✓ Transmission detected")
        elif max_delta > 5:
            print(f"  Status: ⚠ Weak signal detected")
        else:
            print(f"  Status: ✗ No significant signal detected")
        
        print("\n" + "="*70)
        return 0
    
    elif args.mode == 'rf':
        # Scan a band
        if not args.band:
            print("ERROR: --band required for rf mode")
            return 1
        
        bands = {
            '2m': (146.0e6, 147.0e6, 100e3),
            '70cm': (435.0e6, 436.0e6, 100e3),
            '433': (433.0e6, 434.0e6, 50e3),
            '915': (915.0e6, 916.0e6, 100e3)
        }
        
        start_freq, end_freq, step = bands[args.band]
        
        print("\n" + "="*70)
        print(f"RF BAND SCAN: {args.band.upper()}")
        print("="*70)
        print(f"Range: {start_freq/1e6:.1f} - {end_freq/1e6:.1f} MHz")
        print(f"Step: {step/1e3:.0f} kHz\n")
        
        sdr = RtlSdr()
        sdr.sample_rate = 2.8e6
        sdr.gain = 'auto'
        
        freqs = np.arange(start_freq, end_freq, step)
        print(f"Scanning {len(freqs)} frequencies...\n")
        
        results = []
        for freq in freqs:
            sdr.center_freq = freq
            time.sleep(0.01)
            samples = sdr.read_samples(128 * 1024)
            power = 10 * np.log10(np.mean(np.abs(samples)**2) + 1e-10)
            results.append((freq, power))
            
            status = ""
            if power > -10:
                status = " [STRONG]"
            elif power > -20:
                status = " [SIGNAL]"
            
            print(f"  {freq/1e6:>7.3f} MHz: {power:>6.1f} dBm{status}")
        
        sdr.close()
        
        # Summary
        powers = [p for f, p in results]
        avg_power = np.mean(powers)
        max_power = np.max(powers)
        max_freq = results[np.argmax(powers)][0]
        
        print(f"\nSummary:")
        print(f"  Average power: {avg_power:.1f} dBm")
        print(f"  Peak power: {max_power:.1f} dBm at {max_freq/1e6:.3f} MHz")
        print(f"  Signals > -20 dBm: {sum(1 for p in powers if p > -20)}")
        
        print("\n" + "="*70)
        return 0

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
  
  # Setup location
  reconraven.py setup --state AL --city Huntsville
        """
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
    analyze_parser.add_argument('--type', default='all', 
                               choices=['all', 'ism', 'remote', 'protocol', 'fingerprint'],
                               help='Analysis type')
    
    # Dashboard command
    dash_parser = subparsers.add_parser('dashboard', help='Start web dashboard')
    dash_parser.add_argument('--port', type=int, default=5000, help='Port number')
    
    # Database command
    db_parser = subparsers.add_parser('db', help='Database management')
    db_parser.add_argument('action', choices=['stats', 'devices', 'anomalies', 'promote', 'import', 'export'],
                          help='Database action')
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
    cleanup_parser.add_argument('--type', choices=['ism', 'old', 'voice'], 
                                help='Cleanup type: ism=delete ISM recordings, old=delete old unanalyzed, voice=convert to WAV')
    cleanup_parser.add_argument('--days', type=int, default=7, help='Days for old cleanup (default: 7)')
    
    # Test command (diagnostics)
    test_parser = subparsers.add_parser('test', help='Run diagnostic tests')
    test_parser.add_argument('mode', choices=['sdr', 'rf', 'noise', 'freq'], 
                            help='Test mode: sdr=detect SDRs, rf=scan band, noise=check noise floor, freq=test specific frequency')
    test_parser.add_argument('--freq', type=float, help='Frequency in MHz (for freq mode)')
    test_parser.add_argument('--band', choices=['2m', '70cm', '433', '915'], help='Band to scan (for rf mode)')
    test_parser.add_argument('--duration', type=int, default=30, help='Test duration in seconds')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Route to command handler
    commands = {
        'scan': cmd_scan,
        'analyze': cmd_analyze,
        'dashboard': cmd_dashboard,
        'db': cmd_db,
        'setup': cmd_setup,
        'play': cmd_play,
        'cleanup': cmd_cleanup,
        'test': cmd_test
    }
    
    return commands[args.command](args)

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n{'='*70}")
        print(f"FATAL ERROR: {e}")
        print(f"{'='*70}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

