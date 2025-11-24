#!/usr/bin/env python3
"""
Batch Transcription Tool
Transcribe all untranscribed voice recordings in the database
"""

import logging
from database import get_db
from voice_transcriber import VoiceTranscriber
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def batch_transcribe_untranscribed():
    """Find and transcribe all untranscribed voice recordings"""
    db = get_db()
    transcriber = VoiceTranscriber(model_size='base')
    
    # Get all untranscribed recordings
    untranscribed = db.get_untranscribed_recordings()
    
    if not untranscribed:
        logger.info("No untranscribed recordings found")
        return 0
    
    logger.info(f"Found {len(untranscribed)} untranscribed recordings")
    
    successful = 0
    failed = 0
    
    for i, recording in enumerate(untranscribed, 1):
        filename = recording['filename']
        recording_id = recording['id']
        
        # Look for WAV file (preferred) or .npy
        wav_path = Path(f"recordings/audio/{filename.replace('.npy', '.wav')}")
        npy_path = Path(f"recordings/audio/{filename}")
        
        audio_file = None
        if wav_path.exists():
            audio_file = str(wav_path)
        elif npy_path.exists():
            audio_file = str(npy_path)
        else:
            logger.warning(f"[{i}/{len(untranscribed)}] File not found: {filename}")
            failed += 1
            continue
        
        logger.info(f"[{i}/{len(untranscribed)}] Transcribing {filename}...")
        
        try:
            result = transcriber.transcribe_file(audio_file)
            
            if 'error' in result:
                logger.error(f"  Error: {result['error']}")
                failed += 1
                continue
            
            text = result.get('text', '').strip()
            if not text:
                logger.info("  No speech detected")
                failed += 1
                continue
            
            # Save to database
            db.add_transcript(
                recording_id=recording_id,
                text=text,
                language=result.get('language'),
                confidence=result.get('confidence', 0.0),
                duration=result.get('duration', 0.0),
                segments=result.get('segments', [])
            )
            
            logger.info(f"  ✓ Transcribed: '{text[:60]}...'")
            successful += 1
            
        except Exception as e:
            logger.error(f"  Exception: {e}")
            failed += 1
    
    logger.info(f"\nBatch transcription complete:")
    logger.info(f"  Successful: {successful}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Total: {len(untranscribed)}")
    
    return successful


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch transcribe voice recordings')
    parser.add_argument('--model', type=str, default='base',
                       choices=['tiny', 'base', 'small', 'medium', 'large'],
                       help='Whisper model size (default: base)')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("RECONRAVEN BATCH TRANSCRIPTION")
    print("="*70 + "\n")
    
    batch_transcribe_untranscribed()

