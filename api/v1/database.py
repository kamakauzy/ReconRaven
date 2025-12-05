"""Database Query Endpoints

GET  /api/v1/db/transcripts      - Search transcripts
GET  /api/v1/db/devices           - List identified devices
POST /api/v1/db/promote           - Promote device to baseline
GET  /api/v1/db/export            - Export data
GET  /api/v1/db/stats             - Database statistics
"""

import csv
import io
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, Response, jsonify, request

from api.auth import auth
from reconraven.core.database import get_db


bp = Blueprint('database', __name__, url_prefix='/api/v1/db')


@bp.route('/transcripts', methods=['GET'])
@auth.require_auth
def search_transcripts():
    """Search voice transcripts.

    Query params:
        query (str): Search text
        language (str): Filter by language code (EN, ES, etc.)
        band (str): Filter by frequency band (2m, 70cm, etc.)
        min_confidence (float): Minimum confidence score (0-1)
        limit (int): Max results (default 50)
        since (str): ISO timestamp - only transcripts after this
    """
    try:
        query = request.args.get('query', '').lower()
        language = request.args.get('language')
        band = request.args.get('band')
        min_confidence = request.args.get('min_confidence', type=float)
        limit = request.args.get('limit', 50, type=int)
        since = request.args.get('since')

        db = get_db()
        transcripts = db.get_all_transcripts()

        # Apply text search filter
        if query:
            transcripts = [t for t in transcripts if query in t.get('text', '').lower()]

        # Apply language filter
        if language:
            transcripts = [
                t for t in transcripts if t.get('language', '').upper() == language.upper()
            ]

        # Apply band filter
        if band:
            transcripts = [t for t in transcripts if t.get('band') == band]

        # Apply confidence filter
        if min_confidence is not None:
            transcripts = [t for t in transcripts if t.get('confidence', 0) >= min_confidence]

        # Apply time filter
        if since:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            transcripts = [
                t
                for t in transcripts
                if datetime.fromisoformat(t.get('created_at', '').replace('Z', '+00:00')) > since_dt
            ]

        # Limit results
        transcripts = transcripts[:limit]

        return jsonify(
            {
                'count': len(transcripts),
                'query': query,
                'filters': {
                    'language': language,
                    'band': band,
                    'min_confidence': min_confidence,
                },
                'transcripts': transcripts,
            }
        ), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/devices', methods=['GET'])
