"""
ReconRaven - SIGINT Signal Analysis Platform

A comprehensive RTL-SDR based platform for signal intelligence,
direction finding, and RF analysis.
"""

__version__ = '0.1.0-alpha'
__author__ = 'ReconRaven Team'

# Core imports for convenience
from .core.database import get_db
from .core.scanner import AdvancedScanner


__all__ = [
    'AdvancedScanner',
    'get_db',
]
