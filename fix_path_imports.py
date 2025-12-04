#!/usr/bin/env python3
"""Fix missing Path imports and clean up unused imports."""
from pathlib import Path

# Files that need Path import added
add_path_import = [
    'field_analyzer.py',
    'reconraven/recording/logger.py',
    'reconraven/voice/monitor.py',
    'reconraven/voice/transcriber.py',
    'recording_manager.py',
    'rtl433_integration.py',
    'voice_monitor.py',
    'voice_transcriber.py',
]

def add_import_if_needed(filepath):
    """Add 'from pathlib import Path' if not already present."""
    path = Path(filepath)
    if not path.exists():
        print(f"⚠ Skipping {filepath} - not found")
        return
    
    content = path.read_text(encoding='utf-8')
    
    # Check if Path is already imported
    if 'from pathlib import Path' in content or 'import pathlib' in content:
        return
    
    # Find the best place to insert the import
    lines = content.split('\n')
    insert_idx = 0
    
    # Find the last import statement
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_idx = i + 1
        elif insert_idx > 0 and line.strip() and not line.startswith('#'):
            # Found first non-import line
            break
    
    # Insert the import
    lines.insert(insert_idx, 'from pathlib import Path')
    content = '\n'.join(lines)
    
    path.write_text(content, encoding='utf-8')
    print(f"✓ Added Path import to {filepath}")

# Add Path imports
for filepath in add_path_import:
    add_import_if_needed(filepath)

print("\n✅ Done! Now running ruff --fix to remove unused imports...")

