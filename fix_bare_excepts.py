#!/usr/bin/env python3
"""
Fix Bare Except Statements
Convert bare except: to except Exception:
"""

import os
import re


def fix_bare_excepts(filepath):
    """Fix bare except statements in a file"""
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    # Replace bare except: with except Exception:
    # Match: except:\n with any whitespace before
    pattern = r'(\s+)except:\s*\n'
    replacement = r'\1except Exception:\n'

    new_content = re.sub(pattern, replacement, content)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False


def main():
    print('Fixing Bare Except Statements')
    print('=' * 70)

    # Find all Python files
    fixed_count = 0
    for root, dirs, files in os.walk('reconraven'):
        # Skip __pycache__
        dirs[:] = [d for d in dirs if d != '__pycache__']

        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if fix_bare_excepts(filepath):
                    print(f'✓ Fixed {filepath}')
                    fixed_count += 1

    # Also check standalone scripts
    for script in ['launch_demo.py', 'batch_transcribe.py', 'reconraven.py']:
        if os.path.exists(script) and fix_bare_excepts(script):
            print(f'✓ Fixed {script}')
            fixed_count += 1

    print('\n' + '=' * 70)
    print(f'Fixed {fixed_count} files!')


if __name__ == '__main__':
    main()


