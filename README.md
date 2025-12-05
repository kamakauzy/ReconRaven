# ReconRaven

![Banner](reconraven/visualization/static/img/rr.png)

## ⚠️ **ALPHA SOFTWARE - UNDER ACTIVE DEVELOPMENT** ⚠️

**THIS PROJECT IS IN EARLY DEVELOPMENT AND NOT FULLY TESTED!**

- **Expect bugs, crashes, and incomplete features**
- **RF environment setup is CRITICAL** - See `docs/RF_SETUP_GUIDE.md`
- **Not recommended for production use yet**
- **API and command structure may change without notice**
- **Use at your own risk!**

**Known Issues:**
- Scanner may hang during initialization (kill with `pkill -9 python; pkill -9 rtl`)
- RF interference causes false positives or missed detections
- Direction finding requires careful calibration (not fully implemented)
- Voice transcription is resource-intensive
- Database migrations may require manual intervention

**Testing Status:** Hardware detection and basic scanning work. Multi-SDR concurrent scanning works but needs proper RF environment. Advanced features (DF, voice transcription, correlation analysis) are experimental.

---

> Because sometimes you need to know what's broadcasting in your neighborhood. Or your enemy's.

A SIGINT platform built on RTL-SDR for signal intelligence training, research, and field operations. Scans, records, analyzes, and identifies RF signals across multiple bands with zero internet dependency.

**Built for:** SIGINT instructors, RF enthusiasts, security researchers, and anyone who thinks "I wonder what that signal is" way too often.

## What This Thing Does

ReconRaven is a dual-mode SDR platform that works as both a mobile scanning rig and a stationary direction-finding array. It's designed to run on a Raspberry Pi 5 with 1-4 RTL-SDR V4 dongles, but also works great on a PC for development and testing.

**Core Features:**
- Multi-band scanning (2m, 70cm, 433MHz, 915MHz ISM)
- Automatic anomaly detection and recording
- Multi-protocol demodulation (FM/AM/DMR/P25/NXDN/ProVoice/Fusion)
- **REST API with WebSocket support** - Remote control and monitoring
- **Kivy touchscreen UI** - Optimized for 7" displays (800x480)
- **Location-aware frequency database** - Auto-identify repeaters/NOAA by GPS
- **Voice signal auto-detection and transcription (Whisper AI)**
- **Automatic speech-to-text for all voice transmissions**
- **Full-text search across all transcripts**
- **Export transcripts in JSON/CSV/TXT formats**
- Signal analysis and device fingerprinting
- Binary protocol decoding (OOK/ASK/FSK)
- Rolling code detection for security analysis
- Direction finding with 4-SDR coherent array
- Real-time web dashboard with tabbed interface
- SQLite database for all metadata and transcripts
- Fully offline capable (after initial setup)
  - **All JavaScript libraries bundled locally (no CDN dependencies)**
  - **Dashboard works without internet connection**
  - **Whisper AI models downloaded once, run locally**
  - Perfect for field operations and secure environments

**What it's good at:**
- Finding that mystery signal that's been driving you crazy
- Identifying remote controls, sensors, and ISM devices
- Building RF baselines for environments
- Training scenarios for SIGINT operations
- Direction finding for signal hunting

