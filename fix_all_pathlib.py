#!/usr/bin/env python3
"""Fix all remaining pathlib violations - PTH118, PTH119, PTH202, PTH107, PTH110, PTH103, PTH207, PTH116."""
from pathlib import Path

def fix_file(filepath, old_new_pairs):
    """Apply replacements to a file."""
    path = Path(filepath)
    if not path.exists():
        print(f"⚠ Skipping {filepath} - not found")
        return 0
    
    content = path.read_text(encoding='utf-8')
    original = content
    fixed = 0
    
    for old, new in old_new_pairs:
        if old in content:
            content = content.replace(old, new)
            fixed += 1
    
    if content != original:
        path.write_text(content, encoding='utf-8')
        print(f"✓ Fixed {fixed} issue(s) in {filepath}")
        return fixed
    return 0

# Define all fixes
fixes = {
    'field_analyzer.py': [
        ("filename = os.path.basename(npy_file)", "filename = Path(npy_file).name"),
    ],
    
    'reconraven/core/config.py': [
        ("CONFIG_DIR = os.path.join(Path(__file__).parent, 'config')", 
         "CONFIG_DIR = Path(__file__).parent / 'config'"),
        ("BANDS_CONFIG = os.path.join(CONFIG_DIR, 'bands.yaml')", 
         "BANDS_CONFIG = CONFIG_DIR / 'bands.yaml'"),
        ("DEMOD_CONFIG = os.path.join(CONFIG_DIR, 'demod_config.yaml')", 
         "DEMOD_CONFIG = CONFIG_DIR / 'demod_config.yaml'"),
        ("HARDWARE_CONFIG = os.path.join(CONFIG_DIR, 'hardware.yaml')", 
         "HARDWARE_CONFIG = CONFIG_DIR / 'hardware.yaml'"),
        ("self.bands = self._load_yaml(os.path.join(self.config_dir, 'bands.yaml'))", 
         "self.bands = self._load_yaml(self.config_dir / 'bands.yaml')"),
        ("self.demod_params = self._load_yaml(os.path.join(self.config_dir, 'demod_config.yaml'))", 
         "self.demod_params = self._load_yaml(self.config_dir / 'demod_config.yaml')"),
        ("self.hardware_config = self._load_yaml(os.path.join(self.config_dir, 'hardware.yaml'))", 
         "self.hardware_config = self._load_yaml(self.config_dir / 'hardware.yaml')"),
    ],
    
    'reconraven/recording/logger.py': [
        ("os.makedirs(self.output_dir, exist_ok=True)", 
         "Path(self.output_dir).mkdir(parents=True, exist_ok=True)"),
        ("filepath = os.path.join(self.output_dir, filename)", 
         "filepath = Path(self.output_dir) / filename"),
    ],
    
    'reconraven/voice/monitor.py': [
        ("os.makedirs(self.recording_dir, exist_ok=True)", 
         "Path(self.recording_dir).mkdir(parents=True, exist_ok=True)"),
        ("output_file = os.path.join(\n                    self.recording_dir, f'voice_{freq_mhz:.3f}MHz_{timestamp}.wav'\n                )", 
         "output_file = str(Path(self.recording_dir) / f'voice_{freq_mhz:.3f}MHz_{timestamp}.wav')"),
    ],
    
    'reconraven/voice/transcriber.py': [
        ("if not os.path.exists(audio_file):", "if not Path(audio_file).exists():"),
        ("filename = os.path.basename(audio_file)", "filename = Path(audio_file).name"),
        ("audio_files = glob.glob(os.path.join(args.batch, '*.wav'))", 
         "audio_files = list(Path(args.batch).glob('*.wav'))"),
        ("print(f'[{current}/{total}] {os.path.basename(filename)}')", 
         "print(f'[{current}/{total}] {Path(filename).name}')"),
    ],
    
    'reconraven/web/server.py': [
        ("files = glob.glob(os.path.join(recordings_dir, '*.wav'))", 
         "files = list(Path(recordings_dir).glob('*.wav'))"),
        ("stat = os.stat(filepath)", "stat = Path(filepath).stat()"),
        ("audio_dir = os.path.join(Path.cwd(), 'recordings', 'audio')", 
         "audio_dir = Path.cwd() / 'recordings' / 'audio'"),
        ("npy_path = os.path.join('recordings', 'audio', recording_file)", 
         "npy_path = Path('recordings') / 'audio' / recording_file"),
    ],
    
    'recording_manager.py': [
        ("print(f'[WAV] Converting {os.path.basename(npy_filepath)} to audio...')", 
         "print(f'[WAV] Converting {Path(npy_filepath).name} to audio...')"),
        ("npy_size_mb = os.path.getsize(npy_filepath) / (1024 * 1024)", 
         "npy_size_mb = Path(npy_filepath).stat().st_size / (1024 * 1024)"),
        ("wav_size_mb = os.path.getsize(wav_filepath) / (1024 * 1024)", 
         "wav_size_mb = Path(wav_filepath).stat().st_size / (1024 * 1024)"),
        ("if not os.path.exists(filepath):", "if not Path(filepath).exists():"),
        ("size_mb = os.path.getsize(filepath) / (1024 * 1024)\n                os.remove(filepath)", 
         "size_mb = Path(filepath).stat().st_size / (1024 * 1024)\n                Path(filepath).unlink()"),
        ("self.db.update_recording_audio(recording_id, os.path.basename(wav_file))", 
         "self.db.update_recording_audio(recording_id, Path(wav_file).name)"),
        ("npy_size_mb = os.path.getsize(filepath) / (1024 * 1024)\n                    os.remove(filepath)", 
         "npy_size_mb = Path(filepath).stat().st_size / (1024 * 1024)\n                    Path(filepath).unlink()"),
        ("logger.info(f'Transcribing {os.path.basename(wav_filepath)}...')", 
         "logger.info(f'Transcribing {Path(wav_filepath).name}...')"),
        ("if os.path.exists(filepath):\n                size_mb = os.path.getsize(filepath) / (1024 * 1024)\n                os.remove(filepath)", 
         "if Path(filepath).exists():\n                size_mb = Path(filepath).stat().st_size / (1024 * 1024)\n                Path(filepath).unlink()"),
    ],
    
    'rtl433_integration.py': [
        ("print(f'Converted: {cu8_file} ({os.path.getsize(cu8_file) / 1024 / 1024:.1f} MB)')", 
         "print(f'Converted: {cu8_file} ({Path(cu8_file).stat().st_size / 1024 / 1024:.1f} MB)')"),
        ("if os.path.exists(cu8_file):\n                os.remove(cu8_file)", 
         "if Path(cu8_file).exists():\n                Path(cu8_file).unlink()"),
    ],
    
    'voice_monitor.py': [
        ("os.makedirs(self.recording_dir, exist_ok=True)", 
         "Path(self.recording_dir).mkdir(parents=True, exist_ok=True)"),
        ("output_file = os.path.join(\n                    self.recording_dir, f'voice_{freq_mhz:.3f}MHz_{timestamp}.wav'\n                )", 
         "output_file = str(Path(self.recording_dir) / f'voice_{freq_mhz:.3f}MHz_{timestamp}.wav')"),
    ],
    
    'voice_transcriber.py': [
        ("if not os.path.exists(audio_file):", "if not Path(audio_file).exists():"),
        ("filename = os.path.basename(audio_file)", "filename = Path(audio_file).name"),
        ("audio_files = glob.glob(os.path.join(args.batch, '*.wav'))", 
         "audio_files = [str(p) for p in Path(args.batch).glob('*.wav')]"),
        ("print(f'[{current}/{total}] {os.path.basename(filename)}')", 
         "print(f'[{current}/{total}] {Path(filename).name}')"),
    ],
}

# Run fixes
total_fixed = 0
for filepath, replacements in fixes.items():
    total_fixed += fix_file(filepath, replacements)

print(f"\n✅ Total fixes applied: {total_fixed}")

