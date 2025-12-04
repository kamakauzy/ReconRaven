#!/usr/bin/env python3
"""
rtl_433 Integration Module
Bridges ReconRaven with rtl_433 for automatic device identification
"""

import json
import logging
import subprocess
import sys
from pathlib import Path

import numpy as np


logger = logging.getLogger(__name__)


class RTL433Integration:
    """Interface with rtl_433 for protocol decoding"""

    def __init__(self, rtl433_path='rtl_433'):
        self.rtl433_path = rtl433_path
        self.available = self._check_availability()

    def _check_availability(self):
        """Check if rtl_433 is installed"""
        try:
            result = subprocess.run(
                [self.rtl433_path, '-h'], capture_output=True, timeout=5, check=False
            )
            return result.returncode == 0
        except Exception:
            return False

    def convert_npy_to_cu8(self, npy_file, cu8_file):
        """Convert .npy IQ file to .cu8 format for rtl_433"""
        logger.info(f'Converting {npy_file} to rtl_433 format...')

        # Load complex IQ samples
        samples = np.load(npy_file)

        # Convert to interleaved I/Q unsigned 8-bit
        # rtl_433 expects: I,Q,I,Q,... in range 0-255 (127 = zero)
        i_samples = np.real(samples)
        q_samples = np.imag(samples)

        # Normalize to 0-255 range
        i_normalized = ((i_samples + 1) * 127.5).astype(np.uint8)
        q_normalized = ((q_samples + 1) * 127.5).astype(np.uint8)

        # Interleave
        iq_interleaved = np.empty((i_normalized.size + q_normalized.size,), dtype=np.uint8)
        iq_interleaved[0::2] = i_normalized
        iq_interleaved[1::2] = q_normalized

        # Write to file
        iq_interleaved.tofile(cu8_file)

        logger.info(f'Converted: {cu8_file} ({Path(cu8_file).stat().st_size / 1024 / 1024:.1f} MB)')
        return cu8_file

    def analyze_recording(self, npy_file, output_json=None):
        """Analyze a recording with rtl_433"""
        if not self.available:
            return {
                'success': False,
                'error': 'rtl_433 not installed',
                'install_instructions': 'Download from: https://github.com/merbanan/rtl_433/releases',
            }

        # Convert to .cu8 format
        cu8_file = npy_file.replace('.npy', '.cu8')
        self.convert_npy_to_cu8(npy_file, cu8_file)

        # Run rtl_433
        logger.info('\nRunning rtl_433 analysis...')

        try:
            cmd = [
                self.rtl433_path,
                '-r',
                cu8_file,
                '-F',
                'json',  # JSON output
                '-M',
                'level',  # Report signal level
                '-A',  # Analyze all protocols
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)

            # Parse results
            devices = []
            for line in result.stdout.split('\n'):
                if line.strip():
                    try:
                        device = json.loads(line)
                        devices.append(device)
                    except Exception:
                        pass

            # Clean up .cu8 file
            if Path(cu8_file).exists():
                Path(cu8_file).unlink()

            if devices:
                logger.info(f'\nFound {len(devices)} device(s)!')

                # Save results
                if output_json:
                    with open(output_json, 'w') as f:
                        json.dump(devices, f, indent=2)

                return {'success': True, 'devices': devices, 'count': len(devices)}
            logger.info('\nNo devices recognized by rtl_433')
            logger.info('This could mean:')
            logger.info('  - Unknown/proprietary protocol')
            logger.info('  - Signal too weak')
            logger.info('  - Not an ISM device')

            return {'success': True, 'devices': [], 'count': 0, 'message': 'No devices recognized'}

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'rtl_433 timed out (>60s)'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def print_device_info(self, devices):
        """Pretty print device information"""
        logger.info('\n' + '=' * 70)
        logger.info('rtl_433 DEVICE IDENTIFICATION')
        logger.info('=' * 70)

        for i, device in enumerate(devices, 1):
            logger.info(f'\nDevice #{i}:')

            # Common fields
            if 'model' in device:
                logger.info(f"  Model: {device['model']}")
            if 'id' in device:
                logger.info(f"  Device ID: {device['id']}")
            if 'channel' in device:
                logger.info(f"  Channel: {device['channel']}")

            # Sensor data
            if 'temperature_C' in device:
                logger.info(f"  Temperature: {device['temperature_C']}C")
            if 'humidity' in device:
                logger.info(f"  Humidity: {device['humidity']}%")
            if 'pressure_hPa' in device:
                logger.info(f"  Pressure: {device['pressure_hPa']} hPa")

            # Signal quality
            if 'rssi' in device:
                logger.info(f"  RSSI: {device['rssi']} dB")
            if 'snr' in device:
                logger.info(f"  SNR: {device['snr']} dB")

            # Other data
            for key, value in device.items():
                if key not in [
                    'model',
                    'id',
                    'channel',
                    'temperature_C',
                    'humidity',
                    'pressure_hPa',
                    'rssi',
                    'snr',
                    'time',
                ]:
                    logger.info(f'  {key}: {value}')


def analyze_file(filepath):
    """Analyze a recording file with rtl_433"""
    logger.info('\n' + '#' * 70)
    logger.info('# ReconRaven - rtl_433 Integration')
    logger.info('# Automatic device identification')
    logger.info('#' * 70)

    rtl = RTL433Integration()

    if not rtl.available:
        logger.info('\nrtl_433 is not installed!')
        logger.info('\nTo install:')
        logger.info('1. Download from: https://github.com/merbanan/rtl_433/releases')
        logger.info('2. Extract to a folder')
        logger.info('3. Add to PATH or place in project directory')
        logger.info('\nFor Windows: Download rtl_433-win-x64.zip')
        return

    logger.info(f'\nAnalyzing: {filepath}')

    result = rtl.analyze_recording(filepath)

    if result['success']:
        if result['count'] > 0:
            rtl.print_device_info(result['devices'])

            # Save to file
            json_output = filepath.replace('.npy', '_rtl433.json')
            with open(json_output, 'w') as f:
                json.dump(result['devices'], f, indent=2)
            logger.info(f'\nResults saved to: {json_output}')
        else:
            logger.info('\nNo devices identified')
            logger.info('Signal characteristics suggest:')
            logger.info('  - Proprietary protocol (not in rtl_433 database)')
            logger.info('  - Industrial equipment')
            logger.info('  - Custom implementation')
    else:
        logger.info(f"\nError: {result.get('error', 'Unknown')}")
        if 'install_instructions' in result:
            logger.info(f"\n{result['install_instructions']}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        logger.info('Usage: python rtl433_integration.py <file.npy>')
        logger.info('\nExample:')
        logger.info('  python rtl433_integration.py recordings/audio/ISM915_925.000MHz_*.npy')
        sys.exit(1)

    analyze_file(sys.argv[1])
