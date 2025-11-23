#!/usr/bin/env python3
"""
Import existing recordings and analysis into database
"""

import os
import json
import glob
import re
from database import ReconRavenDB

def parse_filename(filename):
    """Extract frequency from filename like ISM915_925.000MHz_*"""
    match = re.search(r'(\d+\.\d+)MHz', filename)
    if match:
        return float(match.group(1)) * 1e6
    return None

def import_analysis_files(db):
    """Import existing analysis JSON files"""
    print("Importing analysis files...")
    
    analysis_files = glob.glob('recordings/audio/*_complete_analysis.json')
    
    for filepath in analysis_files:
        try:
            with open(filepath, 'r') as f:
                analysis = json.load(f)
            
            # Get frequency
            freq = parse_filename(filepath)
            if not freq:
                continue
            
            # Determine band
            if 144e6 <= freq <= 148e6:
                band = '2m'
            elif 420e6 <= freq <= 450e6:
                band = '70cm'
            elif 433e6 <= freq <= 435e6:
                band = 'ISM433'
            elif 902e6 <= freq <= 928e6:
                band = 'ISM915'
            else:
                band = 'Unknown'
            
            # Add device if identified
            if analysis.get('confidence', 0) >= 0.6:
                sig_match = analysis.get('signature_match', {})
                
                device_name = sig_match.get('name', 'Unknown')
                manufacturer = sig_match.get('manufacturer', 'Unknown')
                device_type = sig_match.get('device_type', 'unknown')
                modulation = sig_match.get('modulation', 'Unknown')
                
                # Get bit rate
                bit_rate = None
                if 'bit_rate' in sig_match:
                    bit_rate = sig_match['bit_rate']
                elif 'bit_rate_min' in sig_match:
                    bit_rate = (sig_match['bit_rate_min'] + sig_match.get('bit_rate_max', sig_match['bit_rate_min'])) // 2
                
                device_id = db.add_device(
                    freq=freq,
                    name=device_name,
                    manufacturer=manufacturer,
                    device_type=device_type,
                    modulation=modulation,
                    bit_rate=bit_rate,
                    confidence=analysis['confidence']
                )
                
                print(f"  Added device: {device_name} at {freq/1e6:.3f} MHz ({analysis['confidence']*100:.0f}%)")
            
        except Exception as e:
            print(f"  Error importing {filepath}: {e}")

def import_recordings(db):
    """Import existing IQ recordings"""
    print("\nImporting recordings...")
    
    recording_files = glob.glob('recordings/audio/*.npy')
    
    for filepath in recording_files:
        try:
            filename = os.path.basename(filepath)
            
            # Get frequency and band
            freq = parse_filename(filename)
            if not freq:
                continue
            
            if 144e6 <= freq <= 148e6:
                band = '2m'
            elif 420e6 <= freq <= 450e6:
                band = '70cm'
            elif 433e6 <= freq <= 435e6:
                band = 'ISM433'
            elif 902e6 <= freq <= 928e6:
                band = 'ISM915'
            else:
                band = 'Unknown'
            
            # Get file size
            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            
            # Check if device is known
            device = db.get_device_by_frequency(freq)
            device_id = device['id'] if device else None
            
            # Add recording
            db.add_recording(
                filename=filename,
                freq=freq,
                band=band,
                file_size_mb=file_size_mb,
                device_id=device_id
            )
            
        except Exception as e:
            print(f"  Error importing {filepath}: {e}")
    
    print(f"  Imported {len(recording_files)} recordings")

def create_baseline_from_known_devices(db):
    """Create baseline from known devices"""
    print("\nCreating baseline from known devices...")
    
    devices = db.get_devices()
    
    for device in devices:
        freq = device['frequency_hz']
        
        # Determine band
        if 144e6 <= freq <= 148e6:
            band = '2m'
        elif 420e6 <= freq <= 450e6:
            band = '70cm'
        elif 433e6 <= freq <= 435e6:
            band = 'ISM433'
        elif 902e6 <= freq <= 928e6:
            band = 'ISM915'
        else:
            band = 'Unknown'
        
        # Add to baseline (using typical power for now)
        db.add_baseline_frequency(
            freq=freq,
            band=band,
            power=-50.0,  # Placeholder
            std=5.0
        )
    
    print(f"  Added {len(devices)} frequencies to baseline")

def main():
    print("="*70)
    print("ReconRaven Database Migration")
    print("Importing existing data into database")
    print("="*70)
    
    # Create database
    db = ReconRavenDB('reconraven.db')
    
    # Import data
    import_analysis_files(db)
    import_recordings(db)
    create_baseline_from_known_devices(db)
    
    # Show statistics
    print("\n" + "="*70)
    print("Import Complete!")
    print("="*70)
    
    stats = db.get_statistics()
    print(f"\nDatabase Statistics:")
    print(f"  Baseline frequencies: {stats['baseline_frequencies']}")
    print(f"  Identified devices: {stats['identified_devices']}")
    print(f"  Total recordings: {stats['total_recordings']}")
    print(f"  Analyzed recordings: {stats['analyzed_recordings']}")
    print(f"  Total storage: {stats['total_storage_mb']:.1f} MB")
    
    print(f"\nDatabase saved to: reconraven.db")
    print(f"View with: sqlite3 reconraven.db")
    
    # Show devices
    print("\n" + "="*70)
    print("Identified Devices:")
    print("="*70)
    
    devices = db.get_devices()
    for device in devices:
        print(f"\n{device['name']}")
        print(f"  Frequency: {device['frequency_hz']/1e6:.3f} MHz")
        print(f"  Manufacturer: {device['manufacturer']}")
        print(f"  Type: {device['device_type']}")
        print(f"  Confidence: {device['confidence']*100:.0f}%")
        print(f"  Seen: {device['seen_count']} time(s)")
    
    db.close()

if __name__ == "__main__":
    main()

