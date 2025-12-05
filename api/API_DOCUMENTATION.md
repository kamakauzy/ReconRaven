# ReconRaven REST API Documentation

**Version:** 1.0.0  
**Base URL:** `http://localhost:5001/api/v1/`  
**WebSocket:** `ws://localhost:5001/api/v1/ws`

## Authentication

All endpoints (except `/health` and `/auth/key`) require authentication.

### Methods

**API Key (Header)**
```
X-API-Key: your_api_key_here
```

**JWT Token (Header)**
```
Authorization: Bearer your_jwt_token_here
```

### Getting Your API Key

1. Start the API server:
```bash
python api/server.py
```

2. Retrieve your API key:
```bash
curl http://localhost:5001/api/v1/auth/key
```

Or check: `config/api_key.txt`

### Generating a JWT Token

```bash
curl -X POST http://localhost:5001/api/v1/auth/token \
  -H "X-API-Key: your_api_key"
```

---

## Endpoints

### 🔍 Scanning

#### Get Scan Status
```http
GET /api/v1/scan/status
```

**Response:**
```json
{
  "scanning": false,
  "uptime_seconds": 0,
  "current_frequency": null,
  "bands_scanned": [],
  "anomalies_detected": 42,
  "baseline_frequencies": 150,
  "last_scan": "2025-12-05T19:30:00Z"
}
```

#### Start Scanning
```http
POST /api/v1/scan/start
```

**Body:**
```json
{
  "bands": ["2m", "70cm", "433MHz"],
  "rebuild_baseline": false,
  "dashboard": true
}
```

**Response:**
```json
{
  "status": "started",
  "bands": ["2m", "70cm"],
  "message": "Scanner start requested"
}
```

#### Stop Scanning
```http
POST /api/v1/scan/stop
```

#### Get Recent Anomalies
```http
GET /api/v1/scan/anomalies?limit=50&since=2025-12-05T00:00:00Z&min_power=15.0
```

**Parameters:**
- `limit` (int): Max results (default 50)
- `since` (ISO timestamp): Only anomalies after this time
- `min_power` (float): Minimum power level (dB)

**Response:**
```json
{
  "count": 5,
  "anomalies": [
    {
      "frequency": 146520000,
      "power": 25.3,
      "timestamp": "2025-12-05T19:30:00Z",
      "duration_ms": 150
    }
  ]
}
```

---

### 📡 Demodulation

#### Demodulate Frequency
```http
GET /api/v1/demod/freq/146.52?mode=FM&duration=10&output=wav
```

**Parameters:**
- `mode`: FM, AM, USB, LSB, DMR, P25, etc.
- `duration`: Recording duration (seconds)
- `output`: wav, npy, both

**Response:**
```json
{
  "frequency": 146.52,
  "mode": "FM",
  "status": "success",
  "file_path": "recordings/audio/demod_146.52_FM.wav"
}
```

#### Decode Binary Signal
```http
POST /api/v1/decode/binary
```

**Body:**
```json
{
  "signal_data": [0.1, 0.5, 0.2, ...],
  "protocol": "OOK",
  "sample_rate": 2400000
}
```

**Response:**
```json
{
  "protocol": "OOK",
  "decoded_hex": "0xABCD1234",
  "decoded_binary": "10101011...",
  "confidence": 0.85
}
```

#### List Protocols
```http
GET /api/v1/demod/protocols
```

---

### 🧭 Direction Finding

#### Get Bearing
```http
GET /api/v1/df/bearing/123
```

**Response:**
```json
{
  "anomaly_id": 123,
  "bearing_degrees": 45.0,
  "confidence": 0.85,
  "snr_db": 15.2,
  "accuracy_estimate": 5.0
}
```

#### Calibrate Array
```http
POST /api/v1/df/calibrate
```

**Body:**
```json
{
  "frequency": 146.52,
  "known_bearing": 90.0,
  "duration": 30
}
```

#### DF Status
```http
GET /api/v1/df/status
```

---

### 💾 Database

#### Search Transcripts
```http
GET /api/v1/db/transcripts?query=meeting&language=EN&band=2m&min_confidence=0.8&limit=50
```

**Parameters:**
- `query`: Search text
- `language`: Language code (EN, ES, ZH, RU, etc.)
- `band`: Frequency band filter
- `min_confidence`: Minimum confidence (0-1)
- `limit`: Max results

**Response:**
```json
{
  "count": 2,
  "transcripts": [
    {
      "id": 1,
      "text": "Meeting at checkpoint bravo...",
      "frequency": 146520000,
      "language": "EN",
      "confidence": 0.92,
      "timestamp": "2025-12-05T19:30:00Z"
    }
  ]
}
```