@auth.require_auth
def list_devices():
    """List all identified devices.

    Query params:
        min_confidence (float): Minimum confidence score
        in_baseline (bool): Only baseline devices
        limit (int): Max results
    """
    try:
        min_confidence = request.args.get('min_confidence', 0.0, type=float)
        in_baseline = request.args.get('in_baseline', type=bool)
        limit = request.args.get('limit', 100, type=int)

        db = get_db()
        devices = db.get_devices()

        # Apply filters
        if min_confidence > 0:
            devices = [d for d in devices if d.get('confidence', 0) >= min_confidence]

        if in_baseline is not None:
            devices = [d for d in devices if d.get('in_baseline') == in_baseline]

        devices = devices[:limit]

        return jsonify({'count': len(devices), 'devices': devices}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/promote', methods=['POST'])
@auth.require_auth
def promote_device():
    """Promote identified device to baseline.

    Body params:
        frequency (float): Device frequency
        device_id (int): Device ID (alternative to frequency)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400

        frequency = data.get('frequency')
        device_id = data.get('device_id')

        if not frequency and not device_id:
            return jsonify({'error': 'frequency or device_id required'}), 400

        db = get_db()

        # If device_id provided, look up the frequency
        if device_id and not frequency:
            signals = db.get_all_signals()
            signal = next((s for s in signals if s.get('id') == device_id), None)
            if signal:
                frequency = signal['frequency_hz']
            else:
                return jsonify({'error': f'Device ID {device_id} not found'}), 404

        if frequency:
            # Promote to baseline
            db.promote_to_baseline(frequency)

            return jsonify(
                {
                    'status': 'success',
                    'frequency': frequency,
                    'device_id': device_id,
                    'message': 'Device promoted to baseline',
                }
            ), 200

        return jsonify({'error': 'Could not determine frequency'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/export', methods=['GET'])
@auth.require_auth
def export_data():
    """Export database data.

    Query params:
        format (str): Export format (json, csv, txt)
        type (str): Data type (devices, transcripts, anomalies, all)
    """
    try:
        fmt = request.args.get('format', 'json')
        data_type = request.args.get('type', 'all')

        db = get_db()

        # Gather data based on type
        export_data = {
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'type': data_type,
        }

        if data_type in ('devices', 'all'):
            export_data['devices'] = db.get_devices()

        if data_type in ('transcripts', 'all'):
            export_data['transcripts'] = db.get_all_transcripts()

        if data_type in ('anomalies', 'all'):
            export_data['anomalies'] = db.get_anomalies(limit=1000)

        if data_type == 'all':
            export_data['baseline'] = db.get_all_baseline()
            export_data['statistics'] = db.get_statistics()

        # Format output
        if fmt == 'json':
            return jsonify(export_data), 200

        if fmt == 'csv':
            # Generate CSV for the primary data type
            output = io.StringIO()
            writer = csv.writer(output)

            if data_type == 'devices' and export_data.get('devices'):
                devices = export_data['devices']
                if devices:
                    # Write header
                    writer.writerow(devices[0].keys())
                    # Write rows
                    for device in devices:
                        writer.writerow(device.values())
            elif data_type == 'anomalies' and export_data.get('anomalies'):
                anomalies = export_data['anomalies']
                if anomalies:
                    writer.writerow(anomalies[0].keys())
                    for anomaly in anomalies:
                        writer.writerow(anomaly.values())
            else:
                # For 'all' or transcripts, fall back to JSON
                return jsonify({'error': 'CSV format only supported for devices or anomalies'}), 400

            csv_data = output.getvalue()
            return Response(
                csv_data,
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename=reconraven_{data_type}.csv'},
            )

        if fmt == 'txt':
            # Generate text report
            lines = []
            lines.append('=' * 70)
            lines.append('RECONRAVEN EXPORT REPORT')
            lines.append('=' * 70)
            lines.append(f'Exported: {export_data["exported_at"]}')
            lines.append(f'Type: {data_type}')
            lines.append('')

            if data_type in ('devices', 'all') and export_data.get('devices'):
                lines.append('IDENTIFIED DEVICES')
                lines.append('-' * 70)
                for dev in export_data['devices']:
                    lines.append(
                        f"{dev.get('frequency_hz', 0)/1e6:.3f} MHz - {dev.get('name', 'Unknown')}"
                    )
                    lines.append(
                        f"  Type: {dev.get('device_type', 'N/A')} | "
                        f"Manufacturer: {dev.get('manufacturer', 'N/A')} | "
                        f"Confidence: {dev.get('confidence', 0)*100:.0f}%"
                    )
                    lines.append('')

            if data_type in ('anomalies', 'all') and export_data.get('anomalies'):
                lines.append('ANOMALIES')
                lines.append('-' * 70)
                for anom in export_data['anomalies'][:50]:  # Limit to 50 in text
                    lines.append(
                        f"{anom.get('frequency_hz', 0)/1e6:.3f} MHz - "
                        f"{anom.get('power_dbm', 0):.1f} dBm - "
                        f"{anom.get('detected_at', 'N/A')}"
                    )
                lines.append('')

            if data_type == 'all' and export_data.get('statistics'):
                lines.append('STATISTICS')
                lines.append('-' * 70)
                stats = export_data['statistics']
                for key, value in stats.items():
                    lines.append(f'{key}: {value}')
                lines.append('')

            lines.append('=' * 70)
            lines.append('END OF REPORT')
            lines.append('=' * 70)

            text_data = '\n'.join(lines)
            return Response(
                text_data,
                mimetype='text/plain',
                headers={'Content-Disposition': f'attachment; filename=reconraven_{data_type}.txt'},
            )

        return jsonify({'error': f'Unsupported format: {fmt}'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/stats', methods=['GET'])
@auth.require_auth
def get_stats():
    """Get database statistics."""
    try:
        db = get_db()

        # Calculate storage size
        db_path = Path('reconraven.db')
        db_size_mb = db_path.stat().st_size / (1024 * 1024) if db_path.exists() else 0

        recordings_path = Path('recordings/audio')
        recording_files = list(recordings_path.glob('*.npy')) if recordings_path.exists() else []
        recordings_size_mb = sum(f.stat().st_size for f in recording_files) / (1024 * 1024)

        stats = {
            'baseline_frequencies': db.get_baseline_count(),
            'total_detections': db.get_detection_count(),
            'anomalies': db.get_anomaly_count(),
            'identified_devices': len(db.get_devices()),
            'transcripts': db.get_transcript_count(),
            'recordings_count': len(recording_files),
            'storage': {
                'database_mb': round(db_size_mb, 2),
                'recordings_mb': round(recordings_size_mb, 2),
                'total_mb': round(db_size_mb + recordings_size_mb, 2),
            },
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
