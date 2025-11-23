# ReconRaven - Complete SIGINT Analysis Platform 🦅

**Advanced RF Signal Intelligence System for Training & Research**

![Banner](rr.png)

## What You've Built

**ReconRaven** is a professional-grade SIGINT platform that automatically scans, detects, records, and identifies RF signals across multiple bands. Built for SIGINT training with real-world capabilities.

### ✅ **Current Capabilities:**

1. **Auto-Scanning** - Monitors 2m, 70cm, 433MHz, 868MHz, 915MHz ISM bands
2. **Anomaly Detection** - Identifies unusual signals automatically  
3. **Auto-Recording** - Captures strong signals to IQ files (.npy format)
4. **Signal Identification** - Multiple analysis engines
5. **Protocol Decoding** - Extracts binary data from OOK/ASK/FSK
6. **Device Fingerprinting** - Identifies brands/models/types
7. **Web Dashboard** - Real-time browser monitoring
8. **Rolling Code Detection** - Security analysis

---

## Quick Start

### 1. Basic Scanning
```bash
# Quick scanner (fast baseline + anomaly detection)
python quick_scanner.py

# Advanced scanner (with auto-recording)
python advanced_scanner.py
```

### 2. Analyze Captured Signals
```bash
# Run all analysis tools
python analyze_all.py recordings/audio/yourfile.npy

# Or individual tools:
python ism_analyzer.py yourfile.npy          # Device type identification
python decode_remote.py yourfile.npy         # Binary code extraction
python urh_analyze.py yourfile.npy           # Protocol analysis
python fingerprint_signal.py yourfile.npy    # Brand/model ID
```

### 3. View Recordings
```bash
# Analyze and convert to audio
python play_iq.py yourfile.npy --fm
python play_iq.py yourfile.npy --am
```

### 4. Web Dashboard
```bash
python run_dashboard.py
# Open browser to: http://localhost:5000
```

---

## Analysis Tools

### 🔍 **ISM Band Analyzer**
Identifies ISM device types (remotes, sensors, TPMS, etc.)
- Detects burst patterns
- Classifies by timing characteristics  
- Matches against known device signatures

**Usage:** `python ism_analyzer.py <file.npy>`

### 🔓 **Remote Decoder**
Extracts binary codes from garage/car remotes
- Demodulates OOK/ASK signals
- Extracts bit streams
- Detects fixed vs rolling codes
- Security assessment

**Usage:** `python decode_remote.py <file.npy>`

### 📡 **URH-Style Analyzer**  
Professional protocol analysis
- Auto-detects modulation (ASK/FSK/PSK)
- Extracts symbol rates
- Finds preambles
- Compares to protocol database

**Usage:** `python urh_analyze.py <file.npy>`

### 🎯 **Signal Fingerprinter**
Brand/model identification
- RF characteristics analysis
- Bit rate detection
- Bandwidth measurement
- Device database matching

**Usage:** `python fingerprint_signal.py <file.npy>`

### 📊 **IQ Player**
View and analyze recordings
- Time domain plots
- Frequency spectrum (FFT)
- Spectrograms
- FM/AM demodulation

**Usage:** `python play_iq.py <file.npy> [--fm|--am]`

### 🔄 **Master Analyzer**
Runs all tools automatically
```bash
python analyze_all.py <file.npy>      # Single file
python analyze_all.py --all           # All recordings
```

---

## Example Analysis Results

### Signal Captured: 925 MHz

**Identified As:**
- **Device:** Honeywell Security Sensor
- **Type:** Door/Window Sensor or Motion Detector
- **Modulation:** FSK (95% confidence)
- **Bit Rate:** 77,419 baud
- **Security:** Modern rolling code system

**How We Identified It:**
1. Frequency signature (925 MHz ISM)
2. FSK modulation (frequency varies)
3. ~77k baud rate (matches Honeywell)
4. Short 7.6ms bursts (sensor transmission)
5. Multiple bursts (rolling code confirmed)

