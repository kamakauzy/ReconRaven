#!/bin/bash
#
# ReconRaven Pi Quick Setup Script
# 
# Automated installation and configuration for Raspberry Pi.
# Designed to work with pre-downloaded deployment kit.
#
# Usage: bash pi_quick_setup.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
LOG_FILE="/var/log/reconraven_setup.log"
sudo touch "$LOG_FILE"
sudo chmod 666 "$LOG_FILE"

# Helper functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_step() {
    echo -e "${BLUE}[*]${NC} $1..."
    echo "[$(date)] [STEP] $1" >> "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    echo "[$(date)] [SUCCESS] $1" >> "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
    echo "[$(date)] [ERROR] $1" >> "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
    echo "[$(date)] [WARNING] $1" >> "$LOG_FILE"
}

ask_confirm() {
    local prompt="$1"
    local default="${2:-y}"
    
    if [ "$default" = "y" ]; then
        read -p "$prompt [Y/n]: " response
        response=${response:-y}
    else
        read -p "$prompt [y/N]: " response
        response=${response:-n}
    fi
    
    [[ "$response" =~ ^[Yy]$ ]]
}

# Check if running as non-root
if [ "$EUID" -eq 0 ]; then
    print_error "Do not run this script as root. Run as regular user (pi)."
    exit 1
fi

# Check if deployment kit exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIT_DIR="$(dirname "$SCRIPT_DIR")"

if [ ! -d "$KIT_DIR" ] || [ ! -f "$KIT_DIR/deployment_manifest.json" ]; then
    print_error "Deployment kit not found!"
    echo "Expected location: $KIT_DIR"
    echo "Make sure you've copied the pi_deployment_kit folder to the Pi."
    exit 1
fi

print_header "ReconRaven Pi Quick Setup"

echo "This script will install and configure ReconRaven on your Raspberry Pi."
echo "Estimated time: 45-60 minutes (mostly unattended)"
echo ""
echo "Deployment kit found: $KIT_DIR"
echo "Log file: $LOG_FILE"
echo ""

if ! ask_confirm "Ready to proceed?"; then
    echo "Setup cancelled."
    exit 0
fi

# Get user input
print_header "Configuration"

read -p "Enter WiFi SSID (leave empty if already configured): " WIFI_SSID
if [ -n "$WIFI_SSID" ]; then
    read -sp "Enter WiFi Password: " WIFI_PASSWORD
    echo ""
fi

read -p "Enter timezone [America/Chicago]: " TIMEZONE
TIMEZONE=${TIMEZONE:-America/Chicago}

ENABLE_AUTOSTART=true
if ask_confirm "Enable autostart services (API + Touch UI)?"; then
    ENABLE_AUTOSTART=true
else
    ENABLE_AUTOSTART=false
fi

# Start installation
print_header "System Update"

print_step "Updating package lists"
sudo apt update >> "$LOG_FILE" 2>&1
print_success "Package lists updated"

# Optional: Full upgrade (commented out by default for speed)
# print_step "Upgrading system packages (this may take a while)"
# sudo apt upgrade -y >> "$LOG_FILE" 2>&1
# print_success "System upgraded"

# Configure WiFi if requested
if [ -n "$WIFI_SSID" ]; then
    print_step "Configuring WiFi"
    
    sudo tee /etc/wpa_supplicant/wpa_supplicant.conf > /dev/null <<EOF
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="$WIFI_SSID"
    psk="$WIFI_PASSWORD"
}
EOF
    
    sudo systemctl restart dhcpcd
    sleep 5  # Wait for connection
    print_success "WiFi configured"
fi

# Set timezone
print_step "Setting timezone to $TIMEZONE"
sudo timedatectl set-timezone "$TIMEZONE" >> "$LOG_FILE" 2>&1
print_success "Timezone set"

# Install system dependencies
print_header "Installing System Dependencies"

print_step "Installing RTL-SDR drivers and tools (2-3 minutes)"
sudo apt install -y rtl-sdr librtlsdr-dev >> "$LOG_FILE" 2>&1
print_success "RTL-SDR installed"

print_step "Installing Python development tools (2-3 minutes)"
sudo apt install -y python3-pip python3-dev python3-venv >> "$LOG_FILE" 2>&1
print_success "Python tools installed"

print_step "Installing audio/video processing tools (3-5 minutes)"
sudo apt install -y ffmpeg libsndfile1 sox >> "$LOG_FILE" 2>&1
print_success "Audio/video tools installed"

