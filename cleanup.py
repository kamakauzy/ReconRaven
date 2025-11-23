#!/usr/bin/env python3
"""
Cleanup Script - Remove redundant/deprecated scripts
These have been consolidated into reconraven.py
"""

import os
import shutil
from pathlib import Path

# Files to archive (deprecated/redundant)
DEPRECATED_FILES = [
    'simple_scanner.py',          # Use: reconraven.py scan --quick
    'quick_scanner.py',           # Use: reconraven.py scan --quick
    'run_dashboard.py',           # Use: reconraven.py dashboard
    'start_dashboard.py',         # Use: reconraven.py dashboard
    'run_live_scan.py',           # Use: reconraven.py scan --dashboard
    'scanner_433.py',             # Merged into advanced_scanner.py
    'test_database.py',           # Use: reconraven.py db stats
    'import_data.py',             # Use: reconraven.py db import
    'import_devices.py',          # No longer needed
    'decode_signal.py',           # Use: reconraven.py analyze
    'dashboard_manager.py',       # Merged into web/server.py
    'add_frequency_ranges.py',    # Part of setup_location.py
    'load_us_frequencies.py',     # Part of setup_location.py
    'load_huntsville_frequencies.py', # Use: reconraven.py setup
]

# Testing files (keep but don't commit)
TESTING_FILES = [
    'test_simulation.py',
    'test_mobile_modes.py',
    'test_real_sdr.py',
]

def cleanup():
    """Move deprecated files to archive folder"""
    
    archive_dir = Path('_archived_scripts')
    archive_dir.mkdir(exist_ok=True)
    
    print("ReconRaven Cleanup")
    print("="*70)
    print("\nArchiving deprecated scripts...")
    
    archived_count = 0
    for filename in DEPRECATED_FILES:
        filepath = Path(filename)
        if filepath.exists():
            dest = archive_dir / filename
            print(f"  {filename} -> _archived_scripts/")
            shutil.move(str(filepath), str(dest))
            archived_count += 1
    
    print(f"\nArchived {archived_count} file(s)")
    
    # Update .gitignore
    print("\nUpdating .gitignore...")
    gitignore_path = Path('.gitignore')
    
    with open(gitignore_path, 'a') as f:
        f.write('\n# Archived/deprecated scripts\n')
        f.write('_archived_scripts/\n')
    
    print("\nCleanup complete!")
    print("\nNew workflow:")
    print("  - Scanning:   reconraven.py scan --dashboard")
    print("  - Analysis:   reconraven.py analyze --all")
    print("  - Dashboard:  reconraven.py dashboard")
    print("  - Database:   reconraven.py db stats")
    print("  - Setup:      reconraven.py setup --state AL")
    print("\nRun: python reconraven.py --help for full options")

def list_deprecated():
    """List files that will be archived"""
    print("Files to be archived:")
    print("="*70)
    
    for filename in DEPRECATED_FILES:
        exists = "EXISTS" if Path(filename).exists() else "NOT FOUND"
        print(f"  [{exists:>10}] {filename}")
    
    print(f"\nTotal: {len(DEPRECATED_FILES)} files")
    print("\nRun with --execute to archive these files")

if __name__ == '__main__':
    import sys
    
    if '--execute' in sys.argv:
        response = input("\nArchive deprecated files? (yes/no): ")
        if response.lower() in ['yes', 'y']:
            cleanup()
        else:
            print("Cancelled")
    else:
        list_deprecated()

