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
    from advanced_scanner import AdvancedScanner
    from kill_dashboard import kill_dashboard_processes
    
    scanner = AdvancedScanner()
    
    if not scanner.init_sdr():
        print("ERROR: Failed to initialize SDR!")
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
    
    # Start dashboard if requested
    dashboard = None
    if args.dashboard:
        from web.server import SDRDashboardServer
        print("Starting dashboard...")
        kill_dashboard_processes()
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
        scanner.sdr.close()
    
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
    from kill_dashboard import kill_dashboard_processes
    
    print("Starting ReconRaven Dashboard...")
    kill_dashboard_processes()
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
        print("Importing recordings from recordings/audio/...")
        from import_data import import_recordings
        count = import_recordings()
        print(f"Imported {count} recordings")
    
    elif args.action == 'export':
        import json
        data = db.get_dashboard_data()
        with open(args.output or 'reconraven_export.json', 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Exported to {args.output or 'reconraven_export.json'}")
    
    return 0

def cmd_setup(args):
    """Setup location-specific frequencies"""
    from setup_location import setup_location
    
    if args.auto:
        print("Auto-detecting location...")
        setup_location(auto=True)
    elif args.state:
        setup_location(state=args.state, city=args.city, 
                      lat=args.lat, lon=args.lon)
    else:
        print("ERROR: Specify --auto or --state <STATE>")
        return 1
    
    return 0

def cmd_play(args):
    """Play/convert IQ recording"""
    from play_iq import play_iq
    
    if not os.path.exists(args.file):
        print(f"ERROR: File not found: {args.file}")
        return 1
    
    play_iq(args.file, mode=args.mode, plot=not args.no_plot)
    return 0

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
        'cleanup': cmd_cleanup
    }
    
    return commands[args.command](args)

if __name__ == '__main__':
    sys.exit(main())

