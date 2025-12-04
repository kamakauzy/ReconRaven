#!/usr/bin/env python3
"""Convert os.path.join to pathlib Path operations."""

import re
from pathlib import Path


def fix_pathlib_join(content: str) -> str:
    """Convert os.path.join() to Path() / operations."""
    lines = content.split('\n')
    new_lines = []
    imports_added = False

    for line in lines:
        # Check if this line has os.path.join
        if 'os.path.join(' in line:
            # Simple case: os.path.join(a, b) -> Path(a) / b
            # More complex: os.path.join(a, b, c) -> Path(a) / b / c

            # Extract the os.path.join call
            match = re.search(r'os\.path\.join\(([^)]+)\)', line)
            if match:
                args_str = match.group(1)
                # Split by comma, but be careful of commas in strings
                # For simplicity, let's handle common cases
                args = [arg.strip() for arg in args_str.split(',')]

                if len(args) >= 2:
                    # Convert to Path(first) / second / third / ...
                    path_expr = f"Path({args[0]})"
                    for arg in args[1:]:
                        path_expr += f" / {arg}"

                    new_line = line.replace(match.group(0), path_expr)
                    new_lines.append(new_line)

                    # Make sure Path is imported
                    if not imports_added and 'from pathlib import Path' not in content:
                        imports_added = True
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    result = '\n'.join(new_lines)

    # Add Path import if needed
    if imports_added and 'from pathlib import Path' not in result:
        # Find the right place to add import (after other imports)
        import_lines = []
        other_lines = []
        in_imports = True

        for line in result.split('\n'):
            if (in_imports and (line.startswith(('import ', 'from ')))) or (in_imports and line.strip() == ''):
                import_lines.append(line)
            else:
                if in_imports:
                    in_imports = False
                    import_lines.append('from pathlib import Path')
                other_lines.append(line)

        result = '\n'.join(import_lines + other_lines)

    return result

def main():
    # Get list of files with os.path.join violations
    import subprocess
    result = subprocess.run(
        ['python', '-m', 'ruff', 'check', '.', '--select', 'PTH118'],
        capture_output=True,
        text=True, check=False
    )

    files = set()
    for line in result.stdout.split('\n'):
        if 'PTH118' in line:
            # Extract filename from line like: reconraven/core/scanner.py:123:45: PTH118
            parts = line.split(':')
            if parts:
                files.add(parts[0])

    print(f"Found {len(files)} files with os.path.join")

    for file_path in sorted(files):
        path = Path(file_path)
        if not path.exists():
            continue

        try:
            content = path.read_text(encoding='utf-8')
            new_content = fix_pathlib_join(content)

            if content != new_content:
                path.write_text(new_content, encoding='utf-8')
                print(f"✓ Fixed {file_path}")
        except Exception as e:
            print(f"✗ Error fixing {file_path}: {e}")

if __name__ == '__main__':
    main()

