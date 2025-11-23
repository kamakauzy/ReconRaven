#!/usr/bin/env python3
"""
Auto-cleanup for ReconRaven - Delete ISM recordings, keep analysis data
"""

import os
from database import get_db

def main():
    db = get_db()
    
    print("ReconRaven Auto-Cleanup: ISM Recordings")
    print("="*70)
    
    audio_dir = "recordings/audio"
    recordings = db.get_recordings()
    
    deleted = 0
    saved_mb = 0
    
    print("\nDeleting ISM band recordings (433/915 MHz)...")
    print("Analysis data and metadata will be preserved in database\n")
    
    for rec in recordings:
        band = rec.get('band', '')
        if 'ISM' in band or '433' in str(rec.get('frequency_hz', 0)) or '915' in str(rec.get('frequency_hz', 0)):
            filename = rec['filename']
            filepath = os.path.join(audio_dir, filename)
            if os.path.exists(filepath) and filename.endswith('.npy'):
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                os.remove(filepath)
                saved_mb += size_mb
                deleted += 1
                if deleted % 10 == 0:
                    print(f"  Deleted {deleted} files, freed {saved_mb:.1f} MB...")
    
    print(f"\n[SUCCESS] Deleted {deleted} ISM recordings")
    print(f"[SUCCESS] Freed {saved_mb:.1f} MB ({saved_mb/1024:.2f} GB)")
    print("\nDatabase metadata and analysis results preserved!")

if __name__ == "__main__":
    main()

