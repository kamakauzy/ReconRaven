"""
Configuration loader for SDR SIGINT Platform.
Loads YAML configuration files and provides centralized access.
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml


logger = logging.getLogger(__name__)

# Default configuration paths
CONFIG_DIR = os.path.join(Path(__file__).parent, 'config')
BANDS_CONFIG = os.path.join(CONFIG_DIR, 'bands.yaml')
DEMOD_CONFIG = os.path.join(CONFIG_DIR, 'demod_config.yaml')
HARDWARE_CONFIG = os.path.join(CONFIG_DIR, 'hardware.yaml')


class Config:
    """Central configuration manager for the SDR platform."""

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize configuration manager.

        Args:
            config_dir: Optional custom configuration directory path
        """
        self.config_dir = config_dir or CONFIG_DIR
        self.bands = {}
        self.demod_params = {}
        self.hardware_config = {}
        self.load_all()

    def load_all(self):
        """Load all configuration files."""
        self.bands = self._load_yaml(os.path.join(self.config_dir, 'bands.yaml'))
        self.demod_params = self._load_yaml(os.path.join(self.config_dir, 'demod_config.yaml'))
        self.hardware_config = self._load_yaml(os.path.join(self.config_dir, 'hardware.yaml'))
        logger.info('Configuration loaded successfully')

    def _load_yaml(self, filepath: str) -> dict[str, Any]:
        """Load a YAML configuration file.

        Args:
            filepath: Path to YAML file

        Returns:
            Dictionary containing configuration data
        """
        try:
            if Path(filepath).exists():
                with open(filepath) as f:
                    data = yaml.safe_load(f)
                    logger.info(f'Loaded configuration from {filepath}')
                    return data or {}
            else:
                logger.warning(f'Configuration file not found: {filepath}')
                return {}
        except Exception as e:
            logger.exception(f'Error loading {filepath}: {e}')
            return {}

    def get_scan_bands(self) -> list[dict[str, Any]]:
        """Get list of frequency bands to scan.

        Returns:
            List of band dictionaries with start, end, name, etc.
        """
        return self.bands.get('scan_bands', [])

    def get_drone_bands(self) -> list[dict[str, Any]]:
        """Get list of known drone frequency bands.

        Returns:
            List of drone band dictionaries
        """
        return self.bands.get('drone_bands', [])

    def get_detection_threshold(self) -> float:
        """Get signal detection threshold in dBm.

        Returns:
            Threshold value (default: -60 dBm)
        """
        return self.hardware_config.get('detection_threshold_dbm', -60.0)

    def get_fft_step_size(self) -> int:
        """Get FFT step size in Hz.

        Returns:
            Step size (default: 25 kHz)
        """
        return self.hardware_config.get('fft_step_hz', 25000)

    def get_sample_rate(self) -> int:
        """Get SDR sample rate.

        Returns:
            Sample rate in Hz (default: 2.4 MHz)
        """
        return self.hardware_config.get('sample_rate_hz', 2400000)

    def get_array_config(self) -> dict[str, Any]:
        """Get direction finding array configuration.

        Returns:
            Dictionary with array geometry and settings
        """
        return self.hardware_config.get('df_array', {})

    def get_gps_config(self) -> dict[str, Any]:
        """Get GPS configuration.

        Returns:
            Dictionary with GPS settings
        """
        return self.hardware_config.get('gps', {})

    def get_demod_config(self, mode: str) -> dict[str, Any]:
        """Get demodulation parameters for a specific mode.

        Args:
            mode: Demodulation mode (FM, AM, DMR, P25, etc.)

        Returns:
            Dictionary with demodulation parameters
        """
        return self.demod_params.get(mode, {})

    def get_recording_config(self) -> dict[str, Any]:
        """Get recording configuration.

        Returns:
            Dictionary with recording settings
        """
        return self.hardware_config.get('recording', {})


# Global configuration instance
_config = None


def get_config(config_dir: Optional[str] = None) -> Config:
    """Get or create global configuration instance.

    Args:
        config_dir: Optional custom configuration directory

    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config(config_dir)
    return _config


def reload_config():
    """Reload configuration from files."""
    global _config
    if _config:
        _config.load_all()
