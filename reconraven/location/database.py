"""Location-Aware Frequency Database Schema

SQLite database schema for storing frequency data with geographic information.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class LocationFrequencyDB:
    """Manages location-aware frequency database."""

    def __init__(self, db_path: Path = Path('location_frequencies.db')):
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None
        self._init_database()

    def _init_database(self):
        """Initialize database with schema."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Repeaters table (ham radio repeaters)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repeaters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frequency REAL NOT NULL,
                offset REAL,
                tone REAL,
                callsign TEXT,
                location TEXT,
                city TEXT,
                state TEXT,
                latitude REAL,
                longitude REAL,
                range_km REAL,
                use_type TEXT,
                notes TEXT,
                source TEXT,
                added_date TEXT,
                UNIQUE(frequency, callsign, state)
            )
        """)

        # Public safety frequencies
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public_safety (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frequency REAL NOT NULL,
                description TEXT,
                agency TEXT,
                city TEXT,
                state TEXT,
                county TEXT,
                latitude REAL,
                longitude REAL,
                category TEXT,
                tone REAL,
                source TEXT,
                added_date TEXT,
                UNIQUE(frequency, agency, state)
            )
        """)

        # NOAA weather stations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS noaa_stations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frequency REAL NOT NULL,
                call_sign TEXT,
                station_name TEXT,
                city TEXT,
                state TEXT,
                latitude REAL,
                longitude REAL,
                range_km REAL,
                added_date TEXT,
                UNIQUE(frequency, call_sign)
            )
        """)

        # Aviation frequencies
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS aviation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frequency REAL NOT NULL,
                airport_code TEXT,
                airport_name TEXT,
                type TEXT,
                city TEXT,
                state TEXT,
                latitude REAL,
                longitude REAL,
                added_date TEXT,
                UNIQUE(frequency, airport_code, type)
            )
        """)

        # Marine frequencies
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS marine (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frequency REAL NOT NULL,
                channel_number INTEGER,
                description TEXT,
                location TEXT,
                latitude REAL,
                longitude REAL,
                range_km REAL,
                added_date TEXT,
                UNIQUE(frequency, channel_number, location)
            )
        """)

        # User location cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                latitude REAL,
                longitude REAL,
                city TEXT,
                state TEXT,
                country TEXT,
                timestamp TEXT,
                source TEXT
            )
        """)

        # Create indexes for fast lookups
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_repeaters_freq ON repeaters(frequency)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_repeaters_state ON repeaters(state)')
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_repeaters_location ON repeaters(latitude, longitude)'
        )

        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_public_safety_freq ON public_safety(frequency)'
        )
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_public_safety_state ON public_safety(state)')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_noaa_freq ON noaa_stations(frequency)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_aviation_freq ON aviation(frequency)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_marine_freq ON marine(frequency)')

        self.conn.commit()

    def add_repeater(self, frequency: float, **kwargs):
        """Add ham repeater to database."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO repeaters
            (frequency, offset, tone, callsign, location, city, state,
             latitude, longitude, range_km, use_type, notes, source, added_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                frequency,
                kwargs.get('offset'),
                kwargs.get('tone'),
                kwargs.get('callsign'),
                kwargs.get('location'),
                kwargs.get('city'),
                kwargs.get('state'),
                kwargs.get('latitude'),
                kwargs.get('longitude'),
                kwargs.get('range_km'),
                kwargs.get('use_type'),
                kwargs.get('notes'),
                kwargs.get('source', 'manual'),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self.conn.commit()

    def add_public_safety(self, frequency: float, **kwargs):
        """Add public safety frequency."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO public_safety
            (frequency, description, agency, city, state, county,
             latitude, longitude, category, tone, source, added_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                frequency,
                kwargs.get('description'),
                kwargs.get('agency'),
                kwargs.get('city'),
                kwargs.get('state'),
                kwargs.get('county'),
                kwargs.get('latitude'),
                kwargs.get('longitude'),
                kwargs.get('category'),
                kwargs.get('tone'),
                kwargs.get('source', 'manual'),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self.conn.commit()

    def add_noaa_station(self, frequency: float, **kwargs):
        """Add NOAA weather station."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO noaa_stations
            (frequency, call_sign, station_name, city, state,
             latitude, longitude, range_km, added_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                frequency,
                kwargs.get('call_sign'),
                kwargs.get('station_name'),
                kwargs.get('city'),
                kwargs.get('state'),
                kwargs.get('latitude'),
                kwargs.get('longitude'),
                kwargs.get('range_km'),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self.conn.commit()

    def find_frequency(self, frequency: float, tolerance: float = 0.005) -> list[dict]:
        """Find all known uses of a frequency (±tolerance MHz).

        Args:
            frequency: Frequency in MHz
            tolerance: Tolerance in MHz (default 5 kHz)

        Returns:
            List of matches from all tables
        """
        matches = []
        freq_min = frequency - tolerance
        freq_max = frequency + tolerance

        cursor = self.conn.cursor()

        # Check repeaters
        cursor.execute(
            """
            SELECT 'repeater' as type, * FROM repeaters
            WHERE frequency BETWEEN ? AND ?
        """,
            (freq_min, freq_max),
        )
        matches.extend([dict(row) for row in cursor.fetchall()])

        # Check public safety
        cursor.execute(
            """
            SELECT 'public_safety' as type, * FROM public_safety
            WHERE frequency BETWEEN ? AND ?
        """,
            (freq_min, freq_max),
        )
        matches.extend([dict(row) for row in cursor.fetchall()])

        # Check NOAA
        cursor.execute(
            """
            SELECT 'noaa' as type, * FROM noaa_stations
            WHERE frequency BETWEEN ? AND ?
        """,
            (freq_min, freq_max),
        )
        matches.extend([dict(row) for row in cursor.fetchall()])

        # Check aviation
        cursor.execute(
            """
            SELECT 'aviation' as type, * FROM aviation
            WHERE frequency BETWEEN ? AND ?
        """,
            (freq_min, freq_max),
        )
        matches.extend([dict(row) for row in cursor.fetchall()])

        # Check marine
        cursor.execute(
            """
            SELECT 'marine' as type, * FROM marine
            WHERE frequency BETWEEN ? AND ?
        """,
            (freq_min, freq_max),
        )
        matches.extend([dict(row) for row in cursor.fetchall()])

        return matches

    def find_nearby_frequencies(self, lat: float, lon: float, radius_km: float = 50) -> list[dict]:
        """Find all frequencies within radius of location.

        Uses Haversine formula approximation for distance.
        """
        matches = []
        cursor = self.conn.cursor()

        # Simple lat/lon box filter (fast)
        # Approx: 1 degree latitude = 111 km
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * abs(0.9996))  # Rough longitude correction

        # Repeaters
        cursor.execute(
            """
            SELECT 'repeater' as type, * FROM repeaters
            WHERE latitude BETWEEN ? AND ?
              AND longitude BETWEEN ? AND ?
              AND latitude IS NOT NULL
        """,
            (lat - lat_delta, lat + lat_delta, lon - lon_delta, lon + lon_delta),
        )
        matches.extend([dict(row) for row in cursor.fetchall()])

        # Public safety
        cursor.execute(
            """
            SELECT 'public_safety' as type, * FROM public_safety
            WHERE latitude BETWEEN ? AND ?
              AND longitude BETWEEN ? AND ?
              AND latitude IS NOT NULL
        """,
            (lat - lat_delta, lat + lat_delta, lon - lon_delta, lon + lon_delta),
        )
        matches.extend([dict(row) for row in cursor.fetchall()])

        # NOAA
        cursor.execute(
            """
            SELECT 'noaa' as type, * FROM noaa_stations
            WHERE latitude BETWEEN ? AND ?
              AND longitude BETWEEN ? AND ?
              AND latitude IS NOT NULL
        """,
            (lat - lat_delta, lat + lat_delta, lon - lon_delta, lon + lon_delta),
        )
        matches.extend([dict(row) for row in cursor.fetchall()])

        return matches

    def save_user_location(
        self,
        lat: float,
        lon: float,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        source: str = 'manual',
    ):
        """Save user's current location."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_locations (latitude, longitude, city, state, country, timestamp, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (lat, lon, city, state, country, datetime.now(timezone.utc).isoformat(), source),
        )
        self.conn.commit()

    def get_last_location(self) -> dict | None:
        """Get last saved user location."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM user_locations ORDER BY timestamp DESC LIMIT 1')
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_stats(self) -> dict:
        """Get database statistics."""
        cursor = self.conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM repeaters')
        repeater_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM public_safety')
        public_safety_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM noaa_stations')
        noaa_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM aviation')
        aviation_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM marine')
        marine_count = cursor.fetchone()[0]

        return {
            'repeaters': repeater_count,
            'public_safety': public_safety_count,
            'noaa_stations': noaa_count,
            'aviation': aviation_count,
            'marine': marine_count,
            'total': repeater_count
            + public_safety_count
            + noaa_count
            + aviation_count
            + marine_count,
        }

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


# Global instance
_db_instance: LocationFrequencyDB | None = None


def get_location_db() -> LocationFrequencyDB:
    """Get global location database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = LocationFrequencyDB()
    return _db_instance
