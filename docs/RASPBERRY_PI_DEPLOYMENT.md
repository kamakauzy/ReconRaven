# ReconRaven Raspberry Pi Deployment Guide

Complete guide for deploying ReconRaven on Raspberry Pi 5 with touchscreen.

---

## Table of Contents

1. [Hardware Assembly](#hardware-assembly)
2. [Operating System Setup](#operating-system-setup)
3. [System Dependencies](#system-dependencies)
4. [ReconRaven Installation](#reconraven-installation)
5. [Location Database Setup](#location-database-setup)
6. [Autostart Configuration](#autostart-configuration)
7. [Testing & Validation](#testing--validation)
8. [Troubleshooting](#troubleshooting)
9. [Field Operations](#field-operations)

---

## Hardware Assembly

### Parts Checklist

Before starting, ensure you have:

- [ ] Raspberry Pi 5 (16GB recommended)
- [ ] Official 7" Touchscreen Display (800x480)
- [ ] SmartiPi Touch 2 Case
- [ ] 4x RTL-SDR Blog V4 dongles
- [ ] 4x Nagoya NA-771 dual-band antennas
- [ ] RSHTECH 4-port powered USB hub
- [ ] VK-162 USB GPS dongle
- [ ] 256GB microSD card (A2 speed class)
- [ ] 45W USB-C power supply
- [ ] 20,000+ mAh power bank (field operations)

### Assembly Steps

**Estimated Time:** 2 hours

1. **SmartiPi Case Assembly** (30 minutes)
   - Follow SmartiPi Touch 2 instructions
   - Connect touchscreen ribbon cable to Pi before mounting
   - Install Pi 5 into case standoffs
   - Secure with provided screws

2. **SDR Hub Setup** (20 minutes)
   - Connect USB hub to one of Pi's USB 3.0 ports
   - Plug 4x RTL-SDR dongles into hub
   - Attach antennas to each SDR
   - **IMPORTANT:** Keep SDRs separated by 2-3 inches minimum
   - Use velcro to mount hub to case exterior

3. **GPS Installation** (10 minutes)
   - Plug VK-162 GPS into Pi's remaining USB port (not the hub!)
   - Position GPS module with clear sky view
   - Secure with adhesive or velcro

4. **Power Configuration** (15 minutes)
   - Connect Pi power to 45W USB-C supply
   - Connect USB hub barrel jack to 5V power
   - For field ops: use USB-to-barrel adapter from power bank

5. **Cable Management** (15 minutes)
   - Route antenna cables away from USB cables
   - Use zip ties or velcro straps
   - Ensure no cables block fan vents
   - Leave antenna connectors accessible for swaps

---

## Operating System Setup

### 1. Flash Raspberry Pi OS

**Use:** Raspberry Pi Imager (https://www.raspberrypi.com/software/)

**Recommended OS:** Raspberry Pi OS (64-bit) with Desktop
- **Image:** `2024-11-19-raspios-bookworm-arm64.img` or newer
- **Size:** 8GB+ SD card minimum, 256GB recommended

**Imaging Steps:**

1. Launch Raspberry Pi Imager
2. Choose Device: **Raspberry Pi 5**
3. Choose OS: **Raspberry Pi OS (64-bit)**
4. Choose Storage: Select your microSD card
5. Click ⚙️ (Settings) to configure:
   - ✅ Set hostname: `reconraven`
   - ✅ Enable SSH (password authentication)
   - ✅ Set username: `pi`, password: `<your-password>`
   - ✅ Configure wireless LAN (if using WiFi)
   - ✅ Set locale: Your timezone
6. Write and wait (~10 minutes)

### 2. First Boot Configuration

Insert SD card, connect power, wait for boot (2-3 minutes).

**Initial Setup:**

```bash
# SSH into Pi (if headless)
ssh pi@reconraven.local

# Or use touchscreen directly

# Update system
sudo apt update && sudo apt upgrade -y
# Reboot if kernel updated
sudo reboot

# Enable interfaces
sudo raspi-config
# Navigate to: Interface Options
# Enable: SPI, I2C, Serial Port (GPS)
# Disable: Serial Console
```

### 3. Configure Touchscreen

```bash
# Test touchscreen
sudo apt install xinput-calibrator
DISPLAY=:0 xinput_calibrator

# If rotation needed
sudo nano /boot/firmware/config.txt
# Add line: display_lcd_rotate=2    # 180 degrees if needed

# Auto-hide mouse cursor (clean UI)
sudo apt install unclutter
echo "unclutter -idle 0.1 &" >> ~/.config/lxsession/LXDE-pi/autostart
```

---

## System Dependencies

### 1. Core System Packages

```bash
# RTL-SDR drivers and tools
sudo apt install -y rtl-sdr librtlsdr-dev

# Python development
sudo apt install -y python3-pip python3-dev python3-venv

# Audio/Video processing
sudo apt install -y ffmpeg libsndfile1 sox

# GPS support
sudo apt install -y gpsd gpsd-clients

# Build tools (for Python packages)
sudo apt install -y build-essential cmake pkg-config
sudo apt install -y libffi-dev libssl-dev
sudo apt install -y libblas-dev liblapack-dev gfortran

# Kivy dependencies
sudo apt install -y libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev
sudo apt install -y libgstreamer1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-good
sudo apt install -y libmtdev-dev xclip
```

**Estimated time:** 20-30 minutes

### 2. Configure GPSD

```bash
# Edit GPSD config
sudo nano /etc/default/gpsd

# Change to:
START_DAEMON="true"
USBAUTO="true"
DEVICES="/dev/ttyACM0"  # VK-162 GPS default
GPSD_OPTIONS="-n -G"

# Restart GPSD
sudo systemctl enable gpsd
sudo systemctl start gpsd

# Test GPS
cgps -s
# Wait 30-60 seconds for satellite fix
# Should show lat/lon when locked
```

### 3. RTL-SDR Permissions

```bash
# Add user to plugdev group
sudo usermod -a -G plugdev pi

# Create udev rules
sudo nano /etc/udev/rules.d/20-rtlsdr.rules

# Add:
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", MODE="0666"

# Reload udev
sudo udevadm control --reload-rules
sudo udevadm trigger

# Logout and login (or reboot)
```

---

## ReconRaven Installation

### 1. Clone Repository

```bash
cd ~
git clone https://github.com/kamakauzy/ReconRaven.git
cd ReconRaven
```

### 2. Create Virtual Environment

```bash
# Create venv
python3 -m venv venv

# Activate
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### 3. Install Python Dependencies

```bash
# Install ReconRaven requirements
pip install -r requirements.txt

# This will take 30-45 minutes on Pi 5
# Includes: numpy, scipy, flask, kivy, whisper, etc.
```

**Common Issues:**

If `numpy` or `scipy` fail to build:
```bash
# Use pre-compiled wheels
pip install numpy scipy --extra-index-url https://www.piwheels.org/simple
```

If `kivy` fails:
```bash
# Install kivy from piwheels
pip install kivy kivymd --extra-index-url https://www.piwheels.org/simple
```

### 4. Download Whisper Models (Optional, Recommended)

```bash
# Pre-download models for offline use
python3 -c "import whisper; whisper.load_model('base')"
python3 -c "import whisper; whisper.load_model('small')"

# Takes ~10 minutes, ~3GB download
```

### 5. Test Installation

```bash
# Activate venv
source ~/ReconRaven/venv/bin/activate

# Test SDR detection
python3 reconraven.py test sdr
# Expected: Should detect 4 SDRs

# Test RF environment
python3 reconraven.py test noise
# Expected: < -20 dBm noise floor on all bands

# Quick API test
cd api
python3 server.py &
curl http://localhost:5001/api/v1/health
# Expected: {"status": "healthy", "api_version": "1.0.0"}
pkill -f "python.*server.py"
```

---

## Location Database Setup

### One-Time Setup (Requires Internet)

```bash
# Activate venv
source ~/ReconRaven/venv/bin/activate
cd ~/ReconRaven

# Option 1: Auto-detect location
python3 -c "
from reconraven.location.detector import LocationDetector
from reconraven.location.repeaterbook import RepeaterBookClient
from reconraven.location.noaa import NOAAStations

detector = LocationDetector()
location = detector.auto_detect()

if location:
    print(f'Detected: {location[\"city\"]}, {location[\"state_code\"]}')
    
    # Import repeaters
    client = RepeaterBookClient()
    count = client.setup_state(location['state_code'])
    print(f'Imported {count} repeaters')
    
    # Import NOAA stations
    noaa = NOAAStations()
    noaa.import_all_stations()
    print('Imported NOAA stations')
else:
    print('Location detection failed. Use manual setup.')
"

# Option 2: Manual setup
python3 -c "
from reconraven.location.repeaterbook import RepeaterBookClient
from reconraven.location.noaa import NOAAStations

# Replace with your state
client = RepeaterBookClient()
count = client.setup_state('AL')  # Change 'AL' to your state
print(f'Imported {count} repeaters')

noaa = NOAAStations()
noaa.import_all_stations()
print('Imported NOAA stations')
"
```

**Verify Import:**

```bash
python3 -c "
from reconraven.location.database import get_location_db
db = get_location_db()
stats = db.get_stats()
print(f'Repeaters: {stats[\"repeaters\"]}')
print(f'NOAA: {stats[\"noaa_stations\"]}')
print(f'Total: {stats[\"total\"]}')
"
```

**After this step, ReconRaven works 100% offline!**

---

## Autostart Configuration

### 1. Generate API Key

```bash
source ~/ReconRaven/venv/bin/activate
cd ~/ReconRaven

# Start API once to generate key
python3 api/server.py &
sleep 5
pkill -f "python.*server.py"

# Save API key
cat config/api_key.txt
# Copy this key for later
```

### 2. Install Systemd Services

```bash
cd ~/ReconRaven/systemd

# Edit service files to match your paths
nano reconraven-api.service
# Change User= and WorkingDirectory= if needed
# Change ExecStart= to use venv python:
#   ExecStart=/home/pi/ReconRaven/venv/bin/python3 /home/pi/ReconRaven/api/server.py

nano reconraven-touch.service
# Same edits as above
#   ExecStart=/home/pi/ReconRaven/venv/bin/python3 /home/pi/ReconRaven/touch_app/main.py

# Copy to systemd
sudo cp reconraven-api.service /etc/systemd/system/
sudo cp reconraven-touch.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable reconraven-api
sudo systemctl enable reconraven-touch

# Start services
sudo systemctl start reconraven-api
sudo systemctl start reconraven-touch

# Check status
sudo systemctl status reconraven-api
sudo systemctl status reconraven-touch
```

### 3. Verify Autostart

```bash
# Reboot to test
sudo reboot

# After reboot, check services
sudo systemctl status reconraven-api
sudo systemctl status reconraven-touch

# Touch app should appear on screen after ~30 seconds
# API should be accessible
curl http://localhost:5001/api/v1/health
```

---

## Testing & Validation

### Full System Test

```bash
source ~/ReconRaven/venv/bin/activate
cd ~/ReconRaven

# 1. Hardware check
python3 reconraven.py test sdr
# Expected: 4 SDRs detected

# 2. GPS check
cgps -s
# Expected: GPS fix with lat/lon

# 3. RF environment
python3 reconraven.py test noise
# Expected: Noise floor < -20 dBm on all bands

# 4. Test known frequency (have someone transmit on 146.52 MHz)
python3 reconraven.py test freq --freq 146.52 --duration 60
# Expected: Clear signal spike during transmission

# 5. Touch app test
DISPLAY=:0 python3 touch_app/main.py
# Expected: UI appears on touchscreen

# 6. API test
curl http://localhost:5001/api/v1/health
curl -H "X-API-KEY: <your-api-key>" http://localhost:5001/api/v1/scan/status
# Expected: JSON responses
```

### Performance Benchmarks

**On Raspberry Pi 5 (16GB):**

- Scanner startup: 10-15 seconds
- 4-SDR parallel scanning: No CPU throttling
- Touch UI response time: < 100ms
- Whisper base model transcription: 2-3x realtime
- Memory usage: ~4GB (with 4 SDRs + UI + API)
- Storage: ~100GB for OS + 150GB for recordings

---

## Troubleshooting

### Touch App Won't Start

```bash
# Check display
echo $DISPLAY
# Should be :0

# Test manually
DISPLAY=:0 python3 touch_app/main.py

# Check logs
sudo journalctl -u reconraven-touch -n 50

# Common fix: Set DISPLAY in service file
sudo nano /etc/systemd/system/reconraven-touch.service
# Add: Environment=DISPLAY=:0
sudo systemctl daemon-reload
sudo systemctl restart reconraven-touch
```

### API Connection Errors

```bash
# Check API is running
sudo systemctl status reconraven-api

# Check port
netstat -tuln | grep 5001

# Regenerate API key
rm ~/ReconRaven/config/api_key.txt
rm ~/ReconRaven/config/api_config.yaml
sudo systemctl restart reconraven-api
cat ~/ReconRaven/config/api_key.txt
```

### SDRs Not Detected

```bash
# Check USB
lsusb | grep Realtek
# Should show 4x "Realtek Semiconductor Corp. RTL2838"

# Check permissions
groups
# Should include 'plugdev'

# Test with rtl_test
rtl_test -t
# Should detect all SDRs without errors

# Power issue?
# Try powered USB hub or separate power supply
```

### GPS Not Working

```bash
# Check device
ls -l /dev/ttyACM*
# Should show /dev/ttyACM0

# Check GPSD
sudo systemctl status gpsd

# Test GPS
cgps -s
# Wait 60 seconds for satellite lock

# Restart GPSD
sudo systemctl restart gpsd
```

### High CPU / Thermal Throttling

```bash
# Check temp
vcgencmd measure_temp
# Should be < 70°C under load

# Check throttling
vcgencmd get_throttled
# 0x0 = good, anything else = throttling

# Solutions:
# 1. Install active cooling (fan)
# 2. Reduce scan rate in config/hardware.yaml
# 3. Scan fewer bands simultaneously
# 4. Use Whisper 'tiny' or 'base' model (not 'large')
```

### Slow Performance

```bash
# Check SD card speed
sudo hdparm -t /dev/mmcblk0
# Should be > 40 MB/s

# Check swap
free -h
# If swap in use, consider increasing

# Optimize:
sudo nano /boot/firmware/config.txt
# Add: over_voltage=2
# Add: arm_freq=2400
sudo reboot
```

---

## Field Operations

### Pre-Mission Checklist

```bash
# 1. Check battery
# Power bank should be > 80%

# 2. Verify GPS lock
cgps -s
# Should get fix within 60 seconds outdoors

# 3. Test RF environment
python3 reconraven.py test noise
# Noise floor should be clean

# 4. Verify services
sudo systemctl status reconraven-api reconraven-touch

# 5. Check storage space
df -h
# Should have > 20GB free for recordings
```

### Battery Life Estimates

**Configuration: Pi 5 + 4 SDRs + 7" Display + GPS**

- 20,000 mAh power bank: **3-4 hours**
- 25,000 mAh power bank: **4-5 hours**
- 30,000 mAh power bank: **5-6 hours**

**Optimization tips:**
- Reduce screen brightness
- Disable WiFi if not needed: `sudo rfkill block wifi`
- Lower scan rate in config
- Use 1-2 SDRs instead of 4

### Remote Access (Optional)

```bash
# Enable SSH (already enabled if configured in imager)
sudo systemctl status ssh

# Find IP
hostname -I

# From laptop:
ssh pi@<pi-ip-address>
# Or: ssh pi@reconraven.local

# Access dashboard remotely
http://<pi-ip-address>:5001/api/v1/
```

### Backup Before Mission

```bash
# Backup database
cp ~/ReconRaven/reconraven.db ~/reconraven_backup_$(date +%Y%m%d).db

# Backup location database
cp ~/ReconRaven/location_frequencies.db ~/location_backup_$(date +%Y%m%d).db

# Copy to external storage
# (Insert USB drive, should mount to /media/pi/*)
cp ~/reconraven_backup*.db /media/pi/YOUR_DRIVE/
```

---

## Next Steps

✅ Your Raspberry Pi is now ready for ReconRaven deployment!

**Recommended:**

1. Run initial baseline scan (10-15 minutes)
2. Familiarize yourself with touch UI
3. Test RF environment per `docs/RF_SETUP_GUIDE.md`
4. Practice field deployment at home first
5. Read `docs/DF_SETUP_GUIDE.md` for direction finding

**Questions?**

- Check main `README.md`
- Review `docs/RF_SETUP_GUIDE.md`
- Check GitHub issues

**Ready to scan!** 🚀

