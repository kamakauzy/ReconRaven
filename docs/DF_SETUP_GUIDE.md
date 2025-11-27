# Direction Finding (DF) Array Setup Guide

## Overview

This guide covers setting up a multi-SDR Direction Finding (DF) array for ReconRaven, including the recommended 3D printed V-dipole antenna mounts.

## Hardware Requirements

### Minimum DF Configuration
- **2 RTL-SDR dongles** (basic bearing estimation)
- **4 RTL-SDR dongles** (recommended for accurate MUSIC algorithm)
- **Antennas** with consistent phase characteristics
- **USB hub** (powered, USB 3.0 recommended)
- **Mounting system** for consistent geometry

### Recommended Configuration
- **4x RTL-SDR V4** dongles
- **4x 120° V-dipole antennas** (3D printed mounts)
- **Square or circular array** with 0.5m spacing
- **GPS receiver** for geo-tagging bearings
- **Compass** for array orientation (optional)

## Antenna Selection

### Why V-Dipole Antennas?

The **120° V-dipole** design is recommended because:

1. **Broad Frequency Coverage**
   - Works across 2m (144-148 MHz) and 70cm (420-450 MHz) bands
   - Single antenna covers both amateur bands

2. **Consistent Phase Center**
   - Predictable phase response across frequency range
   - Critical for accurate MUSIC algorithm calculations

3. **Mixed Polarization**
   - Responds to both horizontal and vertical polarization
   - Better signal reception from unknown sources

4. **3D Printable**
   - Repeatable geometry using 3D printed mounts
   - Lightweight and portable
   - Easy to replace if damaged

### 3D Printed V-Dipole Mount

