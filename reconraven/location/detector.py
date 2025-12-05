"""Location Auto-Detection

Automatically detect user location using:
1. GPS hardware (if available)
2. IP geolocation (fallback)
"""

import requests

from reconraven.core.debug_helper import DebugHelper
from reconraven.location.database import get_location_db


class LocationDetector(DebugHelper):
    """Auto-detect user location."""

    def __init__(self):
        super().__init__(component_name='LocationDetector')
        self.debug_enabled = True

    def detect_from_gps(self) -> dict | None:
        """Detect location from GPS hardware.

        Returns:
            dict with lat, lon, altitude, or None if GPS unavailable
        """
        try:
            import gpsd

            # Connect to gpsd
            gpsd.connect()
            packet = gpsd.get_current()

            if packet.mode >= 2:  # 2D fix or better
                location = {
                    'latitude': packet.lat,
                    'longitude': packet.lon,
                    'altitude': packet.alt if packet.mode >= 3 else None,
                    'source': 'GPS',
                    'accuracy_m': packet.error.get('EPX', 0) if hasattr(packet, 'error') else None,
                }

                self.log_info(
                    f"GPS location: {location['latitude']:.4f}, {location['longitude']:.4f}"
                )
                return location
            self.log_warning('GPS has no fix')
            return None

        except (ImportError, AttributeError, ConnectionError) as e:
            self.log_info(f'GPS not available: {e}')
            return None

    def detect_from_ip(self) -> dict | None:
        """Detect location from IP address (fallback).

        Uses ip-api.com (free, no API key needed).

        Returns:
            dict with lat, lon, city, state, country
        """
        try:
            self.log_info('Detecting location from IP...')

            response = requests.get('http://ip-api.com/json/', timeout=10)
            response.raise_for_status()

            data = response.json()

            if data.get('status') == 'success':
                location = {
                    'latitude': data.get('lat'),
                    'longitude': data.get('lon'),
                    'city': data.get('city'),
                    'state': data.get('regionName'),
                    'state_code': data.get('region'),
                    'country': data.get('country'),
                    'zip': data.get('zip'),
                    'source': 'IP_Geolocation',
                }

                self.log_info(
                    f"IP location: {location['city']}, {location['state']} ({location['latitude']:.4f}, {location['longitude']:.4f})"
                )
                return location
            self.log_error(f"IP geolocation failed: {data.get('message')}")
            return None

        except requests.RequestException as e:
            self.log_error(f'Failed to detect location from IP: {e}')
            return None

    def auto_detect(self) -> dict | None:
        """Auto-detect location (GPS first, then IP fallback).

        Returns:
            Location dict or None if all methods fail
        """
        # Try GPS first
        location = self.detect_from_gps()

        # Fallback to IP
        if not location:
            self.log_info('GPS unavailable, falling back to IP geolocation')
            location = self.detect_from_ip()

        # Save to database if successful
        if location:
            db = get_location_db()
            db.save_user_location(
                lat=location['latitude'],
                lon=location['longitude'],
                city=location.get('city'),
                state=location.get('state'),
                country=location.get('country'),
                source=location.get('source', 'unknown'),
            )

            self.log_info('Location saved to database')

        return location

    def get_state_code_from_coordinates(self, lat: float, lon: float) -> str | None:
        """Get state code from coordinates using reverse geocoding.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Two-letter state code or None
        """
        try:
            # Use Nominatim (OpenStreetMap) for reverse geocoding
            url = 'https://nominatim.openstreetmap.org/reverse'
            params = {'lat': lat, 'lon': lon, 'format': 'json'}
            headers = {'User-Agent': 'ReconRaven/1.0 (RF scanning tool)'}

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            address = data.get('address', {})
            state = address.get('state')

            if state:
                # Convert state name to code (simple mapping for common states)
                state_mapping = {
                    'Alabama': 'AL',
                    'Alaska': 'AK',
                    'Arizona': 'AZ',
                    'Arkansas': 'AR',
                    'California': 'CA',
                    'Colorado': 'CO',
                    'Connecticut': 'CT',
                    'Delaware': 'DE',
                    'Florida': 'FL',
                    'Georgia': 'GA',
                    'Hawaii': 'HI',
                    'Idaho': 'ID',
                    'Illinois': 'IL',
                    'Indiana': 'IN',
                    'Iowa': 'IA',
                    'Kansas': 'KS',
                    'Kentucky': 'KY',
                    'Louisiana': 'LA',
                    'Maine': 'ME',
                    'Maryland': 'MD',
                    'Massachusetts': 'MA',
                    'Michigan': 'MI',
                    'Minnesota': 'MN',
                    'Mississippi': 'MS',
                    'Missouri': 'MO',
                    'Montana': 'MT',
                    'Nebraska': 'NE',
                    'Nevada': 'NV',
                    'New Hampshire': 'NH',
                    'New Jersey': 'NJ',
                    'New Mexico': 'NM',
                    'New York': 'NY',
                    'North Carolina': 'NC',
                    'North Dakota': 'ND',
                    'Ohio': 'OH',
                    'Oklahoma': 'OK',
                    'Oregon': 'OR',
                    'Pennsylvania': 'PA',
                    'Rhode Island': 'RI',
                    'South Carolina': 'SC',
                    'South Dakota': 'SD',
                    'Tennessee': 'TN',
                    'Texas': 'TX',
                    'Utah': 'UT',
                    'Vermont': 'VT',
                    'Virginia': 'VA',
                    'Washington': 'WA',
                    'West Virginia': 'WV',
                    'Wisconsin': 'WI',
                    'Wyoming': 'WY',
                }

                return state_mapping.get(state, state[:2].upper())

            return None

        except requests.RequestException as e:
            self.log_error(f'Reverse geocoding failed: {e}')
            return None
