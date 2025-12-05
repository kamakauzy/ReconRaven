"""Voice Transcription Endpoints

POST /api/v1/transcribe/recording/<id>   - Transcribe specific recording
POST /api/v1/transcribe/batch            - Batch transcribe all
GET  /api/v1/transcribe/models           - List available Whisper models
"""

import threading
from pathlib import Path

from flask import Blueprint, jsonify, request

from api.auth import auth
from reconraven.core.database import get_db
from reconraven.utils.recording_manager import RecordingManager
from reconraven.voice.transcriber import VoiceTranscriber


bp = Blueprint('transcription', __name__, url_prefix='/api/v1/transcribe')

# Background batch transcription state
_batch_status = {'running': False, 'progress': 0, 'total': 0}


@bp.route('/recording/<int:recording_id>', methods=['POST'])
@auth.require_auth
def transcribe_recording(recording_id: int):
    """Transcribe a specific recording.

    Body params:
        model (str): Whisper model (tiny, base, small, medium, large)
        language (str): Force specific language (optional, auto-detect default)
    """
    try:
        data = request.get_json() or {}
        model = data.get('model', 'base')
        language = data.get('language')

        # Validate model
        valid_models = ['tiny', 'base', 'small', 'medium', 'large']
        if model not in valid_models:
            return jsonify({'error': f'Invalid model. Must be one of: {valid_models}'}), 400

        db = get_db()

        # Load recording from database
        recordings = db.get_recordings()
        recording = next((r for r in recordings if r['id'] == recording_id), None)

        if not recording:
            return jsonify({'error': f'Recording {recording_id} not found'}), 404

        # Get file path
        filename = recording['filename']
        recordings_dir = Path('recordings/audio')
        file_path = recordings_dir / filename

        if not file_path.exists():
            return jsonify({'error': f'Recording file not found: {filename}'}), 404

        # Convert to WAV if needed
        if filename.endswith('.npy'):
            recording_manager = RecordingManager(db)
            wav_file = recording_manager.demodulate_to_wav(str(file_path))
            if not wav_file:
                return jsonify({'error': 'Failed to convert recording to WAV'}), 500
            file_path = Path(wav_file)

        # Initialize transcriber
        transcriber = VoiceTranscriber(model_size=model)

        # Transcribe
        result = transcriber.transcribe_file(str(file_path), language=language)

        if 'error' in result:
            return jsonify({'error': result['error']}), 500

        return jsonify(
            {
                'recording_id': recording_id,
                'model': model,
                'status': 'success',
                'transcript': result,
                'message': 'Transcription complete',
            }
        ), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _batch_transcribe_worker(model, max_count):
    """Background worker for batch transcription."""
    global _batch_status

    try:
        db = get_db()
        recording_manager = RecordingManager(db)
        transcriber = VoiceTranscriber(model_size=model)

        # Get all recordings
        recordings = db.get_recordings()

        # Filter for WAV files or files that can be converted
        processable_recordings = [r for r in recordings if r['filename'].endswith(('.wav', '.npy'))]

        if max_count:
            processable_recordings = processable_recordings[:max_count]

        _batch_status['total'] = len(processable_recordings)
        _batch_status['progress'] = 0

        for recording in processable_recordings:
            filename = recording['filename']
            recordings_dir = Path('recordings/audio')
            file_path = recordings_dir / filename

            if not file_path.exists():
                continue

            # Convert to WAV if needed
            if filename.endswith('.npy'):
                wav_file = recording_manager.demodulate_to_wav(str(file_path))
                if not wav_file:
                    continue
                file_path = Path(wav_file)

            # Transcribe
            transcriber.transcribe_file(str(file_path))

            _batch_status['progress'] += 1

    finally:
        _batch_status['running'] = False


@bp.route('/batch', methods=['POST'])
@auth.require_auth
def transcribe_batch():
    """Batch transcribe all untranscribed recordings.

    Body params:
        model (str): Whisper model (default: base)
        max_count (int): Max recordings to process (default: all)
    """
    global _batch_status

    try:
        if _batch_status['running']:
            return jsonify(
                {
                    'error': 'Batch transcription already running',
                    'progress': _batch_status['progress'],
                    'total': _batch_status['total'],
                }
            ), 409

        data = request.get_json() or {}
        model = data.get('model', 'base')
        max_count = data.get('max_count')

        # Validate model
        valid_models = ['tiny', 'base', 'small', 'medium', 'large']
        if model not in valid_models:
            return jsonify({'error': f'Invalid model. Must be one of: {valid_models}'}), 400

        # Count recordings to process
        db = get_db()
        recordings = db.get_recordings()
        processable_count = len([r for r in recordings if r['filename'].endswith(('.wav', '.npy'))])

        if max_count:
            processable_count = min(processable_count, max_count)

        # Start batch processing in background thread
        _batch_status['running'] = True
        _batch_status['progress'] = 0
        _batch_status['total'] = processable_count

        thread = threading.Thread(target=_batch_transcribe_worker, args=(model, max_count))
        thread.daemon = True
        thread.start()

        # Estimate time (rough: 1 minute per recording)
        estimated_minutes = processable_count

        return jsonify(
            {
                'model': model,
                'status': 'started',
                'recordings_queued': processable_count,
                'estimated_time_minutes': estimated_minutes,
                'message': 'Batch transcription started',
            }
        ), 200

    except Exception as e:
        _batch_status['running'] = False
        return jsonify({'error': str(e)}), 500


@bp.route('/batch/status', methods=['GET'])
@auth.require_auth
def batch_status():
    """Get batch transcription status."""
    return jsonify(
        {
            'running': _batch_status['running'],
            'progress': _batch_status['progress'],
            'total': _batch_status['total'],
            'percent_complete': (
                (_batch_status['progress'] / _batch_status['total'] * 100)
                if _batch_status['total'] > 0
                else 0
            ),
        }
    ), 200


@bp.route('/models', methods=['GET'])
@auth.require_auth
def list_models():
    """List available Whisper models with details."""
    models = {
        'tiny': {
            'size_mb': 39,
            'speed': 'very_fast',
            'accuracy': '~70%',
            'ram_required_mb': 1000,
            'recommended_for': 'Quick testing',
        },
        'base': {
            'size_mb': 74,
            'speed': 'fast',
            'accuracy': '~80%',
            'ram_required_mb': 1500,
            'recommended_for': 'Default - good balance',
        },
        'small': {
            'size_mb': 244,
            'speed': 'medium',
            'accuracy': '~85%',
            'ram_required_mb': 2000,
            'recommended_for': 'Better accuracy',
        },
        'medium': {
            'size_mb': 769,
            'speed': 'slow',
            'accuracy': '~90%',
            'ram_required_mb': 4000,
            'recommended_for': 'High priority intel',
        },
        'large': {
            'size_mb': 1550,
            'speed': 'very_slow',
            'accuracy': '~95%',
            'ram_required_mb': 6000,
            'recommended_for': 'Maximum accuracy',
        },
    }

    return jsonify({'default': 'base', 'models': models}), 200
