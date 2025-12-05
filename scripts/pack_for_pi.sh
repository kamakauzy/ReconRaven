#!/bin/bash
#
# Pack deployment kit to SD card /boot partition
#
# Usage: ./scripts/pack_for_pi.sh /media/user/boot
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIT_DIR="$(dirname "$SCRIPT_DIR")/pi_deployment_kit"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[*]${NC} $1"
}

# Check arguments
if [ $# -ne 1 ]; then
    echo "Usage: $0 <boot-partition-path>"
    echo ""
    echo "Example:"
    echo "  $0 /media/$USER/boot"
    echo ""
    echo "Make sure SD card is mounted before running!"
    exit 1
fi

BOOT_PATH="$1"

# Validate boot path
if [ ! -d "$BOOT_PATH" ]; then
    print_error "Boot partition not found: $BOOT_PATH"
    echo ""
    echo "Mount your SD card and try again."
    echo "Common locations:"
    echo "  - Linux: /media/$USER/boot or /media/$USER/bootfs"
    echo "  - macOS: /Volumes/boot"
    exit 1
fi

# Check if deployment kit exists
if [ ! -d "$KIT_DIR" ]; then
    print_error "Deployment kit not found: $KIT_DIR"
    echo ""
    echo "Run prepare_pi_deployment.py first to create the kit."
    exit 1
fi

# Check free space
print_info "Checking available space..."
kit_size=$(du -sb "$KIT_DIR" | awk '{print $1}')
available=$(df "$BOOT_PATH" | tail -1 | awk '{print $4}')
available_bytes=$((available * 1024))

kit_size_mb=$((kit_size / 1024 / 1024))
available_mb=$((available_bytes / 1024 / 1024))

echo "  Kit size: ${kit_size_mb} MB"
echo "  Available: ${available_mb} MB"

if [ $kit_size -gt $available_bytes ]; then
    print_error "Not enough space on boot partition!"
    echo ""
    echo "Kit requires ${kit_size_mb} MB but only ${available_mb} MB available."
    echo ""
    echo "Options:"
    echo "  1. Use a larger SD card"
    echo "  2. Copy kit via USB drive instead"
    exit 1
fi

print_success "Sufficient space available"

# Confirm
echo ""
echo "This will copy the deployment kit to:"
echo "  $BOOT_PATH/pi_deployment_kit/"
echo ""
read -p "Continue? [y/N]: " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Copy kit
print_info "Copying deployment kit to SD card..."
print_info "(This may take a few minutes)"

if rsync -av --progress "$KIT_DIR/" "$BOOT_PATH/pi_deployment_kit/" 2>&1 | grep -v "^sending"; then
    print_success "Deployment kit copied successfully!"
else
    # Fallback to cp if rsync not available
    cp -r "$KIT_DIR" "$BOOT_PATH/"
    print_success "Deployment kit copied successfully!"
fi

# Create instructions file on boot partition
cat > "$BOOT_PATH/RECONRAVEN_SETUP.txt" <<'EOF'
ReconRaven Quick Setup Instructions
====================================

The pi_deployment_kit folder has been copied to this boot partition.

After first boot:

1. Copy kit to home directory:
   cp -r /boot/pi_deployment_kit ~/

2. Run setup script:
   cd ~/pi_deployment_kit/scripts
   bash pi_quick_setup.sh

3. Follow interactive prompts

4. Reboot when complete

For manual setup, see:
  ~/pi_deployment_kit/README.txt

For help:
  https://github.com/kamakauzy/ReconRaven

EOF

print_success "Created RECONRAVEN_SETUP.txt on boot partition"

# Sync filesystem
print_info "Syncing filesystem..."
sync

print_success "All done!"
echo ""
echo "Next steps:"
echo "  1. Safely eject SD card"
echo "  2. Insert into Raspberry Pi and boot"
echo "  3. After boot, follow instructions in /boot/RECONRAVEN_SETUP.txt"
echo ""

