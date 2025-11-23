#!/usr/bin/env python3
"""
Run scanner with live dashboard integration
"""

from advanced_scanner import AdvancedScanner
from web.server import SDRDashboardServer
from database import get_db
import threading
import time

print("="*70)
print("ReconRaven - Live Scanning with Dashboard")
print("="*70)

# Start dashboard
print("\nStarting dashboard...")
dashboard = SDRDashboardServer({'host': '0.0.0.0', 'port': 5000})
dashboard.run_threaded()
time.sleep(2)

# Load existing data
db = get_db()
stats = db.get_statistics()
print(f"Database loaded: {stats['total_recordings']} recordings, {stats['identified_devices']} devices")

# Initialize dashboard with existing data
dashboard.update_state({
    'mode': 'scanning',
    'status': 'initializing',
    'baseline_count': stats['baseline_frequencies'],
    'device_count': stats['identified_devices'],
    'recording_count': stats['total_recordings'],
    'anomaly_count': stats['anomalies']
})

print(f"\nDashboard: http://localhost:5000")
print("="*70)

# Create scanner with dashboard integration
scanner = AdvancedScanner(dashboard_server=dashboard)

if not scanner.init_sdr():
    print("Failed to initialize SDR!")
    exit(1)

dashboard.update_state({'status': 'scanning'})

print("\nStarting live scan...")
print("Dashboard will update in real-time!")
print("Press Ctrl+C to stop\n")

try:
    scanner.monitor_with_recording()
except KeyboardInterrupt:
    print("\n\nStopping scanner...")
    dashboard.update_state({'status': 'stopped', 'mode': 'idle'})
    scanner.sdr.close()
    print("Done!")

