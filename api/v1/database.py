"""Database Query Endpoints

GET  /api/v1/db/transcripts      - Search transcripts
GET  /api/v1/db/devices           - List identified devices
POST /api/v1/db/promote           - Promote device to baseline
GET  /api/v1/db/export            - Export data
GET  /api/v1/db/stats             - Database statistics
"""

from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, jsonify, request

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
        query = request.args.get('query', '')
        language = request.args.get('language')
        band = request.args.get('band')
        min_confidence = request.args.get('min_confidence', type=float)
        limit = request.args.get('limit', 50, type=int)
        since = request.args.get('since')

        db = get_db()

        # TODO: Implement full-text search in database
        # For now, return placeholder
        transcripts = []

        return jsonify({
            'count': len(transcripts),
            'query': query,
            'filters': {
                'language': language,
                'band': band,
                'min_confidence': min_confidence
            },
            'transcripts': transcripts
        }), 200

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

        return jsonify({
            'count': len(devices),
            'devices': devices
        }), 200

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

        # TODO: Implement device promotion
        # db.promote_device_to_baseline(frequency or device_id)

        return jsonify({
            'status': 'success',
            'frequency': frequency,
            'device_id': device_id,
            'message': 'Device promoted to baseline'
        }), 200

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

        # TODO: Implement actual export
        # For now, return sample data

        if fmt == 'json':
            export_data = {
                'exported_at': datetime.now(timezone.utc).isoformat(),
                'type': data_type,
                'data': {}
            }
            return jsonify(export_data), 200
        if fmt == 'csv':
            # TODO: Generate CSV
            return jsonify({'error': 'CSV export not yet implemented'}), 501
        if fmt == 'txt':
            # TODO: Generate text report
            return jsonify({'error': 'TXT export not yet implemented'}), 501
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
            'transcripts': 0,  # TODO: Add transcript count
            'recordings_count': len(recording_files),
            'storage': {
                'database_mb': round(db_size_mb, 2),
                'recordings_mb': round(recordings_size_mb, 2),
                'total_mb': round(db_size_mb + recordings_size_mb, 2)
            }
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

