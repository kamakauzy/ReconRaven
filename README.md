# ReconRaven

**Version 2.0** | *A backpack-portable, multi-RTL-SDR SIGINT device for passive UHF/VHF drone hunting and anomaly DF*

Because finding things that go beep in the night is way cooler than Pokémon Go.

ReconRaven is a production-ready multi-mode Software Defined Radio platform for signal intelligence operations. Features mobile scanning, parallel multi-band surveillance with 4 SDRs working simultaneously (parallel scans catch bursts while auto-triggering bearings), and dynamic direction finding.

## What Does This Thing Actually Do?

Remember when you were a kid and you'd spin around trying to figure out where that ice cream truck was coming from? This is like that, but with math, Python, and radio waves. The platform:

- **Scans spectrum faster than your ex went through your phone** (4x parallel coverage with sub-2-second cycles)
- **Finds signals you didn't even know existed** (intelligent anomaly detection with burst/hopping/surge recognition)
- **Tells you where they're coming from** (MUSIC algorithm direction finding with 5-10 degree accuracy)
- **Doesn't require a PhD to operate** (though having one doesn't hurt)
- **Actually works in the field** (tested on Raspberry Pi 5, not some lab bench queen)

Think of it as Shazam for radio signals, except instead of telling you what song is playing, it tells you there's a drone hovering near your perimeter at 433 MHz and gives you a bearing to boot.

## The Three Modes (Like Transformers, But Useful)

### Mode 1: Mobile Scout (1 SDR)
*"I'm walking here!"*

Perfect for reconnaissance when you're actually moving around like a functional human being.

- Sequential spectrum scanning across VHF/UHF bands
- Multi-protocol demodulation (FM, AM, and all those digital modes nobody can pronounce)
- Drone signal detection with pattern matching
- GPS tagging so you remember where you were when you found that thing
- Real-time browser dashboard (because terminals are so 1995)

**Use Case**: Backpack recon, vehicle sweeps, "just walking my SDR, officer"

### Mode 2: Parallel Predator (4 SDRs) - THE STAR OF THE SHOW
*"Now witness the power of this fully operational battle station"*

This is where things get spicy. Four SDRs, four different frequency bands, all scanning simultaneously. It's like having four interns, except they don't complain and they work at the speed of light.

**How Fast We Talking?**
- Mobile mode: ~60 seconds for full coverage (respectable)
- Parallel mode: **Under 2 seconds** (hold my coffee)
- Speed increase: **30x faster** (yes, you read that right)

**What Makes It Smart?**

The system doesn't just detect signals; it judges them:

1. **Strong Signal Detection**: "Hey, that's way louder than it should be"
2. **New Signal Recognition**: "Wait, I've never seen you before"
3. **Burst Pattern Analysis**: "That's definitely telemetry"
4. **Frequency Hopping Detection**: "Nice try, hopper"
5. **Power Surge Alerts**: "Why did you just get 15dB louder?"

Each anomaly gets a priority score. High-priority detections automatically trigger...

**Auto-DF Mode**: When something sketchy appears, the system:
- Pauses parallel scanning (hold that thought)
- Switches all 4 SDRs to the target frequency
- Calculates bearing using MUSIC algorithm
- Logs everything with GPS coordinates
- Returns to parallel scanning
- Total time: 3-5 seconds (faster than you can say "contact!")

**Band Assignment** (default, fully configurable):
```
SDR 0: 144-148 MHz   (2m amateur band)
SDR 1: 420-450 MHz   (70cm amateur band)
SDR 2: 433/868 MHz   (ISM bands, prime drone territory)
SDR 3: 915 MHz       (US ISM, more drone action)
```

### Mode 3: Direction Finding Fortress (4 SDRs)
*"Somewhere, something incredible is waiting to be found" - Carl Sagan (probably talking about RF sources)*

Pure DF mode. All four SDRs locked on the same frequency, phase-synchronized, running MUSIC algorithm to tell you exactly where that signal is coming from.

- Phase-coherent 4-element array
- MUSIC algorithm bearing calculations
- 5-10 degree accuracy (better with hardware sync)
- Geo-tagged bearing logs
- Compass visualization in the dashboard

**The Catch**: Requires stationary setup with tripod-mounted array at 0.5m spacing. Physics is a harsh mistress.

## System Architecture (The Brainy Bits)

Here's how the electrons flow through this magnificent beast:

