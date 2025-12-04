#!/usr/bin/env python3
"""Systematically fix remaining ROE violations across all files."""

import re
import subprocess
from pathlib import Path


def get_violations_by_file():
    """Get all violations grouped by file."""
    result = subprocess.run(
        ['python', '-m', 'ruff', 'check', '.'],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace', check=False
    )

    violations = {}
    stdout = result.stdout or ''
    for line in stdout.split('\n'):
        if ':' in line and '\\' in line:
            parts = line.split(':')
            if len(parts) >= 4:
                file_path = parts[0].strip()
                if file_path not in violations:
                    violations[file_path] = []
                violations[file_path].append(line)

    return violations

def fix_datetime_utc(file_path):
    """Fix datetime.now() to use UTC timezone."""
    path = Path(file_path)
    if not path.exists():
        return False

    content = path.read_text(encoding='utf-8')

    # Add timezone import if needed
    has_datetime_import = 'from datetime import' in content
    has_timezone = 'timezone' in content or ', timezone' in content

    if has_datetime_import and not has_timezone:
        # Add timezone to existing import
        content = re.sub(
            r'from datetime import (.*?)(\n|$)',
            r'from datetime import \1, timezone\2',
            content
        )

    # Replace datetime.now() with datetime.now(timezone.utc)
    original_content = content
    content = re.sub(
        r'datetime\.now\(\)(?![\w\.])',
        'datetime.now(timezone.utc)',
        content
    )

    if content != original_content:
        path.write_text(content, encoding='utf-8')
        return True
    return False

def fix_pathlib_operations(file_path):
    """Fix os.path operations to use pathlib."""
    path = Path(file_path)
    if not path.exists():
        return False

    content = path.read_text(encoding='utf-8')
    original_content = content

    # Add pathlib import if needed
    if 'from pathlib import Path' not in content and 'import pathlib' not in content:
        # Find first import line
        lines = content.split('\n')
        import_idx = -1
        for i, line in enumerate(lines):
            if line.startswith(('import ', 'from ')):
                import_idx = i
                break

        if import_idx >= 0:
            lines.insert(import_idx + 1, 'from pathlib import Path')
            content = '\n'.join(lines)

    # Fix os.makedirs -> Path.mkdir
    content = re.sub(
        r"os\.makedirs\((['\"])([^'\"]+)\1,\s*exist_ok=True\)",
        r"Path(\1\2\1).mkdir(parents=True, exist_ok=True)",
        content
    )

    # Fix os.path.exists -> Path.exists()
    content = re.sub(
        r'os\.path\.exists\(([^)]+)\)',
        r'Path(\1).exists()',
        content
    )

    # Fix os.path.basename -> Path.name
    content = re.sub(
        r'os\.path\.basename\(([^)]+)\)',
        r'Path(\1).name',
        content
    )

    # Fix os.path.dirname -> Path.parent
    content = re.sub(
        r'os\.path\.dirname\(([^)]+)\)',
        r'Path(\1).parent',
        content
    )

    # Fix os.path.getsize -> Path.stat().st_size
    content = re.sub(
        r'os\.path\.getsize\(([^)]+)\)',
        r'Path(\1).stat().st_size',
        content
    )

    # Fix os.remove -> Path.unlink()
    content = re.sub(
        r'os\.remove\(([^)]+)\)',
        r'Path(\1).unlink()',
        content
    )

    # Fix os.getcwd() -> Path.cwd()
    content = re.sub(
        r'os\.getcwd\(\)',
        'Path.cwd()',
        content
    )

    # Fix os.path.isfile -> Path.is_file()
    content = re.sub(
        r'os\.path\.isfile\(([^)]+)\)',
        r'Path(\1).is_file()',
        content
    )

    if content != original_content:
        path.write_text(content, encoding='utf-8')
        return True
    return False

def fix_verbose_logging(file_path):
    """Fix verbose logging messages (TRY401)."""
    path = Path(file_path)
    if not path.exists():
        return False

    content = path.read_text(encoding='utf-8')
    original_content = content

    # Replace logger.error(f"...", exc_info=True) with logger.exception("...")
    content = re.sub(
        r'logger\.error\(([^,]+),\s*exc_info=True\)',
        r'logger.exception(\1)',
        content
    )

    if content != original_content:
        path.write_text(content, encoding='utf-8')
        return True
    return False

def main():
    print("Fixing remaining ROE violations...")

    # Get all files with violations
    violations = get_violations_by_file()
    print(f"Found violations in {len(violations)} files\n")

    fixed_files = []

    for file_path in sorted(violations.keys()):
        changes_made = False

        # Fix datetime issues
        if 'DTZ005' in str(violations[file_path]) and fix_datetime_utc(file_path):
            changes_made = True
            print(f"✓ Fixed datetime in {file_path}")

        # Fix pathlib issues
        if any(x in str(violations[file_path]) for x in ['PTH', 'os.path', 'os.makedirs', 'os.remove']):
            if fix_pathlib_operations(file_path):
                changes_made = True
                print(f"✓ Fixed pathlib in {file_path}")

        # Fix verbose logging
        if 'TRY401' in str(violations[file_path]) and fix_verbose_logging(file_path):
            changes_made = True
            print(f"✓ Fixed logging in {file_path}")

        if changes_made:
            fixed_files.append(file_path)

    print(f"\n\nFixed {len(fixed_files)} files")

    # Run final check
    print("\nRunning final violation check...")
    result = subprocess.run(
        ['python', '-m', 'ruff', 'check', '.', '--statistics'],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace', check=False
    )
    print(result.stdout or '')

if __name__ == '__main__':
    main()

