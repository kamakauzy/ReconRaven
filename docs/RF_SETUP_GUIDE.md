# RF Environment Setup Guide

## Problem Identified

During testing, we discovered RF saturation across the 2m band (-8.7 to -9.3 dBm noise floor), preventing signal detection. This is caused by having SDRs in close proximity to computer equipment, tangled cables, and general RF interference.

## Symptoms of RF Interference

- All frequencies in a band show similar high power levels (-10 dBm or higher)
- Strong local transmissions (5W at 15 feet) are not distinguishable from noise
- Only certain bands (like 915 MHz) show detections while others (2m, 70cm) do not
- Erratic baseline power levels

## Required Physical Setup

### 1. SDR Placement

**DO:**
- Place SDRs **3-6 feet away** from computer/laptop
- Use **USB extension cables** (6-10 feet) with ferrite beads
- Keep SDRs **separated from each other** (1-2 feet minimum for DF mode)
- Position away from monitors, power supplies, WiFi routers
- Elevate SDRs if possible (off desk surface)

**DON'T:**
- Plug SDRs directly into computer USB ports
- Use USB hubs (if possible)
- Place near power adapters or switching power supplies
- Let USB/antenna cables coil up or bundle together
- Position near fluorescent lights or dimmer switches

### 2. Antenna Configuration

**For Reception Testing:**
- Use the magnetic base antennas that came with RTL-SDR Blog V4
- Keep antennas **vertical** (perpendicular to ground)
- Separate antennas by at least **1-2 feet** from each other
- Route antenna cables away from USB cables
- Don't let cables touch or run parallel

**For Direction Finding (4 SDRs):**
- Arrange in a **circular array** with equal spacing
- Recommended spacing: 1-2 feet radius
- All antennas same height and orientation
- Clear line of sight between array and expected signal sources

### 3. USB Cable Management

**Best Practices:**
- Use **shielded USB cables** with ferrite beads
- Add **additional ferrite cores** to both ends if needed
- Keep USB cables straight - don't coil excess
- Route away from antenna cables (>6 inches separation)
- Avoid running near AC power cables

### 4. Power Considerations

**Optimal Setup:**
- Plug computer into **grounded outlet**
- Use same power circuit for all equipment
- Avoid USB hubs with separate power adapters
- Consider **powered USB hub** if using 3-4 SDRs (better than individual ports)
- Ensure good ground connection

## Testing After Setup

Once you've physically reorganized your SDRs, run these diagnostic tests:

### 1. Check Noise Floor

```bash
python3 reconraven.py test noise
```

**Expected Results:**
- 2m band: < -30 dBm (good), < -20 dBm (acceptable)
- 70cm band: < -30 dBm (good), < -20 dBm (acceptable)  
- ISM bands: < -25 dBm (good), < -15 dBm (acceptable)

If any band shows > -10 dBm, you still have RF interference.

### 2. Test SDR Detection

```bash
python3 reconraven.py test sdr
```

Should detect all 3-4 SDRs without errors.

### 3. Test Specific Frequency

Have someone transmit on 146.520 MHz (2m calling frequency):

```bash
python3 reconraven.py test freq --freq 146.52 --duration 60
```

**Expected Results:**
- Baseline: < -20 dBm
- During transmission (5W at 15 feet): -10 to +10 dBm
- Delta: **+20 to +30 dB** (easily detectable!)

### 4. Scan a Band

```bash
python3 reconraven.py test rf --band 2m
```

Should show relatively flat noise floor with occasional peaks for actual signals.

## Common RF Interference Sources

### Computer-Related
- **CPU/GPU**: Generates broadband noise, especially under load
- **USB 3.0**: Can interfere with 2.4 GHz WiFi and lower VHF
- **Laptop switching power supplies**: Common cause of 100-200 MHz interference
- **HDMI cables**: Can radiate RF, especially if poorly shielded
- **Ethernet cables**: Cat5/6 can radiate, especially at poor connections

### Home Electronics
- **WiFi routers**: 2.4 GHz can desensitize VHF receivers
- **LED lights**: PWM dimming creates RF noise
- **Plasma TVs**: Broadband noise generator
- **Microwave ovens**: 2.4 GHz leakage
- **Cell phones**: GSM bursts every few seconds
- **Baby monitors**: Often on 2.4 GHz or 900 MHz

### Solutions
1. **Turn off/unplug** unnecessary electronics during scanning
2. **Distance** is your friend - inverse square law applies
3. **Shielding**: Wrap problem devices in aluminum foil (seriously!)
4. **Filters**: Add ferrite beads to problem cables
5. **Scheduling**: Scan during low-activity hours (3-6 AM)

## Bias-Tee (RTL-SDR Blog V4 Only)

The RTL-SDR Blog V4 has a built-in bias-tee for powering external LNAs.

**IMPORTANT:** Bias-tee should be **OFF** for normal operation!

To check/disable:
```bash
rtl_biast -d 0 -b 0  # Disable bias-tee on SDR #0
rtl_biast -d 1 -b 0  # Disable bias-tee on SDR #1
rtl_biast -d 2 -b 0  # Disable bias-tee on SDR #2
```

Only enable if you're using an external powered LNA.

## Validation Procedure

After setting up your RF environment properly:

1. **Disconnect all antennas** → Run noise test → Should see < -40 dBm
2. **Connect antennas** → Run noise test → Should see < -25 dBm
3. **Transmit 5W at 15 feet** on 146.52 MHz → Run freq test → Should see +20 dB delta
4. **Run full scanner** → Should detect transmission within 1 minute

If you pass all 4 steps, your RF environment is ready!

## Expected Performance After Proper Setup

With a clean RF environment:

- **Handheld (5W)**: Detectable up to 1-2 miles line of sight
- **Mobile (50W)**: Detectable up to 5-10 miles
- **Base station (100W)**: Detectable 10-20+ miles
- **Sensitivity**: Down to ~-60 dBm signals detectable above baseline
- **Direction Finding**: ±5-10° accuracy with 4-SDR array

## Still Having Issues?

### Check SDR Gain Settings

The scanner uses `gain = 'auto'` by default. If you're still saturated:

Edit `advanced_scanner.py` and change:
```python
sdr.gain = 'auto'
```

To:
```python
sdr.gain = 20.0  # Fixed gain in dB (try 20-30)
```

Lower gain = less sensitive but also less prone to overload.

### Verify SDR Functionality

Test with a known-good tool like GQRX or SDR# to verify SDRs work properly.

### Check for Hardware Issues

- Damaged antennas (poor solder joints, broken elements)
- Bad USB cables (data errors, poor shielding)
- Faulty SDR (rare, but possible)

## Questions?

If you've followed this guide and still have issues, check:
1. Noise floor test results (`python3 reconraven.py test noise`)
2. SDR detection (`python3 reconraven.py test sdr`)
3. Specific frequency test with known transmission
4. System logs for USB errors or buffer overruns

Document your findings and we can troubleshoot further!