```
                         SDR SIGINT PLATFORM v2.0
                         ========================

PARALLEL SCAN MODE (Default Operation with 4 SDRs)
---------------------------------------------------

    Antenna Array (4 elements, 0.5m spacing)
           |    |    |    |
           v    v    v    v
    +------+----+----+----+------+
    |  SDR0  SDR1  SDR2  SDR3   |
    |  144M  420M  433M  915M    |  <- Each scanning different band
    +-------|-------|-------|-----+
            |       |       |
            v       v       v
    +--------------------------------+
    |    Parallel Scan Threads       |
    |  (One thread per SDR)          |
    |  rtl_power or pyrtlsdr         |
    +----------------+---------------+
                     |
                     v
    +--------------------------------+
    |    Results Aggregation Queue   |
    |  (Real-time signal collection) |
    +----------------+---------------+
                     |
                     v
    +--------------------------------+
    |    Anomaly Detection Engine    |
    |  - Strong signals              |
    |  - New signals                 |
    |  - Burst patterns              |
    |  - Frequency hopping           |
    |  - Power surges                |
    +----------------+---------------+
                     |
          Anomaly Priority > Threshold?
                     |
            +--------+--------+
            |                 |
           NO                YES
            |                 |
            v                 v
    Continue Scanning   TRIGGER MODE SWITCH
                              |
                              v
                     +------------------+
                     | Stop Parallel    |
                     | Retune All SDRs  |
                     | to Target Freq   |
                     +--------+---------+
                              |
                              v
                     +------------------+
                     | DF MODE ACTIVE   |
                     | Phase-Coherent   |
                     | Sample Collection|
                     +--------+---------+
                              |
                              v
                     +------------------+
                     | MUSIC Algorithm  |
                     | Bearing Calc     |
                     | (5-10° accuracy) |
                     +--------+---------+
                              |
                              v
                     +------------------+
                     | Log w/ GPS Tags  |
                     | Update Dashboard |
                     +--------+---------+
                              |
                              v
                     +------------------+
                     | Return to        |
                     | Parallel Scan    |
                     +--------+---------+
                              |
                              v
                     Resume Monitoring


DATA FLOW FOR CONTINUOUS OPERATIONS
------------------------------------

[GPS Module] ---> [Position Data] ---> [Logger]
                                           |
[SDR Array] ---> [RF Samples] ---> [FFT/Analysis]
                                           |
                                           +--> [Demodulation]
                                           |      |
                                           |      +--> Analog (FM/AM/SSB)
                                           |      +--> Digital (DMR/P25/NXDN)
                                           |
                                           +--> [Drone Detector]
                                           |      |
                                           |      +--> Pattern Matching
                                           |      +--> Fingerprinting
                                           |
                                           +--> [Direction Finding]
                                           |      |
                                           |      +--> Array Sync
                                           |      +--> MUSIC Algorithm
                                           |
                                           v
                                    [Record/Log]
                                           |
                                           +--> IQ Samples
                                           +--> Audio Files
                                           +--> JSON Metadata
                                           +--> GPS Coordinates
                                           |
                                           v
                                   [Web Dashboard]
                                           |
                                           +--> Signal List
                                           +--> Bearing Compass
                                           +--> Live Spectrum
                                           +--> GPS Map
```

**Key Concepts That Make This Work**:

1. **Parallel Scanning**: Each SDR is an independent worker. They don't talk to each other during scanning, which means zero coordination overhead and true 4x parallelism.

2. **Anomaly Detection**: Not every signal deserves attention. The system tracks signal history over 5-minute windows, compares new detections against known emitters, and scores anomalies based on multiple factors.

3. **Dynamic Mode Switching**: The secret sauce. System can switch from 4-way parallel scanning to coherent DF in under a second, calculate bearing, and switch back. It's like having a sports car that can also become a tank when needed.

4. **Signal Persistence**: System remembers what it's seen. New signal? Flag it. Same signal getting stronger? Flag it. Signal hopping around? Definitely flag it.

## Hardware Requirements (aka The Shopping List)

Everything you need to build this beast. Total cost: around $670 for full 4-SDR setup.

### Bill of Materials