#### List Devices
```http
GET /api/v1/db/devices?min_confidence=0.8&in_baseline=true&limit=100
```

**Response:**
```json
{
  "count": 5,
  "devices": [
    {
      "frequency": 433920000,
      "device_type": "Remote Control",
      "manufacturer": "Unknown",
      "confidence": 0.85,
      "in_baseline": true
    }
  ]
}
```

#### Promote Device to Baseline
```http
POST /api/v1/db/promote
```

**Body:**
```json
{
  "frequency": 433.92,
  "device_id": 42
}
```

#### Export Data
```http
GET /api/v1/db/export?format=json&type=all
```

**Parameters:**
- `format`: json, csv, txt
- `type`: devices, transcripts, anomalies, all

#### Database Statistics
```http
GET /api/v1/db/stats
```

**Response:**
```json
{
  "baseline_frequencies": 150,
  "total_detections": 1024,
  "anomalies": 42,
  "identified_devices": 25,
  "transcripts": 10,
  "recordings_count": 50,
  "storage": {
    "database_mb": 5.2,
    "recordings_mb": 1830.0,
    "total_mb": 1835.2
  }
}
```

---

### 🎙️ Voice Transcription

#### Transcribe Recording
```http
POST /api/v1/transcribe/recording/123
```

**Body:**
```json
{
  "model": "base",
  "language": "en"
}
```

**Models:** `tiny`, `base`, `small`, `medium`, `large`

**Response:**
```json
{
  "recording_id": 123,
  "model": "base",
  "transcript": {
    "text": "Checkpoint bravo secure...",
    "language": "en",
    "confidence": 0.92,
    "duration": 10.5,
    "keywords": ["checkpoint", "bravo", "secure"]
  }
}
```

#### Batch Transcribe
```http
POST /api/v1/transcribe/batch
```

**Body:**
```json
{
  "model": "base",
  "max_count": 100
}
```

#### List Models
```http
GET /api/v1/transcribe/models
```

---

### 🔌 WebSocket Events

**Connect:**
```javascript
const socket = io('http://localhost:5001/api/v1/ws');
```

**Subscribe to Events:**
```javascript
socket.emit('subscribe', { events: ['anomalies', 'scan', 'transcripts', 'devices'] });
```

**Event Types:**

**`anomaly_detected`**
```json
{
  "type": "anomaly_detected",
  "timestamp": "2025-12-05T19:30:00Z",
  "data": {
    "frequency": 146520000,
    "power": 25.3
  }
}
```

**`scan_progress`**
```json
{
  "type": "scan_progress",
  "data": {
    "current_frequency": 146500000,
    "progress_percent": 45.2
  }
}
```

**`transcription_complete`**
```json
{
  "type": "transcription_complete",
  "data": {
    "recording_id": 123,
    "text": "Transcript here..."
  }
}
```

**`device_identified`**
```json
{
  "type": "device_identified",
  "data": {
    "frequency": 433920000,
    "device_type": "Remote Control"
  }
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "error": "Error type",
  "message": "Detailed error message"
}
```

**Common Status Codes:**
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (missing/invalid auth)
- `404` - Not Found
- `500` - Internal Server Error
- `501` - Not Implemented

---

## Rate Limiting

- Default: 10 requests/second
- Configure in `config/api_config.yaml`

---

## Examples

### Python
```python
import requests

API_URL = 'http://localhost:5001/api/v1'
API_KEY = 'your_api_key_here'
headers = {'X-API-Key': API_KEY}

# Start scanning
response = requests.post(f'{API_URL}/scan/start', headers=headers, json={
    'bands': ['2m', '70cm'],
    'rebuild_baseline': False
})
print(response.json())

# Get anomalies
response = requests.get(f'{API_URL}/scan/anomalies', headers=headers, params={'limit': 10})
anomalies = response.json()['anomalies']
```

### curl
```bash
# Get API key
curl http://localhost:5001/api/v1/auth/key

# Start scanning
curl -X POST http://localhost:5001/api/v1/scan/start \
  -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{"bands": ["2m"], "rebuild_baseline": false}'

# Get database stats
curl http://localhost:5001/api/v1/db/stats \
  -H "X-API-Key: your_key"
```

---

## Running the API Server

```bash
# Start API server
python api/server.py

# Custom host/port
python -c "from api.server import run_api_server; run_api_server(host='0.0.0.0', port=5001)"
```

---

## Security Notes

- **Local-only by default** - API binds to `0.0.0.0` but should be firewalled
- **API key** stored in `config/api_config.yaml` (SHA256 hash only)
- **JWT tokens** expire after 24 hours
- **No HTTPS** - add reverse proxy (nginx) for production
- **CORS enabled** for development - restrict in production

---

For issues or questions, see: https://github.com/kamakauzy/ReconRaven

