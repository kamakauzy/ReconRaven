# ReconRaven Systemd Services

Systemd service files for autostart on Raspberry Pi.

## Installation

```bash
# Copy service files
sudo cp systemd/*.service /etc/systemd/system/

# Enable services
sudo systemctl enable reconraven-api.service
sudo systemctl enable reconraven-touch.service

# Start services
sudo systemctl start reconraven-api
sudo systemctl start reconraven-touch

# Check status
sudo systemctl status reconraven-api
sudo systemctl status reconraven-touch

# View logs
sudo journalctl -u reconraven-api -f
sudo journalctl -u reconraven-touch -f
```

## Services

### reconraven-api.service
- Starts the REST API server on boot
- Listens on `http://localhost:5001`
- Auto-restarts on failure

### reconraven-touch.service
- Starts the touchscreen UI on boot
- Requires graphical.target (X11)
- Connects to API at localhost:5001

## Notes

- Edit `User=pi` if running as different user
- Edit `/home/pi/ReconRaven` paths to match your installation
- Touchscreen service requires X11/Wayland display server
- API service can run headless

## Troubleshooting

**Touch app doesn't start:**
```bash
# Check display
echo $DISPLAY  # Should be :0

# Test manually
DISPLAY=:0 python3 touch_app/main.py
```

**API key issues:**
```bash
# Check API key file
cat config/api_key.txt

# Regenerate
rm config/api_key.txt config/api_config.yaml
sudo systemctl restart reconraven-api
```

