#!/usr/bin/env python3
"""
Fix analysis modules - they don't have classes but still have print statements
"""

import os
import re


def replace_prints_in_file(filepath):
    """Replace print statements with proper logging in analysis files"""
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    # Add logging import if not present
    if 'import logging' not in content:
        # Find first import
        match = re.search(r'(""".*?"""|\'\'\'.*?\'\'\')', content, re.DOTALL)
        if match:
            insert_pos = match.end()
            content = (
                content[:insert_pos]
                + '\n\nimport logging\n\nlogger = logging.getLogger(__name__)'
                + content[insert_pos:]
            )

    # Replace print with logger
    content = re.sub(r'print\(f?["\']ERROR:([^"\']*)["\']', r'logger.error(\1', content)
    content = re.sub(r'print\(f?["\']WARNING:([^"\']*)["\']', r'logger.warning(\1', content)
    content = re.sub(
        r'print\(f?["\'][^"\']*FAIL[^"\']*["\']',
        lambda m: m.group(0).replace('print(', 'logger.error('),
        content,
    )
    content = re.sub(
        r'print\(f?["\']\[Analysis\]([^"\']*)["\']', r'logger.info("[Analysis]\1', content
    )
    content = re.sub(
        r'print\(f?["\']\[.*?\]([^"\']*)["\']',
        lambda m: m.group(0).replace('print(', 'logger.info('),
        content,
    )
    content = re.sub(r'print\(([^)]+)\)', r'logger.info(\1)', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f'✓ Fixed {filepath}')


# Analysis files (don't have main classes)
ANALYSIS_FILES = [
    'reconraven/analysis/field.py',
    'reconraven/analysis/correlation.py',
    'reconraven/analysis/rtl433.py',
    'reconraven/analysis/binary.py',
]

for filepath in ANALYSIS_FILES:
    if os.path.exists(filepath):
        replace_prints_in_file(filepath)
        print(f'Fixed {filepath}')

print('\nAnalysis modules fixed!')