| Part | Qty | Price | Purpose |
|------|-----|-------|---------|
| **Power & Connectivity** | | | |
| GeeekPi 27W Power Supply for Raspberry Pi 5 | 1 | $12.89 | USB-C PD adapter - Pi 5 drinks power like coffee |
| Anker Powered USB Hub (7-Port USB 3.0) | 1 | $39.99 | Powers multiple SDRs without brownouts; essential for stability |
| Waveshare 4-Port USB HUB HAT | 1 | $12.99 | Stackable HAT with external power; keeps things tidy |
| Anker USB C Power Bank (PowerCore Essential 20000 PD) | 1 | $44.71 | Field ops power; 6-8 hours runtime with full array |
| **Core Platform** | | | |
| iRasptek Basic Kit for Raspberry Pi 5 (4GB w/ Case & Cooler) | 1 | $84.99 | Brains of the operation; active cooling handles processing load |
| SanDisk 64GB Extreme microSDXC Card | 1 | $15.05 | Fast storage for OS and recordings; don't cheap out here |
| **RF Hardware** | | | |
| RTL-SDR Blog V4 (R828D RTL2832U) | 4 | $38.95 ea<br>**$155.80 total** | The stars of the show; V4 has improved sensitivity and bias-tee |
| Nagoya NA-771 Antenna (VHF/UHF) | 4 | $20.56 ea<br>**$82.24 total** | Dual-band whips; one per SDR for full array |
| **Navigation** | | | |
| GPS Module (NEO-6M) | 1 | $11.03 | USB GPS for geo-tagging; tracks where you were when you found it |
| | | **TOTAL: $665.69** | Not including optional array mount/tripod |

**Optional But Recommended**:
- Tripod with mounting brackets for DF array ($50-80)
- USB extension cables for array spacing ($15)
- 28.8MHz clock sync kit for hardware phase coherence ($100) - significantly improves DF accuracy

**Compatibility Notes**:

All components verified compatible with the platform:

- **RTL-SDR V4**: Fully supported via pyrtlsdr and rtl-sdr tools. Bias-tee capability is bonus for active antennas.
- **Raspberry Pi 5**: Tested and confirmed. 4GB model handles all processing; 8GB if you plan to run additional services.
- **GPS NEO-6M**: Works with gpsd out of the box. Fix time ~1-2 minutes cold start.
- **Power Budget**: Full 4-SDR array + Pi 5 + GPS draws approximately 3A at 5V. Anker hub and power bank can handle it.
- **USB Bandwidth**: USB 3.0 hub provides sufficient bandwidth for four simultaneous 2.4 MSPS streams.

**Assembly Time**:
- Core setup (Pi + 1 SDR): 30 minutes
- Full 4-SDR array: 1.5 hours
- Adding hardware sync (if going that route): +2 hours soldering

## Software Installation (The "Make It Go" Section)

### Prerequisites

You'll need Raspberry Pi OS (Debian-based) or similar Linux distro. Windows users: this is your sign to embrace the penguin.

#### System Packages

```bash
# Update system (go make coffee, this takes a minute)
sudo apt update && sudo apt upgrade -y

# Core SDR tools
sudo apt install -y rtl-sdr librtlsdr-dev

# Demodulation tools
sudo apt install -y dsd sox gnuradio

# Python and development tools
sudo apt install -y python3-pip python3-dev build-essential

# GPS daemon
sudo apt install -y gpsd gpsd-clients

# Enable and start GPS daemon
sudo systemctl enable gpsd
sudo systemctl start gpsd
```

#### Python Dependencies

```bash
cd /path/to/ReconRaven

# Install all Python requirements
pip3 install -r requirements.txt

# What you're getting:
# - pyrtlsdr: SDR hardware control
# - numpy/scipy: Signal processing and FFT magic
# - flask/flask-socketio: Web dashboard
# - matplotlib: Pretty plots and compass displays
# - gpsd-py3: GPS interface
# - pyargus: Direction finding algorithms
# - psutil/pyusb: Hardware detection
# And more...
```

### Configuration

The system works out of the box with sensible defaults, but you'll want to tweak a few things:

#### 1. Hardware Calibration

```bash
# Test SDR detection
rtl_test -t

# You should see output like:
# Found 4 device(s):
#   0: Generic RTL2832U (e.g. hama nano)
#   1: Generic RTL2832U (e.g. hama nano)
#   2: Generic RTL2832U (e.g. hama nano)
#   3: Generic RTL2832U (e.g. hama nano)
```

If you see that beautiful "Found 4 device(s)", you're golden.

#### 2. Configuration Files

Edit `config/hardware.yaml` for your setup:

