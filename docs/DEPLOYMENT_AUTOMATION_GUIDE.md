# Quick Start: Deployment Automation

**Time Savings:** Manual deployment ~6 hours → Automated ~1.5 hours = **4.5 hours saved!**

---

## On Your Laptop (Before Pi Arrives)

### 1. Run Preparation Script

```bash
cd ReconRaven
python3 scripts/prepare_pi_deployment.py
```

**Interactive prompts:**
- Your state code (e.g., AL): `AL`
- Your city (optional): `Huntsville`
- Download Whisper models? [Y/n]: `Y`
- Which models? (base/small/medium): `base,small`
- Generate test data? [Y/n]: `Y`

**What it does:** (~30 minutes)
- Downloads Whisper AI models (~3GB)
- Fetches repeater data for your state
- Imports NOAA weather stations
- Generates API keys
- Creates test recordings
- Packages everything

**Output:** `pi_deployment_kit/` folder (~5-8GB)

---

## Transfer to Pi

### Option A: SD Card (Recommended)

```bash
# On laptop with SD card mounted:
./scripts/pack_for_pi.sh /media/user/boot

# Script will:
# - Copy kit to /boot/pi_deployment_kit/
# - Create RECONRAVEN_SETUP.txt with instructions
```

Then boot Pi normally.

### Option B: USB Drive

```bash
# Copy to USB drive:
cp -r pi_deployment_kit /media/user/USB_DRIVE/

# Plug USB into Pi after boot
```

---

## On the Pi

### 1. Copy Kit to Home

```bash
# If from SD card:
cp -r /boot/pi_deployment_kit ~/

# If from USB:
cp -r /media/pi/USB_DRIVE/pi_deployment_kit ~/
```

### 2. Run Setup Script

```bash
cd ~/pi_deployment_kit/scripts
bash pi_quick_setup.sh
```

**Interactive prompts:**
- WiFi SSID: `MyNetwork` (skip if already configured)
- WiFi Password: `********`
- Timezone: `America/Chicago`
- Enable autostart services? [Y/n]: `Y`

**What it does:** (~45 minutes)
- Updates system
- Installs dependencies (RTL-SDR, Python, GPS, Kivy, etc.)
- Creates Python venv
- Installs Python packages (uses pre-downloaded when available)
- Imports Whisper models
- Sets up location database
- Configures systemd services
- Runs validation tests

### 3. Reboot

```bash
sudo reboot
```

After reboot:
- Touch UI appears automatically
- API runs on port 5001
- GPS starts tracking
- Ready to scan!

---

## Validation

To validate installation:

```bash
cd ~/ReconRaven
source venv/bin/activate
python3 scripts/validate_system.py
```

Tests:
- SDR detection (expects 4)
- GPS lock
- Python imports
- Database access
- Location database
- API health
- Whisper models
- Configuration files
- Systemd services
- Performance

Creates `validation_report.json` with detailed results.

---

## Troubleshooting

### Prep script fails on laptop

**Whisper download fails:**
```bash
pip install --upgrade openai-whisper
```

**Location database fails:**
- Check internet connection
- Verify state code is valid (two letters)

### Setup script fails on Pi

**Check logs:**
```bash
tail -f /var/log/reconraven_setup.log
```

**Python packages fail:**
```bash
# Use piwheels for pre-compiled packages:
source ~/ReconRaven/venv/bin/activate
pip install --extra-index-url https://www.piwheels.org/simple <package>
```

**Services don't start:**
```bash
# Check status:
sudo systemctl status reconraven-api
sudo journalctl -u reconraven-api -n 50

# Try manual start:
cd ~/ReconRaven
source venv/bin/activate
python3 api/server.py
```

### Re-run setup

Safe to re-run if interrupted:
```bash
cd ~/pi_deployment_kit/scripts
bash pi_quick_setup.sh
```

Script won't overwrite existing config unless you confirm.

---

## What Gets Automated

**Laptop side:**
- ✓ Whisper model downloads
- ✓ Location database creation
- ✓ API key generation
- ✓ Requirements optimization
- ✓ Test data creation
- ✓ Kit packaging

**Pi side:**
- ✓ System package installation
- ✓ Python environment setup
- ✓ Python package installation
- ✓ GPS configuration
- ✓ RTL-SDR permissions
- ✓ Whisper model import
- ✓ Location database import
- ✓ Systemd service creation
- ✓ Service enablement
- ✓ System validation

**What's still manual:**
- SD card flashing (use Pi Imager)
- Initial OS configuration (in Pi Imager)
- Copying deployment kit to Pi
- Rebooting

---

## File Structure

```
pi_deployment_kit/
├── README.txt                    # Instructions
├── whisper_models/
│   ├── base.pt                  # Whisper models
│   └── small.pt
├── location_data/
│   ├── location_frequencies.db  # Pre-built database
│   └── import_manifest.json
├── config/
│   ├── api_config.yaml          # API configuration
│   └── api_key.txt              # API key
├── python_packages/
│   ├── requirements.txt
│   └── requirements_piwheels.txt
├── test_data/
│   ├── sample_2m_signal.npy
│   └── sample_70cm_signal.npy
├── scripts/
│   ├── pi_quick_setup.sh        # Main setup script
│   └── validate_system.py       # Validation
└── deployment_manifest.json     # Kit metadata
```

---

## Benefits

**Time:**
- Manual: ~6 hours
- Automated: ~1.5 hours
- **Savings: 4.5 hours per deployment**

**Reliability:**
- Pre-validated downloads
- Consistent configuration
- Automatic error detection
- Resumable if interrupted

**Offline:**
- No internet needed on Pi
- All dependencies pre-downloaded
- Works in air-gapped environments

**Reproducible:**
- Same kit works on multiple Pis
- Consistent deployments
- Easy to troubleshoot

---

## Advanced Usage

### Custom Whisper Models

Edit prep script or download manually:
```bash
python3 -c "import whisper; whisper.load_model('medium')"
```

### Multiple States

Run prep script multiple times with different states, or manually combine databases.

### Offline Python Wheels

Download wheels on laptop with internet:
```bash
pip download -r requirements.txt -d pi_deployment_kit/python_packages/offline_wheels/
```

On Pi, install from local wheels:
```bash
pip install --no-index --find-links pi_deployment_kit/python_packages/offline_wheels/ -r requirements.txt
```

---

## Support

**Issues?**
- Check logs: `/var/log/reconraven_setup.log`
- Run validation: `python3 scripts/validate_system.py`
- Manual fallback: `docs/RASPBERRY_PI_DEPLOYMENT.md`

**Questions?**
- GitHub Issues
- Main README.md

---

**Ready to deploy!** 🚀

