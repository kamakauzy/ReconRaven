#!/usr/bin/env python3
"""
Enhanced Dashboard with Database Integration
"""

from web.server import SDRDashboardServer
from database import get_db
import time

def start_dashboard():
    print("="*70)
    print("ReconRaven Dashboard with Database")
    print("="*70)
    
    # Get database
    db = get_db()
    
    # Load statistics
    stats = db.get_statistics()
    print(f"\nDatabase loaded:")
    print(f"  Recordings: {stats['total_recordings']}")
    print(f"  Storage: {stats['total_storage_mb']:.1f} MB")
    print(f"  Devices: {stats['identified_devices']}")
    print(f"  Anomalies: {stats['anomalies']}")
    
    # Create dashboard
    server = SDRDashboardServer({'host': '0.0.0.0', 'port': 5000})
    
    # Add recordings as "signals" for display first
    print(f"\nLoading recordings into dashboard...")
    recordings = db.get_recordings()
    for rec in recordings:
        server.add_signal({
            'frequency_hz': rec['frequency_hz'],
            'power_dbm': rec.get('power_dbm', -50),
            'bandwidth_hz': 25000,
            'band': rec['band'],
            'timestamp': rec['captured_at'],
            'filename': rec['filename']
        })
    
    print(f"  Added {len(recordings)} recordings to dashboard")
    
    # Load identified devices
    print(f"\nLoading identified devices...")
    devices = db.get_devices()
    device_list = []
    for dev in devices:
        device_list.append({
            'frequency_hz': dev['frequency_hz'],
            'name': dev['name'],
            'manufacturer': dev['manufacturer'],
            'type': dev['device_type'],
            'confidence': dev['confidence']
        })
        print(f"  {dev['frequency_hz']/1e6:.1f} MHz: {dev['name']}")
    
    # Update state with ALL data
    server.platform_state.update({
        'mode': 'monitoring',
        'status': 'active',
        'baseline_count': stats['baseline_frequencies'],
        'device_count': stats['identified_devices'],
        'recording_count': stats['total_recordings'],
        'anomaly_count': stats['anomalies'],
        'total_storage_gb': stats['total_storage_mb'] / 1024,
        'identified_devices': device_list
    })
    
    print(f"\nDashboard starting at http://localhost:5000")
    print("Press Ctrl+C to stop\n")
    
    # Start server
    server.run_threaded()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    start_dashboard()

