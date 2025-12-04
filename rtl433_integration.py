#!/usr/bin/env python3
"""
rtl_433 Integration Module
Bridges ReconRaven with rtl_433 for automatic device identification
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np


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
        print(f'Converting {npy_file} to rtl_433 format...')

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

        print(f'Converted: {cu8_file} ({Path(cu8_file).stat().st_size / 1024 / 1024:.1f} MB)')
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
        print('\nRunning rtl_433 analysis...')

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
                print(f'\nFound {len(devices)} device(s)!')

                # Save results
                if output_json:
                    with open(output_json, 'w') as f:
                        json.dump(devices, f, indent=2)

                return {'success': True, 'devices': devices, 'count': len(devices)}
            print('\nNo devices recognized by rtl_433')
            print('This could mean:')
            print('  - Unknown/proprietary protocol')
            print('  - Signal too weak')
            print('  - Not an ISM device')

            return {'success': True, 'devices': [], 'count': 0, 'message': 'No devices recognized'}

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'rtl_433 timed out (>60s)'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def print_device_info(self, devices):
        """Pretty print device information"""
        print('\n' + '=' * 70)
        print('rtl_433 DEVICE IDENTIFICATION')
        print('=' * 70)

        for i, device in enumerate(devices, 1):
            print(f'\nDevice #{i}:')

            # Common fields
            if 'model' in device:
                print(f"  Model: {device['model']}")
            if 'id' in device:
                print(f"  Device ID: {device['id']}")
            if 'channel' in device:
                print(f"  Channel: {device['channel']}")

            # Sensor data
            if 'temperature_C' in device:
                print(f"  Temperature: {device['temperature_C']}C")
            if 'humidity' in device:
                print(f"  Humidity: {device['humidity']}%")
            if 'pressure_hPa' in device:
                print(f"  Pressure: {device['pressure_hPa']} hPa")

            # Signal quality
            if 'rssi' in device:
                print(f"  RSSI: {device['rssi']} dB")
            if 'snr' in device:
                print(f"  SNR: {device['snr']} dB")

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
                    print(f'  {key}: {value}')


def analyze_file(filepath):
    """Analyze a recording file with rtl_433"""
    print('\n' + '#' * 70)
    print('# ReconRaven - rtl_433 Integration')
    print('# Automatic device identification')
    print('#' * 70)

    rtl = RTL433Integration()

    if not rtl.available:
        print('\nrtl_433 is not installed!')
        print('\nTo install:')
        print('1. Download from: https://github.com/merbanan/rtl_433/releases')
        print('2. Extract to a folder')
        print('3. Add to PATH or place in project directory')
        print('\nFor Windows: Download rtl_433-win-x64.zip')
        return

    print(f'\nAnalyzing: {filepath}')

    result = rtl.analyze_recording(filepath)

    if result['success']:
        if result['count'] > 0:
            rtl.print_device_info(result['devices'])

            # Save to file
            json_output = filepath.replace('.npy', '_rtl433.json')
            with open(json_output, 'w') as f:
                json.dump(result['devices'], f, indent=2)
            print(f'\nResults saved to: {json_output}')
        else:
            print('\nNo devices identified')
            print('Signal characteristics suggest:')
            print('  - Proprietary protocol (not in rtl_433 database)')
            print('  - Industrial equipment')
            print('  - Custom implementation')
    else:
        print(f"\nError: {result.get('error', 'Unknown')}")
        if 'install_instructions' in result:
            print(f"\n{result['install_instructions']}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python rtl433_integration.py <file.npy>')
        print('\nExample:')
        print('  python rtl433_integration.py recordings/audio/ISM915_925.000MHz_*.npy')
        sys.exit(1)

    analyze_file(sys.argv[1])
