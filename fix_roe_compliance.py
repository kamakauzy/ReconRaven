#!/usr/bin/env python3
"""
Automated ROE Compliance Fixer
Systematically updates all Python files to comply with ROE requirements
"""

import os
import re


def add_debug_helper_to_class(filepath, class_name):
    """Add DebugHelper inheritance to a class"""
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    # Add import if not present
    if (
        'from reconraven.core.debug_helper import DebugHelper' not in content
        and 'from reconraven.core import' not in content
    ):
        # Find first import statement
        import_pattern = r'(import \w+|from \w+)'
        match = re.search(import_pattern, content)
        if match:
            insert_pos = content.find('\n\n', match.end())
            if insert_pos == -1:
                insert_pos = match.end()
            content = (
                content[:insert_pos]
                + '\n\nfrom reconraven.core.debug_helper import DebugHelper'
                + content[insert_pos:]
            )

    # Update class definition
    class_pattern = rf'class {class_name}:'
    if re.search(class_pattern, content):
        content = re.sub(class_pattern, f'class {class_name}(DebugHelper):', content)

        # Find __init__ and add super() call
        init_pattern = rf'(class {class_name}\(DebugHelper\):.*?def __init__\(self[^)]*\):)'
        match = re.search(init_pattern, content, re.DOTALL)
        if match:
            init_end = match.end()
            # Find first line after def __init__
            next_line_start = content.find('\n', init_end) + 1
            indent_match = re.match(r'(\s+)', content[next_line_start:])
            indent = indent_match.group(1) if indent_match else '        '

            # Add super() call if not present
            if f"super().__init__(component_name='{class_name}')" not in content:
                super_call = f"{indent}super().__init__(component_name='{class_name}')\n{indent}self.debug_enabled = True\n"
                content = content[:next_line_start] + super_call + content[next_line_start:]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f'✓ Updated {filepath}')


def replace_print_with_logging(filepath):
    """Replace print() statements with self.log_*() calls"""
    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()

    updated = False
    new_lines = []

    for line in lines:
        # Skip if in main() function or if __name__ == '__main__'
        if 'def main():' in line or '__name__' in line:
            new_lines.append(line)
            continue

        # Match print statements
        print_match = re.match(r'(\s*)print\((.*)\)', line)
        if print_match:
            indent = print_match.group(1)
            content = print_match.group(2)

            # Determine log level based on content
            if 'ERROR' in content.upper() or 'FAIL' in content.upper():
                log_method = 'log_error'
            elif 'WARN' in content.upper():
                log_method = 'log_warning'
            elif 'DEBUG' in content.upper() or '...' in content or 'OK' in content:
                log_method = 'log_debug'
            else:
                log_method = 'log_info'

            # Replace
            new_line = f'{indent}self.{log_method}({content})\n'
            new_lines.append(new_line)
            updated = True
        else:
            new_lines.append(line)

    if updated:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f'✓ Replaced prints in {filepath}')


def remove_old_logging_pattern(filepath):
    """Remove logger = logging.getLogger(__name__) pattern"""
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    # Remove the logger assignment
    content = re.sub(r'\nlogger = logging\.getLogger\(__name__\)\n', '\n', content)

    # Replace logger.info with self.log_info, etc
    content = re.sub(r'logger\.debug\(', 'self.log_debug(', content)
    content = re.sub(r'logger\.info\(', 'self.log_info(', content)
    content = re.sub(r'logger\.warning\(', 'self.log_warning(', content)
    content = re.sub(r'logger\.error\(', 'self.log_error(', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


# Files and their main classes to update
FILES_TO_UPDATE = {
    'reconraven/utils/recording_manager.py': 'RecordingManager',
    'reconraven/voice/monitor.py': 'VoiceMonitor',
    'reconraven/voice/transcriber.py': 'VoiceTranscriber',
    'reconraven/voice/detector.py': 'VoiceDetector',
    'reconraven/scanning/anomaly_detect.py': 'AnomalyDetector',
    'reconraven/scanning/drone_detector.py': 'DroneDetector',
    'reconraven/scanning/scan_parallel.py': 'ParallelScanner',
    'reconraven/scanning/spectrum.py': 'SpectrumScanner',
    'reconraven/scanning/mode_switch.py': 'ModeSwitcher',
    'reconraven/web/server.py': 'SDRDashboardServer',
    'reconraven/demodulation/digital.py': 'DigitalDemodulator',
    'reconraven/demodulation/analog.py': 'AnalogDemodulator',
    'reconraven/hardware/sdr_controller.py': 'SDRController',
    'reconraven/direction_finding/array_sync.py': 'SDRArraySync',
    'reconraven/direction_finding/bearing_calc.py': 'BearingCalculator',
    'reconraven/visualization/bearing_map.py': 'BearingMap',
    'reconraven/recording/logger.py': 'SignalLogger',
}


def main():
    print('ROE Compliance Automated Fixer')
    print('=' * 70)

    for filepath, class_name in FILES_TO_UPDATE.items():
        print(f'\nProcessing {filepath}...')

        if not os.path.exists(filepath):
            print('  ⚠ File not found, skipping')
            continue

        try:
            # Step 1: Add DebugHelper
            add_debug_helper_to_class(filepath, class_name)

            # Step 2: Replace print statements
            replace_print_with_logging(filepath)

            # Step 3: Remove old logging
            remove_old_logging_pattern(filepath)

        except Exception as e:
            print(f'  ✗ Error: {e}')

    print('\n' + '=' * 70)
    print("Done! Run 'python -m ruff check .' to verify")


if __name__ == '__main__':
    main()
