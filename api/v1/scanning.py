"""Scanning Control Endpoints

GET  /api/v1/scan/status    - Get current scan status
POST /api/v1/scan/start     - Start scanning
POST /api/v1/scan/stop      - Stop scanning
GET  /api/v1/scan/anomalies - Get recent anomalies
"""

from datetime import datetime

from flask import Blueprint, jsonify, request

from api.auth import auth
from reconraven.core.database import get_db


bp = Blueprint('scanning', __name__, url_prefix='/api/v1/scan')


@bp.route('/status', methods=['GET'])
@auth.require_auth
def get_status():
    """Get current scanning status."""
    try:
        db = get_db()

        # Check if scanner is running (would need to implement process check)
        # For now, return basic status
        status = {
            'scanning': False,  # TODO: Check if process running
            'uptime_seconds': 0,
            'current_frequency': None,
            'bands_scanned': [],
            'anomalies_detected': db.get_anomaly_count(),
            'baseline_frequencies': db.get_baseline_count(),
            'last_scan': None
        }

        return jsonify(status), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/start', methods=['POST'])
@auth.require_auth
def start_scan():
    """Start scanning with optional parameters.
    
    Body params:
        bands (list): Band names to scan (e.g. ['2m', '70cm'])
        rebuild_baseline (bool): Rebuild baseline before scanning
        dashboard (bool): Start web dashboard
    """
    try:
        data = request.get_json() or {}
        bands = data.get('bands', [])
        rebuild_baseline = data.get('rebuild_baseline', False)
        dashboard = data.get('dashboard', True)

        # TODO: Implement actual scanner start
        # This would spawn the scanner process
        # For now, return success

        return jsonify({
            'status': 'started',
            'bands': bands,
            'rebuild_baseline': rebuild_baseline,
            'dashboard': dashboard,
            'message': 'Scanner start requested'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/stop', methods=['POST'])
@auth.require_auth
def stop_scan():
    """Stop scanning and cleanup."""
    try:
        # TODO: Implement actual scanner stop
        # This would kill the scanner process gracefully

        return jsonify({
            'status': 'stopped',
            'message': 'Scanner stop requested'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/anomalies', methods=['GET'])
@auth.require_auth
def get_anomalies():
    """Get recent anomalies with filters.
    
    Query params:
        limit (int): Max results (default 50)
        since (str): ISO timestamp - only anomalies after this
        min_power (float): Minimum power level
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        since = request.args.get('since')
        min_power = request.args.get('min_power', type=float)

        db = get_db()
        anomalies = db.get_recent_anomalies(limit=limit)

        # Filter by timestamp if provided
        if since:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            anomalies = [
                a for a in anomalies
                if datetime.fromisoformat(a['timestamp'].replace('Z', '+00:00')) > since_dt
            ]

        # Filter by power if provided
        if min_power is not None:
            anomalies = [a for a in anomalies if a.get('power', 0) >= min_power]

        return jsonify({
            'count': len(anomalies),
            'anomalies': anomalies
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

