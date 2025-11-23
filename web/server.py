"""
Flask Web Server Module
Provides browser-based dashboard for SDR platform.
"""

import logging
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SDRDashboardServer:
    """Web dashboard server for SDR platform."""
    
    def __init__(self, config: dict = None):
        """Initialize dashboard server."""
        self.config = config or {}
        self.app = Flask(__name__, template_folder='../visualization/templates')
        self.app.config['SECRET_KEY'] = 'sdr-sigint-secret-key'
        CORS(self.app)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        self.host = self.config.get('host', '0.0.0.0')
        self.port = self.config.get('port', 5000)
        self.debug = self.config.get('debug', False)
        
        # Platform state
        self.platform_state = {
            'mode': 'unknown',
            'scanning': False,
            'signals': [],
            'bearings': [],
            'gps': None,
            'status': 'idle'
        }
        
        self._setup_routes()
        self._setup_socketio()
        
    def _setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/')
        def index():
            """Main dashboard page."""
            return render_template('dashboard.html')
        
        @self.app.route('/api/status')
        def get_status():
            """Get current platform status."""
            return jsonify(self.platform_state)
        
        @self.app.route('/api/signals')
        def get_signals():
            """Get detected signals."""
            return jsonify({
                'signals': self.platform_state['signals']
            })
        
        @self.app.route('/api/bearings')
        def get_bearings():
            """Get bearing data."""
            return jsonify({
                'bearings': self.platform_state['bearings']
            })
        
        @self.app.route('/api/gps')
        def get_gps():
            """Get GPS data."""
            return jsonify({
                'gps': self.platform_state['gps']
            })
        
        @self.app.route('/api/mode', methods=['POST'])
        def toggle_mode():
            """Toggle operating mode (if supported)."""
            # This would trigger mode change in main app
            return jsonify({'success': True})
    
    def _setup_socketio(self):
        """Setup SocketIO event handlers."""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            logger.info("Client connected to dashboard")
            emit('status_update', self.platform_state)
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            logger.info("Client disconnected from dashboard")
        
        @self.socketio.on('request_update')
        def handle_update_request():
            """Handle update request from client."""
            from database import get_db
            db = get_db()
            
            # Refresh data from database
            stats = db.get_statistics()
            self.platform_state['baseline_count'] = stats['baseline_frequencies']
            self.platform_state['anomaly_count'] = stats['anomalies']
            self.platform_state['device_count'] = stats['identified_devices']
            self.platform_state['recording_count'] = stats['total_recordings']
            self.platform_state['identified_devices'] = db.get_devices()
            
            emit('status_update', self.platform_state)
        
        @self.socketio.on('promote_to_baseline')
        def handle_promote_to_baseline():
            """Promote identified devices to baseline."""
            from database import get_db
            db = get_db()
            
            # Get all identified devices
            devices = db.get_devices()
            promoted_count = 0
            
            for device in devices:
                # Get band info for this frequency
                freq_info = db.get_frequency_range_info(device['frequency_hz'])
                band_name = freq_info['name'] if freq_info else 'Unknown'
                
                # Add device frequency to baseline
                db.add_baseline_frequency(
                    freq=device['frequency_hz'],
                    band=band_name,
                    power=-60.0,  # Default expected power
                    std=5.0       # Default standard deviation
                )
                promoted_count += 1
            
            logger.info(f"Promoted {promoted_count} devices to baseline")
            emit('status_update', {
                'message': f'Promoted {promoted_count} devices to baseline',
                'success': True
            })
            
            # Send updated state
            emit('status_update', self.platform_state)
    
    def update_state(self, state_update: Dict[str, Any]):
        """Update platform state and broadcast to clients.
        
        Args:
            state_update: Dictionary with state updates
        """
        self.platform_state.update(state_update)
        
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
    
    def run(self):
        """Run the web server."""
        logger.info(f"Starting dashboard server on {self.host}:{self.port}")
        self.socketio.run(
            self.app,
            host=self.host,
            port=self.port,
            debug=self.debug,
            use_reloader=False
        )
    
    def run_threaded(self):
        """Run server in a separate thread."""
        server_thread = threading.Thread(target=self.run, daemon=True)
        server_thread.start()
        logger.info("Dashboard server started in background")
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

