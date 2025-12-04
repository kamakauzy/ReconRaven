# ReconRaven Spec Sheet (v1.0 - Current Functionality + Proposed Enhancements)
## Overview
This document provides a comprehensive specification for building/improving ReconRaven, an open-source, backpack-portable SIGINT platform for passive RF monitoring in UHF/VHF/ISM bands. It details all existing features from the GitHub repo (as of latest check), hardware/software reqs, functional breakdowns, and proposed additions (API layer, touchscreen app) for enhanced field ops in denied environments like Pacific near-peer CT/EW. Use this in Cursor for modular development, testing with DARC sim scripts, and integration with Securit360 pentest templates.

### 1. Purpose & High-Level Requirements
- **Core Objective**: Provide a portable, receive-only tool for passive RF reconnaissance, anomaly detection, signal demodulation, voice transcription, device fingerprinting, direction finding (DF), and offline analysis. Designed for SIGINT training, EW research, pentesting (e.g., RF-linked exploits), and CT ops (e.g., drone/IED hunting in cut-off scenarios).
- **Target Use Cases**: Field pentesting with Securit360 (e.g., Burp/Python for RF-web correlations); unsupported combat (CQB/SUT with emissions control); anomaly fingerprinting via DARC Pacific sims; covert ops in denied areas.
- **Key Non-Functional Requirements**:
  - Offline Resilience: Fully self-contained post-setup; no internet during ops.
  - Portability: Backpack/handheld; low-power for 4+ hours on standard banks.
  - Security: No device emissions; harden against side-channels; receive-only compliance.
  - Scalability: Supports 1-4 SDRs; YAML-configurable for bands/protocols.
  - Legal: Public bands only (ham/ISM); no encrypted comms decryption.
  - Performance: Noise floor < -20 dBm; anomaly threshold >15 dB; DF accuracy 5-10° at >10 dB SNR; transcription >80% confidence.
  - Build Env: Python 3.x on Raspberry Pi OS; REPL-friendly for dev.

### 2. Hardware Specifications & Build Requirements
| Component          | Mobile Mode (Backpack)                  | Touchscreen Portable                     | Direction Finding Mode                  |
|--------------------|-----------------------------------------|------------------------------------------|-----------------------------------------|
| **Processor**     | Raspberry Pi 5 (8GB RAM min)           | Raspberry Pi 5 (16GB RAM min)           | Same as Touchscreen                    |
| **SDR Receivers** | 1x RTL-SDR V4 (USB, coherent-capable)  | 4x RTL-SDR V4                           | 4x RTL-SDR V4 in coherent array        |
| **Antennas**      | 1x Dual-band (e.g., Nagoya NA-771, SMA)| 4x Nagoya NA-771                        | 4x Nagoya NA-771 + V-dipole mounts on 0.5m frame |
| **Display**       | N/A                                    | Official Raspberry Pi 7" touchscreen (800x480) | Same                                   |
| **Power**         | 20,000mAh USB-C bank (5V/3A+)          | 25,000mAh+ bank                         | Same                                   |
| **Storage**       | 128GB+ microSD (A2-rated)              | 256GB+ microSD                          | Same                                   |
| **Peripherals**   | Optional USB GPS (e.g., VK-162)        | SmartiPi Touch 2 case, 4-port powered USB hub, USB GPS | Same + rigid array frame              |
| **Cooling**       | Passive                                | Active fan/heatsink                     | Same                                   |
| **Est. Cost**     | ~$220                                  | ~$620                                   | ~$650                                  |
| **Build Notes**   | Blacklist SDRs from kernel; test USB bandwidth. | Calibrate touchscreen; auto-dim backlight. | Phase-align array; mount at 1m+ height.|

- **Compatibility & Validation**: RTL-SDR V4 required; test noise floor via CLI; integrate GPS for geo-tagging. Shield from interference (e.g., disable WiFi).

### 3. Software Architecture & Build Requirements
- **Language/Stack**: Python 3.x; Flask for web; NumPy/SciPy for signals; Whisper for transcription; SQLite for DB.
- **Directory Structure**:
ReconRaven/
├── reconraven.py               # CLI entry point
├── advanced_scanner.py         # Scanning engine
├── database.py                 # SQLite interface
├── hardware/                   # SDR control/calibration
├── scanning/                   # Baseline/threshold logic
├── demodulation/               # Protocol decoders (plugins)
├── direction_finding/          # MUSIC algo/phase correction
├── web/                        # Flask dashboard (refactor to API client)
├── visualization/              # UI graphs/timelines
├── config/                     # YAMLs (bands.yaml, hardware.yaml, demod_config.yaml)
├── examples/                   # Scripts (e.g., drone_hunt.py, DARC integrations)
├── _archived_scripts/          # Legacy
├── docs/                       # Guides (RF_SETUP_GUIDE.md, API docs)
├── recordings/audio/           # .npy IQ / .wav files
├── reconraven.db               # SQLite DB
├── requirements.txt            # Deps (add kivy, flask-restful, flask-socketio)
├── api/                        # Proposed: REST endpoints
├── touch_app/                  # Proposed: Kivy touchscreen app
└── README.md                   # Updated spec
- **Dependencies**: rtl-sdr, numpy, scipy, flask, whisper-ai, etc. Proposed: kivy, flask-restful/socketio.
- **Installation/Build Flow**:
1. Clone repo; install system pkgs (rtl-sdr, python3-pip).
2. pip install -r requirements.txt; download Whisper models.
3. Validate SDR/noise/known freqs via CLI.
4. Build baseline on initial scan.
5. Proposed: Run `setup --api` for key gen; `setup --touch` for Kivy/autostart.
- **Modularity**: YAML plugins for demod/DF; API as central hub for UIs.

