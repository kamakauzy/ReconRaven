#!/usr/bin/env python3
"""
Standalone Dashboard Server
Runs the web interface for real-time monitoring
"""

import sys
import time
import logging
from web.server import create_app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    print("\n" + "="*70)
    print("ReconRaven Dashboard Server")
    print("="*70)
    print("\nStarting web server on http://0.0.0.0:5000")
    print("Access from:")
    print("  - This PC: http://localhost:5000")
    print("  - Other devices: http://<your-ip>:5000")
    print("\nPress Ctrl+C to stop\n")
    
    config = {
        'host': '0.0.0.0',
        'port': 5000,
        'debug': False
    }
    
    try:
        server = create_app(config)
        
        # Simulate some test data for demonstration
        server.update_state({
            'mode': 'monitoring',
            'scanning': True,
            'status': 'active'
        })
        
        # Add a test signal
        server.add_signal({
            'freq': 147.0e6,
            'power': -1.5,
            'band': '2m',
            'timestamp': time.time()
        })
        
        server.run()
        
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