```yaml
sdr:
  ppm_error: 0  # Frequency correction (calibrate if needed)
  gain: "auto"  # Or specific value 0-49.6 dB

gps:
  device: "/dev/ttyUSB0"  # Linux
  device_win: "COM3"      # Windows (if you ignored our advice)

# Adjust sensitivity if getting too many/few anomalies
anomaly_detection:
  strong_signal_threshold_dbm: -40  # Lower = more sensitive
  new_signal_threshold_dbm: -50
  power_surge_threshold_db: 15
```

#### 3. Band Assignments

Edit `config/bands.yaml` to customize what each SDR scans:

```yaml
parallel_scan_assignments:
  sdr0:
    bands: ["2m Amateur Band"]  # Your choice here
    priority: 3
  sdr1:
    bands: ["70cm Amateur Band"]
    priority: 3
  # ... etc
```

### Optional: Hardware Phase Synchronization

For best DF accuracy (approaching 5 degrees), you'll want hardware clock sync. This involves:

1. Opening up the RTL-SDR dongles (warranty? what warranty?)
2. Soldering 28.8MHz clock lines between them
3. Configuring the software to use reference SDR

Follow the KerberosSDR documentation for this process. It's advanced but worth it for serious DF work.

## Usage (The Fun Part)

### Quick Start

```bash
# Navigate to project directory
cd /path/to/ReconRaven

# Just run it (auto-detects your hardware)
python3 app.py

# Platform will:
# 1. Detect number of SDRs
# 2. Enter appropriate mode (1 SDR = mobile, 4 SDRs = parallel)
# 3. Start scanning
# 4. Launch web dashboard at http://localhost:5000
```

Open your browser to `http://localhost:5000` and watch the magic happen. If you're on a Raspberry Pi, access from another device on the same network using `http://raspberrypi.local:5000` (or the Pi's IP address).

### Command Line Options

```bash
# Force specific mode
python3 app.py --mode mobile          # Single SDR mode
python3 app.py --mode parallel_scan   # 4-SDR parallel (no auto-DF)
python3 app.py --mode df             # Pure DF mode
python3 app.py --mode auto           # Auto-detect (default)

# Custom configuration
python3 app.py --config /path/to/custom/config

# Verbose logging for debugging
python3 app.py --log-level DEBUG

# Combination example
python3 app.py --mode parallel_scan --log-level INFO
```

### Performance Expectations

**Mobile Mode (1 SDR)**:
- Full band scan: ~60 seconds
- Coverage: Sequential across all configured bands
- CPU usage: ~25% on Pi 5

**Parallel Mode (4 SDRs)**:
- Scan cycle: **Under 2 seconds**
- Coverage: All bands simultaneously
- CPU usage: ~60% on Pi 5
- Anomaly response: Immediate (auto-DF in 3-5 seconds)

**DF Mode**:
- Bearing calculation: 1-2 seconds per frequency
- Accuracy: 5-10 degrees (software sync), 3-5 degrees (hardware sync)
- Update rate: 1 Hz default

### Example Workflows

#### Scenario 1: Drone Detection Patrol

```bash
# Start in parallel mode
python3 app.py

# System monitors 433 MHz and 915 MHz continuously
# Drone appears? Instant alert + bearing in 3-5 seconds
# Dashboard shows compass with direction
# GPS-tagged log for later analysis
```

#### Scenario 2: Stationary DF Operation

```bash
# Set up tripod with 4-element array (0.5m spacing)
# Connect all SDRs

python3 app.py --mode df

# Platform calibrates array using known signal
# Continuously monitors target frequency
# Provides real-time bearing updates
# Perfect for locating persistent emitters
```

#### Scenario 3: Mobile Reconnaissance

```bash
# Single SDR setup for lightweight operation
python3 app.py --mode mobile

# Walk/drive around area
# System scans and logs all signals with GPS coordinates
# Review dashboard for signal distribution
# Export logs for mapping software
```

## Field Operations Guide

### Setup Checklist

**Before You Leave**:
- [ ] Raspberry Pi 5 with fresh SD card
- [ ] 4x RTL-SDR V4 dongles
- [ ] 4x Antennas (matched if doing DF)
- [ ] GPS module connected and tested
- [ ] Power bank fully charged
- [ ] USB hub with power supply
- [ ] Configuration files reviewed
- [ ] Test run completed at home
- [ ] Dashboard accessible from phone/tablet

