"""NOAA Weather Radio Stations Database

NOAA weather radio frequencies and station information.
Based on NWS station database.
"""

from reconraven.core.debug_helper import DebugHelper
from reconraven.location.database import get_location_db


class NOAAStations(DebugHelper):
    """NOAA weather radio station database."""

    # NOAA Weather Radio frequencies (MHz)
    NOAA_FREQUENCIES = [162.400, 162.425, 162.450, 162.475, 162.500, 162.525, 162.550]

    # Major NOAA stations (curated list - expand as needed)
    STATIONS = [
        # Alabama
        {
            'freq': 162.550,
            'call': 'WXL95',
            'name': 'Birmingham',
            'city': 'Birmingham',
            'state': 'AL',
            'lat': 33.5186,
            'lon': -86.8104,
            'range': 65,
        },
        {
            'freq': 162.400,
            'call': 'KEC83',
            'name': 'Huntsville',
            'city': 'Huntsville',
            'state': 'AL',
            'lat': 34.7304,
            'lon': -86.5859,
            'range': 65,
        },
        {
            'freq': 162.475,
            'call': 'WXJ44',
            'name': 'Mobile',
            'city': 'Mobile',
            'state': 'AL',
            'lat': 30.6954,
            'lon': -88.0399,
            'range': 65,
        },
        # California
        {
            'freq': 162.400,
            'call': 'WXK95',
            'name': 'Los Angeles',
            'city': 'Los Angeles',
            'state': 'CA',
            'lat': 34.0522,
            'lon': -118.2437,
            'range': 65,
        },
        {
            'freq': 162.550,
            'call': 'WXK46',
            'name': 'San Francisco',
            'city': 'San Francisco',
            'state': 'CA',
            'lat': 37.7749,
            'lon': -122.4194,
            'range': 65,
        },
        {
            'freq': 162.475,
            'call': 'WXK75',
            'name': 'San Diego',
            'city': 'San Diego',
            'state': 'CA',
            'lat': 32.7157,
            'lon': -117.1611,
            'range': 65,
        },
        # Florida
        {
            'freq': 162.550,
            'call': 'WXK40',
            'name': 'Miami',
            'city': 'Miami',
            'state': 'FL',
            'lat': 25.7617,
            'lon': -80.1918,
            'range': 65,
        },
        {
            'freq': 162.400,
            'call': 'WXK76',
            'name': 'Tampa',
            'city': 'Tampa',
            'state': 'FL',
            'lat': 27.9506,
            'lon': -82.4572,
            'range': 65,
        },
        # Georgia
        {
            'freq': 162.550,
            'call': 'WXJ72',
            'name': 'Atlanta',
            'city': 'Atlanta',
            'state': 'GA',
            'lat': 33.7490,
            'lon': -84.3880,
            'range': 65,
        },
        # Illinois
        {
            'freq': 162.550,
            'call': 'WXJ77',
            'name': 'Chicago',
            'city': 'Chicago',
            'state': 'IL',
            'lat': 41.8781,
            'lon': -87.6298,
            'range': 65,
        },
        # New York
        {
            'freq': 162.550,
            'call': 'WXJ35',
            'name': 'New York City',
            'city': 'New York',
            'state': 'NY',
            'lat': 40.7128,
            'lon': -74.0060,
            'range': 65,
        },
        # Texas
        {
            'freq': 162.550,
            'call': 'KEC53',
            'name': 'Houston',
            'city': 'Houston',
            'state': 'TX',
            'lat': 29.7604,
            'lon': -95.3698,
            'range': 65,
        },
        {
            'freq': 162.475,
            'call': 'KZZ72',
            'name': 'Dallas',
            'city': 'Dallas',
            'state': 'TX',
            'lat': 32.7767,
            'lon': -96.7970,
            'range': 65,
        },
        # Washington
        {
            'freq': 162.425,
            'call': 'WWG87',
            'name': 'Seattle',
            'city': 'Seattle',
            'state': 'WA',
            'lat': 47.6062,
            'lon': -122.3321,
            'range': 65,
        },
    ]

    def __init__(self):
        super().__init__(component_name='NOAAStations')
        self.debug_enabled = True

    def import_all_stations(self):
        """Import all NOAA stations to database."""
        db = get_location_db()
        imported = 0

        for station in self.STATIONS:
            db.add_noaa_station(
                frequency=station['freq'],
                call_sign=station['call'],
                station_name=station['name'],
                city=station['city'],
                state=station['state'],
                latitude=station['lat'],
                longitude=station['lon'],
                range_km=station['range'],
            )
            imported += 1

        self.log_info(f'Imported {imported} NOAA stations')
        return imported

    def get_all_frequencies(self) -> list[float]:
        """Get list of all NOAA frequencies."""
        return self.NOAA_FREQUENCIES.copy()

    def is_noaa_frequency(self, freq: float, tolerance: float = 0.005) -> bool:
        """Check if frequency is a NOAA weather radio frequency.

        Args:
            freq: Frequency in MHz
            tolerance: Tolerance in MHz

        Returns:
            True if frequency matches a NOAA channel
        """
        return any(abs(freq - noaa_freq) <= tolerance for noaa_freq in self.NOAA_FREQUENCIES)