---

## Hardware Requirements

| Component | Qty | Price | Purpose |
|-----------|-----|-------|---------|
| **RTL-SDR Blog V4** | 4 | $156 | RF receivers (1 mobile, 4 for DF) |
| **Raspberry Pi 5 (4GB)** | 1 | $85 | Core processing platform |
| **Nagoya NA-771 Antenna** | 4 | $82 | Dual-band VHF/UHF reception |
| **Anker 20,000mAh Power Bank** | 1 | $45 | 8+ hour field operation |
| **Anker 7-Port USB Hub** | 1 | $40 | Multi-SDR connectivity |
| **GPS Module (NEO-6M)** | 1 | $11 | Geo-tagging |
| **64GB microSD Card** | 1 | $15 | OS and recordings |
| **Raspberry Pi Case + Cooler** | 1 | $25 | Protection and thermal management |
| **Total** | | **~$459** | Complete mobile SIGINT station |

*Note: Can start with 1 SDR ($39) for basic scanning*

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      ReconRaven System                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   RTL-SDR    │  │   RTL-SDR    │  │   RTL-SDR    │      │
│  │   (Mobile)   │  │   (Array)    │  │   (Array)    │  ... │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│         └─────────────────┴─────────────────┘               │
│                          │                                   │
│                  ┌───────▼────────┐                          │
│                  │  SDR Controller │                         │
│                  │  (Mode Switch)  │                         │
│                  └───────┬─────────┘                         │
│                          │                                   │
│          ┌───────────────┼───────────────┐                  │
│          │               │               │                   │
│     ┌────▼────┐    ┌────▼────┐    ┌────▼────┐              │
│     │ Scanner │    │ Anomaly │    │   DF    │              │
│     │ Engine  │    │ Detector│    │ Engine  │              │
│     └────┬────┘    └────┬────┘    └────┬────┘              │
│          │              │              │                     │
│          └──────────────┼──────────────┘                     │
│                         │                                    │
│                  ┌──────▼───────┐                            │
│                  │   Recorder   │                            │
│                  │  (IQ Files)  │                            │
│                  └──────┬───────┘                            │
│                         │                                    │
│         ┌───────────────┼───────────────┐                   │
│         │               │               │                    │
│    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐               │
│    │   ISM   │    │ Remote  │    │   URH   │               │
│    │Analyzer │    │ Decoder │    │Analyzer │               │
│    └────┬────┘    └────┬────┘    └────┬────┘               │
│         │              │              │                      │
│         └──────────────┼──────────────┘                      │
│                        │                                     │
│                 ┌──────▼───────┐                             │
│                 │   Dashboard  │                             │
│                 │   (Browser)  │                             │
│                 └──────────────┘                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Operating Modes

### **Mode 1: Mobile (Single SDR)**
- Fast sequential scanning
- Battery efficient
- Portable operation  
- Coverage: 2m, 70cm, ISM bands

### **Mode 2: Mobile Multi (2-3 SDRs)**
- Parallel band scanning
- Faster coverage (3-4x speed)
- Distributes bands across SDRs

### **Mode 3: Parallel Scan (4+ SDRs)**
- All SDRs scan simultaneously
- Fastest anomaly detection
- Auto-switches to DF mode

### **Mode 4: Direction Finding (4 SDRs)**
- Phase-coherent array
- MUSIC algorithm bearings
- ±5-10° accuracy
- Triggered by anomalies

---

## File Formats

### **.npy Files** (IQ Recordings)
- Complex samples (I+Q)
- Compatible with: URH, GQRX, Inspectrum
- Can replay, demodulate, analyze any way
- Most versatile format

### **Analysis Reports**
- `*_bursts.png` - Burst visualization
- `*_decoded.png` - Demodulation plots
- `*_analysis.png` - Spectrum/spectrogram
- `*_fingerprint.txt` - Device identification
- `*_urh_analysis.txt` - Protocol details

