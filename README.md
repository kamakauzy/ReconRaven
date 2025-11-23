# ReconRaven

![Banner](rr.png)

> Because sometimes you need to know what's broadcasting in your neighborhood. Or your enemy's.

A complete SIGINT platform built on RTL-SDR for signal intelligence training, research, and field operations. Scans, records, analyzes, and identifies RF signals across multiple bands with zero internet dependency.

**Built for:** SIGINT instructors, RF enthusiasts, security researchers, and anyone who thinks "I wonder what that signal is" way too often.

## What This Thing Does

ReconRaven is a dual-mode SDR platform that works as both a mobile scanning rig and a stationary direction-finding array. It's designed to run on a Raspberry Pi 5 with 1-4 RTL-SDR V4 dongles, but also works great on a PC for development and testing.

**Core Features:**
- Multi-band scanning (2m, 70cm, 433MHz, 915MHz ISM)
- Automatic anomaly detection and recording
- Multi-protocol demodulation (FM/AM/DMR/P25/NXDN/ProVoice/Fusion)
- Signal analysis and device fingerprinting
- Binary protocol decoding (OOK/ASK/FSK)
- Rolling code detection for security analysis
- Direction finding with 4-SDR coherent array
- Real-time web dashboard
- SQLite database for all metadata
- Fully offline capable (after initial setup)

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
- Raspberry Pi 5 (4GB+ recommended)
- 1x RTL-SDR V4 
- Dual-band antenna (Nagoya NA-771 or similar)
- 20000mAh USB-C power bank
- USB GPS module (optional but recommended)
- Cost: ~$200

### Mobile Multi Mode (Faster Scanning)
- Same as mobile but with 2-4 SDRs
- Scans multiple bands in parallel
- Cost: ~$300-400

### Direction Finding Mode (Stationary)
- Everything from mobile mode
- 3 additional RTL-SDR V4 dongles (4 total)
- 4x matched antennas
- 28.8MHz clock sync kit
- Tripod or mount for array
- Cost: ~$670 all-in

**Full parts list with links in the Hardware section below.**

---

## Quick Start

### Installation

```bash
# Clone the repo
git clone https://github.com/kamakauzy/ReconRaven.git
cd ReconRaven

# Install system dependencies (Raspberry Pi/Linux)
sudo apt update
sudo apt install rtl-sdr librtlsdr-dev python3-pip

# Install Python dependencies
pip install -r requirements.txt

# On Windows, you'll also need Zadig for driver installation
# See WINDOWS_SETUP.md for details
```

### First Run Setup

**Download frequencies for your area** (one-time, then works offline forever):

```bash
# Auto-detect your location
python reconraven.py setup --auto

# Or specify manually (recommended for accuracy)
python reconraven.py setup --state AL --city Huntsville --lat 34.7304 --lon -86.5859
```

This pulls ham repeaters, public safety frequencies, and NOAA weather stations for your state. You'll need internet for this step, but after that everything runs offline.

### Basic Usage

```bash
# Start scanning with web dashboard
python reconraven.py scan --dashboard
# Dashboard: http://localhost:5000

# Quick baseline scan (no monitoring)
python reconraven.py scan --quick

# Analyze captured signals
python reconraven.py analyze --all

# View database stats
python reconraven.py db stats

# List identified devices
python reconraven.py db devices
```

### The Dashboard

Open `http://localhost:5000` in your browser to see:
- Real-time scanning status
- Baseline frequency count
- Active anomalies
- Identified devices with confidence scores
- Direction finding bearings (if in DF mode)
- GPS position

The dashboard updates in real-time as signals are detected and analyzed.

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
- Signals significantly above baseline
- Temporary - shows what's currently transmitting
- Triggers automatic recording if strong enough
- These are the "something interesting is happening" alerts

**3. Identified Devices**
- Analyzed signals matched to known protocols/devices
- Persistent across sessions
- Includes manufacturer, device type, confidence score
- Your growing RF signature database

**Typical workflow:**
```
Initial scan → Build baseline → Monitor → Detect anomaly → Auto-record → 
Analyze recording → Identify device → (optional) Promote to baseline
```

**Pro tip:** After you've identified all the devices in your area, use the "Promote to Baseline" button in the dashboard. This marks them as expected, so future scans only flag new/unknown signals.

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

### Recommended Build (Full Capability)

| Part | Qty | Price | Notes |
|------|-----|-------|-------|
| Raspberry Pi 5 (4GB) with case & cooler | 1 | $85 | iRasptek kit recommended |
| RTL-SDR Blog V4 | 4 | $39 ea | $156 total for 4 |
| Nagoya NA-771 antenna | 4 | $21 ea | $84 total, get authentic |
| Anker 7-port USB 3.0 hub (powered) | 1 | $40 | Prevents power issues |
| GPS Module (NEO-6M) | 1 | $11 | For geo-tagging |
| SanDisk 64GB microSD | 1 | $15 | Fast card recommended |
| Anker PowerCore 20000 PD | 1 | $45 | 8+ hour runtime |
| 28.8MHz clock sync kit | 1 | $25 | For DF mode (optional) |
| **Total** | | **~$670** | Full DF-capable system |

### Budget Build (Mobile Only)

| Part | Qty | Price |
|------|-----|-------|
| Raspberry Pi 5 kit | 1 | $85 |
| RTL-SDR Blog V4 | 1 | $39 |
| Nagoya NA-771 | 1 | $21 |
| USB hub | 1 | $20 |
| GPS module | 1 | $11 |
| MicroSD card | 1 | $15 |
| Power bank | 1 | $30 |
| **Total** | | **~$220** |

### Assembly Notes

- **Mobile build:** 30 minutes. Plug stuff in, install software, done.
- **DF array:** Add 1 hour for clock sync soldering and array mounting.
- **Clock sync:** Requires basic soldering. Tutorials available online (KerberosSDR method works).
- **Array geometry:** 0.5m spacing in circular or linear array. Calibrate with known source.

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
python reconraven.py scan --dashboard
```
- Let it build baseline (first run, ~10 minutes)
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
├── reconraven.py          # Unified CLI (use this)
├── advanced_scanner.py    # Core scanning engine
├── database.py            # SQLite interface
├── hardware/              # SDR control
├── scanning/              # Spectrum & anomaly detection
├── demodulation/          # Protocol decoders
├── direction_finding/     # DF algorithms
├── web/                   # Flask dashboard
├── visualization/         # Dashboard UI
├── config/                # YAML configs
├── examples/              # Usage examples
└── _archived_scripts/     # Old single-purpose scripts
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
