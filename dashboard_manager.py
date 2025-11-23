#!/usr/bin/env python3
"""
Enhanced Dashboard Integration
Connects scanner to web dashboard for real-time visualization
"""

import json
import os
import glob
from web.server import SDRDashboardServer
from threading import Thread
import time

class DashboardManager:
    """Manages dashboard updates from scanner"""
    
    def __init__(self, dashboard_server):
        self.server = dashboard_server
        self.baseline = {}
        self.devices = {}
        self.recordings = []
        
    def load_baseline(self, baseline_file='baseline.json'):
        """Load baseline from file"""
        if os.path.exists(baseline_file):
            with open(baseline_file, 'r') as f:
                self.baseline = json.load(f)
                self.server.update_state({
                    'baseline_loaded': True,
                    'baseline_freqs': len(self.baseline)
                })
    
    def add_baseline_freq(self, freq, power, band):
        """Add frequency to baseline"""
        self.baseline[str(freq)] = {
            'freq': freq,
            'power': power,
            'band': band,
            'normal': True
        }
        
        # Save baseline
        with open('baseline.json', 'w') as f:
            json.dump(self.baseline, f, indent=2)
    
    def report_anomaly(self, freq, power, baseline_power, band):
        """Report anomaly to dashboard"""
        delta = power - baseline_power
        
        signal_data = {
            'frequency_hz': freq,
            'power_dbm': power,
            'baseline_dbm': baseline_power,
            'delta_db': delta,
            'band': band,
            'anomaly': True,
            'timestamp': time.time()
        }
        
        self.server.add_signal(signal_data)
        
    def report_recording(self, filename, freq, power, band):
        """Report new recording"""
        recording_data = {
            'filename': filename,
            'frequency_hz': freq,
            'power_dbm': power,
            'band': band,
            'timestamp': time.time()
        }
        
        self.recordings.append(recording_data)
        self.server.update_state({
            'recordings': len(self.recordings),
            'last_recording': recording_data
        })
    
    def add_identified_device(self, freq, device_info):
        """Add identified device to dashboard"""
        device_key = f"{freq}_{device_info.get('type', 'unknown')}"
        
        self.devices[device_key] = {
            'frequency_hz': freq,
            'name': device_info.get('name', 'Unknown'),
            'type': device_info.get('type', 'unknown'),
            'manufacturer': device_info.get('manufacturer', 'Unknown'),
            'confidence': device_info.get('confidence', 0),
            'first_seen': device_info.get('timestamp', time.time())
        }
        
        self.server.update_state({
            'identified_devices': list(self.devices.values())
        })
    
    def load_analysis_results(self):
        """Load analysis results from recordings folder"""
        analysis_files = glob.glob('recordings/audio/*_complete_analysis.json')
        
        for filepath in analysis_files:
            try:
                with open(filepath, 'r') as f:
                    analysis = json.load(f)
                    
                    # Extract device info if identified
                    if analysis.get('confidence', 0) >= 0.6:
                        # Get frequency from filename
                        filename = os.path.basename(filepath)
                        freq_str = filename.split('_')[1].replace('MHz', '')
                        freq = float(freq_str.replace('.', '')) * 1e6
                        
                        device_info = {
                            'name': self._get_device_name(analysis),
                            'type': analysis.get('signature_match', {}).get('device_type', 'unknown'),
                            'manufacturer': analysis.get('signature_match', {}).get('manufacturer', 'Unknown'),
                            'confidence': analysis.get('confidence', 0),
                            'timestamp': os.path.getmtime(filepath)
                        }
                        
                        self.add_identified_device(freq, device_info)
            except Exception as e:
                print(f"Error loading {filepath}: {e}")
    
    def _get_device_name(self, analysis):
        """Extract device name from analysis"""
        if analysis.get('rtl433_result', {}).get('count', 0) > 0:
            return analysis['rtl433_result']['devices'][0].get('model', 'Unknown')
        elif analysis.get('signature_match'):
            return analysis['signature_match'].get('name', 'Unknown')
        return 'Unknown Device'
    
    def get_summary(self):
        """Get summary for dashboard"""
        return {
            'baseline_count': len(self.baseline),
            'device_count': len(self.devices),
            'recording_count': len(self.recordings),
            'devices': list(self.devices.values())
        }

def start_dashboard_with_data():
    """Start dashboard and load existing data"""
    # Create dashboard server
    server = SDRDashboardServer({
        'host': '0.0.0.0',
        'port': 5000
    })
    
    # Create manager
    manager = DashboardManager(server)
    
    # Load existing data
    print("Loading baseline...")
    manager.load_baseline()
    
    print("Loading analysis results...")
    manager.load_analysis_results()
    
    # Update dashboard with summary
    summary = manager.get_summary()
    server.update_state({
        'mode': 'monitoring',
        'status': 'active',
        **summary
    })
    
    print(f"\nDashboard Summary:")
    print(f"  Baseline frequencies: {summary['baseline_count']}")
    print(f"  Identified devices: {summary['device_count']}")
    print(f"  Recordings: {summary['recording_count']}")
    print(f"\nStarting dashboard server...")
    
    # Start server
    server.run_threaded()
    
    print(f"Dashboard available at: http://localhost:5000")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    start_dashboard_with_data()

