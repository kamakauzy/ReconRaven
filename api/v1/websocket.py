"""WebSocket Real-Time Updates

WebSocket endpoint: /api/v1/ws/updates

Pushes real-time events:
- New anomaly detected
- Scan progress updates
- Transcription completed
- Device identified
"""

from datetime import datetime, timezone

from flask import Blueprint
from flask_socketio import SocketIO, emit, join_room, leave_room


# Will be initialized by main app
socketio = None


bp = Blueprint('websocket', __name__)


def init_socketio(app):
    """Initialize SocketIO with Flask app."""
    global socketio
    socketio = SocketIO(
        app,
        cors_allowed_origins='*',  # TODO: Restrict in production
        async_mode='threading',
        logger=False,
        engineio_logger=False
    )

    # Register event handlers
    @socketio.on('connect', namespace='/api/v1/ws')
    def handle_connect():
        """Client connected to WebSocket."""
        # TODO: Verify auth token
        emit('connected', {'message': 'Connected to ReconRaven API', 'timestamp': datetime.now(timezone.utc).isoformat()})

    @socketio.on('disconnect', namespace='/api/v1/ws')
    def handle_disconnect():
        """Client disconnected."""

    @socketio.on('subscribe', namespace='/api/v1/ws')
    def handle_subscribe(data):
        """Subscribe to specific event types."""
        event_types = data.get('events', [])
        for event_type in event_types:
            join_room(event_type)
        emit('subscribed', {'events': event_types})

    @socketio.on('unsubscribe', namespace='/api/v1/ws')
    def handle_unsubscribe(data):
        """Unsubscribe from event types."""
        event_types = data.get('events', [])
        for event_type in event_types:
            leave_room(event_type)
        emit('unsubscribed', {'events': event_types})

    return socketio


def emit_anomaly_detected(anomaly_data: dict):
    """Emit anomaly detection event."""
    if socketio:
        socketio.emit(
            'anomaly_detected',
            {
                'type': 'anomaly_detected',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': anomaly_data
            },
            namespace='/api/v1/ws',
            room='anomalies'
        )


def emit_scan_progress(progress_data: dict):
    """Emit scan progress update."""
    if socketio:
        socketio.emit(
            'scan_progress',
            {
                'type': 'scan_progress',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': progress_data
            },
            namespace='/api/v1/ws',
            room='scan'
        )


def emit_transcription_complete(transcript_data: dict):
    """Emit transcription completion event."""
    if socketio:
        socketio.emit(
            'transcription_complete',
            {
                'type': 'transcription_complete',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': transcript_data
            },
            namespace='/api/v1/ws',
            room='transcripts'
        )


def emit_device_identified(device_data: dict):
    """Emit device identification event."""
    if socketio:
        socketio.emit(
            'device_identified',
            {
                'type': 'device_identified',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': device_data
            },
            namespace='/api/v1/ws',
            room='devices'
        )