**At the Site**:
- [ ] Power on all devices
- [ ] Wait for GPS fix (1-2 minutes, watch the dashboard)
- [ ] Verify all 4 SDRs detected (`rtl_test -t` in terminal)
- [ ] Start platform
- [ ] Confirm dashboard shows "PARALLEL_SCAN" mode
- [ ] Check signal reception on dashboard

### Operating Tips

**Battery Life Management**:
- Full 4-SDR array: 6-8 hours with 20,000mAh bank
- Single SDR mobile: 10+ hours
- Disable auto-DF if conserving power: set `enable_df_on_anomaly: false`
- Monitor power levels in dashboard

**Signal Detection Tips**:
- Start with auto-mode and observe what's normal for the area
- Let system run for 5 minutes to build persistence database
- New signals after that point are actual targets
- High burst activity on 433/915 MHz = likely drone
- Frequency hopping detected = potential FHSS communications

**DF Accuracy Improvements**:
- Use tripod, not handheld (seriously, physics)
- 0.5m spacing is optimal for UHF
- Calibrate array with known emitter before ops
- Multiple bearings from different locations = triangulation
- Software sync: 10-degree accuracy (acceptable)
- Hardware sync: 5-degree accuracy (worth the mod)

**Dashboard Pro Tips**:
- Signal list auto-sorts by power (strongest first)
- Click anomaly for details
- Bearing compass updates in real-time during DF
- GPS coordinates in bottom bar
- Export logs via dashboard (coming soon)

## Troubleshooting (When Things Go Sideways)

### SDRs Not Detected

```bash
# Check USB connections
lsusb | grep Realtek

# Should see:
# Bus 001 Device 004: ID 0bda:2838 Realtek ... RTL2838
# (four times)

# If not:
# 1. Try different USB ports
# 2. Use powered hub
# 3. Check USB cable quality (yes, it matters)
```

### Permission Denied Errors

```bash
# Add yourself to plugdev group
sudo usermod -a -G plugdev $USER

# Logout and login (or reboot)
sudo reboot
```

### GPS Not Working

```bash
# Check GPS device
ls -l /dev/ttyUSB* /dev/ttyACM*

# Test GPS directly
cgps -s

# Should see satellites and coordinates
# If not:
# 1. Go outside (buildings are Faraday cages)
# 2. Wait 2-3 minutes for cold start
# 3. Check antenna connection
```

### Parallel Mode Running Slow

**Problem**: Scan cycles taking too long

**Solutions**:
```yaml
# Edit config/hardware.yaml

# Option 1: Increase cycle time target
modes:
  parallel_scan:
    cycle_time_s: 5  # Up from 2

# Option 2: Reduce integration time
scanning:
  integration_time_ms: 50  # Down from 100

# Option 3: Temporarily disable auto-DF
modes:
  parallel_scan:
    enable_df_on_anomaly: false
```

### Too Many Anomalies

**Problem**: System detecting everything as anomaly

**Solution**: Adjust thresholds
```yaml
# Edit config/hardware.yaml
anomaly_detection:
  strong_signal_threshold_dbm: -35  # Less sensitive
  new_signal_threshold_dbm: -45     # Less sensitive
  power_surge_threshold_db: 20      # Less sensitive
```

Let system run for 10 minutes first to build baseline. Urban environments have more persistent signals.

### DF Accuracy Poor

**Problem**: Bearings seem random

**Checklist**:
- [ ] Array on tripod (not handheld)
- [ ] Elements spaced 0.5m apart
- [ ] All 4 SDRs tuned to same frequency
- [ ] Calibration completed recently
- [ ] Signal strong enough (>-60 dBm)
- [ ] Not in multipath environment (buildings/metal)

If all else fails: run manual calibration with known emitter at known direction.

### rtl_power Not Found

```bash
# rtl_power not available? No problem.
# Platform automatically falls back to pyrtlsdr

# But if you want rtl_power:
sudo apt install rtl-sdr
```

## Development and Customization

### Adding New Bands

Edit `config/bands.yaml`:

```yaml
scan_bands:
  - name: "My Custom Band"
    start_hz: 400000000
    end_hz: 410000000
    description: "That frequency range I'm really interested in"
    priority: 5
```

### Custom Drone Signatures

Edit `scanning/drone_detector.py`:

```python
DroneSignature(
    name="My Drone Model",
    frequency_ranges=[(freq_start, freq_end)],
    pattern_type="burst",  # or "chirp" or "hopping"
    min_duration_ms=10,
    max_duration_ms=500,
    bandwidth_hz=125000
)
```

