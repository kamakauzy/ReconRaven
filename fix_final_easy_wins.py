#!/usr/bin/env python3
"""Fix TRY401, DTZ005, and F401 violations - the easy wins."""
import re
from pathlib import Path

# Files and their fixes
fixes = {
    # TRY401 - Remove redundant exception from logger.exception
    'batch_transcribe.py': [
        ("logger.exception(f'  Exception: {e}')", "logger.exception('  Exception occurred')"),
    ],
    'config.py': [
        ("logger.exception(f'Error loading {filepath}: {e}')", "logger.exception(f'Error loading {filepath}')"),
    ],
    'reconraven/core/config.py': [
        ("logger.exception(f'Error loading {filepath}: {e}')", "logger.exception(f'Error loading {filepath}')"),
    ],
    'reconraven/hardware/sdr_controller.py': [
        ("logger.exception(f'Error detecting SDR devices: {e}')", "logger.exception('Error detecting SDR devices')"),
    ],
    'recording_manager.py': [
        ("logger.exception(f'Cleanup error: {e}')", "logger.exception('Cleanup error')"),
        ("logger.exception(f'Transcription error: {e}')", "logger.exception('Transcription error')"),
    ],
    'voice_monitor.py': [
        ("logger.exception(f'Error starting voice monitor: {e}')", "logger.exception('Error starting voice monitor')"),
    ],
    'voice_transcriber.py': [
        ("logger.exception(f'Transcription error: {e}')", "logger.exception('Transcription error')"),
    ],
    
    # DTZ005 - Add timezone to datetime.now()
    'advanced_scanner.py': [
        ("timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')", 
         "timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')"),
        ("'detected_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')",
         "'detected_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')"),
    ],
    'reconraven.py': [
        ("cutoff = datetime.now() - timedelta(days=args.days or 7)",
         "cutoff = datetime.now(timezone.utc) - timedelta(days=args.days or 7)"),
    ],
    'reconraven/voice/monitor.py': [
        ("timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')",
         "timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')"),
    ],
    'reconraven/voice/transcriber.py': [
        ("'transcribed_at': datetime.now().isoformat()",
         "'transcribed_at': datetime.now(timezone.utc).isoformat()"),
    ],
    'recording_manager.py': [
        ("if datetime.now() - captured > timedelta(days=days_old):",
         "if datetime.now(timezone.utc) - captured > timedelta(days=days_old):"),
    ],
    'voice_monitor.py': [
        ("timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')",
         "timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')"),
    ],
    'voice_transcriber.py': [
        ("'transcribed_at': datetime.now().isoformat()",
         "'transcribed_at': datetime.now(timezone.utc).isoformat()"),
    ],
}

# Unused imports to remove
remove_imports = {
    'reconraven.py': [
        'test_multi_sdr_initialization,',
        'test_sdr_initialization,',
    ],
    'reconraven/hardware/__init__.py': [
        'OperatingMode, ',
    ],
}

def apply_fixes():
    """Apply all fixes."""
    fixed_count = 0
    
    # Apply replacements
    for filepath, replacements in fixes.items():
        path = Path(filepath)
        if not path.exists():
            print(f"⚠ Skipping {filepath} - not found")
            continue
            
        content = path.read_text(encoding='utf-8')
        original = content
        
        for old, new in replacements:
            if old in content:
                content = content.replace(old, new)
                fixed_count += 1
                print(f"✓ Fixed in {filepath}")
            
        if content != original:
            path.write_text(content, encoding='utf-8')
    
    # Remove unused imports
    for filepath, imports_to_remove in remove_imports.items():
        path = Path(filepath)
        if not path.exists():
            print(f"⚠ Skipping {filepath} - not found")
            continue
            
        content = path.read_text(encoding='utf-8')
        original = content
        
        for import_str in imports_to_remove:
            if import_str in content:
                content = content.replace(import_str, '')
                # Clean up any double commas or trailing commas
                content = re.sub(r',\s*,', ',', content)
                content = re.sub(r',\s*\)', ')', content)
                content = re.sub(r'\(\s*,', '(', content)
                fixed_count += 1
                print(f"✓ Removed unused import in {filepath}")
        
        if content != original:
            path.write_text(content, encoding='utf-8')
    
    print(f"\n✅ Fixed {fixed_count} violations!")

if __name__ == '__main__':
    apply_fixes()

