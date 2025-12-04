#!/usr/bin/env python3
"""
Fix Deprecated Imports (UP035)
Update old import paths to new ones for Python 3.9+
"""

import os
import re


def fix_deprecated_imports(filepath):
    """Fix deprecated import patterns"""
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    original = content

    # collections.Mapping -> collections.abc.Mapping
    content = re.sub(
        r'from collections import (.*?)(Mapping|MutableMapping|Sequence|MutableSequence|Set|MutableSet|Iterable|Iterator|Callable)',
        r'from collections.abc import \1\2',
        content
    )

    # collections.abc imports that might need updating
    content = re.sub(
        r'import collections\s',
        'import collections.abc\n',
        content
    )

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    print('Fixing Deprecated Imports')
    print('=' * 70)

    fixed_count = 0
    for root, dirs, files in os.walk('reconraven'):
        dirs[:] = [d for d in dirs if d != '__pycache__']

        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if fix_deprecated_imports(filepath):
                    print(f'✓ Fixed {filepath}')
                    fixed_count += 1

    print('\n' + '=' * 70)
    print(f'Fixed {fixed_count} files!')


if __name__ == '__main__':
    main()


