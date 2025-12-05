"""Location-Aware Frequency Matcher

Intelligently identifies frequencies based on user location.
"""

from reconraven.core.debug_helper import DebugHelper
from reconraven.location.database import get_location_db
from reconraven.location.detector import LocationDetector
from reconraven.location.noaa import NOAAStations


class FrequencyMatcher(DebugHelper):
    """Match frequencies to known transmitters based on location."""

    def __init__(self):
        super().__init__(component_name='FrequencyMatcher')
        self.debug_enabled = True
        self.db = get_location_db()
        self.detector = LocationDetector()
        self.noaa = NOAAStations()

    def identify_frequency(
        self, frequency: float, user_lat: float | None = None, user_lon: float | None = None
    ) -> dict | None:
        """Identify a frequency based on location context.

        Args:
            frequency: Frequency in MHz
            user_lat: User latitude (optional, will auto-detect)
            user_lon: User longitude (optional, will auto-detect)

        Returns:
            Identification dict or None if unknown
        """
        # Get user location if not provided
        if user_lat is None or user_lon is None:
            last_location = self.db.get_last_location()
            if last_location:
                user_lat = last_location['latitude']
                user_lon = last_location['longitude']
            else:
                self.log_warning('No user location available, identification may be incomplete')

        # Check if it's a NOAA frequency
        if self.noaa.is_noaa_frequency(frequency):
            self.log_info(f'{frequency} MHz identified as NOAA Weather Radio')
            noaa_matches = self.db.find_frequency(frequency)
            noaa_matches = [m for m in noaa_matches if m['type'] == 'noaa']
            if noaa_matches:
                return {
                    'frequency': frequency,
                    'type': 'NOAA Weather Radio',
                    'confidence': 1.0,
                    'details': noaa_matches[0],
                }

        # Search database for exact matches
        matches = self.db.find_frequency(frequency, tolerance=0.005)

        if not matches:
            self.log_debug(f'No matches found for {frequency} MHz')
            return None

        # If we have location, filter by proximity
        if user_lat and user_lon:
            matches = self._filter_by_proximity(matches, user_lat, user_lon, max_distance_km=100)

        if not matches:
            self.log_debug(f'No nearby matches for {frequency} MHz')
            return None

        # Return best match (first one for now, could add confidence scoring)
        best_match = matches[0]

        identification = {
            'frequency': frequency,
            'type': best_match['type'],
            'confidence': 0.9,  # High confidence if in range
            'details': best_match,
        }

        self.log_info(
            f"{frequency} MHz identified as {best_match['type']}: {best_match.get('callsign') or best_match.get('description')}"
        )
        return identification

    def _filter_by_proximity(
        self, matches: list[dict], user_lat: float, user_lon: float, max_distance_km: float = 100
    ) -> list[dict]:
        """Filter matches by proximity to user.

        Uses simple distance calculation to filter out far-away matches.
        """
        filtered = []

        for match in matches:
            match_lat = match.get('latitude')
            match_lon = match.get('longitude')

            if match_lat is None or match_lon is None:
                # No location data, keep it
                filtered.append(match)
                continue

            # Simple distance calculation (Haversine approximation)
            lat_diff = abs(user_lat - match_lat)
            lon_diff = abs(user_lon - match_lon)
            distance_km = ((lat_diff**2 + lon_diff**2) ** 0.5) * 111.0  # Rough approximation

            if distance_km <= max_distance_km:
                match['distance_km'] = round(distance_km, 1)
                filtered.append(match)

        # Sort by distance
        filtered.sort(key=lambda m: m.get('distance_km', 9999))

        return filtered

    def get_nearby_frequencies(self, radius_km: float = 50) -> list[dict]:
        """Get all known frequencies near user's location.

        Args:
            radius_km: Search radius in kilometers

        Returns:
            List of frequencies with details
        """
        # Get user location
        last_location = self.db.get_last_location()
        if not last_location:
            self.log_warning('No user location available')
            location = self.detector.auto_detect()
            if not location:
                self.log_error('Failed to detect location')
                return []
            last_location = location

        user_lat = last_location['latitude']
        user_lon = last_location['longitude']

        # Get nearby frequencies from database
        nearby = self.db.find_nearby_frequencies(user_lat, user_lon, radius_km)

        self.log_info(f'Found {len(nearby)} frequencies within {radius_km} km')
        return nearby
