"""ReconRaven REST API Server

Main Flask application that serves the REST API.
Integrates all endpoint blueprints and WebSocket support.
"""

from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS

from api.auth import auth
from api.v1 import database, demodulation, direction_finding, scanning, transcription, websocket


def create_app():
    """Create and configure Flask application."""
    app = Flask(__name__)

    # Enable CORS for local development
    CORS(app, resources={r'/api/*': {'origins': '*'}})

    # Register blueprints
    app.register_blueprint(scanning.bp)
    app.register_blueprint(demodulation.bp)
    app.register_blueprint(direction_finding.bp)
    app.register_blueprint(database.bp)
    app.register_blueprint(transcription.bp)

    # Initialize WebSocket
    socketio = websocket.init_socketio(app)

    # Root endpoint
    @app.route('/api/v1/', methods=['GET'])
    def api_root():
        """API information and available endpoints."""
        return jsonify(
            {
                'name': 'ReconRaven API',
                'version': '1.0.0',
                'status': 'operational',
                'endpoints': {
                    'scanning': '/api/v1/scan',
                    'demodulation': '/api/v1/demod',
                    'direction_finding': '/api/v1/df',
                    'database': '/api/v1/db',
                    'transcription': '/api/v1/transcribe',
                    'websocket': '/api/v1/ws',
                },
                'authentication': {
                    'methods': ['API Key', 'JWT'],
                    'api_key_header': 'X-API-Key',
                    'jwt_header': 'Authorization: Bearer <token>',
                },
                'documentation': '/api/v1/docs',
            }
        )

    # Health check endpoint (no auth required)
    @app.route('/api/v1/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({'status': 'healthy', 'api_version': '1.0.0'}), 200

    # Get API key endpoint (one-time, no auth)
    @app.route('/api/v1/auth/key', methods=['GET'])
    def get_api_key():
        """Retrieve API key (if available in file)."""
        key_file = Path('config/api_key.txt')
        if key_file.exists():
            with key_file.open('r') as f:
                content = f.read()
            return jsonify(
                {'message': 'API key found', 'key_file': str(key_file), 'content': content}
            ), 200
        return jsonify(
            {
                'error': 'API key file not found',
                'message': 'Start the API server to generate a new key',
            }
        ), 404

    # Generate JWT token endpoint
    @app.route('/api/v1/auth/token', methods=['POST'])
    @auth.require_auth
    def generate_token():
        """Generate JWT token (requires API key)."""
        token = auth.generate_jwt()
        return jsonify({'token': token, 'expires_in_hours': auth.jwt_expiry_hours}), 200

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Endpoint not found'}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({'error': 'Internal server error'}), 500

    return app, socketio


def run_api_server(host='0.0.0.0', port=5001, debug=False):
    """Run the API server."""
    app, socketio = create_app()

    print(f"\n{'='*60}")
    print('  ReconRaven REST API Server')
    print(f"{'='*60}")
    print(f'  API URL: http://{host}:{port}/api/v1/')
    print(f'  WebSocket: ws://{host}:{port}/api/v1/ws')
    print(f'  Health: http://{host}:{port}/api/v1/health')
    print(f'  Docs: http://{host}:{port}/api/v1/docs')
    print(f"{'='*60}\n")

    # Check if API key exists
    key_file = Path('config/api_key.txt')
    if key_file.exists():
        print(f'  API Key file: {key_file}')
        print(f'  Retrieve it: curl http://{host}:{port}/api/v1/auth/key')
    else:
        print('  Generating new API key on first start...')

    print(f"\n{'='*60}\n")

    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    run_api_server(debug=True)