**What it's terrible at:**
- Making coffee
- Decrypting anything (that's your job)
- Working through walls thicker than your excuses

---

## Hardware Requirements

You'll need one of these configurations:

### Mobile Mode (Backpack Recon)
- Raspberry Pi 5 (8GB+ recommended, 16GB for touchscreen UI)
- 1x RTL-SDR V4 
- Dual-band antenna (Nagoya NA-771 or similar)
- 20000mAh USB-C power bank
- USB GPS module (optional but recommended)
- Cost: ~$220

### Touchscreen Portable System
- Raspberry Pi 5 (16GB required for GUI + 4 SDRs)
- Official 7" touchscreen display (800x480)
- SmartiPi Touch 2 case (integrates Pi + display)
- 4x RTL-SDR V4 dongles
- 4x Nagoya NA-771 antennas
- RSHTECH 4-port powered USB hub
- VK-162 USB GPS dongle
- 256GB microSD (A2 speed class)
- High-capacity power bank (25,000mAh+)
- Cost: ~$620

### Direction Finding Mode (Stationary)
- Touchscreen portable system (above)
- V-dipole antenna mounts (3D printed)
- 0.5m square array frame
- DF calibration (MUSIC algorithm built-in)
- Cost: ~$650 (with 3D printed antennas)

**Full parts list with links in the Hardware section below.**

---

## Quick Start

**IMPORTANT Documentation:**
- **Raspberry Pi Deployment:** `docs/RASPBERRY_PI_DEPLOYMENT.md` - **START HERE FOR PI BUILDS!**
- **RF Environment Setup:** `docs/RF_SETUP_GUIDE.md` - Critical for all deployments
- **Direction Finding:** `docs/DF_SETUP_GUIDE.md` - For 4-SDR DF array

### PC/Laptop Installation (Development/Testing)

```bash
# Clone the repo
git clone https://github.com/kamakauzy/ReconRaven.git
cd ReconRaven

# Install system dependencies (Raspberry Pi/Linux)
sudo apt update
sudo apt install rtl-sdr librtlsdr-dev python3-pip

# Install Python dependencies
pip3 install -r requirements.txt

# Test your SDRs and RF environment
python3 reconraven.py test sdr      # Detect SDRs
python3 reconraven.py test noise    # Check noise floor
python3 reconraven.py test freq --freq 146.52 --duration 60  # Monitor frequency

# If tests pass, run the scanner
python3 reconraven.py scan --dashboard

# On Windows, you'll also need Zadig to install WinUSB drivers for RTL-SDR
# Download from: https://zadig.akeo.ie/
# Plug in SDR, run Zadig, select "Bulk-In Interface", install WinUSB driver
```

### First Run Setup

**CRITICAL: Validate RF Environment First!**

```bash
# 1. Test SDR detection (should show 1-4 SDRs)
python3 reconraven.py test sdr

# 2. Check noise floor (MUST be < -20 dBm on all bands)
python3 reconraven.py test noise

# 3. Test reception with a known transmitter
#    (have someone transmit on 146.52 MHz while test runs)
python3 reconraven.py test freq --freq 146.52 --duration 60

# Expected: Baseline < -20 dBm, transmission shows +20-30 dB increase
```

**If noise > -10 dBm:** RF interference detected! See `docs/RF_SETUP_GUIDE.md` for solutions.

**Once tests pass:**

```bash
# Start scanning with dashboard
python3 reconraven.py scan --dashboard --rebuild-baseline

# Dashboard: http://localhost:5000
```

**Optional - Download frequencies for your area** (one-time, requires internet):

```bash
# Auto-detect location
python3 reconraven.py setup --auto

# Or specify manually
python3 reconraven.py setup --state AL --city Huntsville
```

This pulls ham repeaters and public safety frequencies. After this, everything runs offline.

### Basic Usage

```bash
# Start scanning with web dashboard
python reconraven.py scan --dashboard
# Dashboard: http://localhost:5000

# Voice monitoring
python voice_monitor.py --freq 146.52 --mode FM --record
python voice_monitor.py --scan 2m

# Signal correlation analysis
python correlation_engine.py --correlations
python correlation_engine.py --network

# Analyze captured signals
python reconraven.py analyze --all

# View database stats
python reconraven.py db stats

# List identified devices
python reconraven.py db devices
```

### The Dashboard

Open `http://localhost:5000` in your browser to access:

**Tab 1: 🔍 Signals** (Smart Signal Monitoring)
- Real-time scanning status
- **Smart Anomalies** - Only unidentified signals (known devices auto-promoted)
- Identified devices with confidence scores and baseline status
- "Ignore Forever" button for unwanted signals
- Recording status tracking

**Tab 2: 🕸️ Network** (Intelligence Analysis)
- Visual network graph showing device relationships
- Temporal correlations (devices that transmit together)
- Sequential patterns (A→B→C sequences)
- Behavioral anomalies
- Device behavioral profiles

**Tab 3: 📡 Voice** (Voice Monitoring)
- Live voice monitoring controls
- FM/AM/SSB/USB/LSB demodulation
- Quick band scans (2m, 70cm, GMRS, FRS, Marine VHF)
- Auto-recording with playback
- Voice recordings archive

**Tab 4: 💬 Transcripts** (Voice Intelligence)
- **Automatic transcription of all voice signals using Whisper AI**
- Full-text search across all transcripts
- Filter by language (EN/ES/ZH/RU/etc)
- Filter by frequency band (2m, 70cm, etc)
- Confidence scores and timestamps
- Export to JSON/CSV/TXT for reports
- Audio playback linked to transcripts
- Keyword highlighting and frequency analysis

**Tab 5: 📊 Timeline** (Activity History)
- Activity timeline visualization
- Time range selection (1h, 6h, 24h, 7d)
- Event history and patterns

**Dashboard Features:**
- Auto-promotes identified devices to baseline (no manual intervention)
- Only shows TRUE unknowns as anomalies
- Auto-refresh every 10 seconds
- Direction finding bearings (if in DF mode with 4 SDRs)
- GPS position tracking

---

## REST API & Remote Control

ReconRaven includes a full REST API for remote control and integration.

**Start the API server:**

```bash
cd api
python3 server.py
# API: http://localhost:5001/api/v1/
# WebSocket: ws://localhost:5001/api/v1/ws
```

**Quick API test:**

```bash
# Get API key
curl http://localhost:5001/api/v1/auth/key

# Health check
curl http://localhost:5001/api/v1/health

# Get scan status (requires API key)
curl -H "X-API-Key: YOUR_KEY" http://localhost:5001/api/v1/scan/status

# Start scanning
curl -X POST -H "X-API-Key: YOUR_KEY" \
     -H "Content-Type: application/json" \
     -d '{"bands": ["2m", "70cm"]}' \
     http://localhost:5001/api/v1/scan/start
```

**Available endpoints:**

- `/api/v1/scan/*` - Scanning control (start, stop, status, anomalies)
- `/api/v1/demod/*` - Demodulation and decoding
- `/api/v1/df/*` - Direction finding
- `/api/v1/db/*` - Database queries (transcripts, devices, export)
- `/api/v1/transcribe/*` - Transcription control
- `/api/v1/ws` - WebSocket for real-time updates

**Full API documentation:** `api/API_DOCUMENTATION.md`

**Touchscreen UI:** For Pi deployments with 7" display, use the Kivy touch app:

```bash
python3 touch_app/main.py
# Optimized for 800x480 touchscreens
# Auto-starts on Pi with systemd
```

---

## How It Works

### Data Model (Understanding What You're Looking At)

ReconRaven tracks three types of data:

**1. Baseline Frequencies**
- What's "normal" in your RF environment
- Built during initial 3-pass scan
- Used as reference to detect anomalies
- Examples: local ham repeaters, NOAA, your garage door opener

**2. Anomalies / Active Signals**
- **Smart filtering:** Only shows UNIDENTIFIED signals
- Signals significantly above baseline
- Triggers automatic recording if strong enough
- Known devices automatically filtered out

**3. Identified Devices**
- Analyzed signals matched to known protocols/devices
- **Auto-promoted to baseline** (no manual work needed)
- Includes manufacturer, device type, confidence score
- Shows baseline status with badge
- Your growing RF signature database

**Typical workflow:**
```
Initial scan → Build baseline → Monitor → Detect anomaly → Auto-record → 
Analyze recording → Identify device → AUTO-PROMOTE to baseline
```

**How it works now:** The system automatically promotes identified devices to baseline on every dashboard refresh. You'll only see truly unknown signals as anomalies. Use the "Ignore Forever" button for known but unwanted signals (car alarms, neighbor's garage door, etc.).

