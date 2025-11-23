#!/usr/bin/env python3
"""
Location-Aware Frequency Database
Huntsville, AL specific frequencies with GPS coordinates
"""

from database import get_db
import math

# Huntsville, AL coordinates
HUNTSVILLE_LAT = 34.7304
HUNTSVILLE_LON = -86.5859

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in km between two coordinates"""
    R = 6371  # Earth radius in km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

# Huntsville-specific frequencies with locations
HUNTSVILLE_FREQUENCIES = [
    # Ham Repeaters (actual Huntsville repeaters from RepeaterBook)
    {
        'freq': 145.230e6,
        'name': 'W4XE 2m Repeater',
        'type': 'ham_repeater',
        'band': '2m',
        'mode': 'FM',
        'tone': '186.2',
        'callsign': 'W4XE',
        'location': 'Huntsville',
        'lat': 34.73,
        'lon': -86.59,
        'range_km': 80,
        'notes': 'Huntsville Amateur Radio Club'
    },
    {
        'freq': 145.290e6,
        'name': 'KK4AI 2m Repeater',
        'type': 'ham_repeater',
        'band': '2m',
        'mode': 'FM',
        'tone': '100.0',
        'callsign': 'KK4AI',
        'location': 'Huntsville',
        'lat': 34.73,
        'lon': -86.59,
        'range_km': 60
    },
    {
        'freq': 146.940e6,
        'name': 'N4HSV 2m Repeater',
        'type': 'ham_repeater',
        'band': '2m',
        'mode': 'FM',
        'tone': '100.0',
        'callsign': 'N4HSV',
        'location': 'Huntsville',
        'lat': 34.73,
        'lon': -86.59,
        'range_km': 80,
        'notes': 'Madison County ARES/RACES'
    },
    {
        'freq': 442.000e6,
        'name': 'KE4BLC 70cm Repeater',
        'type': 'ham_repeater',
        'band': '70cm',
        'mode': 'FM',
        'tone': '203.5',
        'callsign': 'KE4BLC',
        'location': 'Huntsville',
        'lat': 34.73,
        'lon': -86.59,
        'range_km': 60
    },
    {
        'freq': 442.175e6,
        'name': 'W4TCL 70cm Repeater',
        'type': 'ham_repeater',
        'band': '70cm',
        'mode': 'FM',
        'tone': '100.0',
        'callsign': 'W4TCL',
        'location': 'Huntsville',
        'lat': 34.73,
        'lon': -86.59,
        'range_km': 60
    },
    {
        'freq': 443.000e6,
        'name': 'WA4NPL 70cm Repeater',
        'type': 'ham_repeater',
        'band': '70cm',
        'mode': 'FM',
        'callsign': 'WA4NPL',
        'location': 'Huntsville',
        'lat': 34.73,
        'lon': -86.59,
        'range_km': 60
    },
    
    # Huntsville Police
    {
        'freq': 858.4375e6,
        'name': 'Huntsville PD North Dispatch',
        'type': 'police',
        'band': 'UHF',
        'mode': 'P25',
        'location': 'Huntsville',
        'lat': 34.73,
        'lon': -86.59,
        'range_km': 40,
        'agency': 'Huntsville Police Department'
    },
    {
        'freq': 859.2625e6,
        'name': 'Huntsville PD South Dispatch',
        'type': 'police',
        'band': 'UHF',
        'mode': 'P25',
        'location': 'Huntsville',
        'lat': 34.73,
        'lon': -86.59,
        'range_km': 40,
        'agency': 'Huntsville Police Department'
    },
    {
        'freq': 859.7125e6,
        'name': 'Huntsville PD West Dispatch',
        'type': 'police',
        'band': 'UHF',
        'mode': 'P25',
        'location': 'Huntsville',
        'lat': 34.73,
        'lon': -86.59,
        'range_km': 40,
        'agency': 'Huntsville Police Department'
    },
    
    # Madison Police & Fire
    {
        'freq': 855.5625e6,
        'name': 'Madison PD Dispatch',
        'type': 'police',
        'band': 'UHF',
        'mode': 'P25',
        'tone': 'DPL 754',
        'location': 'Madison, AL',
        'lat': 34.699,
        'lon': -86.748,
        'range_km': 30,
        'agency': 'Madison Police Department'
    },
    {
        'freq': 855.9875e6,
        'name': 'Madison FD Dispatch',
        'type': 'fire',
        'band': 'UHF',
        'mode': 'P25',
        'tone': 'DPL 411',
        'location': 'Madison, AL',
        'lat': 34.699,
        'lon': -86.748,
        'range_km': 30,
        'agency': 'Madison Fire Department'
    },
    
    # Hospitals
    {
        'freq': 451.4500e6,
        'name': 'Huntsville Hospital',
        'type': 'hospital',
        'band': 'UHF',
        'mode': 'DMR',
        'location': 'Huntsville',
        'lat': 34.730,
        'lon': -86.586,
        'range_km': 10,
        'agency': 'Huntsville Hospital'
    },
    {
        'freq': 452.2500e6,
        'name': 'Huntsville Hospital',
        'type': 'hospital',
        'band': 'UHF',
        'mode': 'DMR',
        'location': 'Huntsville',
        'lat': 34.730,
        'lon': -86.586,
        'range_km': 10,
        'agency': 'Huntsville Hospital'
    },
    
    # State Troopers
    {
        'freq': 154.920e6,
        'name': 'Alabama State Troopers',
        'type': 'state_police',
        'band': 'VHF',
        'mode': 'FM',
        'location': 'North Alabama',
        'lat': 34.73,
        'lon': -86.59,
        'range_km': 100,
        'agency': 'Alabama State Troopers'
    },
    {
        'freq': 155.445e6,
        'name': 'Alabama State Troopers',
        'type': 'state_police',
        'band': 'VHF',
        'mode': 'FM',
        'location': 'North Alabama',
        'lat': 34.73,
        'lon': -86.59,
        'range_km': 100,
        'agency': 'Alabama State Troopers'
    },
    
    # NOAA Weather (covers Huntsville)
    {
        'freq': 162.550e6,
        'name': 'NOAA Weather WX7 Huntsville',
        'type': 'weather',
        'band': 'VHF',
        'mode': 'FM',
        'location': 'Huntsville',
        'lat': 34.73,
        'lon': -86.59,
        'range_km': 80,
        'agency': 'NOAA National Weather Service'
    },
]

def add_location_table():
    """Add GPS location tracking to database"""
    db = get_db()
    cursor = db.conn.cursor()
    
    # Add location columns to devices table if not exists
    try:
        cursor.execute('ALTER TABLE devices ADD COLUMN latitude REAL')
        cursor.execute('ALTER TABLE devices ADD COLUMN longitude REAL')
        cursor.execute('ALTER TABLE devices ADD COLUMN range_km REAL')
        cursor.execute('ALTER TABLE devices ADD COLUMN agency TEXT')
        cursor.execute('ALTER TABLE devices ADD COLUMN tone TEXT')
        cursor.execute('ALTER TABLE devices ADD COLUMN callsign TEXT')
        cursor.execute('ALTER TABLE devices ADD COLUMN notes TEXT')
    except sqlite3.OperationalError:
        pass  # Columns already exist
    
    # Add current_location table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS current_location (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            latitude REAL,
            longitude REAL,
            altitude_m REAL,
            accuracy_m REAL,
            source TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Set Huntsville as default location
    cursor.execute('''
        INSERT OR REPLACE INTO current_location (id, latitude, longitude, source)
        VALUES (1, ?, ?, 'manual')
    ''', (HUNTSVILLE_LAT, HUNTSVILLE_LON))
    
    db.conn.commit()
    print("Location tracking enabled")
    return db

def load_huntsville_frequencies():
    """Load Huntsville-specific frequencies"""
    print("="*70)
    print("Loading Huntsville, AL Frequency Database")
    print(f"Location: {HUNTSVILLE_LAT}, {HUNTSVILLE_LON}")
    print("="*70)
    
    db = add_location_table()
    
    print(f"\nAdding {len(HUNTSVILLE_FREQUENCIES)} location-aware frequencies...")
    
    for entry in HUNTSVILLE_FREQUENCIES:
        # Add to devices with location data
        device_id = db.add_device(
            freq=entry['freq'],
            name=entry['name'],
            manufacturer=entry.get('agency', 'Local'),
            device_type=entry['type'],
            modulation=entry['mode'],
            confidence=1.0  # Known frequency
        )
        
        # Update with location data
        cursor = db.conn.cursor()
        cursor.execute('''
            UPDATE devices SET
                latitude = ?,
                longitude = ?,
                range_km = ?,
                agency = ?,
                tone = ?,
                callsign = ?,
                notes = ?
            WHERE id = ?
        ''', (
            entry.get('lat'),
            entry.get('lon'),
            entry.get('range_km'),
            entry.get('agency'),
            entry.get('tone'),
            entry.get('callsign'),
            entry.get('notes'),
            device_id
        ))
        
        print(f"  {entry['freq']/1e6:.4f} MHz - {entry['name']}")
        if 'range_km' in entry:
            print(f"    Range: {entry['range_km']} km")
    
    db.conn.commit()
    
    # Summary by type
    print("\n" + "="*70)
    print("Summary by Type:")
    print("="*70)
    
    by_type = {}
    for entry in HUNTSVILLE_FREQUENCIES:
        t = entry['type']
        by_type[t] = by_type.get(t, 0) + 1
    
    for dtype, count in sorted(by_type.items()):
        print(f"  {dtype}: {count}")
    
    stats = db.get_statistics()
    print(f"\nTotal devices in database: {stats['identified_devices']}")
    
    db.close()

def check_frequency_in_range(freq_hz, current_lat=None, current_lon=None):
    """Check if a frequency is expected at current location"""
    db = get_db()
    
    # Get current location
    if current_lat is None or current_lon is None:
        cursor = db.conn.cursor()
        cursor.execute('SELECT latitude, longitude FROM current_location WHERE id = 1')
        row = cursor.fetchone()
        if row:
            current_lat, current_lon = row
    
    if current_lat is None:
        return None
    
    # Find devices at this frequency with location data
    cursor = db.conn.cursor()
    cursor.execute('''
        SELECT name, device_type, latitude, longitude, range_km, agency
        FROM devices
        WHERE frequency_hz = ? AND latitude IS NOT NULL
    ''', (freq_hz,))
    
    results = cursor.fetchall()
    
    for row in results:
        name, dtype, lat, lon, range_km, agency = row
        
        if lat and lon and range_km:
            distance = haversine_distance(current_lat, current_lon, lat, lon)
            
            if distance <= range_km:
                return {
                    'in_range': True,
                    'name': name,
                    'type': dtype,
                    'distance_km': distance,
                    'range_km': range_km,
                    'agency': agency
                }
    
    return {'in_range': False}

if __name__ == "__main__":
    load_huntsville_frequencies()
    
    # Test range checking
    print("\n" + "="*70)
    print("Testing Location-Aware Detection")
    print("="*70)
    
    test_freqs = [
        145.230e6,  # W4XE repeater (should be in range)
        858.4375e6,  # Huntsville PD (should be in range)
        146.000e6,  # Random (not expected in Huntsville)
    ]
    
    for freq in test_freqs:
        result = check_frequency_in_range(freq, HUNTSVILLE_LAT, HUNTSVILLE_LON)
        print(f"\n{freq/1e6:.4f} MHz:")
        if result and result.get('in_range'):
            print(f"  IN RANGE: {result['name']}")
            print(f"  Type: {result['type']}")
            print(f"  Distance: {result['distance_km']:.1f} km")
            print(f"  Expected range: {result['range_km']} km")
        else:
            print(f"  Not expected at this location")

