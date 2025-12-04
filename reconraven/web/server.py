"""
Flask Web Server Module
Provides browser-based dashboard for SDR platform.
"""

import logging
import threading
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit


logger = logging.getLogger(__name__)


class SDRDashboardServer:
    """Web dashboard server for SDR platform."""

    def __init__(self, config: dict = None):
        """Initialize dashboard server."""
        self.config = config or {}
        self.app = Flask(
            __name__,
            template_folder='../visualization/templates',
            static_folder='../visualization/static',
        )
        self.app.config['SECRET_KEY'] = 'sdr-sigint-secret-key'
        CORS(self.app)
        self.socketio = SocketIO(
            self.app,
            cors_allowed_origins='*',
            max_http_buffer_size=10_000_000,  # 10MB buffer for large payloads
            ping_timeout=60,
            ping_interval=25,
        )

        self.host = self.config.get('host', '0.0.0.0')
        self.port = self.config.get('port', 5000)
        self.debug = self.config.get('debug', False)

        # Demo mode flag
        self.demo_mode = self.config.get('demo_mode', False)

        # Platform state
        self.platform_state = {
            'mode': 'unknown',
            'scanning': False,
            'signals': [],
            'bearings': [],
            'gps': None,
            'status': 'idle',
            'anomaly_count': 0,
            'recording_count': 0,
            'baseline_count': 0,
            'device_count': 0,
            'anomalies': [],
            'identified_devices': [],
        }

        self._setup_routes()
        self._setup_socketio()

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route('/')
        def index():
            """Main dashboard page."""
            from flask import make_response

            # Use enhanced dashboard with demo data
            response = make_response(render_template('dashboard_enhanced.html'))
            # Force browser to never cache this page
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response

        @self.app.route('/api/demo-data')
        def get_demo_data_endpoint():
            """Get demo data for UI testing."""
            return jsonify(self.get_demo_data())

        @self.app.route('/api/status')
        def get_status():
            """Get current platform status."""
            return jsonify(self.platform_state)

        @self.app.route('/api/signals')
        def get_signals():
            """Get detected signals."""
            return jsonify({'signals': self.platform_state['signals']})

        @self.app.route('/api/bearings')
        def get_bearings():
            """Get bearing data."""
            return jsonify({'bearings': self.platform_state['bearings']})

        @self.app.route('/api/gps')
        def get_gps():
            """Get GPS data."""
            return jsonify({'gps': self.platform_state['gps']})

        @self.app.route('/api/correlations')
        def get_correlations():
            """Get signal correlations."""
            from correlation_engine import CorrelationEngine

            engine = CorrelationEngine()
            correlations = engine.find_temporal_correlations()
            return jsonify({'correlations': correlations})

        @self.app.route('/api/sequences')
        def get_sequences():
            """Get sequential patterns."""
            from correlation_engine import CorrelationEngine

            engine = CorrelationEngine()
            sequences = engine.find_sequential_patterns()
            return jsonify({'sequences': sequences})

        @self.app.route('/api/network')
        def get_network():
            """Get device network map."""
            from correlation_engine import CorrelationEngine

            engine = CorrelationEngine()
            network = engine.build_device_network()
            return jsonify(network)

        @self.app.route('/api/behavioral-anomalies')
        def get_behavioral_anomalies():
            """Get behavioral anomalies."""
            from correlation_engine import CorrelationEngine

            engine = CorrelationEngine()
            anomalies = engine.detect_behavioral_anomalies()
            return jsonify({'anomalies': anomalies})

        @self.app.route('/api/behavior-profile')
        def get_behavior_profile():
            """Get behavioral profile for a frequency."""
            from correlation_engine import CorrelationEngine

            freq_mhz = request.args.get('freq', type=float)
            if not freq_mhz:
                return jsonify({'error': 'Frequency parameter required'}), 400

            engine = CorrelationEngine()
            profile = engine.get_device_behavior_profile(freq_mhz * 1e6)
            return jsonify(profile)

        @self.app.route('/api/voice-recordings')
        def get_voice_recordings():
            """Get list of voice recordings."""
            import glob
            import os

            recordings_dir = 'recordings/voice'
            if not os.path.exists(recordings_dir):
                return jsonify({'recordings': []})

            files = glob.glob(os.path.join(recordings_dir, '*.wav'))
            recordings = []

            for filepath in files:
                filename = os.path.basename(filepath)
                stat = os.stat(filepath)
                recordings.append(
                    {
                        'filename': filename,
                        'timestamp': filename.split('_')[1] if '_' in filename else 'unknown',
                        'frequency_mhz': filename.split('_')[0]
                        .replace('voice_', '')
                        .replace('MHz', '')
                        if '_' in filename
                        else 'unknown',
                        'size_mb': stat.st_size / 1024 / 1024,
                        'duration': 'unknown',  # Would need to parse WAV header
                    }
                )

            recordings.sort(key=lambda x: x['timestamp'], reverse=True)
            return jsonify({'recordings': recordings})

        @self.app.route('/api/timeline')
        def get_timeline():
            """Get activity timeline."""
            from database import get_db

            db = get_db()

            time_range = request.args.get('range', '24h')

            # Parse range
            hours = {'1h': 1, '6h': 6, '24h': 24, '7d': 168}[time_range]

            cursor = db.conn.cursor()
            cursor.execute(
                """
                SELECT 
                    frequency_hz,
                    power_dbm,
                    is_anomaly,
                    detected_at
                FROM signals
                WHERE detected_at > datetime('now', ?)
                ORDER BY detected_at
            """,
                (f'-{hours} hours',),
            )

            events = []
            for row in cursor.fetchall():
                events.append(
                    {
                        'frequency_hz': row[0],
                        'power_dbm': row[1],
                        'is_anomaly': bool(row[2]),
                        'detected_at': row[3],  # Changed from timestamp to detected_at
                        'band': self._get_band_for_frequency(row[0]),  # Add band info
                    }
                )

            return jsonify({'events': events, 'range': time_range})

        @self.app.route('/api/mode', methods=['POST'])
        def toggle_mode():
            """Toggle operating mode (if supported)."""
            # This would trigger mode change in main app
            return jsonify({'success': True})

        @self.app.route('/recordings/audio/<path:filename>')
        def serve_audio(filename):
            """Serve audio files for playback."""
            import os

            from flask import send_from_directory

            audio_dir = os.path.join(os.getcwd(), 'recordings', 'audio')
            return send_from_directory(audio_dir, filename)

    def _setup_socketio(self):
        """Setup SocketIO event handlers."""

        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            logger.info('Client connected to dashboard')
            emit('status_update', self.platform_state)

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            logger.info('Client disconnected from dashboard')

        @self.socketio.on('request_update')
        def handle_update_request():
            """Handle update request from client - SIMPLIFIED"""
            from database import get_db

            db = get_db()

            # Refresh stats from database
            stats = db.get_statistics()
            self.platform_state['baseline_count'] = stats['baseline_frequencies']
            self.platform_state['recording_count'] = stats['total_recordings']
            self.platform_state['anomaly_count'] = stats['anomalies']
            self.platform_state['device_count'] = stats['identified_devices']

            # Load anomalies (simple query, no joins) - REDUCED to prevent packet overflow
            anomalies = db.get_anomalies(limit=20)
            self.platform_state['anomalies'] = anomalies

            # Load identified signals (simple query, no joins) - REDUCED to prevent packet overflow
            devices = db.get_identified_signals(limit=15)
            self.platform_state['identified_devices'] = devices

            logger.info(f'[REFRESH] Loaded {len(anomalies)} anomalies, {len(devices)} devices')

            emit('status_update', self.platform_state)

        @self.socketio.on('promote_to_baseline')
        def handle_promote_to_baseline():
            """Auto-promote all identified devices to baseline."""
            from database import get_db

            db = get_db()

            promoted_count = db.auto_promote_devices_to_baseline()

            logger.info(f'Auto-promoted {promoted_count} devices to baseline')
            emit(
                'status_update',
                {'message': f'Auto-promoted {promoted_count} devices to baseline', 'success': True},
            )

            # Send updated state
            emit('status_update', self.platform_state)

        @self.socketio.on('promote_frequency')
        def handle_promote_frequency(data):
            """Promote a single frequency to baseline."""
            from database import get_db

            db = get_db()

            frequency = data.get('frequency')
            band = data.get('band', 'Unknown')

            if frequency:
                # Get band info
                freq_info = db.get_frequency_range_info(frequency)
                if freq_info:
                    band = freq_info['name']

                # Add to baseline with user_promoted flag
                db.add_baseline_frequency(
                    freq=frequency,
                    band=band,
                    power=-60.0,
                    std=5.0,
                    user_promoted=True,  # User explicitly promoted this
                )

                logger.info(f'Promoted {frequency/1e6:.3f} MHz to baseline')
                emit(
                    'status_update',
                    {'message': f'Promoted {frequency/1e6:.3f} MHz to baseline', 'success': True},
                )

        @self.socketio.on('start_df')
        def handle_start_df(data):
            """Start direction finding on a frequency."""
            frequency = data.get('frequency')
            logger.info(f'DF requested for {frequency/1e6:.3f} MHz')

            # In future: trigger actual DF mode
            emit(
                'status_update',
                {'message': 'DF not yet implemented (requires 4 SDRs)', 'success': False},
            )

        @self.socketio.on('analyze_signal')
        def handle_analyze_signal(data):
            """Trigger on-demand signal analysis."""
            import os
            import subprocess

            from database import get_db

            recording_file = data.get('recording_file')
            frequency_hz = data.get('frequency_hz')

            if not recording_file:
                emit('analysis_error', {'error': 'No recording file specified'})
                return

            logger.info(f'On-demand analysis requested for {recording_file}')

            # Notify client that analysis started
            emit('analysis_started', {'recording_file': recording_file})

            # Run field_analyzer.py in subprocess
            try:
                npy_path = os.path.join('recordings', 'audio', recording_file)
                if not os.path.exists(npy_path):
                    emit('analysis_error', {'error': f'Recording file not found: {npy_path}'})
                    return

                result = subprocess.run(
                    ['python', 'field_analyzer.py', npy_path],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,  # 2 minutes
                )

                if result.returncode == 0:
                    # Analysis successful - fetch results from database
                    db = get_db()

                    # Get the signal with full analysis data
                    anomalies = db.get_anomalies(limit=1000)
                    signal = None
                    for a in anomalies:
                        if (
                            a.get('recording_file') == recording_file
                            or a.get('recording_filename') == recording_file
                        ):
                            signal = a
                            break

                    if signal:
                        emit('analysis_complete', signal)
                        logger.info(f'Analysis complete for {recording_file}')
                    else:
                        emit(
                            'analysis_error',
                            {'error': 'Analysis completed but results not found in database'},
                        )
                else:
                    emit('analysis_error', {'error': f'Analysis failed: {result.stderr}'})
                    logger.error(f'Analysis failed: {result.stderr}')

            except subprocess.TimeoutExpired:
                emit('analysis_error', {'error': 'Analysis timed out (>2 minutes)'})
                logger.error(f'Analysis timeout for {recording_file}')
            except Exception as e:
                emit('analysis_error', {'error': str(e)})
                logger.error(f'Analysis exception: {e}')

        @self.socketio.on('ignore_device')
        def handle_ignore_device(data):
            """Ignore/suppress a device."""
            from database import get_db

            db = get_db()

            frequency_hz = data.get('frequency_hz')
            if not frequency_hz:
                emit('status_update', {'message': 'No frequency specified', 'success': False})
                return

            db.ignore_device(frequency_hz)
            logger.info(f'Ignored device at {frequency_hz/1e6:.3f} MHz')

            emit(
                'status_update',
                {
                    'message': f'Ignored device at {frequency_hz/1e6:.3f} MHz (added to baseline)',
                    'success': True,
                },
            )

        @self.socketio.on('start_voice_monitor')
        def handle_start_voice_monitor(data):
            """Start voice monitoring."""

            frequency_mhz = data.get('frequency_mhz')
            mode = data.get('mode', 'FM')
            auto_record = data.get('auto_record', True)

            if not frequency_mhz:
                emit('voice_status', {'status': 'error', 'message': 'No frequency specified'})
                return

            # TODO: Implement voice monitoring
            emit('voice_status', {'status': 'monitoring', 'frequency': frequency_mhz, 'mode': mode})

        @self.socketio.on('stop_voice_monitor')
        def handle_stop_voice_monitor():
            """Stop voice monitoring."""
            # TODO: Implement stop voice monitoring
            emit('voice_status', {'status': 'idle'})

        @self.socketio.on('request_transcripts')
        def handle_request_transcripts(data):
            """Get all transcripts from database."""
            from database import get_db

            db = get_db()

            try:
                transcripts = db.get_all_transcripts(limit=100)
                emit('transcripts_update', {'transcripts': transcripts})
            except Exception as e:
                logger.error(f'Failed to load transcripts: {e}')
                emit('transcripts_update', {'transcripts': []})

        @self.socketio.on('search_transcripts')
        def handle_search_transcripts(data):
            """Search transcripts by keyword."""
            from database import get_db

            db = get_db()

            keyword = data.get('keyword', '').strip()
            if not keyword:
                emit('transcripts_update', {'transcripts': []})
                return

            try:
                results = db.search_transcripts(keyword, limit=50)
                emit('transcripts_update', {'transcripts': results})
            except Exception as e:
                logger.error(f'Failed to search transcripts: {e}')
                emit('transcripts_update', {'transcripts': []})

        @self.socketio.on('stop_voice_monitor')
        def handle_stop_voice_monitor():
            """Stop voice monitoring."""
            if hasattr(self, 'voice_monitor'):
                self.voice_monitor.stop_monitoring()
                emit('status_update', {'message': 'Voice monitor stopped', 'success': True})

        @self.socketio.on('scan_voice_band')
        def handle_scan_voice_band(data):
            """Scan a voice band."""
            import threading

            from voice_monitor import VoiceMonitor

            band = data.get('band', '2m')

            if not hasattr(self, 'voice_monitor'):
                self.voice_monitor = VoiceMonitor()

            # Run scan in background thread
            scan_thread = threading.Thread(
                target=self.voice_monitor.scan_voice_bands, args=(band, 5), daemon=True
            )
            scan_thread.start()

            emit(
                'status_update',
                {'message': f'Started scanning {band.upper()} band', 'success': True},
            )

    def update_state(self, state_update: Dict[str, Any]):
        """Update platform state and broadcast to clients - SIMPLIFIED"""
        # Just update what's provided
        self.platform_state.update(state_update)

        # ALWAYS load fresh data from DB when emitting
        try:
            from database import get_db

            db = get_db()

            anomalies = db.get_anomalies(limit=20)
            devices = db.get_identified_signals(limit=15)

            self.platform_state['anomalies'] = anomalies
            self.platform_state['identified_devices'] = devices

            # Update counts too
            stats = db.get_statistics()
            self.platform_state['anomaly_count'] = stats['anomalies']
            self.platform_state['device_count'] = stats['identified_devices']

        except Exception as e:
            logger.error(f'[UPDATE_STATE] Error loading from DB: {e}')

        # Broadcast to all connected clients
        self.socketio.emit('status_update', self.platform_state)

    def add_signal(self, signal_data: Dict[str, Any]):
        """Add detected signal to dashboard.

        Args:
            signal_data: Signal information dictionary
        """
        self.platform_state['signals'].append(signal_data)

        # Keep only last 100 signals
        if len(self.platform_state['signals']) > 100:
            self.platform_state['signals'] = self.platform_state['signals'][-100:]

        self.socketio.emit('new_signal', signal_data)

    def add_bearing(self, bearing_data: Dict[str, Any]):
        """Add bearing data to dashboard.

        Args:
            bearing_data: Bearing information dictionary
        """
        self.platform_state['bearings'].append(bearing_data)

        # Keep only last 50 bearings
        if len(self.platform_state['bearings']) > 50:
            self.platform_state['bearings'] = self.platform_state['bearings'][-50:]

        self.socketio.emit('new_bearing', bearing_data)

    def update_gps(self, gps_data: Dict[str, Any]):
        """Update GPS data on dashboard.

        Args:
            gps_data: GPS information dictionary
        """
        self.platform_state['gps'] = gps_data
        self.socketio.emit('gps_update', gps_data)

    def _get_band_for_frequency(self, freq_hz):
        """Helper to determine band from frequency."""
        if 144e6 <= freq_hz <= 148e6:
            return '2m'
        if 420e6 <= freq_hz <= 450e6:
            return '70cm'
        if 433e6 <= freq_hz <= 435e6:
            return 'ISM433'
        if 902e6 <= freq_hz <= 928e6:
            return 'ISM915'
        return 'Unknown'

    def get_demo_data(self):
        """Generate realistic demo data based on actual testing."""
        import random
        from datetime import datetime, timedelta

        demo_signals = []
        base_time = datetime.now()

        # ISM 915 MHz signals (like we actually detected) - ANOMALIES
        for i, freq in enumerate([907.8e6, 907.9e6, 915.2e6, 921.5e6, 926.1e6]):
            demo_signals.append(
                {
                    'id': i + 1,
                    'frequency_hz': freq,
                    'band': 'ISM915',
                    'power_dbm': random.uniform(-10, -4),
                    'baseline_power_dbm': random.uniform(-25, -20),
                    'delta_db': random.uniform(12, 18),
                    'is_anomaly': True,
                    'is_baseline': False,
                    'recorded': True,
                    'recording_file': f'ISM915_{freq/1e6:.1f}MHz_test.npy',
                    'device_name': random.choice(
                        [
                            'Garage Door Opener',
                            'Wireless Sensor',
                            'Security System',
                            'Unknown ISM Device',
                        ]
                    ),
                    'device_type': 'Remote Control',
                    'device_confidence': random.uniform(0.7, 0.95),
                    'detected_at': (
                        base_time - timedelta(minutes=random.randint(1, 60))
                    ).isoformat(),
                    'detection_count': random.randint(5, 50),
                }
            )

        # 2m Amateur Band signals - ANOMALIES
        for i, freq in enumerate(
            [146.520e6, 146.562e6, 147.420e6, 147.540e6], start=len(demo_signals)
        ):
            demo_signals.append(
                {
                    'id': i + 1,
                    'frequency_hz': freq,
                    'band': '2m',
                    'power_dbm': random.uniform(-35, -25),
                    'baseline_power_dbm': random.uniform(-75, -65),
                    'delta_db': random.uniform(30, 45),
                    'is_anomaly': True,
                    'is_baseline': False,
                    'recorded': True,
                    'recording_file': f'2m_{freq/1e6:.3f}MHz_voice.wav',
                    'device_name': 'Amateur Radio FM',
                    'device_type': 'Voice Transmission',
                    'device_confidence': random.uniform(0.85, 0.98),
                    'detected_at': (
                        base_time - timedelta(minutes=random.randint(1, 30))
                    ).isoformat(),
                    'detection_count': random.randint(2, 15),
                }
            )

        # 70cm signals - ANOMALIES
        for i, freq in enumerate([446.000e6, 446.500e6, 433.920e6], start=len(demo_signals)):
            demo_signals.append(
                {
                    'id': i + 1,
                    'frequency_hz': freq,
                    'band': '70cm' if freq > 440e6 else 'ISM433',
                    'power_dbm': random.uniform(-40, -30),
                    'baseline_power_dbm': random.uniform(-70, -60),
                    'delta_db': random.uniform(20, 35),
                    'is_anomaly': True,
                    'is_baseline': False,
                    'recorded': random.choice([True, False]),
                    'recording_file': f'70cm_{freq/1e6:.3f}MHz.npy'
                    if random.random() > 0.5
                    else None,
                    'device_name': random.choice(
                        ['FRS Radio', 'Walkie-Talkie', 'Remote Control', None]
                    ),
                    'device_type': random.choice(['Voice', 'Digital', 'FSK', None]),
                    'device_confidence': random.uniform(0.6, 0.9)
                    if random.random() > 0.3
                    else None,
                    'detected_at': (
                        base_time - timedelta(minutes=random.randint(1, 120))
                    ).isoformat(),
                    'detection_count': random.randint(1, 8),
                }
            )

        # BASELINE SIGNALS - Normal background noise and expected transmissions
        baseline_freqs = [
            (144.390e6, '2m'),  # APRS frequency
            (145.800e6, '2m'),  # Common repeater input
            (146.940e6, '2m'),  # Repeater output
            (432.100e6, '70cm'),  # Satellite downlink
            (435.000e6, '70cm'),  # ISS downlink
            (441.000e6, '70cm'),  # Common repeater
            (902.500e6, 'ISM915'),  # Background ISM
            (904.200e6, 'ISM915'),  # Weather station
            (910.000e6, 'ISM915'),  # Ambient ISM
            (924.500e6, 'ISM915'),  # TPMS sensors
            (433.075e6, 'ISM433'),  # Weather sensors
            (433.920e6, 'ISM433'),  # Background remote
        ]

        for i, (freq, band) in enumerate(baseline_freqs, start=len(demo_signals)):
            baseline_power = random.uniform(-75, -65)
            current_power = baseline_power + random.uniform(-3, 3)  # Within normal variance

            demo_signals.append(
                {
                    'id': i + 1,
                    'frequency_hz': freq,
                    'band': band,
                    'power_dbm': current_power,
                    'baseline_power_dbm': baseline_power,
                    'delta_db': abs(current_power - baseline_power),
                    'is_anomaly': False,
                    'is_baseline': True,
                    'recorded': False,
                    'recording_file': None,
                    'device_name': None,
                    'device_type': None,
                    'device_confidence': None,
                    'detected_at': (
                        base_time - timedelta(minutes=random.randint(5, 180))
                    ).isoformat(),
                    'detection_count': random.randint(50, 500),  # High count = consistent baseline
                }
            )

        # Generate SDR assignments (4 SDRs for DF mode)
        demo_sdr_assignments = [
            {
                'index': 0,
                'freq_count': 224,
                'bands': [
                    '2m: 144.00 - 147.90 MHz (14 freqs)',
                    '70cm: 420.20 - 449.90 MHz (123 freqs)',
                    'ISM915: 902.10 - 927.90 MHz (87 freqs)',
                ],
                'status': 'active',
                'current_freq': 146.520e6,
                'signal_strength': random.uniform(-50, -30),
            },
            {
                'index': 1,
                'freq_count': 223,
                'bands': [
                    '2m: 144.10 - 147.70 MHz (13 freqs)',
                    '70cm: 420.00 - 449.70 MHz (124 freqs)',
                    'ISM915: 902.20 - 927.70 MHz (86 freqs)',
                ],
                'status': 'active',
                'current_freq': 907.9e6,
                'signal_strength': random.uniform(-10, -4),
            },
            {
                'index': 2,
                'freq_count': 223,
                'bands': [
                    '2m: 144.20 - 147.80 MHz (13 freqs)',
                    '70cm: 420.10 - 449.80 MHz (123 freqs)',
                    'ISM915: 902.00 - 927.80 MHz (87 freqs)',
                ],
                'status': 'active',
                'current_freq': 433.920e6,
                'signal_strength': random.uniform(-45, -35),
            },
            {
                'index': 3,
                'freq_count': 210,
                'bands': [
                    '2m: 144.30 - 147.60 MHz (12 freqs)',
                    '70cm: 420.30 - 449.60 MHz (120 freqs)',
                    'ISM915: 902.30 - 927.60 MHz (78 freqs)',
                ],
                'status': 'active',
                'current_freq': 146.562e6,
                'signal_strength': random.uniform(-40, -25),
            },
        ]

        # Generate bearing data for DF visualization
        demo_bearings = [
            {
                'frequency_hz': 907.8e6,
                'bearing': 45.0,
                'confidence': 0.85,
                'timestamp': (base_time - timedelta(minutes=2)).isoformat(),
            },
            {
                'frequency_hz': 146.520e6,
                'bearing': 135.0,
                'confidence': 0.92,
                'timestamp': (base_time - timedelta(minutes=5)).isoformat(),
            },
            {
                'frequency_hz': 433.920e6,
                'bearing': 270.0,
                'confidence': 0.78,
                'timestamp': (base_time - timedelta(minutes=8)).isoformat(),
            },
        ]

        return {
            'mode': 'df',  # Direction Finding mode with 4 SDRs
            'status': 'monitoring',
            'scanning': True,
            'sdr_count': 4,
            'active_count': len([s for s in demo_signals if s['detection_count'] > 5]),
            'anomaly_count': len(demo_signals),
            'recording_count': len([s for s in demo_signals if s['recorded']]),
            'device_count': len([s for s in demo_signals if s.get('device_name')]),
            'baseline_count': 653,
            'anomalies': demo_signals,
            'identified_devices': [s for s in demo_signals if s.get('device_name')],
            'sdr_assignments': demo_sdr_assignments,
            'bearings': demo_bearings,
            'gps': {
                'latitude': 40.7128,
                'longitude': -74.0060,
                'altitude': 10.5,
                'satellites': 8,
                'fix_quality': 'GPS',
            },
        }

    def run(self):
        """Run the web server."""
        logger.info(f'Starting dashboard server on {self.host}:{self.port}')
        self.socketio.run(
            self.app, host=self.host, port=self.port, debug=self.debug, use_reloader=False
        )

    def run_threaded(self):
        """Run server in a separate thread."""
        server_thread = threading.Thread(target=self.run, daemon=True)
        server_thread.start()
        logger.info('Dashboard server started in background')
        return server_thread


def create_app(config: dict = None) -> SDRDashboardServer:
    """Create dashboard server instance.

    Args:
        config: Server configuration dictionary

    Returns:
        SDRDashboardServer instance
    """
    return SDRDashboardServer(config)


def start_server(config: dict = None) -> SDRDashboardServer:
    """Start dashboard server.

    Args:
        config: Server configuration dictionary

    Returns:
        Running SDRDashboardServer instance
    """
    server = create_app(config)
    server.run_threaded()
    return server
