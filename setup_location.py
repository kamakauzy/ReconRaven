#!/usr/bin/env python3
"""
ReconRaven Location Setup Tool
Downloads state-specific frequencies from public databases
"""

import requests
import json
import argparse
from database import get_db
import os
import time

class FrequencyDownloader:
    """Download frequencies from public APIs"""
    
    def __init__(self):
        self.db = get_db()
        self.cache_dir = "frequency_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_location_from_ip(self):
        """Get approximate location from IP (for --auto mode)"""
        try:
            print("Detecting location from IP...")
            response = requests.get('http://ip-api.com/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success':
                    print(f"  Detected: {data['city']}, {data['regionName']}")
                    return {
                        'city': data['city'],
                        'state': data['regionName'],
                        'state_code': data['region'],
                        'lat': data['lat'],
                        'lon': data['lon'],
                        'zip': data.get('zip', '')
                    }
        except Exception as e:
            print(f"  Failed: {e}")
        return None
    
    def download_repeaterbook_csv(self, state_code):
        """Download ham repeaters from RepeaterBook
        RepeaterBook provides free CSV exports of all US repeaters
        """
        print(f"\n[1/3] Downloading ham repeaters for {state_code}...")
        
        # RepeaterBook CSV download (free, no API key needed)
        url = f"https://www.repeaterbook.com/api/export.php?state={state_code}&type=csv"
        
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                # Save to cache
                cache_file = f"{self.cache_dir}/repeaterbook_{state_code}.csv"
                with open(cache_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                # Parse CSV
                repeaters = self._parse_repeaterbook_csv(response.text, state_code)
                print(f"  Found {len(repeaters)} repeaters")
                return repeaters
            else:
                print(f"  Failed: HTTP {response.status_code}")
                return []
        except Exception as e:
            print(f"  Error: {e}")
            return []
    
    def _parse_repeaterbook_csv(self, csv_text, state_code):
        """Parse RepeaterBook CSV format"""
        repeaters = []
        lines = csv_text.strip().split('\n')
        
        if len(lines) < 2:
            return repeaters
        
        # Skip header
        for line in lines[1:]:
            try:
                parts = line.split(',')
                if len(parts) < 10:
                    continue
                
                # CSV format: Frequency,Offset,Tone,Call,Location,County,State,Lat,Lon,Notes...
                freq_str = parts[0].strip()
                if not freq_str:
                    continue
                
                freq_mhz = float(freq_str)
                freq_hz = freq_mhz * 1e6
                
                # Determine band
                if 144 <= freq_mhz <= 148:
                    band = '2m'
                elif 420 <= freq_mhz <= 450:
                    band = '70cm'
                elif 222 <= freq_mhz <= 225:
                    band = '1.25m'
                else:
                    continue
                
                repeater = {
                    'freq': freq_hz,
                    'name': f"{parts[3].strip()} {band} Repeater",
                    'type': 'ham_repeater',
                    'band': band,
                    'mode': 'FM',
                    'callsign': parts[3].strip(),
                    'tone': parts[2].strip(),
                    'location': parts[4].strip(),
                    'state': state_code,
                    'lat': float(parts[7].strip()) if parts[7].strip() else None,
                    'lon': float(parts[8].strip()) if parts[8].strip() else None,
                    'range_km': 60 if band == '2m' else 40  # Estimated
                }
                
                repeaters.append(repeater)
                
            except (ValueError, IndexError) as e:
                continue
        
        return repeaters
    
    def download_public_safety(self, state_code, lat=None, lon=None):
        """Download public safety frequencies
        Uses RadioReference API (requires free account) or falls back to static data
        """
        print(f"\n[2/3] Looking up public safety frequencies for {state_code}...")
        
        # For now, return state-level allocations (no API key needed)
        # In future: integrate RadioReference API with user's key
        
        # State police typically use these bands
        ps_freqs = []
        
        # VHF Low Band (some states)
        if state_code in ['AL', 'MS', 'LA', 'AR', 'TN', 'KY']:
            ps_freqs.extend([
                {
                    'freq': 154.920e6,
                    'name': f'{state_code} State Police',
                    'type': 'state_police',
                    'band': 'VHF',
                    'mode': 'FM',
                    'state': state_code,
                    'lat': lat,
                    'lon': lon,
                    'range_km': 100
                },
                {
                    'freq': 155.445e6,
                    'name': f'{state_code} State Police',
                    'type': 'state_police',
                    'band': 'VHF',
                    'mode': 'FM',
                    'state': state_code,
                    'lat': lat,
                    'lon': lon,
                    'range_km': 100
                }
            ])
        
        print(f"  Added {len(ps_freqs)} state-level frequencies")
        print("  Note: For detailed local frequencies, use RadioReference.com")
        
        return ps_freqs
    
    def download_noaa_weather(self, lat, lon):
        """Get NOAA weather radio stations near location"""
        print(f"\n[3/3] Finding NOAA weather radio stations...")
        
        # NOAA weather frequencies (standard across US)
        noaa_freqs = [
            162.400e6, 162.425e6, 162.450e6, 162.475e6,
            162.500e6, 162.525e6, 162.550e6
        ]
        
        # All NOAA stations use these 7 frequencies
        # Assign closest one based on location (simplified)
        # In reality, would query NOAA transmitter database
        
        stations = []
        for i, freq in enumerate(noaa_freqs):
            stations.append({
                'freq': freq,
                'name': f'NOAA Weather Radio WX{i+1}',
                'type': 'weather',
                'band': 'VHF',
                'mode': 'FM',
                'lat': lat,
                'lon': lon,
                'range_km': 80,
                'notes': 'NOAA National Weather Service'
            })
        
        print(f"  Added {len(stations)} NOAA channels")
        return stations
    
    def save_to_database(self, frequencies):
        """Save downloaded frequencies to database"""
        print(f"\nSaving {len(frequencies)} frequencies to database...")
        
        added = 0
        updated = 0
        
        for freq_data in frequencies:
            try:
                # Add as device
                device_id = self.db.add_device(
                    freq=freq_data['freq'],
                    name=freq_data['name'],
                    manufacturer=freq_data.get('callsign', 'Public'),
                    device_type=freq_data['type'],
                    modulation=freq_data.get('mode', 'FM'),
                    confidence=1.0
                )
                
                # Update with location data
                if freq_data.get('lat') and freq_data.get('lon'):
                    cursor = self.db.conn.cursor()
                    cursor.execute('''
                        UPDATE devices SET
                            latitude = ?,
                            longitude = ?,
                            range_km = ?,
                            tone = ?,
                            callsign = ?,
                            notes = ?
                        WHERE id = ?
                    ''', (
                        freq_data['lat'],
                        freq_data['lon'],
                        freq_data.get('range_km'),
                        freq_data.get('tone'),
                        freq_data.get('callsign'),
                        freq_data.get('notes'),
                        device_id
                    ))
                    self.db.conn.commit()
                
                added += 1
                
            except Exception as e:
                updated += 1
                continue
        
        print(f"  Added: {added}")
        print(f"  Updated/Skipped: {updated}")
        
        return added
    
    def update_location(self, lat, lon, city=None, state=None):
        """Update current location in database"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO current_location (id, latitude, longitude, source)
            VALUES (1, ?, ?, ?)
        ''', (lat, lon, 'manual' if city else 'auto'))
        self.db.conn.commit()
        
        print(f"\nLocation updated: {lat:.4f}, {lon:.4f}")
        if city and state:
            print(f"  {city}, {state}")

def main():
    parser = argparse.ArgumentParser(
        description='Download frequency database for your location',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Automatic detection:
  python setup_location.py --auto
  
  # Manual location:
  python setup_location.py --state AL --city Huntsville
  
  # Specific coordinates:
  python setup_location.py --lat 34.7304 --lon -86.5859 --state AL
  
  # Update existing data:
  python setup_location.py --state AL --update
        """
    )
    
    parser.add_argument('--auto', action='store_true',
                       help='Auto-detect location from IP')
    parser.add_argument('--state', type=str,
                       help='State code (e.g., AL, CA, TX)')
    parser.add_argument('--city', type=str,
                       help='City name')
    parser.add_argument('--lat', type=float,
                       help='Latitude')
    parser.add_argument('--lon', type=float,
                       help='Longitude')
    parser.add_argument('--update', action='store_true',
                       help='Update existing data')
    
    args = parser.parse_args()
    
    print("="*70)
    print("ReconRaven Location Setup")
    print("="*70)
    
    downloader = FrequencyDownloader()
    
    # Determine location
    if args.auto:
        location = downloader.get_location_from_ip()
        if not location:
            print("\nAuto-detection failed. Please specify --state manually.")
            return
        
        state_code = location['state_code']
        lat = location['lat']
        lon = location['lon']
        city = location['city']
        state_name = location['state']
        
    elif args.state:
        state_code = args.state.upper()
        city = args.city
        state_name = args.state
        
        # Use provided coordinates or geocode city
        if args.lat and args.lon:
            lat = args.lat
            lon = args.lon
        else:
            # Default to state center (simplified)
            print(f"\nNote: Using approximate coordinates for {state_code}")
            print("For better results, use --lat and --lon")
            lat, lon = 34.0, -86.0  # Placeholder
    else:
        print("\nError: Must specify --auto OR --state")
        parser.print_help()
        return
    
    print(f"\nLocation: {city if city else state_name}, {state_code}")
    print(f"Coordinates: {lat:.4f}, {lon:.4f}")
    
    # Download data
    all_frequencies = []
    
    # 1. Ham repeaters
    repeaters = downloader.download_repeaterbook_csv(state_code)
    all_frequencies.extend(repeaters)
    
    # 2. Public safety
    ps_freqs = downloader.download_public_safety(state_code, lat, lon)
    all_frequencies.extend(ps_freqs)
    
    # 3. NOAA weather
    noaa_freqs = downloader.download_noaa_weather(lat, lon)
    all_frequencies.extend(noaa_freqs)
    
    # Save to database
    if all_frequencies:
        added = downloader.save_to_database(all_frequencies)
        downloader.update_location(lat, lon, city, state_name)
        
        # Summary
        stats = downloader.db.get_statistics()
        print("\n" + "="*70)
        print("Setup Complete!")
        print("="*70)
        print(f"\nTotal devices in database: {stats['identified_devices']}")
        print(f"Baseline frequencies: {stats['baseline_frequencies']}")
        
        print("\nBreakdown:")
        cursor = downloader.db.conn.cursor()
        cursor.execute('''
            SELECT device_type, COUNT(*) 
            FROM devices 
            GROUP BY device_type
            ORDER BY COUNT(*) DESC
        ''')
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")
        
        print("\nReady to scan!")
        print("Run: python run_live_scan.py")
    else:
        print("\nNo frequencies downloaded. Check your internet connection.")

if __name__ == "__main__":
    main()