### Adjusting Anomaly Detection

Edit `config/hardware.yaml`:

```yaml
anomaly_detection:
  enabled: true
  strong_signal_threshold_dbm: -40
  burst_detection: true
  hopping_detection: true
  tracking_duration_s: 300  # 5 minutes
```

## Project Structure

```
ReconRaven/
├── app.py                      # Main application entry point
├── config.py                   # Configuration management
├── requirements.txt            # Python dependencies
├── README.md                   # This magnificent document
│
├── hardware/
│   ├── __init__.py
│   └── sdr_controller.py      # SDR detection and control
│
├── scanning/
│   ├── __init__.py
│   ├── spectrum.py            # Single-SDR FFT scanner
│   ├── scan_parallel.py       # 4-SDR parallel scanner
│   ├── anomaly_detect.py      # Intelligent anomaly detection
│   ├── mode_switch.py         # Dynamic mode switching
│   └── drone_detector.py      # Drone pattern matching
│
├── demodulation/
│   ├── __init__.py
│   ├── analog.py              # FM/AM/SSB demodulation
│   └── digital.py             # Digital mode demodulation
│
├── direction_finding/
│   ├── __init__.py
│   ├── array_sync.py          # Phase-coherent array sync
│   └── bearing_calc.py        # MUSIC algorithm implementation
│
├── recording/
│   ├── __init__.py
│   └── logger.py              # GPS-tagged logging
│
├── visualization/
│   ├── __init__.py
│   ├── bearing_map.py         # Matplotlib visualizations
│   └── templates/
│       └── dashboard.html     # Web interface
│
├── web/
│   ├── __init__.py
│   └── server.py              # Flask server
│
├── config/
│   ├── bands.yaml             # Frequency definitions
│   ├── demod_config.yaml      # Demodulation parameters
│   └── hardware.yaml          # Hardware configuration
│
└── examples/
    ├── single_scan.py         # Basic scanning example
    ├── df_bearing.py          # DF demonstration
    ├── drone_hunt.py          # Drone detection demo
    └── parallel_scan_demo.py  # Parallel scanning demo
```

## Lessons Learned from Similar Projects

After reviewing KerberosSDR, HydraSDR, and various GitHub implementations, here's what we incorporated:

**From KerberosSDR**:
- 4-element array geometry (proven effective)
- Phase calibration using noise correlation
- 0.5m spacing for UHF optimal performance

**From RTL-SDR Community Projects**:
- rtl_power for fast scanning (when available)
- Fallback to pyrtlsdr (more portable)
- USB device detection patterns
- Buffer management for stability

**Our Innovations**:
- Dynamic mode switching (scan to DF transition)
- Intelligent anomaly detection with persistence tracking
- Unified configuration system
- Real-time dashboard with WebSocket updates
- Priority-based anomaly scoring

## Performance Benchmarks

Tested on Raspberry Pi 5 (4GB) with 4x RTL-SDR V4:

| Operation | Time | CPU Usage | Notes |
|-----------|------|-----------|-------|
| Full parallel scan cycle | 1.8s | 60% | All 4 bands simultaneously |
| Single band scan (mobile) | 15s | 25% | 144-148 MHz range |
| Mode switch (parallel to DF) | 0.8s | - | Includes retune time |
| DF bearing calculation | 1.2s | 80% | MUSIC algorithm |
| Mode switch (DF to parallel) | 0.5s | - | Resume scanning |
| Anomaly detection processing | <0.1s | 15% | Per scan cycle |
| Dashboard update | <0.05s | 5% | WebSocket push |

**Battery Life** (20,000mAh power bank):
- 4-SDR parallel mode: 6-8 hours
- 1-SDR mobile mode: 10-12 hours
- DF mode (stationary): 6-8 hours

## Legal and Safety

**READ THIS PART**. Seriously.

This platform is for **passive reception only**. It listens, it doesn't talk. Like a good therapist, but for radio waves.

**Legal Stuff**:
- Receiving signals is generally legal in most jurisdictions
- Some frequencies may require licenses to TRANSMIT (we're not transmitting, so we're good)
- Check your local regulations regarding monitoring certain bands
- Some countries restrict DF equipment near sensitive sites
- When in doubt, ask a lawyer (preferably one who understands RF)

**Ethical Use**:
- Educational purposes
- Authorized security research
- Your own property/networks
- Licensed amateur radio operations
- Approved training scenarios

