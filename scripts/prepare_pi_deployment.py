#!/usr/bin/env python3
"""
ReconRaven Pi Deployment Kit Preparation Script

Runs on your laptop to pre-download everything needed for Pi deployment.
Creates a deployment kit that can be copied to SD card or USB drive.

Usage:
    python3 scripts/prepare_pi_deployment.py
"""

import hashlib
import json
import os
import secrets
import shutil
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_step(text: str):
    """Print a step indicator."""
    print(f"[*] {text}...")


def print_success(text: str):
    """Print success message."""
    print(f"[✓] {text}")


def print_error(text: str):
    """Print error message."""
    print(f"[✗] {text}")


def print_warning(text: str):
    """Print warning message."""
    print(f"[!] {text}")


def get_user_input(prompt: str, default: str = "") -> str:
    """Get user input with optional default."""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    return input(f"{prompt}: ").strip()


def confirm(prompt: str, default: bool = True) -> bool:
    """Ask for yes/no confirmation."""
    default_str = "Y/n" if default else "y/N"
    response = input(f"{prompt} [{default_str}]: ").strip().lower()
    if not response:
        return default
    return response in ('y', 'yes')


def calculate_checksum(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


class DeploymentKitBuilder:
    """Builds a Pi deployment kit with all necessary files."""

    def __init__(self, output_dir: Path = Path('pi_deployment_kit')):
        self.output_dir = output_dir
        self.manifest: dict[str, Any] = {
            'created': datetime.now(timezone.utc).isoformat(),
            'version': '1.0.0',
            'items': {}
        }

    def create_directory_structure(self):
        """Create the deployment kit directory structure."""
        print_step("Creating directory structure")

        dirs = [
            self.output_dir,
            self.output_dir / 'whisper_models',
            self.output_dir / 'location_data',
            self.output_dir / 'config',
            self.output_dir / 'python_packages',
            self.output_dir / 'test_data',
            self.output_dir / 'scripts',
        ]

        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

        print_success("Directory structure created")

    def download_whisper_models(self, models: list[str]):
        """Download Whisper AI models."""
        try:
            import whisper
        except ImportError:
            print_error("Whisper not installed. Run: pip install openai-whisper")
            return

        print_step(f"Downloading Whisper models: {', '.join(models)}")

        for model_name in models:
            try:
                print(f"  Downloading '{model_name}' model (this may take a while)...")
                model = whisper.load_model(model_name)
                print_success(f"'{model_name}' model downloaded")

                # Find model file in cache
                cache_dir = Path.home() / '.cache' / 'whisper'
                model_files = list(cache_dir.glob(f'{model_name}.pt'))

                if model_files:
                    dest = self.output_dir / 'whisper_models' / f'{model_name}.pt'
                    shutil.copy2(model_files[0], dest)
                    checksum = calculate_checksum(dest)

                    self.manifest['items'][f'whisper_{model_name}'] = {
                        'file': str(dest.relative_to(self.output_dir)),
                        'size_bytes': dest.stat().st_size,
                        'checksum': checksum
                    }
                    print_success(f"'{model_name}' model copied to deployment kit")

            except Exception as e:
                print_error(f"Failed to download '{model_name}': {e}")

    def setup_location_database(self, state_code: str, city: str = ""):
        """Download and setup location database."""
        print_step(f"Setting up location database for {state_code}")

        try:
            from reconraven.location.database import get_location_db
            from reconraven.location.repeaterbook import RepeaterBookClient
            from reconraven.location.noaa import NOAAStations

            # Create temporary database
            temp_db_path = self.output_dir / 'location_data' / 'location_frequencies.db'

            # Override database path
            import reconraven.location.database as db_module
            db_module.DB_PATH = temp_db_path

            db = get_location_db()

            # Import repeaters
            print(f"  Fetching repeaters for {state_code}...")
            client = RepeaterBookClient(db=db)
            repeater_count = client.setup_state(state_code)
            print_success(f"Imported {repeater_count} repeaters")

            # Import NOAA stations
            print("  Importing NOAA weather stations...")
            noaa = NOAAStations(db=db)
            noaa.import_all_stations()
            print_success("Imported NOAA stations")

            # Get stats
            stats = db.get_stats()

            # Close database
            db.close()

            # Calculate checksum
            checksum = calculate_checksum(temp_db_path)

            self.manifest['items']['location_database'] = {
                'file': 'location_data/location_frequencies.db',
                'size_bytes': temp_db_path.stat().st_size,
                'checksum': checksum,
                'state': state_code,
                'city': city,
                'stats': stats
            }

            # Create import manifest
            import_manifest = {
                'state': state_code,
                'city': city,
                'imported': datetime.now(timezone.utc).isoformat(),
                'stats': stats
            }

            manifest_path = self.output_dir / 'location_data' / 'import_manifest.json'
            with open(manifest_path, 'w') as f:
                json.dump(import_manifest, f, indent=2)

            print_success("Location database ready")

        except Exception as e:
            print_error(f"Failed to setup location database: {e}")
            import traceback
            traceback.print_exc()

    def generate_api_keys(self):
        """Generate API keys and configuration."""
        print_step("Generating API keys")

        try:
            import yaml

            # Generate keys
            api_key = secrets.token_urlsafe(32)
            jwt_secret = secrets.token_urlsafe(64)

            # Create config
            config = {
                'api_key_hash': hashlib.sha256(api_key.encode()).hexdigest(),
                'jwt_secret': jwt_secret,
                'jwt_expiry_hours': 24,
                'rate_limit_per_second': 10,
                'allowed_origins': ['http://localhost:5000'],
                'created': datetime.now(timezone.utc).isoformat()
            }

            # Write config
            config_path = self.output_dir / 'config' / 'api_config.yaml'
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)

            # Write API key
            key_path = self.output_dir / 'config' / 'api_key.txt'
            with open(key_path, 'w') as f:
                f.write(f"API Key (save this - won't be shown again):\n{api_key}\n")

            self.manifest['items']['api_config'] = {
                'files': ['config/api_config.yaml', 'config/api_key.txt'],
                'note': 'Pre-generated API keys for immediate use'
            }

            print_success("API keys generated")
            print(f"  API Key: {api_key}")
            print("  (Saved to config/api_key.txt in deployment kit)")

        except Exception as e:
            print_error(f"Failed to generate API keys: {e}")

    def create_test_data(self):
        """Create sample test recordings."""
        print_step("Creating test data")

        try:
            import numpy as np

            # Create sample IQ data (simulated signals)
            test_data = [
                ('sample_2m_signal.npy', 146.52e6, 2400000),
                ('sample_70cm_signal.npy', 446.0e6, 2400000),
            ]

            test_manifest = {'recordings': []}

            for filename, center_freq, sample_rate in test_data:
                # Generate 1 second of simulated signal
                samples = 2400000
                t = np.arange(samples) / sample_rate
                signal_freq = 1000  # 1 kHz tone

                # Simulate FM signal
                i_component = np.cos(2 * np.pi * signal_freq * t) * 0.5
                q_component = np.sin(2 * np.pi * signal_freq * t) * 0.5
                iq_data = i_component + 1j * q_component

                # Add noise
                noise = (np.random.randn(samples) + 1j * np.random.randn(samples)) * 0.1
                iq_data += noise

                # Save
                file_path = self.output_dir / 'test_data' / filename
                np.save(file_path, iq_data)

                test_manifest['recordings'].append({
                    'filename': filename,
                    'center_freq_hz': center_freq,
                    'sample_rate_hz': sample_rate,
                    'duration_sec': 1.0,
                    'size_bytes': file_path.stat().st_size
                })

            # Save manifest
            manifest_path = self.output_dir / 'test_data' / 'test_manifest.json'
            with open(manifest_path, 'w') as f:
                json.dump(test_manifest, f, indent=2)

            self.manifest['items']['test_data'] = {
                'files': [r['filename'] for r in test_manifest['recordings']],
                'count': len(test_manifest['recordings'])
            }

            print_success("Test data created")

        except Exception as e:
            print_error(f"Failed to create test data: {e}")

    def prepare_python_packages(self):
        """Prepare Python package requirements with piwheels URLs."""
        print_step("Preparing Python packages configuration")

        try:
            # Read original requirements
            req_path = Path('requirements.txt')
            if not req_path.exists():
                print_warning("requirements.txt not found, skipping")
                return

            # Copy requirements
            dest_path = self.output_dir / 'python_packages' / 'requirements.txt'
            shutil.copy2(req_path, dest_path)

            # Create piwheels-optimized version
            piwheels_path = self.output_dir / 'python_packages' / 'requirements_piwheels.txt'
            with open(piwheels_path, 'w') as f:
                f.write("# ReconRaven requirements optimized for Raspberry Pi\n")
                f.write("# Use piwheels for pre-compiled packages\n\n")
                f.write("--extra-index-url https://www.piwheels.org/simple\n\n")

                with open(req_path) as req_file:
                    f.write(req_file.read())

            self.manifest['items']['python_packages'] = {
                'files': ['requirements.txt', 'requirements_piwheels.txt'],
                'note': 'Use requirements_piwheels.txt on Pi for faster install'
            }

            print_success("Python package configuration ready")

        except Exception as e:
            print_error(f"Failed to prepare Python packages: {e}")

    def copy_deployment_scripts(self):
        """Copy deployment scripts to kit."""
        print_step("Copying deployment scripts")

        scripts = [
            'scripts/pi_quick_setup.sh',
            'scripts/validate_system.py',
            'scripts/pack_for_pi.sh'
        ]

        copied = []
        for script in scripts:
            src = Path(script)
            if src.exists():
                dest = self.output_dir / 'scripts' / src.name
                shutil.copy2(src, dest)
                dest.chmod(0o755)  # Make executable
                copied.append(src.name)
            else:
                print_warning(f"Script not found: {script}")

        self.manifest['items']['scripts'] = {
            'files': copied,
            'note': 'Deployment and validation scripts'
        }

        print_success(f"Copied {len(copied)} scripts")

    def create_readme(self):
        """Create deployment kit README."""
        print_step("Creating README")

        readme_content = """# ReconRaven Pi Deployment Kit

This deployment kit contains everything you need to quickly deploy ReconRaven on your Raspberry Pi.

## Contents

- `whisper_models/` - Pre-downloaded Whisper AI models
- `location_data/` - Pre-built location database with repeaters and NOAA stations
- `config/` - Pre-generated API keys and configuration
- `python_packages/` - Python requirements optimized for Pi
- `test_data/` - Sample recordings for testing
- `scripts/` - Deployment and validation scripts
- `deployment_manifest.json` - Detailed manifest of kit contents

## Quick Start

### Option 1: Copy to SD Card Before Boot

1. Flash Raspberry Pi OS to SD card using Pi Imager
2. Mount the SD card `/boot` partition on your laptop
3. Copy this entire `pi_deployment_kit/` folder to `/boot/`
4. Eject SD card and boot Pi
5. On Pi, copy from `/boot/` to home:
   ```bash
   cp -r /boot/pi_deployment_kit ~/
   cd ~/pi_deployment_kit/scripts
   bash pi_quick_setup.sh
   ```

### Option 2: Transfer via USB Drive

1. Copy this entire folder to a USB drive
2. Boot Pi and plug in USB drive
3. USB should auto-mount to `/media/pi/`
4. Copy to home directory:
   ```bash
   cp -r /media/pi/YOUR_DRIVE/pi_deployment_kit ~/
   cd ~/pi_deployment_kit/scripts
   bash pi_quick_setup.sh
   ```

## Deployment Script

The `pi_quick_setup.sh` script will:
- Install all system dependencies
- Set up Python virtual environment
- Install Python packages (optimized for Pi)
- Import Whisper models
- Set up location database
- Configure systemd services
- Run validation tests

**Estimated time:** 45-60 minutes (mostly unattended)

## Manual Setup

If you prefer to follow the manual deployment guide, see:
`docs/RASPBERRY_PI_DEPLOYMENT.md` in the main repository.

## Validation

After setup completes, run validation:
```bash
python3 scripts/validate_system.py
```

## Troubleshooting

If setup fails:
1. Check logs: `/var/log/reconraven_setup.log`
2. Re-run setup script (it's safe to re-run)
3. Consult `docs/RASPBERRY_PI_DEPLOYMENT.md` for manual steps

## Contents Manifest

See `deployment_manifest.json` for detailed information about:
- File checksums
- Download dates
- Location database stats
- Package versions

## Support

For issues or questions:
- GitHub: https://github.com/kamakauzy/ReconRaven
- Documentation: See `docs/` folder in repository

---

Generated: {timestamp}
Kit Version: 1.0.0
"""

        readme_path = self.output_dir / 'README.txt'
        with open(readme_path, 'w') as f:
            f.write(readme_content.format(
                timestamp=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            ))

        print_success("README created")

    def save_manifest(self):
        """Save deployment manifest."""
        print_step("Saving deployment manifest")

        manifest_path = self.output_dir / 'deployment_manifest.json'
        with open(manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=2)

        print_success("Manifest saved")

    def create_archive(self):
        """Create compressed archive of deployment kit."""
        print_step("Creating compressed archive")

        archive_path = Path(f'{self.output_dir}.tar.gz')

        try:
            with tarfile.open(archive_path, 'w:gz') as tar:
                tar.add(self.output_dir, arcname=self.output_dir.name)

            size_mb = archive_path.stat().st_size / (1024 * 1024)
            print_success(f"Archive created: {archive_path} ({size_mb:.1f} MB)")

        except Exception as e:
            print_error(f"Failed to create archive: {e}")

    def print_summary(self):
        """Print summary of deployment kit."""
        print_header("Deployment Kit Summary")

        total_size = sum(
            f.stat().st_size
            for f in self.output_dir.rglob('*')
            if f.is_file()
        )

        print(f"Location: {self.output_dir.absolute()}")
        print(f"Total Size: {total_size / (1024**3):.2f} GB")
        print(f"\nContents:")

        for item_name, item_info in self.manifest['items'].items():
            print(f"  ✓ {item_name}")
            if 'stats' in item_info:
                for key, value in item_info['stats'].items():
                    print(f"      {key}: {value}")

        print("\n" + "="*60)
        print("Next Steps:")
        print("="*60)
        print("1. Copy pi_deployment_kit/ to USB drive or SD card /boot/")
        print("2. Boot Raspberry Pi")
        print("3. Run: cd ~/pi_deployment_kit/scripts && bash pi_quick_setup.sh")
        print("4. Wait ~45 minutes for automated setup")
        print("5. Reboot and start scanning!")
        print("="*60 + "\n")


