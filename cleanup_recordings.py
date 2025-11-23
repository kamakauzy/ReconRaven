#!/usr/bin/env python3
"""
Manual cleanup script for ReconRaven recordings
Cleans up old unanalyzed recordings to save disk space
"""

import os
from database import get_db
from recording_manager import RecordingManager

def main():
    db = get_db()
    manager = RecordingManager(db)
    
    print("ReconRaven Recording Cleanup")
    print("="*70)
    
    # Get all recordings
    recordings = db.get_recordings()
    
    analyzed_count = sum(1 for r in recordings if r['analyzed'])
    unanalyzed_count = len(recordings) - analyzed_count
    
    print(f"\nTotal recordings: {len(recordings)}")
    print(f"Analyzed: {analyzed_count}")
    print(f"Unanalyzed: {unanalyzed_count}")
    
    # Calculate disk usage
    audio_dir = "recordings/audio"
    total_size_mb = 0
    file_count = 0
    
    if os.path.exists(audio_dir):
        for filename in os.listdir(audio_dir):
            filepath = os.path.join(audio_dir, filename)
            if os.path.isfile(filepath):
                total_size_mb += os.path.getsize(filepath) / (1024 * 1024)
                file_count += 1
    
    print(f"\nDisk usage:")
    print(f"  Files: {file_count}")
    print(f"  Size: {total_size_mb:.1f} MB ({total_size_mb/1024:.2f} GB)")
    
    # Cleanup options
    print("\n" + "="*70)
    print("CLEANUP OPTIONS:")
    print("="*70)
    print("1. Delete all ISM band recordings (433/915 MHz) - keep analysis data")
    print("2. Convert voice recordings to WAV, delete .npy")
    print("3. Delete ALL unanalyzed recordings older than 7 days")
    print("4. Delete ALL recordings (DANGEROUS)")
    print("5. Exit (no cleanup)")
    
    choice = input("\nSelect option (1-5): ")
    
    if choice == '1':
        # Delete ISM recordings
        deleted = 0
        saved_mb = 0
        
        for rec in recordings:
            band = rec.get('band', '')
            if 'ISM' in band:
                filename = rec['filename']
                filepath = os.path.join(audio_dir, filename)
                if os.path.exists(filepath):
                    size_mb = os.path.getsize(filepath) / (1024 * 1024)
                    os.remove(filepath)
                    saved_mb += size_mb
                    deleted += 1
                    print(f"  Deleted: {filename} ({size_mb:.1f} MB)")
        
        print(f"\nDeleted {deleted} ISM recordings, freed {saved_mb:.1f} MB")
    
    elif choice == '2':
        # Convert voice to WAV
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
                            
                            # Update database
                            db.update_recording_audio(rec['id'], os.path.basename(wav_file))
        
        print(f"\nConverted {converted} voice recordings, freed {saved_mb:.1f} MB")
    
    elif choice == '3':
        # Delete old unanalyzed
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=7)
        
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
                        print(f"  Deleted: {filename} ({size_mb:.1f} MB)")
        
        print(f"\nDeleted {deleted} old recordings, freed {saved_mb:.1f} MB")
    
    elif choice == '4':
        confirm = input("\n⚠️  DELETE ALL RECORDINGS? Type 'YES' to confirm: ")
        if confirm == 'YES':
            deleted = 0
            for filename in os.listdir(audio_dir):
                filepath = os.path.join(audio_dir, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
                    deleted += 1
            print(f"\nDeleted {deleted} files. All recordings removed.")
        else:
            print("Aborted.")
    
    else:
        print("No cleanup performed.")
    
    print("\nDone!")

if __name__ == "__main__":
    main()

