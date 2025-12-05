"""API Authentication & Authorization

Handles API key generation, JWT tokens, and request validation.
Local-only by default with optional JWT for mobile clients.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

import jwt
import yaml
from flask import jsonify, request


class APIAuth:
    """Manages API authentication and authorization."""

    def __init__(self, config_path: Path = Path('config/api_config.yaml')):
        self.config_path = config_path
        self.config = self._load_or_create_config()
        self.api_key_hash = self.config['api_key_hash']
        self.jwt_secret = self.config['jwt_secret']
        self.jwt_expiry_hours = self.config.get('jwt_expiry_hours', 24)

    def _load_or_create_config(self) -> dict:
        """Load existing config or create new with generated keys."""
        if self.config_path.exists():
            with self.config_path.open('r') as f:
                return yaml.safe_load(f)

        # Generate new keys
        api_key = secrets.token_urlsafe(32)
        jwt_secret = secrets.token_urlsafe(64)

        config = {
            'api_key_hash': hashlib.sha256(api_key.encode()).hexdigest(),
            'jwt_secret': jwt_secret,
            'jwt_expiry_hours': 24,
            'rate_limit_per_second': 10,
            'allowed_origins': ['http://localhost:5000'],
            'created': datetime.now(timezone.utc).isoformat(),
        }

        # Save config
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open('w') as f:
            yaml.dump(config, f, default_flow_style=False)

        # Save raw API key separately (one-time display)
        key_file = self.config_path.parent / 'api_key.txt'
        with key_file.open('w') as f:
            f.write(f"API Key (save this - won't be shown again):\n{api_key}\n")

        print(f'[API] Generated new API key: {api_key}')
        print(f'[API] Saved to: {key_file}')

        return config

    def verify_api_key(self, provided_key: str) -> bool:
        """Verify provided API key matches stored hash."""
        if not provided_key:
            return False
        key_hash = hashlib.sha256(provided_key.encode()).hexdigest()
        return secrets.compare_digest(key_hash, self.api_key_hash)

    def generate_jwt(self, user_data: dict | None = None) -> str:
        """Generate JWT token for session auth."""
        payload = {
            'exp': datetime.now(timezone.utc) + timedelta(hours=self.jwt_expiry_hours),
            'iat': datetime.now(timezone.utc),
            'sub': 'reconraven_client',
            'data': user_data or {},
        }
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')

    def verify_jwt(self, token: str) -> dict | None:
        """Verify JWT token and return payload."""
        try:
            return jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def require_auth(self, f):
        """Decorator to require API key or valid JWT."""

        @wraps(f)
        def decorated(*args, **kwargs):
            # Check for API key in header
            api_key = request.headers.get('X-API-Key')
            if api_key and self.verify_api_key(api_key):
                return f(*args, **kwargs)

            # Check for JWT token
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                payload = self.verify_jwt(token)
                if payload:
                    request.jwt_payload = payload
                    return f(*args, **kwargs)

            return jsonify(
                {'error': 'Unauthorized', 'message': 'Valid API key or JWT required'}
            ), 401

        return decorated


# Global instance
auth = APIAuth()