print_step "Installing GPS support (1-2 minutes)"
sudo apt install -y gpsd gpsd-clients >> "$LOG_FILE" 2>&1
print_success "GPS tools installed"

print_step "Installing build tools (5-7 minutes)"
sudo apt install -y build-essential cmake pkg-config \
    libffi-dev libssl-dev libblas-dev liblapack-dev gfortran >> "$LOG_FILE" 2>&1
print_success "Build tools installed"

print_step "Installing Kivy dependencies (5-7 minutes)"
sudo apt install -y libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
    libgstreamer1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    libmtdev-dev xclip >> "$LOG_FILE" 2>&1
print_success "Kivy dependencies installed"

# Configure GPSD
print_step "Configuring GPSD for USB GPS"
sudo tee /etc/default/gpsd > /dev/null <<EOF
START_DAEMON="true"
USBAUTO="true"
DEVICES="/dev/ttyACM0"
GPSD_OPTIONS="-n -G"
EOF

sudo systemctl enable gpsd >> "$LOG_FILE" 2>&1
sudo systemctl start gpsd >> "$LOG_FILE" 2>&1
print_success "GPSD configured"

# Configure RTL-SDR permissions
print_step "Configuring RTL-SDR permissions"
sudo usermod -a -G plugdev "$USER"

sudo tee /etc/udev/rules.d/20-rtlsdr.rules > /dev/null <<EOF
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", MODE="0666"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger
print_success "RTL-SDR permissions configured"

# Clone/Setup ReconRaven
print_header "ReconRaven Installation"

INSTALL_DIR="$HOME/ReconRaven"

if [ -d "$INSTALL_DIR" ]; then
    print_warning "ReconRaven directory already exists at $INSTALL_DIR"
    if ask_confirm "Remove and re-clone?" "n"; then
        rm -rf "$INSTALL_DIR"
    else
        print_error "Aborting to avoid overwriting existing installation"
        exit 1
    fi
fi

print_step "Cloning ReconRaven repository"
cd "$HOME"
git clone https://github.com/kamakauzy/ReconRaven.git >> "$LOG_FILE" 2>&1
cd "$INSTALL_DIR"
print_success "Repository cloned"

# Create virtual environment
print_step "Creating Python virtual environment (1-2 minutes)"
python3 -m venv venv >> "$LOG_FILE" 2>&1
source venv/bin/activate
pip install --upgrade pip setuptools wheel >> "$LOG_FILE" 2>&1
print_success "Virtual environment created"

# Install Python packages
print_step "Installing Python packages (20-30 minutes - longest step!)"
echo "This will take a while. Perfect time for coffee ☕"

if [ -f "$KIT_DIR/python_packages/requirements_piwheels.txt" ]; then
    print_step "Using piwheels-optimized requirements"
    pip install -r "$KIT_DIR/python_packages/requirements_piwheels.txt" >> "$LOG_FILE" 2>&1
else
    pip install -r requirements.txt >> "$LOG_FILE" 2>&1
fi
print_success "Python packages installed"