### Storage

Everything lives in `reconraven.db` (SQLite):
- Baseline frequencies
- Signal detections
- Device identifications  
- Recording metadata
- Analysis results

IQ recordings go in `recordings/audio/` as `.npy` files (raw NumPy arrays). Each 10-second capture is ~366MB. The database just stores metadata - frequency, timestamp, power level, etc.

To keep disk usage sane, the system can auto-cleanup recordings after analysis (implement this yourself or wait for the next update, we're lazy).

### Operating Modes

**Mobile Mode (1 SDR)**
- Sequential scanning across all bands
- Good for recon on foot or in vehicles
- ~8 hour battery life

**Mobile Multi Mode (2-4 SDRs)**
- Parallel scanning of different bands
- Much faster coverage
- Still portable

**Direction Finding Mode (4 SDRs)**
- Phase-coherent array for bearing calculation
- MUSIC algorithm for 5-10° accuracy
- Stationary operation (needs stable mount)
- Auto-switches from scanning on signal detection

The system auto-detects which mode to use based on how many SDRs you plug in. No configuration needed.

---

## Analysis Tools

ReconRaven includes multiple layers of analysis:

### Layer 1: Voice Transcription & SIGINT

**Automatic speech-to-text transcription for SIGINT collection:**

The system automatically detects voice signals on known voice bands (2m, 70cm, GMRS, FRS, Marine VHF, Aviation) and transcribes them using OpenAI's Whisper AI. No cloud connection needed - runs 100% locally.

```bash
# Manual transcription of a single recording
python voice_transcriber.py --file recordings/audio/voice_146.520.wav

# Batch transcribe all recordings in a folder
python voice_transcriber.py --batch recordings/audio/ --output transcripts.json

# Batch transcribe all untranscribed recordings in database
python batch_transcribe.py

# Use different Whisper model sizes
python voice_transcriber.py --file recording.wav --model base    # Default (fastest)
python voice_transcriber.py --file recording.wav --model small   # More accurate
python voice_transcriber.py --file recording.wav --model medium  # Best accuracy
```

**Transcript Search & Analysis:**

```bash
# Search database for keywords (via dashboard Transcripts tab)
# - Full-text search across all transcripts
# - Filter by language, frequency band, date
# - Export to JSON/CSV/TXT for reports
# - Keyword frequency analysis
```

**How it works:**
1. System detects voice signal (FM/AM on voice bands)
2. Records and demodulates to WAV audio
3. Automatically transcribes using Whisper (base model by default)
4. Saves transcript to database with metadata
5. Extracts keywords for searchability
6. Appears in dashboard Transcripts tab

**Supported languages:** Whisper auto-detects 99+ languages including English, Spanish, Chinese, Russian, Arabic, French, German, Japanese, etc.

**Privacy note:** All processing happens locally on your machine. No data is sent to the cloud.

### Layer 2: Signal Correlation & Behavioral Analysis

**NEW!** Pattern recognition and intelligence gathering without decryption:

```bash
# Find temporal correlations (signals that occur together)
python correlation_engine.py --correlations

# Detect sequential patterns (A→B→C sequences)
python correlation_engine.py --sequences

# Get behavioral profile for a specific device
python correlation_engine.py --profile 434.5

# Build network map of device relationships
python correlation_engine.py --network

# Detect behavioral anomalies
python correlation_engine.py --anomalies
```

**What it detects:**
- Command/response relationships ("signal A always triggers signal B")
- Synchronized transmissions (mesh networks, coordinated devices)
- Periodic reporting (sensors with regular check-ins)
- Hub devices (command centers with many connections)
- Behavioral changes (new devices, unusual activity patterns)

**Use cases:**
- Map sensor networks without knowing protocols
- Identify command/control relationships
- Predict device behavior
- Auto-prioritize threats

### Layer 2: Voice Traffic Monitoring

**NEW!** Listen to and record voice communications:

```bash
# Monitor a specific frequency
python voice_monitor.py --freq 146.52 --mode FM --record

# Scan a voice band looking for activity
python voice_monitor.py --scan 2m --dwell 5

# Monitor ham repeater
python voice_monitor.py --freq 146.94 --mode FM --duration 300

# Monitor GMRS channels
python voice_monitor.py --scan gmrs --dwell 10
```

**Supported modes:**
- FM (narrow band - ham, public safety, GMRS/FRS)
- WFM (wide band - broadcast FM)
- AM (aviation, AM broadcast)
- USB/LSB (SSB - ham HF)

**Features:**
- Auto-recording on voice activity
- Band scanning (2m, 70cm, GMRS, FRS, Marine VHF)
- Multiple frequency monitoring
- WAV file output for later review

### Layer 3: ISM & Binary Analysis

When ReconRaven records a signal, you can throw it through multiple analyzers:

### ISM Analyzer (`ism_analyzer.py`)
Specialized for 433/915 MHz ISM bands. Detects:
- Burst patterns (door remotes, car keys)
- Sensor transmission timing
- Device type classification

### Binary Decoder (`decode_remote.py`)
Extracts the actual bits from OOK/ASK/FSK signals:
- Demodulates to binary stream
- Finds preambles (10101010, 11110000, etc.)
- Converts to hex for analysis
- Detects rolling codes

### Protocol Analyzer (`urh_analyze.py`)
Uses Universal Radio Hacker's libraries to:
- Auto-detect modulation type
- Extract symbol rates
- Find protocol structures
- Compare against known protocol database

### Device Fingerprinter (`fingerprint_signal.py`)
Deep RF characteristics analysis:
- Carrier frequency offset
- Bandwidth and deviation measurements
- Modulation depth analysis
- Brand/model identification from RF quirks

### Field Analyzer (`field_analyzer.py`)
Master tool that combines everything:
- RF analysis → Signature matching → Binary decoding → rtl_433 protocol decode
- Multi-level confidence scoring
- Fully offline capable
- Generates comprehensive reports

### Using the Analyzers

```bash
# Run all analysis tools on a recording
python reconraven.py analyze --file recordings/audio/capture_915MHz.npy

# Specific analysis type
python reconraven.py analyze --file capture.npy --type ism
python reconraven.py analyze --file capture.npy --type remote
python reconraven.py analyze --file capture.npy --type protocol

# Batch analyze everything
python reconraven.py analyze --all
```

Or use the individual scripts directly for more control:

```bash
python ism_analyzer.py recording.npy
python decode_remote.py recording.npy
python fingerprint_signal.py recording.npy
```

---

## Database Management

### Quick Stats

```bash
python reconraven.py db stats
```

Shows:
- Baseline frequency count
- Total signals detected
- Anomaly count
- Identified devices
- Storage usage

### Viewing Data

```bash
# List identified devices
python reconraven.py db devices

# Show recent anomalies
python reconraven.py db anomalies --limit 50

# Direct SQLite queries
sqlite3 reconraven.db "SELECT * FROM devices WHERE confidence > 0.8"
```

### Promoting Devices to Baseline

After you've identified all the RF sources in your area, promote them to baseline so future scans only alert on new signals:

```bash
python reconraven.py db promote
```

Or use the button in the web dashboard.

### Backup and Export

```bash
# Backup database
cp reconraven.db reconraven_backup_$(date +%Y%m%d).db

# Export to JSON
python reconraven.py db export --output backup.json

# Import recordings from disk
python reconraven.py db import
```

---

## Hardware Details

### Recommended Build (Portable Touchscreen SIGINT Platform)

| Part | Qty | Price | Notes |
|------|-----|-------|-------|
| Raspberry Pi 5 (16GB) | 1 | $132 | 16GB for GUI + 4 SDRs |
| Official 7" Touchscreen | 1 | $83 | 800x480 capacitive touch |
| SmartiPi Touch 2 Case | 1 | $43 | Integrates Pi + display |
| CanaKit 45W USB-C PSU | 1 | $16 | Powers Pi + display |
| RTL-SDR Blog V4 | 4 | $40 ea | $160 total for 4 SDRs |
| Nagoya NA-771 antenna | 4 | $21 ea | $84 total, dual-band |
| RSHTECH 4-Port Powered Hub | 1 | $18 | 5V/4A for SDRs |
| USB to Barrel Cable (2pk) | 1 | $5 | Hub battery power |
| VK-162 USB GPS Dongle | 1 | $25 | Geo-tagging + timing |
| 256GB microSD (A2) | 1 | $25 | OS + recordings |
| Power bank (20K+ mAh) | 1 | $30 | 2-4hr field runtime |
| **Total** | | **~$621** | Complete portable system |

### Budget Build (Mobile Single-SDR)

| Part | Qty | Price |
|------|-----|-------|
| Raspberry Pi 5 (8GB) | 1 | $80 |
| RTL-SDR Blog V4 | 1 | $40 |
| Nagoya NA-771 | 1 | $21 |
| USB GPS dongle | 1 | $25 |
| MicroSD card | 1 | $25 |
| Power bank | 1 | $30 |
| **Total** | | **~$221** |

### Assembly Notes

- **Mobile build:** 30 minutes. Plug stuff in, install software, done.
- **Touchscreen portable:** 2 hours assembly + software setup. Integrated case with Pi 5, display, GPS, and 4 SDRs.
- **DF array:** Add 1 hour for antenna mounting and calibration. No clock sync needed (software phase correction).
- **Array geometry:** 0.5m spacing recommended. 3D print V-dipole mounts or use omnidirectional antennas.
- **GPS:** USB GPS dongle plugs into Pi's native USB port (not hub). Works with SmartiPi case.

---

## Configuration

All configs are in `config/`:

### `bands.yaml`
Frequency band definitions and scan assignments:
```yaml
bands:
  2m:
    name: "2 Meter Ham Band"
    start_hz: 144000000
    end_hz: 148000000
    step_hz: 25000
    priority: medium
```

### `hardware.yaml`
SDR calibration and thresholds:
```yaml
sdr:
  sample_rate: 2400000
  gain: auto
  ppm_error: 0

anomaly_detection:
  threshold_db: 15  # How much above baseline = anomaly
  min_duration_ms: 100
```

### `demod_config.yaml`
Protocol-specific demodulation settings:
```yaml
protocols:
  FM:
    mode: "fm"
    deviation: 5000
    squelch: -40
```

Tweak these based on your RF environment and hardware quirks.

---

## Location-Aware Frequency Database

ReconRaven includes a slick feature: it knows where you are (if you tell it) and only flags frequencies relevant to your location.

### How It Works

During setup, you download frequency data for your state:
- Ham repeaters with GPS coordinates and range
- Public safety (police/fire/EMS)
- NOAA weather stations
- Marine channels (if coastal)

When scanning, ReconRaven checks: "Am I near a registered repeater on this frequency?" If yes, it auto-identifies it. If no, it flags as unknown.

### Setting Up Location

```bash
# Option 1: Auto-detect (uses IP geolocation)
python reconraven.py setup --auto

# Option 2: Specify state (gets all statewide frequencies)
python reconraven.py setup --state CA

# Option 3: Exact location (best for accurate repeater matching)
python reconraven.py setup --state AL --city Huntsville --lat 34.7304 --lon -86.5859
```

### Data Sources

- Ham repeaters: RepeaterBook API
- Public safety: RadioReference data
- NOAA: NWS station database
- All cached locally for offline use

Run setup once, works forever offline. Re-run if you move or want to update the database.

---

## Field Operations Guide

### Pre-Deployment Checklist

- [ ] Location setup complete (`reconraven.py setup`)
- [ ] Hardware connected and powered
- [ ] Antennas attached (check for proper connections)
- [ ] GPS has fix (if using GPS)
- [ ] Initial baseline scan complete
- [ ] Dashboard accessible from your device

### Typical Workflow

**1. Initial Recon**
```bash
python advanced_scanner.py
```
- Let it build baseline (first run, ~10 minutes)
- Dashboard auto-starts at http://localhost:5000
- Check dashboard for identified devices
- Note any unexpected signals

**2. Active Monitoring**
- Scanner auto-records anomalies (>15dB above baseline)
- Watch dashboard for real-time alerts
- Recordings saved to `recordings/audio/`

**3. Post-Mission Analysis**
```bash
# Analyze all captures
python reconraven.py analyze --all

# Review identified devices
python reconraven.py db devices

# Check for rolling codes or encrypted signals
python decode_remote.py recordings/audio/suspicious_915MHz.npy
```

**4. Update Baseline**
```bash
# After identifying friendly signals, promote to baseline
python reconraven.py db promote
```

### Power Management

- Mobile mode (1 SDR): 8+ hours on 20000mAh
- Mobile multi (4 SDRs): 5-6 hours
- DF mode (4 SDRs active): 4-5 hours
- Tip: Throttle scan rate in `hardware.yaml` to extend battery

### Troubleshooting in the Field

**Scanner won't start:**
- Check SDR connection: `rtl_test`
- Verify permissions (Linux): `sudo usermod -a -G plugdev $USER`
- Kill lingering processes: `python kill_dashboard.py`

**No signals detected:**
- Check antenna connections
- Verify gain setting (try `manual` in hardware.yaml)
- Run quick scan on known frequency (146.52 MHz - 2m simplex)

**Dashboard not updating:**
- Check Flask is running: `netstat -an | grep 5000`
- Try different browser
- Clear browser cache

**High disk usage:**
- IQ files are 366MB per 10 seconds
- Delete old recordings: `rm recordings/audio/*.npy`
- Or implement auto-cleanup (TODO for next version)

---

## Advanced Features

### Direction Finding

With 4 SDRs in a coherent array, ReconRaven can calculate signal bearings.

**Setup:**
1. Mount 4 SDRs in circular or linear array
2. Install clock sync hardware (28.8MHz distribution)
3. Calibrate array geometry in `hardware.yaml`
4. Use known transmitter for calibration

**Usage:**
- System auto-switches to DF mode on strong signal detection
- MUSIC algorithm calculates bearing
- Accuracy: 5-10° typical (depends on SNR and calibration)
- Results shown in dashboard with compass visualization

**Limitations:**
- Requires stable mount (no DF while mobile)
- Accuracy degrades below ~10dB SNR
- Multipath can cause errors (use open areas)

### Drone Detection

ReconRaven can detect drone control signals (UHF control links):

```bash
# Monitor drone bands specifically
python examples/drone_hunt.py
```

Looks for:
- Burst patterns typical of telemetry
- Frequency hopping
- Known DJI/other manufacturer patterns

**Note:** RTL-SDR is limited to UHF. Won't catch 2.4/5.8GHz video links. Consider adding a second SDR with upconverter for those bands.

### Multi-Protocol Demodulation

Supports analog and digital voice:
- Analog: FM, AM, SSB
- Digital: DMR, P25, NXDN, ProVoice, Fusion

Requires `dsd` (Digital Speech Decoder) installed:
```bash
sudo apt install dsd
```

Demodulation happens automatically when strong voice signals are detected.

---

## Development & Contributing

### Project Structure

```
ReconRaven/
├── reconraven.py              # Unified CLI
├── reconraven/                # Main package
│   ├── core/                  # Scanner, database, config
│   ├── hardware/              # SDR control
│   ├── scanning/              # Spectrum & anomaly detection
│   ├── demodulation/          # Protocol decoders
│   ├── direction_finding/     # DF algorithms
│   ├── voice/                 # Voice detection & transcription
│   ├── analysis/              # Signal analysis tools
│   ├── recording/             # Recording management
│   ├── location/              # Location-aware frequency DB
│   ├── visualization/         # Web dashboard
│   ├── web/                   # Flask server
│   └── utils/                 # Utilities
├── api/                       # REST API server
│   ├── server.py              # Main API server
│   ├── auth.py                # Authentication
│   └── v1/                    # API v1 endpoints
├── touch_app/                 # Kivy touchscreen UI
│   ├── main.py                # Touch app entry
│   ├── api_client.py          # API client
│   └── screens/               # UI screens
├── scripts/                   # Deployment & automation
├── config/                    # YAML configurations
├── docs/                      # Documentation
├── systemd/                   # Service files
└── tests/                     # Test suite
```

### Testing Without Hardware

```bash
# Use simulation mode
python app.py --simulate

# Or test individual components
python test_simulation.py
```

### Contributing

Pull requests welcome. Areas that need work:
- Better protocol decoders (especially proprietary stuff)
- Improved DF algorithms
- Auto-cleanup for recordings
- Better device signature database
- Windows driver installation automation
- Android app for dashboard (someone please)

Code style: We're not picky. Make it work, make it readable, add comments for weird stuff.

---

## Known Issues & Limitations

### Hardware Limitations

- RTL-SDR V4 range: 24 MHz - 1766 MHz (no HF, no 2.4/5.8 GHz)
- Sample rate limited to 2.4 Msps (affects wide signals)
- 8-bit ADC (dynamic range limitations)
- No transmit capability (receive-only)

### Software Quirks

- Windows driver setup is annoying (Zadig required)
- Some protocols poorly documented (we do our best)
- DF mode needs manual calibration
- Dashboard can lag with 1000+ signals (we'll optimize eventually)

### Legal Stuff

**Important:** ReconRaven is a receive-only platform. It cannot and will not transmit.

**Legal to use:** Receiving public RF signals (ham, public safety, ISM, etc.)

**NOT legal:** 
- Decrypting encrypted communications
- Intercepting private communications with intent to use/disclose
- Using this to violate privacy laws in your jurisdiction

**Your responsibility:** Know your local laws. This tool is for education, research, and authorized operations only. If you're not sure if something is legal, it probably isn't.

We built this for SIGINT training. Use it responsibly.

---

## Credits & Thanks

Built by instructors for instructors. 

Inspired by:
- KerberosSDR (DF techniques)
- Universal Radio Hacker (protocol analysis)
- rtl_433 (ISM decoding)
- The entire RTL-SDR community

If this helps your training program, drop us a note. If you find bugs, open an issue. If you want to contribute, send a PR.

---

## License

MIT License - See LICENSE file

TL;DR: Do whatever you want with it. Build on it, break it, sell it, whatever. Just don't blame us when things go sideways.

---

## Support

**Documentation:** You're reading it.

**Issues:** GitHub issues tab

**Questions:** Open a discussion on GitHub

**Security issues:** Email us (see profile)

**"It doesn't work":** That's not a question. Check the troubleshooting section first.

---

Built with spite for expensive SIGINT gear and love for the RTL-SDR community.

Now go find some signals.
