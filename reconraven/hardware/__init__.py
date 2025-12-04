"""Hardware control and SDR management module."""

from .sdr_controller import OperatingMode, SDRController, detect_sdr_mode


__all__ = ['SDRController', 'detect_sdr_mode']
