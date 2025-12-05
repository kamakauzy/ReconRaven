"""API Client for Touch App

Handles all communication with ReconRaven REST API.
"""


import requests


class ReconRavenAPI:
    """Client for ReconRaven REST API."""

    def __init__(self, base_url: str = 'http://localhost:5001/api/v1', api_key: str | None = None):
        self.base_url = base_url
        self.api_key = api_key or self._load_api_key()
        self.headers = {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json'
        } if self.api_key else {}
        self.cache = {}
        self.last_update = {}

    def _load_api_key(self) -> str | None:
        """Load API key from file."""
        try:
            with open('config/api_key.txt') as f:
                content = f.read()
                # Extract key from file (format: "API Key...: <key>")
                for line in content.split('\n'):
                    if ':' in line and len(line.split(':')[1].strip()) > 20:
                        return line.split(':')[1].strip()
            return None
        except (FileNotFoundError, IndexError):
            return None

    def _get(self, endpoint: str, params: dict | None = None) -> dict | None:
        """Make GET request to API."""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, headers=self.headers, params=params, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API GET error ({endpoint}): {e}")
            return None

    def _post(self, endpoint: str, data: dict | None = None) -> dict | None:
        """Make POST request to API."""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.post(url, headers=self.headers, json=data, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API POST error ({endpoint}): {e}")
            return None

    # Scanning endpoints
    def get_scan_status(self) -> dict | None:
        """Get current scanning status."""
        return self._get('/scan/status')

    def start_scan(self, bands: list[str] | None = None, rebuild_baseline: bool = False) -> dict | None:
        """Start scanning."""
        data = {
            'bands': bands or [],
            'rebuild_baseline': rebuild_baseline,
            'dashboard': False
        }
        return self._post('/scan/start', data)

    def stop_scan(self) -> dict | None:
        """Stop scanning."""
        return self._post('/scan/stop')

    def get_anomalies(self, limit: int = 50) -> list[dict]:
        """Get recent anomalies."""
        result = self._get('/scan/anomalies', {'limit': limit})
        return result.get('anomalies', []) if result else []

    # Database endpoints
    def get_devices(self, min_confidence: float = 0.0) -> list[dict]:
        """Get identified devices."""
        result = self._get('/db/devices', {'min_confidence': min_confidence})
        return result.get('devices', []) if result else []

    def get_transcripts(self, query: str = '', limit: int = 50) -> list[dict]:
        """Search transcripts."""
        result = self._get('/db/transcripts', {'query': query, 'limit': limit})
        return result.get('transcripts', []) if result else []

    def get_stats(self) -> dict:
        """Get database statistics."""
        result = self._get('/db/stats')
        return result if result else {}

    def promote_device(self, frequency: float) -> dict | None:
        """Promote device to baseline."""
        return self._post('/db/promote', {'frequency': frequency})

    # Demodulation endpoints
    def demodulate_frequency(self, frequency: float, mode: str = 'FM', duration: int = 10) -> dict | None:
        """Demodulate a frequency."""
        return self._get(f'/demod/freq/{frequency}', {'mode': mode, 'duration': duration})

    # Direction finding endpoints
    def get_bearing(self, anomaly_id: int) -> dict | None:
        """Get bearing for anomaly."""
        return self._get(f'/df/bearing/{anomaly_id}')

    def get_df_status(self) -> dict | None:
        """Get DF system status."""
        return self._get('/df/status')

    # Transcription endpoints
    def transcribe_recording(self, recording_id: int, model: str = 'base') -> dict | None:
        """Transcribe a recording."""
        return self._post(f'/transcribe/recording/{recording_id}', {'model': model})

    # Health check
    def is_connected(self) -> bool:
        """Check if API is reachable."""
        try:
            response = requests.get(f'{self.base_url}/health', timeout=2)
            return response.status_code == 200
        except requests.RequestException:
            return False

