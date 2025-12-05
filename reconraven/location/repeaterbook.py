"""RepeaterBook API Integration

Fetches ham radio repeater data from RepeaterBook's public API.
https://www.repeaterbook.com/wiki/doku.php?id=api
"""

import requests

from reconraven.core.debug_helper import DebugHelper
from reconraven.location.database import get_location_db


class RepeaterBookClient(DebugHelper):
    """Client for RepeaterBook API."""

    BASE_URL = 'https://www.repeaterbook.com/api/export.php'

    def __init__(self):
        super().__init__(component_name='RepeaterBookClient')
        self.debug_enabled = True

    def fetch_by_state(self, state_code: str) -> list[dict]:
        """Fetch all repeaters for a state.

        Args:
            state_code: Two-letter state code (e.g., 'AL', 'CA')

        Returns:
            List of repeater dictionaries
        """
        self.log_info(f'Fetching repeaters for state: {state_code}')

        try:
            params = {'state': state_code.upper(), 'country': 'United States'}

            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            repeaters = data.get('results', [])

            self.log_info(f'Fetched {len(repeaters)} repeaters for {state_code}')
            return repeaters

        except requests.RequestException as e:
            self.log_error(f'Failed to fetch repeaters: {e}')
            return []

    def fetch_by_location(self, lat: float, lon: float, radius_miles: int = 50) -> list[dict]:
        """Fetch repeaters within radius of location.

        Args:
            lat: Latitude
            lon: Longitude
            radius_miles: Search radius in miles

        Returns:
            List of repeater dictionaries
        """
        self.log_info(f'Fetching repeaters near ({lat}, {lon}) within {radius_miles} miles')

        try:
            params = {'lat': lat, 'long': lon, 'distance': radius_miles}

            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            repeaters = data.get('results', [])

            self.log_info(f'Fetched {len(repeaters)} nearby repeaters')
            return repeaters

        except requests.RequestException as e:
            self.log_error(f'Failed to fetch repeaters: {e}')
            return []

    def import_to_database(self, repeaters: list[dict]):
        """Import repeaters into location database.

        Args:
            repeaters: List of repeaters from API
        """
        db = get_location_db()
        imported = 0

        for rep in repeaters:
            try:
                # Parse frequency (might be in different formats)
                freq_str = rep.get('Frequency', rep.get('frequency', ''))
                freq = float(freq_str) if freq_str else None

                if not freq:
                    continue

                # Parse offset
                offset_str = rep.get('Offset', rep.get('offset', ''))
                offset = float(offset_str) if offset_str and offset_str != 'simplex' else None

                # Parse tone
                tone_str = rep.get('PL', rep.get('tone', ''))
                tone = float(tone_str) if tone_str and tone_str.replace('.', '').isdigit() else None

                # Parse coordinates
                lat_str = rep.get('Lat', rep.get('latitude', ''))
                lon_str = rep.get('Long', rep.get('longitude', ''))
                lat = float(lat_str) if lat_str else None
                lon = float(lon_str) if lon_str else None

                db.add_repeater(
                    frequency=freq,
                    offset=offset,
                    tone=tone,
                    callsign=rep.get('Call Sign', rep.get('callsign')),
                    location=rep.get('Nearest City', rep.get('location')),
                    city=rep.get('Nearest City', rep.get('city')),
                    state=rep.get('State', rep.get('state')),
                    latitude=lat,
                    longitude=lon,
                    range_km=None,  # Not provided by API
                    use_type=rep.get('Use', rep.get('use')),
                    notes=rep.get('Notes', rep.get('notes')),
                    source='RepeaterBook',
                )
                imported += 1

            except (ValueError, KeyError, TypeError) as e:
                self.log_warning(f'Failed to import repeater: {e}')
                continue

        self.log_info(f'Imported {imported} repeaters to database')
        return imported

    def setup_state(self, state_code: str) -> int:
        """One-shot setup: fetch and import repeaters for a state.

        Args:
            state_code: Two-letter state code

        Returns:
            Number of repeaters imported
        """
        repeaters = self.fetch_by_state(state_code)
        return self.import_to_database(repeaters)

    def setup_location(self, lat: float, lon: float, radius_miles: int = 50) -> int:
        """One-shot setup: fetch and import repeaters for a location.

        Args:
            lat: Latitude
            lon: Longitude
            radius_miles: Search radius

        Returns:
            Number of repeaters imported
        """
        repeaters = self.fetch_by_location(lat, lon, radius_miles)
        return self.import_to_database(repeaters)
