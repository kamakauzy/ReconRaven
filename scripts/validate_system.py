#!/usr/bin/env python3
"""
ReconRaven System Validation Script

Runs comprehensive tests to validate Pi deployment.

Usage:
    python3 scripts/validate_system.py
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Colors
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'


def print_header(text: str):
    """Print header."""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
    print(f"{Colors.BLUE}  {text}{Colors.NC}")
    print(f"{Colors.BLUE}{'='*60}{Colors.NC}\n")


def print_test(text: str):
    """Print test name."""
    print(f"{Colors.BLUE}[TEST]{Colors.NC} {text}...", end=' ', flush=True)


def print_pass(text: str = "PASS"):
    """Print pass."""
    print(f"{Colors.GREEN}✓ {text}{Colors.NC}")


def print_fail(text: str = "FAIL"):
    """Print fail."""
    print(f"{Colors.RED}✗ {text}{Colors.NC}")


def print_warn(text: str = "WARN"):
    """Print warning."""
    print(f"{Colors.YELLOW}! {text}{Colors.NC}")


def run_command(cmd: list[str], timeout: int = 30) -> tuple[bool, str]:
    """Run command and return success status and output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


class SystemValidator:
    """System validation suite."""

    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.tests_warned = 0
        self.results = {}

    def test_sdr_detection(self) -> bool:
        """Test SDR detection."""
        print_test("SDR Detection")

        success, output = run_command(['rtl_test', '-t'], timeout=10)

        if not success:
            print_fail("rtl_test failed")
            self.results['sdr'] = {'status': 'fail', 'message': 'rtl_test not found or failed'}
            return False

        # Count SDRs
        sdr_count = output.count('Found')

        if sdr_count == 0:
            print_fail("No SDRs detected")
            self.results['sdr'] = {'status': 'fail', 'count': 0}
            return False
        if sdr_count == 4:
            print_pass(f"{sdr_count} SDRs detected")
            self.results['sdr'] = {'status': 'pass', 'count': sdr_count}
            return True
        print_warn(f"Only {sdr_count}/4 SDRs detected")
        self.results['sdr'] = {'status': 'warn', 'count': sdr_count}
        return True

    def test_gps(self) -> bool:
        """Test GPS functionality."""
        print_test("GPS Detection")

        # Check if GPS device exists
        if not Path('/dev/ttyACM0').exists():
            print_fail("GPS device not found at /dev/ttyACM0")
            self.results['gps'] = {'status': 'fail', 'message': 'Device not found'}
            return False

        # Check GPSD
        success, output = run_command(['systemctl', 'is-active', 'gpsd'], timeout=5)

        if not success:
            print_warn("GPSD service not running")
            self.results['gps'] = {'status': 'warn', 'message': 'Service not active'}
            return True

        # Try to get GPS status
        print("\n      Waiting 15 seconds for GPS fix...", end='', flush=True)
        time.sleep(15)

        success, output = run_command(['timeout', '5', 'cgps', '-s'], timeout=10)

        if '3D' in output:
            print_pass("\n      GPS has 3D fix")
            self.results['gps'] = {'status': 'pass', 'fix': '3D'}
            return True
        if '2D' in output:
            print_warn("\n      GPS has 2D fix")
            self.results['gps'] = {'status': 'warn', 'fix': '2D'}
            return True
        print_warn("\n      GPS has no fix (may need sky view)")
        self.results['gps'] = {'status': 'warn', 'fix': 'none'}
        return True

    def test_python_imports(self) -> bool:
        """Test Python module imports."""
        print_test("Python Module Imports")

        modules_to_test = [
            'numpy',
            'scipy',
            'flask',
            'flask_socketio',
            'kivy',
            'whisper',
            'yaml',
            'reconraven'
        ]

        failed_imports = []

        for module in modules_to_test:
            try:
                __import__(module)
            except ImportError:
                failed_imports.append(module)

        if failed_imports:
            print_fail(f"Failed: {', '.join(failed_imports)}")
            self.results['python_imports'] = {
                'status': 'fail',
                'failed': failed_imports
            }
            return False

        print_pass("All modules imported successfully")
        self.results['python_imports'] = {'status': 'pass'}
        return True

    def test_database(self) -> bool:
        """Test database accessibility."""
        print_test("Database Access")

        db_path = Path('reconraven.db')

        if not db_path.exists():
            print_warn("Database not initialized yet")
            self.results['database'] = {'status': 'warn', 'message': 'Not initialized'}
            return True

        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Check tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]

            conn.close()

            if len(tables) > 0:
                print_pass(f"{len(tables)} tables found")
                self.results['database'] = {'status': 'pass', 'tables': len(tables)}
                return True
            print_warn("Database exists but has no tables")
            self.results['database'] = {'status': 'warn', 'tables': 0}
            return True

        except Exception as e:
            print_fail(f"Error: {e}")
            self.results['database'] = {'status': 'fail', 'error': str(e)}
            return False

    def test_location_database(self) -> bool:
        """Test location database."""
        print_test("Location Database")

        db_path = Path('location_frequencies.db')

        if not db_path.exists():
            print_warn("Location database not found")
            self.results['location_db'] = {'status': 'warn', 'message': 'Not found'}
            return True

        try:
            from reconraven.location.database import get_location_db

            db = get_location_db()
            stats = db.get_stats()
            db.close()

            total = stats.get('total', 0)

            if total > 0:
                print_pass(f"{total} frequencies loaded")
                self.results['location_db'] = {'status': 'pass', 'stats': stats}
                return True
            print_warn("Database empty")
            self.results['location_db'] = {'status': 'warn', 'count': 0}
            return True

        except Exception as e:
            print_fail(f"Error: {e}")
            self.results['location_db'] = {'status': 'fail', 'error': str(e)}
            return False

    def test_api(self) -> bool:
        """Test API accessibility."""
        print_test("API Health Check")

        try:
            import requests

            response = requests.get('http://localhost:5001/api/v1/health', timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'healthy':
                    print_pass("API responding")
                    self.results['api'] = {'status': 'pass', 'response': data}
                    return True

            print_warn(f"API returned status {response.status_code}")
            self.results['api'] = {'status': 'warn', 'code': response.status_code}
            return True

        except Exception as e:
            print_warn(f"API not accessible: {e}")
            self.results['api'] = {'status': 'warn', 'error': str(e)}
            return True

    def test_whisper_models(self) -> bool:
        """Test Whisper model availability."""
        print_test("Whisper Models")

        whisper_cache = Path.home() / '.cache' / 'whisper'

        if not whisper_cache.exists():
            print_warn("No Whisper models cached")
            self.results['whisper'] = {'status': 'warn', 'message': 'No models'}
            return True

        models = list(whisper_cache.glob('*.pt'))

        if models:
            model_names = [m.stem for m in models]
            print_pass(f"Models: {', '.join(model_names)}")
            self.results['whisper'] = {'status': 'pass', 'models': model_names}
            return True
        print_warn("Whisper cache exists but empty")
        self.results['whisper'] = {'status': 'warn', 'count': 0}
        return True

    def test_config_files(self) -> bool:
        """Test configuration files."""
        print_test("Configuration Files")

        config_dir = Path('config')
        required_files = ['bands.yaml', 'hardware.yaml', 'demod_config.yaml']

        if not config_dir.exists():
            print_warn("Config directory not found")
            self.results['config'] = {'status': 'warn', 'message': 'Directory not found'}
            return True

        missing = []
        for file in required_files:
            if not (config_dir / file).exists():
                missing.append(file)

        if missing:
            print_warn(f"Missing: {', '.join(missing)}")
            self.results['config'] = {'status': 'warn', 'missing': missing}
            return True

        print_pass("All config files present")
        self.results['config'] = {'status': 'pass'}
        return True

    def test_systemd_services(self) -> bool:
        """Test systemd services."""
        print_test("Systemd Services")

        services = ['reconraven-api', 'reconraven-touch']
        service_status = {}

        for service in services:
            success, output = run_command(['systemctl', 'is-enabled', service], timeout=5)
            enabled = 'enabled' in output.lower()

            success, output = run_command(['systemctl', 'is-active', service], timeout=5)
            active = 'active' in output.lower()

            service_status[service] = {'enabled': enabled, 'active': active}

        all_ok = all(s['enabled'] and s['active'] for s in service_status.values())

        if all_ok:
            print_pass("All services enabled and active")
            self.results['services'] = {'status': 'pass', 'services': service_status}
            return True
        print_warn("Some services not fully configured")
        self.results['services'] = {'status': 'warn', 'services': service_status}
        return True

    def test_performance(self) -> bool:
        """Test basic performance."""
        print_test("Performance Check")

        try:
            import numpy as np

            # CPU test
            start = time.time()
            _ = np.random.randn(1000, 1000) @ np.random.randn(1000, 1000)
            cpu_time = time.time() - start

            # Disk test
            start = time.time()
            test_file = Path('/tmp/reconraven_disk_test.bin')
            data = np.random.randn(10_000_000)
            np.save(test_file, data)
            disk_time = time.time() - start
            test_file.unlink()

            print_pass(f"CPU: {cpu_time:.2f}s, Disk: {disk_time:.2f}s")
            self.results['performance'] = {
                'status': 'pass',
                'cpu_time': cpu_time,
                'disk_time': disk_time
            }
            return True

        except Exception as e:
            print_warn(f"Performance test failed: {e}")
            self.results['performance'] = {'status': 'warn', 'error': str(e)}
            return True

    def run_all_tests(self):
        """Run all validation tests."""
        print_header("ReconRaven System Validation")

        tests = [
            ('SDR Detection', self.test_sdr_detection),
            ('GPS', self.test_gps),
            ('Python Imports', self.test_python_imports),
            ('Database', self.test_database),
            ('Location Database', self.test_location_database),
            ('API Health', self.test_api),
            ('Whisper Models', self.test_whisper_models),
            ('Configuration', self.test_config_files),
            ('Systemd Services', self.test_systemd_services),
            ('Performance', self.test_performance),
        ]

        for test_name, test_func in tests:
            self.tests_run += 1
            result = test_func()

            if result:
                if self.results.get(test_name.lower().replace(' ', '_'), {}).get('status') == 'pass':
                    self.tests_passed += 1
                else:
                    self.tests_warned += 1
            else:
                self.tests_failed += 1

    def print_summary(self):
        """Print test summary."""
        print_header("Validation Summary")

        print(f"Tests Run:    {self.tests_run}")
        print(f"{Colors.GREEN}Passed:       {self.tests_passed}{Colors.NC}")
        print(f"{Colors.YELLOW}Warnings:     {self.tests_warned}{Colors.NC}")
        print(f"{Colors.RED}Failed:       {self.tests_failed}{Colors.NC}")

        print("\n" + "="*60)

        if self.tests_failed == 0:
            print(f"{Colors.GREEN}✓ System validation PASSED!{Colors.NC}")
            print("\nYour ReconRaven system is ready for use!")
        elif self.tests_failed < 3:
            print(f"{Colors.YELLOW}⚠ System validation PASSED with warnings{Colors.NC}")
            print("\nSystem is mostly ready. Review warnings above.")
        else:
            print(f"{Colors.RED}✗ System validation FAILED{Colors.NC}")
            print("\nPlease address the failed tests before using the system.")

        print("="*60 + "\n")

    def save_report(self):
        """Save validation report to file."""
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'tests_run': self.tests_run,
                'passed': self.tests_passed,
                'warned': self.tests_warned,
                'failed': self.tests_failed
            },
            'results': self.results
        }

        report_file = Path('validation_report.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Detailed report saved to: {report_file}\n")


def main():
    """Main entry point."""
    # Check we're in the right directory
    if not Path('reconraven').exists():
        print(f"{Colors.RED}Error: Must run from ReconRaven root directory{Colors.NC}")
        sys.exit(1)

    validator = SystemValidator()

    try:
        validator.run_all_tests()
        validator.print_summary()
        validator.save_report()

        sys.exit(0 if validator.tests_failed == 0 else 1)

    except KeyboardInterrupt:
        print(f"\n{Colors.RED}Validation interrupted by user{Colors.NC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Validation error: {e}{Colors.NC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

