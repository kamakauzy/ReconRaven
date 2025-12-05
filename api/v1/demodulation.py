"""Demodulation & Decoding Endpoints

GET  /api/v1/demod/freq/<freq>          - Demodulate specific frequency
POST /api/v1/decode/binary              - Decode binary signal data
GET  /api/v1/demod/protocols            - List supported protocols
"""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from flask import Blueprint, jsonify, request

from api.auth import auth
from reconraven.core.database import get_db
from reconraven.demodulation.analog import AnalogDemodulator, AnalogMode


bp = Blueprint('demodulation', __name__, url_prefix='/api/v1')


@bp.route('/demod/freq/<float:freq>', methods=['GET'])
@auth.require_auth
def demodulate_frequency(freq: float):
    """Demodulate a specific frequency.

    Query params:
        mode (str): Demodulation mode (FM, AM, USB, LSB, DMR, P25, etc.)
        duration (int): Recording duration in seconds (default 10)
        output (str): Output format (wav, npy, both)
    """
    try:
        mode_str = request.args.get('mode', 'FM').upper()
        duration = request.args.get('duration', 10, type=int)

        # Validate duration
        if duration > 60:
            return jsonify({'error': 'Duration limited to 60 seconds'}), 400

        # Map mode string to AnalogMode enum
        mode_map = {
            'FM': AnalogMode.FM,
            'AM': AnalogMode.AM,
            'USB': AnalogMode.USB,
            'LSB': AnalogMode.LSB,
            'WFM': AnalogMode.FM_WIDE,
            'WBFM': AnalogMode.FM_WIDE,
        }

        if mode_str not in mode_map:
            return jsonify(
                {
                    'error': f'Unsupported mode: {mode_str}',
                    'supported_modes': list(mode_map.keys()),
                }
            ), 400

        mode = mode_map[mode_str]

        # Create output directory
        output_dir = Path('recordings/audio')
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        filename_base = f'demod_{freq:.3f}MHz_{mode_str}_{timestamp}'

        # Initialize demodulator
        demodulator = AnalogDemodulator()

        # Output file path
        wav_file = output_dir / f'{filename_base}.wav'

        # Start demodulation
        freq_hz = freq * 1e6 if freq < 10000 else freq
        success = demodulator.start_demodulation(
            frequency_hz=freq_hz, mode=mode, output_file=str(wav_file)
        )

        if not success:
            return jsonify({'error': 'Failed to start demodulation'}), 500

        # Let it run for the specified duration
        import time

        time.sleep(duration)

        # Stop demodulation
        demodulator.stop_demodulation()

        # Check if file was created
        if not wav_file.exists():
            return jsonify({'error': 'Demodulation failed to create output file'}), 500

        # Add to database
        db = get_db()
        file_size_mb = wav_file.stat().st_size / (1024 * 1024)
        db.add_recording(
            filename=wav_file.name,
            freq=freq_hz,
            band='',
            duration=duration,
            file_size_mb=file_size_mb,
        )

        return jsonify(
            {
                'frequency': freq,
                'mode': mode_str,
                'duration': duration,
                'status': 'success',
                'file_path': str(wav_file),
                'file_size_mb': round(file_size_mb, 2),
                'message': 'Demodulation complete',
            }
        ), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/decode/binary', methods=['POST'])
@auth.require_auth
def decode_binary():
    """Decode binary protocol from signal data.

    Body params:
        signal_data (list): Raw signal samples
        protocol (str): Protocol hint (OOK, ASK, FSK, auto)
        sample_rate (int): Sample rate of signal
    """
    try:
        data = request.get_json()
        if not data or 'signal_data' not in data:
            return jsonify({'error': 'signal_data required'}), 400

        signal_data = data['signal_data']
        protocol = data.get('protocol', 'auto')

        # Convert to numpy array if needed
        if isinstance(signal_data, list):
            signal_array = np.array(signal_data, dtype=np.complex64)
        else:
            signal_array = signal_data

        # Basic demodulation to binary
        # For OOK/ASK: Use amplitude detection
        amplitude = np.abs(signal_array)
        threshold = np.mean(amplitude) + np.std(amplitude)
        binary_data = (amplitude > threshold).astype(int)

        # Find edges (transitions)
        edges = np.diff(binary_data)
        rising_edges = np.where(edges == 1)[0]

        # Convert to binary string
        binary_str = ''.join(str(b) for b in binary_data[:1000])  # Limit to first 1000 bits

        # Convert to hex (group by 4 bits)
        hex_str = ''
        try:
            for i in range(0, len(binary_str) - 3, 4):
                nibble = binary_str[i : i + 4]
                if len(nibble) == 4:
                    hex_str += format(int(nibble, 2), 'x')
        except ValueError:
            hex_str = 'invalid'

        # Calculate confidence based on edge consistency
        if len(rising_edges) > 1:
            edge_intervals = np.diff(rising_edges)
            confidence = 1.0 - (np.std(edge_intervals) / (np.mean(edge_intervals) + 1))
            confidence = max(0.0, min(1.0, confidence))
        else:
            confidence = 0.0

        # Detect preamble patterns
        preamble_patterns = ['10101010', '11110000', '01010101']
        preamble_found = any(pattern in binary_str for pattern in preamble_patterns)

        return jsonify(
            {
                'protocol': protocol,
                'decoded_hex': f'0x{hex_str[:32]}' if hex_str != 'invalid' else 'invalid',
                'decoded_binary': binary_str[:128],  # First 128 bits
                'preamble_found': preamble_found,
                'confidence': round(confidence, 2),
                'bit_count': len(binary_data),
                'edge_count': len(rising_edges),
                'message': 'Decoding complete',
            }
        ), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/demod/protocols', methods=['GET'])
@auth.require_auth
def list_protocols():
    """List all supported demodulation protocols."""
    protocols = {
        'voice': {
            'analog': ['FM', 'AM', 'USB', 'LSB', 'WFM'],
            'digital': ['DMR', 'P25', 'NXDN', 'ProVoice', 'Fusion'],
        },
        'binary': {
            'modulation': ['OOK', 'ASK', 'FSK', 'GFSK', 'PSK'],
            'protocols': ['rtl_433', 'custom'],
        },
    }

    return jsonify(protocols), 200
