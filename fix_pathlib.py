#!/usr/bin/env python3
"""
Convert os.path operations to pathlib.Path
Systematic conversion of PTH* violations
"""

import os
import re


def fix_pathlib(filepath):
    """Convert os.path operations to pathlib"""
    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()

    ''.join(lines)
    modified = False

    # Add pathlib import if using os.path
    has_os_path = any('os.path' in line for line in lines)
    has_pathlib = any('from pathlib import Path' in line or 'import pathlib' in line for line in lines)

    if has_os_path and not has_pathlib:
        # Find import section
        import_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                import_idx = i

        if import_idx is not None:
            # Add after last import
            while import_idx + 1 < len(lines) and (lines[import_idx + 1].strip().startswith(('import ', 'from ')) or not lines[import_idx + 1].strip()):
                import_idx += 1
            lines.insert(import_idx + 1, 'from pathlib import Path\n')
            modified = True

    # Convert common patterns
    content = ''.join(lines)
    new_content = content

    # os.path.join -> Path with /
    # This is complex, so we'll handle simple cases
    new_content = re.sub(
        r"os\.path\.join\((['\"])([^'\"]+)\1,\s*(['\"])([^'\"]+)\3\)",
        r"str(Path(\1\2\1) / \3\4\3)",
        new_content
    )

    # os.path.exists(path) -> Path(path).exists()
    new_content = re.sub(
        r'os\.path\.exists\(([^)]+)\)',
        r'Path(\1).exists()',
        new_content
    )

    # os.path.basename(path) -> Path(path).name
    new_content = re.sub(
        r'os\.path\.basename\(([^)]+)\)',
        r'Path(\1).name',
        new_content
    )

    # os.path.dirname(path) -> Path(path).parent
    new_content = re.sub(
        r'os\.path\.dirname\(([^)]+)\)',
        r'str(Path(\1).parent)',
        new_content
    )

    # os.path.getsize(path) -> Path(path).stat().st_size
    new_content = re.sub(
        r'os\.path\.getsize\(([^)]+)\)',
        r'Path(\1).stat().st_size',
        new_content
    )

    # os.path.isfile(path) -> Path(path).is_file()
    new_content = re.sub(
        r'os\.path\.isfile\(([^)]+)\)',
        r'Path(\1).is_file()',
        new_content
    )

    # os.makedirs -> Path.mkdir
    new_content = re.sub(
        r'os\.makedirs\(([^,)]+),?\s*exist_ok=True\)',
        r'Path(\1).mkdir(parents=True, exist_ok=True)',
        new_content
    )
    new_content = re.sub(
        r'os\.makedirs\(([^)]+)\)',
        r'Path(\1).mkdir(parents=True)',
        new_content
    )

    # os.remove -> Path.unlink
    new_content = re.sub(
        r'os\.remove\(([^)]+)\)',
        r'Path(\1).unlink()',
        new_content
    )

    # os.getcwd() -> Path.cwd()
    new_content = re.sub(
        r'os\.getcwd\(\)',
        r'str(Path.cwd())',
        new_content
    )

    # glob.glob with os.path.join -> Path.glob
    new_content = re.sub(
        r'glob\.glob\(os\.path\.join\(([^,]+),\s*([^\)]+)\)\)',
        r'list(Path(\1).glob(\2))',
        new_content
    )

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True

    return modified


def main():
    print('Converting os.path to pathlib')
    print('=' * 70)

    fixed_count = 0
    for root, dirs, files in os.walk('reconraven'):
        dirs[:] = [d for d in dirs if d != '__pycache__']

        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if fix_pathlib(filepath):
                    print(f'✓ Fixed {filepath}')
                    fixed_count += 1

    # Also check standalone scripts
    for script in ['launch_demo.py', 'batch_transcribe.py', 'reconraven.py']:
        if os.path.exists(script) and fix_pathlib(script):
            print(f'✓ Fixed {script}')
            fixed_count += 1

    print('\n' + '=' * 70)
    print(f'Fixed {fixed_count} files!')
    print('Note: Some complex patterns may need manual review')


if __name__ == '__main__':
    main()