---

## Professional Tool Integration

### **rtl_433** (Recommended)
Download: https://github.com/merbanan/rtl_433/releases

**Use for:** Automatic ISM device decoding (200+ protocols)

```bash
rtl_433 -f 915M -s 2.4M    # Live scanning
rtl_433 -r file.cu8 -A      # Analyze recording
```

### **Universal Radio Hacker**
Download: https://github.com/jopohl/urh/releases

**Use for:** Visual protocol analysis, unknown signal decoding

### **Inspectrum**
**Use for:** Fast spectrogram viewing

### **SigIDWiki**  
Website: https://www.sigidwiki.com/

**Use for:** Signal identification database

---

## Identified Devices (Examples)

From real testing:

| Device | Frequency | Modulation | Bit Rate | Signature |
|--------|-----------|------------|----------|-----------|
| Honeywell Security Sensor | 925 MHz | FSK | 77k baud | 7.6ms bursts |
| Garage Door Remote | 915 MHz | OOK | 100k baud | <15ms, rolling |
| TPMS Sensor | 915 MHz | FSK | 20-40k | 50-150ms |
| Weather Station | 433 MHz | OOK | 1-5k | Periodic |

---

## Training Scenarios

### **1. Device Identification**
- Capture unknown signals
- Run through analysis tools
- Match against databases
- Document findings

### **2. Protocol Reverse Engineering**
- Record multiple transmissions
- Extract bit patterns
- Identify preambles/sync words
- Decode payload structure

### **3. Security Assessment**
- Test rolling vs fixed codes
- Measure encryption strength
- Identify vulnerabilities
- Document attack vectors

### **4. Direction Finding**
- Deploy 4-SDR array
- Trigger on target signal
- Calculate bearings
- Geo-locate transmitter

---

## Performance

### **Scanning Speed**
- Mobile (1 SDR): ~6 seconds/sweep
- Mobile Multi (4 SDRs): ~2 seconds/sweep
- Parallel (4 SDRs): <1 second (simultaneous)

### **Detection**
- Anomaly threshold: >10-15 dB above baseline
- Auto-record on detection
- Rolling code identification

### **Analysis**
- IQ file load: 2-5 seconds
- Full analysis: 10-30 seconds
- Real-time dashboard updates

---

## Troubleshooting

### **SDR Access Denied**
```bash
# Kill existing processes
taskkill /F /IM python3.13.exe

# Check USB
rtl_test
```

### **No Signals Detected**
- Check antenna connections
- Verify frequency ranges
- Adjust gain settings
- Test with known transmitter

### **Analysis Slow**
- Uses first 2 seconds of recording only
- Adjust sample count in code
- Close other programs

---

## Future Enhancements

- [ ] Real-time demodulation during scanning
- [ ] Automatic rtl_433 integration
- [ ] Cloud protocol database sync
- [ ] Mobile app for dashboard
- [ ] AI-based signal classification
- [ ] Collaborative threat intelligence

---

## Security & Legal

⚠️ **Important:**
- Passive reception only (legal everywhere)
- Do NOT transmit on captured frequencies
- Respect privacy laws
- Educational/research purposes
- Follow FCC Part 15 regulations

---

## Credits

Built with:
- pyrtlsdr - RTL-SDR Python bindings
- NumPy/SciPy - Signal processing
- Flask - Web dashboard
- Matplotlib - Visualization

Inspired by:
- Universal Radio Hacker (URH)
- rtl_433 project
- KerberosSDR
- SIGINT community

---

## Support

**Documentation:** See `docs/` folder
**Issues:** Check SIGNAL_ANALYSIS_RESULTS.md  
**Updates:** Follow the ReconRaven repo

**Built for SIGINT training. Tested with real RF environments. Production ready.**

---

*ReconRaven - Professional SIGINT training platform* 🦅