def main():
    """Main entry point."""
    print_header("ReconRaven Pi Deployment Kit Builder")

    # Check we're in the right directory
    if not Path('reconraven').exists():
        print_error("Must run from ReconRaven root directory")
        print("Usage: python3 scripts/prepare_pi_deployment.py")
        sys.exit(1)

    # Get user input
    print("This script will create a deployment kit with pre-downloaded content.")
    print("Kit size: ~5-8 GB depending on options selected.\n")

    state_code = get_user_input("Your state code (e.g., AL, CA, TX)", "AL").upper()
    city = get_user_input("Your city (optional)", "")

    download_whisper = confirm("Download Whisper models?", True)
    if download_whisper:
        models_str = get_user_input("Which models? (base/small/medium, comma-separated)", "base,small")
        whisper_models = [m.strip() for m in models_str.split(',')]
    else:
        whisper_models = []

    generate_test_data = confirm("Generate test data?", True)

    # Confirm
    print("\nConfiguration:")
    print(f"  State: {state_code}")
    if city:
        print(f"  City: {city}")
    print(f"  Whisper models: {', '.join(whisper_models) if whisper_models else 'None'}")
    print(f"  Test data: {'Yes' if generate_test_data else 'No'}")

    if not confirm("\nProceed with kit creation?", True):
        print("Aborted.")
        sys.exit(0)

    # Build kit
    builder = DeploymentKitBuilder()

    try:
        builder.create_directory_structure()
        builder.setup_location_database(state_code, city)
        builder.generate_api_keys()
        builder.prepare_python_packages()

        if whisper_models:
            builder.download_whisper_models(whisper_models)

        if generate_test_data:
            builder.create_test_data()

        builder.copy_deployment_scripts()
        builder.create_readme()
        builder.save_manifest()
        builder.create_archive()

        builder.print_summary()

        print_success("Deployment kit created successfully!")

    except KeyboardInterrupt:
        print_error("\nAborted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Failed to create deployment kit: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

