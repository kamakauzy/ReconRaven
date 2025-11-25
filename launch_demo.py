#!/usr/bin/env python3
"""
Launch dashboard server in demo mode
"""
import sys
sys.path.insert(0, '/home/brad/ReconRaven')

from web.server import SDRDashboardServer

if __name__ == '__main__':
    print("Starting ReconRaven Dashboard in DEMO MODE...")
    print("Dashboard will be available at http://localhost:5000")
    print("Press Ctrl+C to stop")
    
    server = SDRDashboardServer({'demo_mode': True, 'debug': True})
    server.run()

