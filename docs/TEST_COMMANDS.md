# Quick Test Commands

## After Physical RF Setup

Once you've reorganized your SDRs per the RF Setup Guide, use these commands to validate:

## 1. Detect SDRs
```bash
python3 reconraven.py test sdr
```
**Purpose:** Verify all SDRs are detected and accessible  
**Expected:** Shows 3-4 SDRs with tuner info and no errors

## 2. Check Noise Floor
```bash
python3 reconraven.py test noise
```
**Purpose:** Measure RF noise across all bands  
**Expected Results:**
- Good: < -30 dBm
- Acceptable: -20 to -30 dBm  
- Problem: > -10 dBm (still too much interference)

**Action:** If > -10 dBm, further separate SDRs from interference sources

## 3. Monitor Specific Frequency
```bash
python3 reconraven.py test freq --freq 146.52 --duration 60
```
**Purpose:** Watch one frequency for transmissions  
**Use Case:** Have someone transmit, verify you see +20-30 dB increase

**Parameters:**
- `--freq`: Frequency in MHz (e.g., 146.52)
- `--duration`: How long to monitor in seconds (default: 30)

**Expected:** Baseline < -20 dBm, transmission causes +20+ dB spike

## 4. Scan Band for Signals
```bash
python3 reconraven.py test rf --band 2m
```
**Purpose:** Quick scan of a band to see activity  
**Bands Available:**
- `2m`: 146-147 MHz (ham 2-meter band)
- `70cm`: 435-436 MHz (ham 70cm band)
- `433`: 433-434 MHz (ISM remote controls)
- `915`: 915-916 MHz (ISM devices)

**Expected:** Shows all frequencies with power levels, flags signals > -20 dBm

## Full Scanner Commands

Once tests pass, run the full scanner:

### Build Baseline (First Time)
```bash
python3 reconraven.py scan --dashboard --rebuild-baseline
```
Builds noise baseline for your RF environment (takes ~2 minutes)

### Normal Scanning
```bash
python3 reconraven.py scan --dashboard
```
Starts full concurrent scanning with web dashboard at http://localhost:5000

### Quick Scan (Baseline Only)
```bash
python3 reconraven.py scan --quick
```
Just builds/updates baseline without monitoring

## Troubleshooting Flow

1. **SDRs not detected?**
   - Check USB connections
   - Try `lsusb | grep Realtek` (Linux/WSL)
   - Check udev rules or drivers

2. **High noise floor (> -10 dBm)?**
   - Move SDRs away from computer (use USB extension cables)
   - Turn off nearby electronics
   - Add ferrite beads to USB cables
   - Check bias-tee is OFF: `rtl_biast -d 0 -b 0`

3. **Transmission not detected?**
   - Run freq test: `python3 reconraven.py test freq --freq 146.52 --duration 60`
   - Verify baseline is low (< -20 dBm)
   - Verify transmission causes +20+ dB increase
   - Check antenna is connected

4. **Scanner hangs/crashes?**
   - Kill stuck processes: `pkill -9 python; pkill -9 rtl`
   - Check disk space (recordings can fill up fast)
   - Review logs in terminal output

## Example Test Session

```bash
# 1. Check SDRs
python3 reconraven.py test sdr
# Expected: Found 3 RTL-SDR device(s)

# 2. Check noise
python3 reconraven.py test noise
# Expected: All bands < -20 dBm

# 3. Test 2m reception (have someone TX on 146.52)
python3 reconraven.py test freq --freq 146.52 --duration 60
# Expected: Baseline -25 dBm, TX shows -5 dBm (+20 dB delta)

# 4. Scan 2m band
python3 reconraven.py test rf --band 2m
# Expected: Mostly flat around -25 to -30 dBm with occasional peaks

# 5. If all pass, start scanner
python3 reconraven.py scan --dashboard
```

## Quick Stats

After scanner has been running:

```bash
# View database stats
python3 reconraven.py db stats

# List anomalies
python3 reconraven.py db anomalies --limit 20

# List identified devices
python3 reconraven.py db devices --limit 20
```

## Need Help?

See `docs/RF_SETUP_GUIDE.md` for detailed RF environment setup instructions.





