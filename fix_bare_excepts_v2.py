#!/usr/bin/env python3
"""Fix bare except clauses by adding Exception type."""

import re
from pathlib import Path


def fix_bare_except(content: str) -> str:
    """Replace bare 'except:' with 'except Exception as e:'."""
    # Pattern: except: (with optional whitespace)
    pattern = r'(\s+)except\s*:\s*$'
    replacement = r'\1except Exception as e:'
    return re.sub(pattern, replacement, content, flags=re.MULTILINE)

def main():
    files_to_fix = [
        'reconraven/core/scanner.py',
        'reconraven/scanning/scan_parallel.py',
        'reconraven/scanning/spectrum.py',
        'reconraven/demodulation/analog.py',
        'reconraven/demodulation/digital.py',
        'reconraven/hardware/sdr_controller.py',
        'reconraven/voice/monitor.py',
        'reconraven/voice/detector.py',
        'reconraven/voice/transcriber.py',
        'reconraven/visualization/bearing_map.py',
        'reconraven/web/server.py',
        'reconraven/recording/logger.py',
    ]

    for file_path in files_to_fix:
        path = Path(file_path)
        if not path.exists():
            print(f"Skip {file_path} (not found)")
            continue

        content = path.read_text(encoding='utf-8')
        new_content = fix_bare_except(content)

        if content != new_content:
            path.write_text(new_content, encoding='utf-8')
            print(f"Fixed {file_path}")
        else:
            print(f"No changes needed in {file_path}")

if __name__ == '__main__':
    main()