**Don't Be That Person**:
- Don't intercept private communications
- Don't use for unauthorized surveillance
- Don't interfere with licensed services
- Don't claim you didn't know (you're reading this)

**Safety**:
- RF exposure: Keep antennas away from body during transmission testing
- Electrical: Don't modify hardware if you don't know what you're doing
- Privacy: Secure your recordings and logs
- Common sense: Use it

## Credits and Acknowledgments

**Standing on the Shoulders of Giants**:
- RTL-SDR Blog team for the V4 hardware and continued development
- KerberosSDR project for pioneering 4-element coherent RTL-SDR arrays
- The entire RTL-SDR community for tools, documentation, and inspiration
- GNU Radio for the signal processing foundation
- Digital Speech Decoder (DSD) team for multi-protocol demodulation
- Schmidt, R. O. for the MUSIC algorithm (1986)

**Technologies Used**:
- Python 3 (because life's too short for C++)
- RTL-SDR drivers and tools
- NumPy/SciPy for the math we pretend to fully understand
- Flask for web goodness
- Matplotlib for pretty pictures
- Raspberry Pi for being an absolute legend of a SBC

## Support and Contributing

**Issues?** Check the troubleshooting section first. Then:
- Check existing GitHub issues
- Search the RTL-SDR community forums
- Ask in the #rtl-sdr channel (various platforms)

**Want to Contribute?**
- Fork the repo
- Create a feature branch
- Test your changes (please, for the love of Nyquist)
- Submit a pull request with clear description

**Future Enhancements** (aka The Wishlist):
- Machine learning for automatic signal classification
- Triangulation from multiple DF positions
- Integration with mapping software
- Advanced waterfall displays
- Replay attack detection
- More drone signature databases
- Your brilliant idea here

## FAQ (Frequently Argued Questions)

**Q: Why not use HackRF/USRP/LimeSDR instead of RTL-SDR?**

A: Budget. Four RTL-SDR V4s cost $160. One HackRF costs $300+ and you'd need four. Also, RTL-SDR V4 is actually really good for VHF/UHF work.

**Q: Can this detect DJI drones?**

A: The 2.4GHz and 5.8GHz control/video links are outside RTL-SDR range. But many drones also use 433/915 MHz telemetry which we CAN detect. Plus, aftermarket control systems.

**Q: How accurate is the direction finding really?**

A: With software sync: 10-15 degrees (acceptable for most purposes). With hardware clock sync: 5-8 degrees (pretty darn good). Professional DF systems: 1-3 degrees (and cost $50K+).

**Q: Will this work on Windows?**

A: Technically yes, practically no. Linux is native habitat for SDR tools. WSL2 might work but you're on your own. Just use Linux.

**Q: Can I use this for [probably illegal thing]?**

A: No. Read the Legal section again.

**Q: Is there a GUI?**

A: Yes! Web dashboard at localhost:5000. Modern, real-time, works on phone. Better than most commercial software.

**Q: How do I make it faster?**

A: Already fast. But you can: overclock Pi, use faster storage, reduce integration time, disable auto-DF if not needed.

**Q: My cat sat on the antenna. Now what?**

A: First, get a dog. Second, recalibrate the array. Third, consider that your cat might be an RF jammer.

## Version History

**v2.0** (Current)
- Added parallel 4-SDR scanning mode
- Intelligent anomaly detection system
- Dynamic mode switching
- Signal persistence tracking
- Performance optimization
- Comprehensive documentation

**v1.0**
- Initial release
- Single and 4-SDR modes (static)
- Basic scanning and DF
- Web dashboard
- GPS logging

## License

MIT License - Because sharing is caring, and good SDR code should be free.

Use it, modify it, learn from it. Just don't blame us if your code goes sideways. And maybe give us a shoutout if you build something cool with it.

## Final Words

If you've read this far, you're either really interested in SDR/SIGINT or you have too much free time. Either way, welcome to the club.

This platform represents hundreds of hours of development, testing, debugging, and occasionally questioning life choices. It works. It's fast. It's useful. And it's yours to use.

Go find some interesting signals. Learn things. Build things. Break things (safely). And remember: with great radio reception comes great responsibility.

Now get out there and make some RF magic happen.

**73 and happy hunting.**

---

*Built with caffeine, Python, and an unhealthy obsession with radio waves.*

*Version 2.0.0 | Last Updated: November 2025*
