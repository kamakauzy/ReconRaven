#!/usr/bin/env python3
"""
Kill any running dashboard processes
"""

import psutil
import sys

def kill_dashboard_processes():
    """Find and kill any processes using port 5000"""
    killed = 0
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check if it's a Python process
            if 'python' in proc.info['name'].lower():
                cmdline = proc.info['cmdline']
                if cmdline and any('dashboard' in str(arg).lower() or '5000' in str(arg) for arg in cmdline):
                    print(f"Killing process {proc.info['pid']}: {' '.join(cmdline)}")
                    proc.kill()
                    killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if killed == 0:
        print("No dashboard processes found.")
    else:
        print(f"Killed {killed} process(es)")
    
    return killed

if __name__ == "__main__":
    kill_dashboard_processes()

