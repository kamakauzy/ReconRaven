#!/usr/bin/env python3
"""
Import device identifications from URH analysis files
"""

from database import get_db
import glob
import re

def parse_urh_file(filepath):
    """Parse URH analysis text file"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Extract modulation
    modulation = None
    if 'FSK: 95%' in content:
        modulation = 'FSK'
    elif 'ASK: ' in content or 'OOK: ' in content:
        modulation = 'ASK/OOK'
    
    # Extract symbol rate
    bit_rate = None
    match = re.search(r'Symbol rate: (\d+) symbols/sec', content)
    if match:
        bit_rate = int(match.group(1))
    
    # Check for device matches
    devices = []
    if 'Honeywell' in content:
        devices.append('Honeywell Security')
    if 'Keeloq' in content:
        devices.append('Keeloq Garage Door')
    if 'Acurite' in content:
        devices.append('Acurite Weather Station')
    
    return {
        'modulation': modulation,
        'bit_rate': bit_rate,
        'potential_devices': devices
    }

def main():
    print("="*70)
    print("Importing Device Identifications from Analysis")
    print("="*70)
    
    db = get_db()
    
    # Device signatures from our previous analysis
    known_devices = {
        925.0: {
            'name': 'Honeywell Security Sensor',
            'manufacturer': 'Honeywell',
            'type': 'security_sensor',
            'bit_rate': 77000,
            'confidence': 0.85
        },
        920.0: {
            'name': 'High-Speed Data Link',
            'manufacturer': 'Unknown',
            'type': 'industrial_telemetry',
            'bit_rate': 218000,
            'confidence': 0.50
        },
        913.1: {
            'name': 'Battery-Powered Sensor',
            'manufacturer': 'Unknown',
            'type': 'sensor',
            'bit_rate': 60000,
            'confidence': 0.60
        },
        914.1: {
            'name': 'Wireless Sensor',
            'manufacturer': 'Honeywell',
            'type': 'security_sensor',
            'bit_rate': 69000,
            'confidence': 0.70
        },
        908.6: {
            'name': 'Wireless Sensor',
            'manufacturer': 'Honeywell',
            'type': 'security_sensor',
            'bit_rate': 67000,
            'confidence': 0.70
        },
        909.5: {
            'name': 'Medium-Speed Sensor',
            'manufacturer': 'Unknown',
            'type': 'sensor',
            'bit_rate': 39000,
            'confidence': 0.60
        },
        902.1: {
            'name': 'Smart Meter / Industrial Link',
            'manufacturer': 'Unknown',
            'type': 'industrial_telemetry',
            'bit_rate': 240000,
            'confidence': 0.80
        },
        905.9: {
            'name': 'Smart Meter / Industrial Link',
            'manufacturer': 'Unknown',
            'type': 'industrial_telemetry',
            'bit_rate': 240000,
            'confidence': 0.80
        },
        911.7: {
            'name': 'Smart Meter / Industrial Link',
            'manufacturer': 'Unknown',
            'type': 'industrial_telemetry',
            'bit_rate': 240000,
            'confidence': 0.80
        }
    }
    
    print("\nAdding identified devices to database...")
    
    for freq_mhz, device in known_devices.items():
        freq_hz = freq_mhz * 1e6
        
        device_id = db.add_device(
            freq=freq_hz,
            name=device['name'],
            manufacturer=device['manufacturer'],
            device_type=device['type'],
            modulation='FSK',
            bit_rate=device['bit_rate'],
            confidence=device['confidence']
        )
        
        print(f"  {freq_mhz:.1f} MHz: {device['name']} ({device['confidence']*100:.0f}%)")
    
    # Update statistics
    stats = db.get_statistics()
    
    print("\n" + "="*70)
    print("Import Complete!")
    print("="*70)
    print(f"\nIdentified Devices: {stats['identified_devices']}")
    print(f"Total Recordings: {stats['total_recordings']}")
    
    print("\nDevices by Type:")
    devices = db.get_devices()
    by_type = {}
    for dev in devices:
        dtype = dev['device_type']
        by_type[dtype] = by_type.get(dtype, 0) + 1
    
    for dtype, count in by_type.items():
        print(f"  {dtype}: {count}")
    
    db.close()

if __name__ == "__main__":
    main()

