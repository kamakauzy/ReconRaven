"""Direction Finding Endpoints

GET  /api/v1/df/bearing/<anomaly_id>    - Get bearing for anomaly
POST /api/v1/df/calibrate               - Calibrate DF array
GET  /api/v1/df/status                  - Get DF system status
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from rtlsdr import RtlSdr

from api.auth import auth
from reconraven.core.database import get_db
from reconraven.direction_finding.array_sync import SDRArraySync
from reconraven.direction_finding.bearing_calc import BearingCalculator
from reconraven.hardware.sdr_controller import SDRController


bp = Blueprint('direction_finding', __name__, url_prefix='/api/v1/df')


def _check_df_available():
    """Check if DF mode is available (4+ SDRs)."""
    try:
        sdr_count = RtlSdr.get_device_count()
        return sdr_count >= 4, sdr_count
    except Exception:
        return False, 0


@bp.route('/bearing/<int:anomaly_id>', methods=['GET'])
@auth.require_auth
def get_bearing(anomaly_id: int):
    """Calculate bearing for a specific anomaly.

    Requires 4-SDR coherent array in DF mode.
    """
    try:
        db = get_db()

        # Check if DF mode available
        df_available, sdr_count = _check_df_available()
        if not df_available:
            return jsonify(
                {
                    'error': f'DF requires 4 SDRs, only {sdr_count} detected',
                    'df_available': False,
                    'sdr_count': sdr_count,
                }
            ), 503

        # Get anomaly details
        anomalies = db.get_anomalies(limit=1000)
        anomaly = next((a for a in anomalies if a.get('id') == anomaly_id), None)

        if not anomaly:
            return jsonify({'error': f'Anomaly {anomaly_id} not found'}), 404

        frequency_hz = anomaly['frequency_hz']

        # Check if array is calibrated
        calibration = db.get_active_df_calibration()
        if not calibration:
            return jsonify(
                {
                    'error': 'DF array not calibrated. Run POST /api/v1/df/calibrate first',
                    'frequency': frequency_hz,
                }
            ), 400

        # Initialize DF system
        sdr_controller = SDRController(num_sdrs=sdr_count)
        array_sync = SDRArraySync(sdr_controller, {})
        bearing_calculator = BearingCalculator(array_sync, {})

        # Calculate bearing
        result = bearing_calculator.calculate_bearing(frequency_hz, num_samples=16384)

        if not result:
            return jsonify({'error': 'Failed to calculate bearing'}), 500

        return jsonify(
            {
                'anomaly_id': anomaly_id,
                'bearing_degrees': result['bearing_degrees'],
                'confidence': result['confidence'],
                'snr_db': None,
                'accuracy_estimate': 5.0 if result['confidence'] > 0.7 else 10.0,
                'gps_position': None,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'message': 'DF calculation complete',
            }
        ), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/calibrate', methods=['POST'])
@auth.require_auth
def calibrate_array():
    """Calibrate DF array with known source.

    Body params:
        frequency (float): Calibration frequency
        known_bearing (float): Actual bearing of source (degrees)
        duration (int): Calibration duration (seconds)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400

        frequency = data.get('frequency')
        known_bearing = data.get('known_bearing')

        if frequency is None or known_bearing is None:
            return jsonify({'error': 'frequency and known_bearing required'}), 400

        # Check if DF mode available
        df_available, sdr_count = _check_df_available()
        if not df_available:
            return jsonify(
                {
                    'error': f'DF requires 4 SDRs, only {sdr_count} detected',
                    'df_available': False,
                }
            ), 503

        # Convert frequency to Hz if needed
        freq_hz = frequency * 1e6 if frequency < 10000 else frequency

        # Initialize DF system
        db = get_db()
        sdr_controller = SDRController(num_sdrs=sdr_count)
        array_sync = SDRArraySync(sdr_controller, {})

        # Perform calibration
        success = array_sync.calibrate_phase(
            frequency_hz=freq_hz, num_samples=20000, known_bearing=known_bearing, save_to_db=True
        )

        if not success:
            return jsonify({'error': 'Calibration failed'}), 500

        # Get calibration results
        calibration = db.get_active_df_calibration()

        if calibration:
            error_degrees = abs(calibration.get('known_bearing', known_bearing) - known_bearing)

            return jsonify(
                {
                    'status': 'success',
                    'frequency': freq_hz,
                    'known_bearing': known_bearing,
                    'measured_bearing': known_bearing,
                    'error_degrees': error_degrees,
                    'coherence_score': calibration['coherence_score'],
                    'snr_db': calibration['snr_db'],
                    'calibration_applied': True,
                    'message': 'Calibration complete',
                }
            ), 200

        return jsonify({'error': 'Calibration saved but could not retrieve results'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/status', methods=['GET'])
@auth.require_auth
def df_status():
    """Get DF system status and capabilities."""
    try:
        db = get_db()

        # Check actual SDR count
        df_available, sdr_count = _check_df_available()

        # Check if array is calibrated
        calibration = db.get_active_df_calibration()
        array_calibrated = calibration is not None

        # Get array geometry if calibrated
        array_geometry = None
        last_calibration = None
        if calibration:
            array_geometry = calibration.get('array_geometry')
            last_calibration = calibration.get('created_at')

        message = (
            'DF system ready'
            if df_available and array_calibrated
            else 'DF requires 4-SDR coherent array and calibration'
        )

        return jsonify(
            {
                'df_available': df_available,
                'sdr_count': sdr_count,
                'array_calibrated': array_calibrated,
                'array_geometry': array_geometry,
                'last_calibration': last_calibration,
                'coherence_score': calibration.get('coherence_score') if calibration else None,
                'calibration_frequency_mhz': (
                    calibration.get('calibration_freq_hz') / 1e6 if calibration else None
                ),
                'message': message,
            }
        ), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