**Recommended Design:**
- [120° V-Dipole Guide on MyMiniFactory](https://www.myminifactory.com/object/3d-print-120-degree-v-dipole-guide-133341)

**Print Settings:**
- Material: PLA or PETG
- Infill: 20% minimum
- Supports: Not required
- Quantity: 4 (one per SDR)

**Assembly:**
1. Print 4 antenna mounts
2. Cut dipole elements to length:
   - **2m band (146 MHz)**: λ/4 = 0.51m per element
   - **70cm band (435 MHz)**: λ/4 = 0.17m per element
   - For dual-band, use 2m length with 70cm loading
3. Solder elements to coax feed
4. Attach to RTL-SDR dongles

### Alternative Antennas

If V-dipoles aren't available, you can use:

1. **Omnidirectional Antennas** (e.g., ground planes, discones)
   - Pros: Simple, wideband
   - Cons: Less predictable phase, lower gain

2. **Standard Dipoles** (vertical or horizontal)
   - Pros: Good phase characteristics
   - Cons: Narrowband, polarization-specific

3. **Monopoles** (quarter-wave verticals)
   - Pros: Compact, simple
   - Cons: Ground plane dependent

**Important:** All antennas in the array **MUST** be identical for phase coherence!

## Array Geometry

### Square Array (Recommended)

```
     [SDR #0]
        |
    0.5m spacing
        |
[SDR #1]--+--[SDR #2]
        |
      [SDR #3]
```

**Advantages:**
- 360° azimuth coverage
- Equal spacing for all pairs
- Simple to construct

**Configuration:**
```yaml
# config/hardware.yaml
df_array:
  geometry: "square"
  spacing_m: 0.5
  element_positions:
    - [0.0, 0.0]   # Reference at origin
    - [0.5, 0.0]   # East
    - [0.5, 0.5]   # Northeast
    - [0.0, 0.5]   # North
```

### Linear Array

```
[SDR #0]---[SDR #1]---[SDR #2]---[SDR #3]
  0.5m       0.5m       0.5m
```

**Advantages:**
- Simple to construct (mount on bar)
- Good for mobile/vehicle mounting

**Disadvantages:**
- 180° ambiguity (can't distinguish front/back)
- Narrower effective aperture

**Configuration:**
```yaml
df_array:
  geometry: "linear"
  spacing_m: 0.5
  element_positions:
    - [0.0, 0.0]
    - [0.5, 0.0]
    - [1.0, 0.0]
    - [1.5, 0.0]
```

### Circular Array

```
       [SDR #0]
           |
   [SDR #3]   [SDR #1]
           |
       [SDR #2]
```

**Advantages:**
- Excellent 360° coverage
- No geometric bias

**Disadvantages:**
- More complex to construct
- Requires precise positioning

## Element Spacing

**Rule of Thumb:** Spacing should be **0.4λ to 0.6λ** at the frequency of interest.

| Frequency | Wavelength (λ) | Recommended Spacing |
|-----------|----------------|---------------------|
| 146 MHz (2m) | 2.05m | 0.5m - 1.0m |
| 435 MHz (70cm) | 0.69m | 0.3m - 0.4m |
| 915 MHz (ISM) | 0.33m | 0.15m - 0.2m |

**For Multi-Band Arrays:**
- Use spacing optimized for **lowest frequency**
- 0.5m spacing works well for 2m/70cm dual-band

**Spacing Too Small:** Phase ambiguity, grating lobes  
**Spacing Too Large:** Reduced angular resolution

## Physical Setup

### Step 1: Construct Array Frame

**Materials:**
- PVC pipe or wood frame
- Clamps or zip ties for SDR mounting
- Weatherproof enclosure (for outdoor use)

**Construction:**
1. Build frame to maintain **consistent spacing**
2. Mark antenna positions clearly
3. Ensure frame is **rigid** (flex causes phase errors)
4. Add cable management for USB and antenna coax

### Step 2: Mount Antennas

1. Install V-dipole mounts at marked positions
2. Orient all antennas **identically**
3. Keep elements **away from metal** (>λ/4 clearance)
4. Route coax feeds to SDR dongles

### Step 3: Connect SDRs

1. Label each SDR: **SDR #0, #1, #2, #3**
2. Connect to **powered USB hub**
3. Keep USB cables **short and identical length**
4. Avoid USB 2.0 hubs (bandwidth issues)

### Step 4: Verify Hardware

```bash
# List USB devices
lsusb | grep Realtek

# Test each SDR
rtl_test -d 0
rtl_test -d 1
rtl_test -d 2
rtl_test -d 3

# Or use ReconRaven
python reconraven.py test sdr
```

## Calibration

### Why Calibrate?

DF arrays require **phase calibration** because:
- SDR dongles have slightly different oscillator phases
- USB cable lengths differ
- Antenna mounting introduces phase offsets

**Without calibration:** Bearing errors of ±30°+  
**With calibration:** Bearing errors of ±5° or better

### Calibration Methods

#### Method 1: Known Bearing (Most Accurate)

Use a transmitter at a **known bearing** for reference.

**Setup:**
1. Place transmitter 50-100m away at known compass bearing
2. Use handheld radio on simplex frequency (146.52 MHz)
3. Transmit continuously during calibration

**Run Calibration:**
```bash
python reconraven.py test df-cal --freq 146.52 --bearing 45
```

**Example Output:**
```
Detected SDRs: 4
Calibration Frequency: 146.520 MHz
Known Bearing: 45°

CALIBRATION SUCCESSFUL!
Method: Cross-correlation with known bearing 45°
Coherence: 0.87 (>0.7 is good)
SNR: 23.4 dB

Phase Offsets (radians):
  SDR #0: +0.0000 rad (+0.0°)   [Reference]
  SDR #1: -0.2341 rad (-13.4°)
  SDR #2: +0.1532 rad (+8.8°)
  SDR #3: -0.0921 rad (-5.3°)

✓ EXCELLENT coherence - Array is well synchronized
✓ STRONG signal - Calibration very reliable
```

#### Method 2: Ambient Noise (Convenient)

Use a **strong local signal** (FM broadcast, repeater).

**Setup:**
1. Tune to strong local FM station or amateur repeater
2. No transmitter needed

**Run Calibration:**
```bash
python reconraven.py test df-cal --freq 146.52
```

**Less accurate than known bearing, but acceptable for initial setup.**

### Calibration Quality Metrics

**Coherence Score (0.0 - 1.0):**
- **>0.8**: Excellent - Array is well synchronized
- **0.7-0.8**: Good - Usable for DF
- **<0.7**: Poor - Check connections and spacing

**SNR (Signal-to-Noise Ratio):**
- **>15 dB**: Strong signal - Reliable calibration
- **10-15 dB**: Good signal - Acceptable
- **<10 dB**: Weak signal - Recalibrate with stronger source

### When to Recalibrate

Recalibrate when:
- **Hardware changes** (new SDR, antenna, cable)
- **Array moved** or geometry changed
- **Temperature changes** (>20°C difference)
- **Poor DF accuracy** (bearings consistently off)

## Verification

### Test DF Accuracy

1. **Use Known Transmitter:**
   ```bash
   # Start scanner with dashboard
   python reconraven.py scan --dashboard
   
   # Transmit from known location
   # Check bearing on dashboard
   ```

2. **Compare with Compass:**
   - Take visual bearing with compass
   - Compare to ReconRaven bearing
   - Should agree within ±5° for good calibration

3. **Triangulation Test:**
   - Take bearings from 2-3 different locations
   - Plot bearing lines on map
   - Lines should intersect at transmitter

### Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| Coherence <0.7 | Loose connections | Check all RF connectors |
| Bearings off by ~90° | Array orientation wrong | Verify element positions in config |
| 180° ambiguity | Linear array | Use square/circular array |
| Bearings jump randomly | RF coupling | Increase spacing or add ferrite |
| Low SNR | Weak signal | Use stronger cal source |

## Dashboard DF Display

Once calibrated, the dashboard shows:

**Direction Finding Panel:**
- **Compass visualization** with bearing arrow
- **Recent bearings list** with frequencies
- **Confidence scores** (0.0-1.0)
- **Array health indicator**

**Example Display:**
```
🧭 DIRECTION FINDING
━━━━━━━━━━━━━━━━━━━━━━━━━

    Compass [Visual with arrow at 45°]

📡 Recent Bearings:
┌──────────────┬──────────┬────────────┐
│ Frequency    │ Bearing  │ Confidence │
├──────────────┼──────────┼────────────┤
│ 146.520 MHz  │ 45°      │ 0.91       │
│ 433.920 MHz  │ 135°     │ 0.78       │
│ 915.800 MHz  │ 270°     │ 0.85       │
└──────────────┴──────────┴────────────┘

Array Status: ✓ Calibrated (Coherence: 0.87)
```

## Advanced Topics

### GPS Integration

Add GPS for:
- **Geo-tagged bearings** (lat/lon + bearing)
- **Triangulation** across multiple measurement points
- **Mapping** signal sources

**Setup:**
```yaml
# config/hardware.yaml
gps:
  enabled: true
  device: "/dev/ttyUSB0"  # Linux
  min_satellites: 4
```

### Array Orientation

For **absolute bearings** (true north), you need to know array orientation:

1. **Method 1: Compass**
   - Mount compass on array frame
   - Record heading when calibrating

2. **Method 2: GPS Track**
   - Move array in known direction
   - Calculate heading from GPS track

3. **Method 3: Known Transmitter**
   - Use transmitter at known absolute bearing
   - Calibrate with `--bearing` option

### Multi-Frequency Calibration

For **wideband DF** (2m + 70cm + ISM), calibrate at multiple frequencies:

```bash
# Calibrate for 2m band
python reconraven.py test df-cal --freq 146.52

# Calibrate for 70cm band  
python reconraven.py test df-cal --freq 435.0

# System interpolates for other frequencies
```

## Summary Checklist

- [ ] Obtain 4 RTL-SDR V4 dongles
- [ ] Print 4x V-dipole antenna mounts
- [ ] Assemble antennas with correct element lengths
- [ ] Build array frame with 0.5m spacing
- [ ] Mount antennas in square array configuration
- [ ] Connect SDRs to powered USB hub
- [ ] Label SDRs #0-3 clearly
- [ ] Update `config/hardware.yaml` with array geometry
- [ ] Run `python reconraven.py test sdr` to verify detection
- [ ] Run `python reconraven.py test df-cal --freq 146.52 --bearing 45`
- [ ] Verify coherence >0.7 and SNR >10 dB
- [ ] Test with known transmitter
- [ ] Start scanning with `python reconraven.py scan --dashboard`
- [ ] Verify DF display shows bearings

## References

- [3D Printed V-Dipole Mount (MyMiniFactory)](https://www.myminifactory.com/object/3d-print-120-degree-v-dipole-guide-133341)
- [MUSIC Algorithm (Wikipedia)](https://en.wikipedia.org/wiki/MUSIC_(algorithm))
- [RTL-SDR Direction Finding](https://www.rtl-sdr.com/tag/direction-finding/)
- [Antenna Array Theory](https://en.wikipedia.org/wiki/Antenna_array)

---

**Questions or issues?** Check `docs/TROUBLESHOOTING.md` or open an issue on GitHub.

