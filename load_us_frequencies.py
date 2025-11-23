#!/usr/bin/env python3
"""
Load US frequency database - Ham repeaters, ISM devices, services
"""

from database import get_db

# US Ham Repeater Frequencies (2m - 144-148 MHz)
US_2M_REPEATERS = [
    # Common 2m repeater pairs (input + 0.6 MHz offset)
    {'freq': 145.110e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 145.130e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 145.150e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 145.170e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 145.190e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 145.210e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 145.230e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 145.250e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 145.270e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 145.290e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 145.310e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 145.330e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 145.350e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 145.370e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 145.390e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 145.410e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 145.430e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 145.450e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 145.470e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 145.490e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.400e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.430e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.460e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.490e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.520e6, 'name': '2m National Simplex', 'type': 'ham_calling', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.550e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.580e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.610e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.640e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.670e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.700e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.730e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.760e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.790e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.820e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.850e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.880e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.910e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.940e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 146.970e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
    {'freq': 147.000e6, 'name': '2m Repeater', 'type': 'ham_repeater', 'band': '2m', 'mode': 'FM'},
]

# US 70cm Repeater Frequencies (420-450 MHz)
US_70CM_REPEATERS = [
    {'freq': 442.000e6, 'name': '70cm Repeater', 'type': 'ham_repeater', 'band': '70cm', 'mode': 'FM'},
    {'freq': 442.025e6, 'name': '70cm Repeater', 'type': 'ham_repeater', 'band': '70cm', 'mode': 'FM'},
    {'freq': 442.050e6, 'name': '70cm Repeater', 'type': 'ham_repeater', 'band': '70cm', 'mode': 'FM'},
    {'freq': 442.075e6, 'name': '70cm Repeater', 'type': 'ham_repeater', 'band': '70cm', 'mode': 'FM'},
    {'freq': 442.100e6, 'name': '70cm Repeater', 'type': 'ham_repeater', 'band': '70cm', 'mode': 'FM'},
    {'freq': 442.125e6, 'name': '70cm Repeater', 'type': 'ham_repeater', 'band': '70cm', 'mode': 'FM'},
    {'freq': 442.150e6, 'name': '70cm Repeater', 'type': 'ham_repeater', 'band': '70cm', 'mode': 'FM'},
    {'freq': 442.175e6, 'name': '70cm Repeater', 'type': 'ham_repeater', 'band': '70cm', 'mode': 'FM'},
    {'freq': 442.200e6, 'name': '70cm Repeater', 'type': 'ham_repeater', 'band': '70cm', 'mode': 'FM'},
    {'freq': 443.000e6, 'name': '70cm Repeater', 'type': 'ham_repeater', 'band': '70cm', 'mode': 'FM'},
    {'freq': 444.000e6, 'name': '70cm Repeater', 'type': 'ham_repeater', 'band': '70cm', 'mode': 'FM'},
    {'freq': 445.000e6, 'name': '70cm Repeater', 'type': 'ham_repeater', 'band': '70cm', 'mode': 'FM'},
    {'freq': 446.000e6, 'name': '70cm Repeater', 'type': 'ham_repeater', 'band': '70cm', 'mode': 'FM'},
    {'freq': 447.000e6, 'name': '70cm Repeater', 'type': 'ham_repeater', 'band': '70cm', 'mode': 'FM'},
    {'freq': 448.000e6, 'name': '70cm Repeater', 'type': 'ham_repeater', 'band': '70cm', 'mode': 'FM'},
]

# US ISM 915 MHz Common Devices
US_ISM_915_DEVICES = [
    {'freq': 902.000e6, 'name': 'Smart Meter', 'type': 'utility', 'band': 'ISM915', 'mode': 'FSK'},
    {'freq': 904.000e6, 'name': 'Smart Meter', 'type': 'utility', 'band': 'ISM915', 'mode': 'FSK'},
    {'freq': 906.000e6, 'name': 'RFID Reader', 'type': 'access_control', 'band': 'ISM915', 'mode': 'FSK'},
    {'freq': 908.000e6, 'name': 'Wireless Sensor', 'type': 'iot', 'band': 'ISM915', 'mode': 'FSK'},
    {'freq': 910.000e6, 'name': 'Cordless Phone', 'type': 'consumer', 'band': 'ISM915', 'mode': 'FSK'},
    {'freq': 912.000e6, 'name': 'Baby Monitor', 'type': 'consumer', 'band': 'ISM915', 'mode': 'FSK'},
    {'freq': 913.500e6, 'name': 'Garage Door Opener', 'type': 'remote', 'band': 'ISM915', 'mode': 'OOK'},
    {'freq': 915.000e6, 'name': 'ISM General Use', 'type': 'ism', 'band': 'ISM915', 'mode': 'Various'},
    {'freq': 918.000e6, 'name': 'Wireless Sensor', 'type': 'iot', 'band': 'ISM915', 'mode': 'FSK'},
    {'freq': 920.000e6, 'name': 'Smart Meter', 'type': 'utility', 'band': 'ISM915', 'mode': 'FSK'},
    {'freq': 922.000e6, 'name': 'RFID Reader', 'type': 'access_control', 'band': 'ISM915', 'mode': 'FSK'},
    {'freq': 925.000e6, 'name': 'Security System', 'type': 'security', 'band': 'ISM915', 'mode': 'FSK'},
    {'freq': 927.000e6, 'name': 'Paging System', 'type': 'paging', 'band': 'ISM915', 'mode': 'FSK'},
]

# US 433 MHz ISM Devices
US_ISM_433_DEVICES = [
    {'freq': 433.075e6, 'name': 'Car Remote', 'type': 'remote', 'band': 'ISM433', 'mode': 'OOK'},
    {'freq': 433.100e6, 'name': 'Gate Remote', 'type': 'remote', 'band': 'ISM433', 'mode': 'OOK'},
    {'freq': 433.920e6, 'name': 'ISM Center Frequency', 'type': 'ism', 'band': 'ISM433', 'mode': 'Various'},
    {'freq': 434.000e6, 'name': 'Weather Station', 'type': 'weather', 'band': 'ISM433', 'mode': 'OOK'},
    {'freq': 434.100e6, 'name': 'Wireless Doorbell', 'type': 'consumer', 'band': 'ISM433', 'mode': 'OOK'},
    {'freq': 434.200e6, 'name': 'TPMS Sensor', 'type': 'automotive', 'band': 'ISM433', 'mode': 'FSK'},
    {'freq': 434.300e6, 'name': 'Temperature Sensor', 'type': 'sensor', 'band': 'ISM433', 'mode': 'OOK'},
    {'freq': 434.400e6, 'name': 'Remote Control', 'type': 'remote', 'band': 'ISM433', 'mode': 'OOK'},
    {'freq': 434.500e6, 'name': 'Wireless Sensor', 'type': 'iot', 'band': 'ISM433', 'mode': 'FSK'},
]

# US Public Safety & Services
US_PUBLIC_SAFETY = [
    {'freq': 154.160e6, 'name': 'Fire Dispatch', 'type': 'public_safety', 'band': 'VHF', 'mode': 'FM'},
    {'freq': 154.280e6, 'name': 'Police Dispatch', 'type': 'public_safety', 'band': 'VHF', 'mode': 'FM'},
    {'freq': 155.160e6, 'name': 'Emergency Services', 'type': 'public_safety', 'band': 'VHF', 'mode': 'FM'},
    {'freq': 156.800e6, 'name': 'Marine Channel 16', 'type': 'marine', 'band': 'VHF', 'mode': 'FM'},
    {'freq': 162.400e6, 'name': 'NOAA Weather Radio WX1', 'type': 'weather', 'band': 'VHF', 'mode': 'FM'},
    {'freq': 162.425e6, 'name': 'NOAA Weather Radio WX2', 'type': 'weather', 'band': 'VHF', 'mode': 'FM'},
    {'freq': 162.450e6, 'name': 'NOAA Weather Radio WX3', 'type': 'weather', 'band': 'VHF', 'mode': 'FM'},
    {'freq': 162.475e6, 'name': 'NOAA Weather Radio WX4', 'type': 'weather', 'band': 'VHF', 'mode': 'FM'},
    {'freq': 162.500e6, 'name': 'NOAA Weather Radio WX5', 'type': 'weather', 'band': 'VHF', 'mode': 'FM'},
    {'freq': 162.525e6, 'name': 'NOAA Weather Radio WX6', 'type': 'weather', 'band': 'VHF', 'mode': 'FM'},
    {'freq': 162.550e6, 'name': 'NOAA Weather Radio WX7', 'type': 'weather', 'band': 'VHF', 'mode': 'FM'},
]

def load_all_frequencies():
    """Load all known US frequencies into database"""
    print("="*70)
    print("Loading US Frequency Database")
    print("="*70)
    
    db = get_db()
    
    all_freqs = (
        US_2M_REPEATERS + 
        US_70CM_REPEATERS + 
        US_ISM_915_DEVICES + 
        US_ISM_433_DEVICES +
        US_PUBLIC_SAFETY
    )
    
    print(f"\nTotal frequencies to load: {len(all_freqs)}")
    
    # Add to baseline (these are known/expected frequencies)
    for entry in all_freqs:
        db.add_baseline_frequency(
            freq=entry['freq'],
            band=entry['band'],
            power=-60.0,  # Default expected power
            std=5.0
        )
    
    # Also add as known "devices" for reference
    device_count = 0
    for entry in all_freqs:
        if entry['type'] != 'ham_repeater':  # Don't add every repeater as a device
            db.add_device(
                freq=entry['freq'],
                name=entry['name'],
                manufacturer='Known Service',
                device_type=entry['type'],
                modulation=entry.get('mode', 'FM'),
                confidence=1.0  # Known frequency
            )
            device_count += 1
    
    stats = db.get_statistics()
    
    print("\n" + "="*70)
    print("Load Complete!")
    print("="*70)
    print(f"\nBaseline frequencies: {stats['baseline_frequencies']}")
    print(f"Known devices/services: {stats['identified_devices']}")
    
    print("\nBreakdown:")
    print(f"  2m Ham Repeaters: {len(US_2M_REPEATERS)}")
    print(f"  70cm Ham Repeaters: {len(US_70CM_REPEATERS)}")
    print(f"  915 MHz ISM Devices: {len(US_ISM_915_DEVICES)}")
    print(f"  433 MHz ISM Devices: {len(US_ISM_433_DEVICES)}")
    print(f"  Public Safety/Services: {len(US_PUBLIC_SAFETY)}")
    
    print("\nNow when you scan:")
    print("  - Known frequencies won't trigger anomalies")
    print("  - Unknown frequencies will be highlighted")
    print("  - Dashboard will show what each frequency is")
    
    db.close()

if __name__ == "__main__":
    load_all_frequencies()

