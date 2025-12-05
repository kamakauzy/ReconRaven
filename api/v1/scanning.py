"""Scanning Control Endpoints

GET  /api/v1/scan/status    - Get current scan status
POST /api/v1/scan/start     - Start scanning
POST /api/v1/scan/stop      - Stop scanning
GET  /api/v1/scan/anomalies - Get recent anomalies
"""

import multiprocessing
import os
import signal
import time
from datetime import datetime
from pathlib import Path

import psutil
from flask import Blueprint, jsonify, request

from api.auth import auth
from reconraven.core.database import get_db


bp = Blueprint('scanning', __name__, url_prefix='/api/v1/scan')

# Global scanner state
_scanner_process = None
_scanner_start_time = None
_scanner_pid_file = Path('reconraven_scanner.pid')


def _is_scanner_running():
    """Check if scanner process is running."""
    global _scanner_process, _scanner_pid_file

    # Check if we have a process reference
    if _scanner_process and _scanner_process.is_alive():
        return True

    # Check PID file
    if _scanner_pid_file.exists():
        try:
            with _scanner_pid_file.open('r') as f:
                pid = int(f.read().strip())
            # Check if process exists
            if psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                # Verify it's our scanner process
                if 'reconraven' in ' '.join(proc.cmdline()).lower():
                    return True
            # PID file exists but process doesn't - clean up
            _scanner_pid_file.unlink()
        except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return False


@bp.route('/status', methods=['GET'])
@auth.require_auth
def get_status():
    """Get current scanning status."""
    try:
        db = get_db()
        is_running = _is_scanner_running()

        # Calculate uptime
        uptime = 0
        if is_running and _scanner_start_time:
            uptime = int(time.time() - _scanner_start_time)

        status = {
            'scanning': is_running,
            'uptime_seconds': uptime,
            'current_frequency': None,
            'bands_scanned': [],
            'anomalies_detected': db.get_anomaly_count(),
            'baseline_frequencies': db.get_baseline_count(),
            'last_scan': None,
        }

        return jsonify(status), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _scanner_worker(rebuild_baseline):
    """Worker function to run scanner in separate process."""
    import sys

    from reconraven.core.scanner import AdvancedScanner

    try:
        # Write PID file
        _scanner_pid_file.write_text(str(os.getpid()))

        # Initialize scanner
        scanner = AdvancedScanner()
        if not scanner.init_sdr():
            return

        # Load or build baseline
        db = get_db()
        stats = db.get_statistics()

        if rebuild_baseline or stats['baseline_frequencies'] == 0:
            scanner.build_baseline()
        else:
            for entry in db.get_baseline():
                scanner.baseline[entry['frequency_hz']] = {
                    'mean': entry['power_dbm'],
                    'std': entry['std_dbm'] or 5.0,
                    'max': entry['power_dbm'] + 10,
                    'band': entry['band'],
                }

        # Run monitoring
        scanner.monitor_with_recording()

    except Exception as e:
        print(f'Scanner error: {e}', file=sys.stderr)
    finally:
        # Cleanup PID file
        if _scanner_pid_file.exists():
            _scanner_pid_file.unlink()


@bp.route('/start', methods=['POST'])
@auth.require_auth
def start_scan():
    """Start scanning with optional parameters.

    Body params:
        bands (list): Band names to scan (e.g. ['2m', '70cm'])
        rebuild_baseline (bool): Rebuild baseline before scanning
        dashboard (bool): Start web dashboard
    """
    global _scanner_process, _scanner_start_time

    try:
        # Check if already running
        if _is_scanner_running():
            return jsonify({'error': 'Scanner already running'}), 409

        data = request.get_json() or {}
        rebuild_baseline = data.get('rebuild_baseline', False)

        # Start scanner process
        _scanner_process = multiprocessing.Process(
            target=_scanner_worker, args=(rebuild_baseline,), daemon=False
        )
        _scanner_process.start()
        _scanner_start_time = time.time()

        # Wait briefly to ensure it started
        time.sleep(1)

        if _scanner_process.is_alive():
            return jsonify(
                {
                    'status': 'started',
                    'pid': _scanner_process.pid,
                    'rebuild_baseline': rebuild_baseline,
                    'message': 'Scanner started successfully',
                }
            ), 200

        return jsonify({'error': 'Scanner failed to start'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/stop', methods=['POST'])
@auth.require_auth
def stop_scan():
    """Stop scanning and cleanup."""
    global _scanner_process, _scanner_start_time

    try:
        if not _is_scanner_running():
            return jsonify({'error': 'Scanner not running'}), 404

        # Try graceful shutdown first
        if _scanner_process and _scanner_process.is_alive():
            _scanner_process.terminate()
            _scanner_process.join(timeout=5)

            # Force kill if still alive
            if _scanner_process.is_alive():
                _scanner_process.kill()
                _scanner_process.join()

        # Clean up PID file
        elif _scanner_pid_file.exists():
            try:
                with _scanner_pid_file.open('r') as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)
            except (ValueError, ProcessLookupError):
                pass
            finally:
                _scanner_pid_file.unlink()

        _scanner_process = None
        _scanner_start_time = None

        return jsonify({'status': 'stopped', 'message': 'Scanner stopped successfully'}), 200

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
                a
                for a in anomalies
                if datetime.fromisoformat(a['timestamp'].replace('Z', '+00:00')) > since_dt
            ]

        # Filter by power if provided
        if min_power is not None:
            anomalies = [a for a in anomalies if a.get('power', 0) >= min_power]

        return jsonify({'count': len(anomalies), 'anomalies': anomalies}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