# Import Whisper models
if [ -d "$KIT_DIR/whisper_models" ]; then
    print_step "Importing Whisper models"
    
    WHISPER_CACHE="$HOME/.cache/whisper"
    mkdir -p "$WHISPER_CACHE"
    
    cp "$KIT_DIR/whisper_models"/*.pt "$WHISPER_CACHE/" 2>/dev/null || true
    
    model_count=$(ls -1 "$WHISPER_CACHE"/*.pt 2>/dev/null | wc -l)
    print_success "Imported $model_count Whisper models"
fi

# Import location database
if [ -f "$KIT_DIR/location_data/location_frequencies.db" ]; then
    print_step "Importing location database"
    
    cp "$KIT_DIR/location_data/location_frequencies.db" "$INSTALL_DIR/"
    
    print_success "Location database imported"
fi

# Import API configuration
if [ -d "$KIT_DIR/config" ]; then
    print_step "Importing API configuration"
    
    mkdir -p "$INSTALL_DIR/config"
    cp "$KIT_DIR/config/api_config.yaml" "$INSTALL_DIR/config/" 2>/dev/null || true
    cp "$KIT_DIR/config/api_key.txt" "$INSTALL_DIR/config/" 2>/dev/null || true
    
    print_success "API configuration imported"
fi

# Copy test data
if [ -d "$KIT_DIR/test_data" ]; then
    print_step "Copying test data"
    
    mkdir -p "$INSTALL_DIR/recordings/audio"
    cp "$KIT_DIR/test_data"/*.npy "$INSTALL_DIR/recordings/audio/" 2>/dev/null || true
    
    print_success "Test data copied"
fi

# Configure systemd services
if [ "$ENABLE_AUTOSTART" = true ]; then
    print_header "Configuring Autostart Services"
    
    print_step "Creating systemd service files"
    
    # API service
    sudo tee /etc/systemd/system/reconraven-api.service > /dev/null <<EOF
[Unit]
Description=ReconRaven REST API Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/api/server.py
Restart=always
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Touch UI service
    sudo tee /etc/systemd/system/reconraven-touch.service > /dev/null <<EOF
[Unit]
Description=ReconRaven Touchscreen Application
After=network.target graphical.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment=DISPLAY=:0
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/touch_app/main.py
Restart=always
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical.target
EOF

    sudo systemctl daemon-reload
    
    print_step "Enabling services"
    sudo systemctl enable reconraven-api >> "$LOG_FILE" 2>&1
    sudo systemctl enable reconraven-touch >> "$LOG_FILE" 2>&1
    
    print_step "Starting API service"
    sudo systemctl start reconraven-api >> "$LOG_FILE" 2>&1
    sleep 3
    
    print_success "Services configured and enabled"
fi

# Run validation
print_header "System Validation"

print_step "Running validation tests"

# Test SDR detection
print_step "Testing SDR detection"
if rtl_test -t 2>&1 | grep -q "Found"; then
    sdr_count=$(rtl_test -t 2>&1 | grep "Found" | wc -l)
    print_success "Detected $sdr_count SDR(s)"
else
    print_warning "No SDRs detected - make sure they're plugged in"
fi

# Test GPS
print_step "Testing GPS (waiting 15 seconds for fix)"
timeout 15 cgps -s >> "$LOG_FILE" 2>&1 || true
if timeout 2 cgps -s 2>&1 | grep -q "3D"; then
    print_success "GPS has 3D fix"
elif timeout 2 cgps -s 2>&1 | grep -q "2D"; then
    print_success "GPS has 2D fix"
else
    print_warning "GPS has no fix yet (may need more time/sky view)"
fi

# Test API
if [ "$ENABLE_AUTOSTART" = true ]; then
    print_step "Testing API connection"
    sleep 2
    if curl -s http://localhost:5001/api/v1/health | grep -q "healthy"; then
        print_success "API is responding"
    else
        print_warning "API not responding yet (may need more time)"
    fi
fi

# Test Python imports
print_step "Testing Python imports"
source "$INSTALL_DIR/venv/bin/activate"
if python3 -c "import reconraven; import numpy; import scipy; import flask; import kivy" 2>> "$LOG_FILE"; then
    print_success "All Python imports successful"
else
    print_warning "Some Python imports failed - check log"
fi

# Print summary
print_header "Setup Complete!"

echo -e "${GREEN}ReconRaven has been successfully installed and configured!${NC}"
echo ""
echo "Installation directory: $INSTALL_DIR"
echo "Virtual environment: $INSTALL_DIR/venv"
echo ""

if [ "$ENABLE_AUTOSTART" = true ]; then
    echo "Services configured:"
    echo "  - reconraven-api (port 5001)"
    echo "  - reconraven-touch (touchscreen UI)"
    echo ""
    echo "Services will start automatically on boot."
    echo ""
fi

echo "Next steps:"
echo "  1. Reboot the Pi: sudo reboot"
if [ "$ENABLE_AUTOSTART" = true ]; then
    echo "  2. After reboot, touch UI should appear automatically"
    echo "  3. API accessible at: http://$(hostname -I | awk '{print $1}'):5001"
else
    echo "  2. Manually start API: cd $INSTALL_DIR && source venv/bin/activate && python3 api/server.py"
    echo "  3. Manually start Touch UI: cd $INSTALL_DIR && source venv/bin/activate && python3 touch_app/main.py"
fi
echo "  4. Run validation: cd $INSTALL_DIR && source venv/bin/activate && python3 scripts/validate_system.py"
echo ""

echo "Documentation:"
echo "  - Main README: $INSTALL_DIR/README.md"
echo "  - Pi Deployment Guide: $INSTALL_DIR/docs/RASPBERRY_PI_DEPLOYMENT.md"
echo "  - RF Setup Guide: $INSTALL_DIR/docs/RF_SETUP_GUIDE.md"
echo ""

echo "Setup log saved to: $LOG_FILE"
echo ""

if ask_confirm "Reboot now?"; then
    echo "Rebooting in 5 seconds..."
    sleep 5
    sudo reboot
else
    echo "Remember to reboot before starting!"
fi

