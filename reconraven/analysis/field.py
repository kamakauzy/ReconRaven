#!/usr/bin/env python3
"""
Complete Field-Capable Analysis System
Integrates: Binary decoding, rtl_433, device signatures, manufacturer identification
"""

import json
import logging
import sys
from pathlib import Path

import numpy as np

from reconraven.analysis.binary import BinaryDecoder
from reconraven.analysis.rtl433 import RTL433Integration
from reconraven.core.database import get_db


logger = logging.getLogger(__name__)


class FieldAnalyzer:
    """Complete signal analysis with offline capability"""

    def __init__(self):
        self.signatures = self._load_signatures()
        self.rtl433 = RTL433Integration()
        self.db = get_db()

    def _load_signatures(self):
        """Load local device signature database"""
        try:
            with open('device_signatures.json') as f:
                return json.load(f)
        except Exception as e:
            logger.info(f'Warning: Could not load device_signatures.json: {e}')
            return {}

    def analyze_signal(self, npy_file):
        """Complete analysis of a captured signal"""
        logger.info('\n' + '#' * 70)
        logger.info('# ReconRaven - Complete Field Analysis')
        logger.info('# Offline-capable signal identification')
        logger.info('#' * 70)
        logger.info(f'\nFile: {npy_file}\n')

        results = {
            'file': npy_file,
            'binary_decode': None,
            'rtl433_result': None,
            'signature_match': None,
            'identification': None,
            'confidence': 0,
        }

        # Step 1: Binary Decode
        logger.info('\n[STEP 1] Binary Decoding...')
        logger.info('-' * 70)
        samples = np.load(npy_file)
        decoder = BinaryDecoder(samples[: int(2.4e6 * 5)])  # First 5 seconds

        bits = decoder.decode_to_binary()
        if bits is not None:
            results['binary_decode'] = {
                'success': True,
                'modulation': decoder.modulation,
                'symbol_rate': decoder.symbol_rate,
                'total_bits': len(bits),
                'bit_sample': ''.join(map(str, bits[:100])),
            }

            # Find preambles
            preambles = decoder.find_preamble(bits)
            results['binary_decode']['preambles'] = preambles

            if preambles:
                logger.info(f'  Found {len(preambles)} known preamble(s)')
                for p in preambles:
                    logger.info(f"    {p['pattern']} - {p['description']}")
        else:
            results['binary_decode'] = {'success': False}
            logger.info('  Binary decode failed')

        # Step 2: Signature Matching
        logger.info('\n[STEP 2] Device Signature Matching...')
        logger.info('-' * 70)

        # Extract frequency from filename
        freq = self._extract_frequency(npy_file)

        if decoder.modulation and decoder.symbol_rate:
            match = self._match_signature(
                freq, decoder.modulation, decoder.symbol_rate, preambles if bits is not None else []
            )

            if match:
                results['signature_match'] = match
                logger.info(f"  MATCH: {match['name']}")
                logger.info(f"  Manufacturer: {match['manufacturer']}")
                logger.info(f"  Device Type: {match['device_type']}")
                logger.info(f"  Confidence: {match['confidence']*100:.0f}%")

                if 'typical_devices' in match:
                    logger.info('  Typical devices:')
                    for dev in match['typical_devices'][:3]:
                        logger.info(f'    - {dev}')
            else:
                logger.info('  No signature match found')

        # Step 3: rtl_433 Analysis
        logger.info('\n[STEP 3] rtl_433 Protocol Analysis...')
        logger.info('-' * 70)

        if self.rtl433.available:
            rtl_result = self.rtl433.analyze_recording(npy_file)
            results['rtl433_result'] = rtl_result

            if rtl_result['success'] and rtl_result['count'] > 0:
                logger.info(f"  rtl_433 identified {rtl_result['count']} device(s)!")
                for device in rtl_result['devices']:
                    if 'model' in device:
                        logger.info(f"    Model: {device['model']}")
                    if 'id' in device:
                        logger.info(f"    ID: {device['id']}")

                # Use rtl_433 result as primary identification
                results['identification'] = 'rtl_433'
                results['confidence'] = 0.95
            else:
                logger.info('  rtl_433: No devices recognized')

                # Use signature match if available
                if results['signature_match']:
                    results['identification'] = 'signature_match'
                    results['confidence'] = results['signature_match']['confidence']
        else:
            logger.info('  rtl_433 not available - using signature matching only')
            if results['signature_match']:
                results['identification'] = 'signature_match'
                results['confidence'] = results['signature_match']['confidence']

        # Step 4: Final Classification
        logger.info('\n' + '=' * 70)
        logger.info('FINAL IDENTIFICATION')
        logger.info('=' * 70)

        if results['confidence'] >= 0.6:
            logger.info(f'\nDevice Identified: {self._get_device_name(results)}')
            logger.info(f"Confidence: {results['confidence']*100:.0f}%")
            logger.info(f"Method: {results['identification']}")

            # Additional details
            if results['signature_match']:
                sig = results['signature_match']
                logger.info(f"\nManufacturer: {sig['manufacturer']}")
                logger.info(f"Type: {sig['device_type']}")
                if 'security' in sig:
                    logger.info(f"Security: {sig['security']}")
        else:
            logger.info('\nDevice: UNKNOWN / PROPRIETARY')
            logger.info(f"Confidence: {results['confidence']*100:.0f}%")
            logger.info('\nPossible reasons:')
            logger.info('  - Custom/proprietary protocol')
            logger.info('  - Industrial equipment not in database')
            logger.info('  - New/uncommon device')

        # Save results to JSON
        output_file = npy_file.replace('.npy', '_complete_analysis.json')
        with open(output_file, 'w') as f:
            # Convert numpy types to Python types for JSON
            results_json = self._convert_to_json_serializable(results)
            json.dump(results_json, f, indent=2)

        logger.info(f'\nComplete analysis saved: {output_file}')

        # Save to database
        self._save_to_database(npy_file, results)

        return results

    def _extract_frequency(self, filename):
        """Extract frequency from filename"""
        import re

        match = re.search(r'(\d+\.\d+)MHz', filename)
        if match:
            return float(match.group(1)) * 1e6
        return None

    def _match_signature(self, frequency, modulation, bit_rate, preambles):
        """Match signal against device signature database"""
        if not self.signatures or 'device_signatures' not in self.signatures:
            return None

        best_match = None
        best_score = 0

        for _sig_name, sig in self.signatures['device_signatures'].items():
            score = 0

            # Check frequency
            if frequency and 'frequencies' in sig:
                for sig_freq in sig['frequencies']:
                    if abs(frequency - sig_freq) < 1e6:  # Within 1 MHz
                        score += 0.4
                        break

            # Check modulation
            if modulation and 'modulation' in sig:
                if modulation.upper().replace('/', '') in sig['modulation'].upper().replace(
                    '/', ''
                ):
                    score += 0.3

            # Check bit rate
            if bit_rate and 'bit_rate_min' in sig and 'bit_rate_max' in sig:
                if sig['bit_rate_min'] <= bit_rate <= sig['bit_rate_max']:
                    score += 0.2
            elif bit_rate and 'bit_rate' in sig:
                tolerance = sig['bit_rate'] * 0.15
                if abs(bit_rate - sig['bit_rate']) < tolerance:
                    score += 0.2

            # Check preamble
            if preambles and 'preamble' in sig:
                for p in preambles:
                    if p['pattern'] == sig['preamble']:
                        score += 0.1
                        break

            # Update best match
            if score > best_score and score >= sig.get('confidence_threshold', 0.6):
                best_score = score
                best_match = sig.copy()
                best_match['confidence'] = score

        return best_match

    def _get_device_name(self, results):
        """Get device name from results"""
        if results['rtl433_result'] and results['rtl433_result'].get('count', 0) > 0:
            device = results['rtl433_result']['devices'][0]
            return device.get('model', 'Unknown')
        if results['signature_match']:
            return results['signature_match']['name']
        return 'Unknown'

    def _convert_to_json_serializable(self, obj):
        """Convert numpy types to Python types"""
        if isinstance(obj, dict):
            return {k: self._convert_to_json_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._convert_to_json_serializable(v) for v in obj]
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    def _save_to_database(self, npy_file, results):
        """Save analysis results to database"""
        try:
            # Get recording ID from filename
            filename = Path(npy_file).name
            recordings = self.db.get_recordings()
            recording_id = None

            for rec in recordings:
                if rec['filename'] == filename:
                    recording_id = rec['id']
                    break

            if not recording_id:
                logger.info(f'[DB] Warning: Could not find recording for {filename}')
                return

            # Extract data for database
            binary_decode = results.get('binary_decode', {})
            modulation = binary_decode.get('modulation', 'Unknown')
            bit_rate = binary_decode.get('bit_rate')

            preambles_str = None
            if binary_decode.get('preambles'):
                preambles_str = ','.join([p['pattern'] for p in binary_decode['preambles'][:3]])

            # Convert results to JSON
            results_json = json.dumps(self._convert_to_json_serializable(results))

            # Save analysis results
            cursor = self.db.conn.cursor()
            cursor.execute(
                """
                INSERT INTO analysis_results
                (recording_id, analysis_type, modulation, bit_rate, preambles, results_json, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    recording_id,
                    'field_analysis',
                    modulation,
                    bit_rate,
                    preambles_str,
                    results_json,
                    results['confidence'],
                ),
            )
            self.db.conn.commit()

            logger.info(f'[DB] Analysis results saved (recording_id={recording_id})')

            # Also add/update device (always create, even if unknown)
            device_name = self._get_device_name(results)
            frequency = self._extract_frequency(filename)

            if frequency:
                manufacturer = None
                device_type = None

                if results.get('signature_match'):
                    manufacturer = results['signature_match'].get('manufacturer')
                    device_type = results['signature_match'].get('device_type')
                elif results.get('rtl433_result') and results['rtl433_result'].get('count', 0) > 0:
                    device = results['rtl433_result']['devices'][0]
                    manufacturer = device.get('manufacturer', 'Unknown')
                    device_type = device.get('model', 'Unknown')

                # Always create device entry (even if "Unknown")
                device_id = self.db.add_device(
                    freq=frequency,
                    name=device_name
                    if device_name != 'Unknown'
                    else f'{frequency/1e6:.3f} MHz Signal',
                    manufacturer=manufacturer,
                    device_type=device_type,
                    modulation=modulation,
                    bit_rate=bit_rate,
                    confidence=results['confidence'],
                )

                # Mark recording as analyzed
                self.db.mark_recording_analyzed(recording_id, device_id)

                logger.info(f'[DB] Device added/updated: {device_name}')

        except Exception as e:
            logger.info(f'[DB] Error saving to database: {e}')
            import traceback

            traceback.print_exc()


def main():
    if len(sys.argv) < 2:
        logger.info('Usage: python field_analyzer.py <recording.npy>')
        logger.info('\nExample:')
        logger.info('  python field_analyzer.py recordings/audio/ISM915_925.000MHz_*.npy')
        sys.exit(1)

    analyzer = FieldAnalyzer()
    analyzer.analyze_signal(sys.argv[1])


if __name__ == '__main__':
    main()