### 4. Detailed Functional Requirements (Current Repo Functionality)
All features offline/receive-only. Includes inputs/outputs, edges, validation.

- **Scanning & Anomaly Detection**:
- Bands: 2m/70cm/433MHz/915MHz ISM; configurable steps/priorities in YAML.
- Baseline Building: 3-pass automated build; compares live signals to baseline (>15 dB deviation flags anomaly); auto-promotes identified devices to baseline.
- Outputs: Anomalies (freq, strength, type); real-time spectrum; ignore/promote actions.
- Edges: Interference (false positives); multi-SDR bandwidth limits.
- Validation: Known transmitter tests; ensure < -20 dBm noise floor.

- **Demodulation & Decoding**:
- Protocols: FM/AM/DMR/P25/NXDN/ProVoice/Fusion (voice); OOK/ASK/FSK (binary to hex); rolling-code detection.
- Voice: Auto-detect on bands (e.g., GMRS/FRS/Marine); demod to WAV.
- Binary/ISM: Burst timing, sensor patterns, RF quirks for fingerprinting.
- Outputs: Decoded data; fingerprints (offset, bandwidth, model).
- Edges: Noisy signals (manual fallback); batch resource limits.
- Validation: DARC sims (e.g., drone links).

- **Voice Transcription & Intel Processing**:
- Auto-transcribe: Whisper models (base/small/medium/large; 99+ langs).
- Store/Search: Transcripts, confidence, keywords, lang in DB; full-text queries (band/date filters).
- Outputs: Searchable transcripts; JSON/CSV/TXT exports; timestamped playback.
- Edges: Low SNR accuracy; multi-lang mixes.
- Validation: Sample recordings; >80% confidence.

- **Direction Finding**:
- Setup: 4-SDR array with MUSIC algorithm; bearing estimation (5-10° accuracy).
- Inputs: Anomaly ID; auto from scan.
- Outputs: Degrees relative to array; GPS geo-tag.
- Edges: Multipath envs; calibration required.
- Validation: Known source tests; future Kalman for motion.

- **Correlation & Behavioral Analysis**:
- Patterns: Temporal/sequential; network graphs; behavior flags.
- Outputs: Device correlations, profiles, reports.
- Edges: Sparse data (min 30min scans).
- Validation: DARC IED/emitter sims.

- **Data Management**:
- DB: SQLite for detections, devices, transcripts, .npy recordings.
- Ops: Stats, promote, export, backups.
- Location-Aware: Auto-load freq DB (repeaters/NOAA/public records) based on IP/state/lat-lon (setup phase); optional USB GPS for real-time geo.
- Edges: DB migrations; prune old data.
- Validation: Query/export integrity.

- **Web Dashboard (Current UI)**:
- Flask local server[](http://localhost:5000).
- Tabs: Signals (anomalies/recording), Network (graphs), Voice (monitor), Transcripts (search/export), Timeline (history/zoom).
- Features: Real-time refresh; demod/DF/ignore buttons.
- Edges: Browser compat; no external JS.
- Validation: Noisy RF load tests.

- **CLI Usage**:
- Commands: reconraven.py [scan/db/analyze/test/etc.].
- Examples: Dashboard scan; voice monitor; batch transcribe; correlations.
- Edges: Hang recovery.
- Validation: Script sims.

### 5. Proposed Additions: New Features & Integration Requirements
- **REST API Layer**:
- Base: http://localhost:5000/api/v1/; JSON with API key/JWT (local-only).
- Endpoints:
  - Scanning: GET /scan/status; POST /scan/start (bands, rebuild_baseline); POST /scan/stop.
  - Demod: GET /demod/freq/{freq}; POST /decode/binary (signal_data, protocol).
  - DF: GET /df/bearing/{anomaly_id}; POST /df/calibrate (known_source).
  - DB: GET /db/transcripts (search/filters); GET /db/devices; POST /db/promote; GET /db/export (format/type).
  - Transcription: POST /transcribe/recording/{id}.
  - Websockets: /ws/updates for real-time.
- Reqs: Rate limit 10 req/s; input validation; error codes.
- Integration: Refactor web as client; Securit360 hooks.
- Build: Add to Flask; curl/Postman tests.
- Edges: Overload; offline.

- **Touchscreen Application**:
- Stack: Kivy (fullscreen on 7"); API requests; optional speechrecognition.
- Features: Mirrors web tabs (Signals/Network/Voice/Transcripts/Timeline); swipe nav; large glove-friendly buttons; dark theme; haptic alerts; API poll (5-10s).
- Autostart: Systemd service; detect screen (/dev/fb0 or xrandr); CLI fallback.
- Reqs: Offline cache; themes in YAML.
- Integration: API client; same auth.
- Build: main.py in touch_app/.
- Edges: Pi perf; gestures.
- Validation: Virtual/field sims.

- **Enhancement Roadmap**:
- Plugins: TETRA/ML fingerprinting.
- Optimizations: Power duty-cycles.
- Integrations: Securit360 exports; DARC sim imports.

### 6. Testing & Validation Requirements
- Unit/Integration: Pytest (e.g., thresholds, DF math); mock SDRs.
- Real-World: DARC Pacific sims (drone/IED).
- Edges: Multi-SDR hangs; low-battery; encrypted skips.
- Metrics: Scan speed (>1MHz/s); transcription accuracy; DF error <10°.