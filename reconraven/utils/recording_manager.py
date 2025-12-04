#!/usr/bin/env python3
"""
Smart Recording Cleanup Module
Automatically manages disk space by cleaning up recordings after analysis
Also handles voice signal transcription
"""

import logging
import os
from datetime import datetime

import numpy as np
from scipy import signal


logger = logging.getLogger(__name__)


class RecordingManager:
    """Manages recording lifecycle, cleanup, and transcription"""

    def __init__(self, db):
        self.db = db
        self.voice_transcriber = None  # Lazy load

    def _get_transcriber(self):
        """Lazy load voice transcriber"""
        if self.voice_transcriber is None:
            try:
                from reconraven.voice.transcriber import VoiceTranscriber

                self.voice_transcriber = VoiceTranscriber(model_size='base')
            except Exception as e:
                logger.warning(f'Could not load transcriber: {e}')
        return self.voice_transcriber

    def should_keep_recording(self, frequency_hz, band):
        """Determine if recording should be kept based on band/type"""
        # ISM bands - delete after analysis (short bursts, no replay value)
        ism_bands = ['ISM433', 'ISM915']
        if band in ism_bands:
            return False

        # Voice bands - convert to WAV and delete .npy
        voice_bands = ['2m', '70cm']
        if band in voice_bands:
            return 'convert_to_wav'

        # Unknown - keep for manual review
        return True

    def demodulate_to_wav(self, npy_filepath):
        """Convert IQ .npy to demodulated WAV audio"""
        try:
            print(f'[WAV] Converting {os.path.basename(npy_filepath)} to audio...')

            # Load IQ samples
            samples = np.load(npy_filepath)

            # FM demodulation
            # Calculate instantaneous phase
            phase = np.unwrap(np.angle(samples))

            # Derivative of phase = instantaneous frequency
            audio = np.diff(phase)

            # Normalize to 16-bit PCM range
            audio = audio / np.max(np.abs(audio)) * 32767
            audio = audio.astype(np.int16)

            # Downsample to 48kHz for audio playback
            # Original is 2.4 Msps, way too high for audio
            decimation_factor = 50  # 2.4M / 50 = 48kHz
            audio_downsampled = signal.decimate(audio, decimation_factor, zero_phase=True)

            # Save as WAV
            wav_filepath = npy_filepath.replace('.npy', '.wav')

            from scipy.io import wavfile

            wavfile.write(wav_filepath, 48000, audio_downsampled.astype(np.int16))

            # Get file sizes
            npy_size_mb = os.path.getsize(npy_filepath) / (1024 * 1024)
            wav_size_mb = os.path.getsize(wav_filepath) / (1024 * 1024)

            print(
                f'[WAV] Success! {npy_size_mb:.1f}MB → {wav_size_mb:.1f}MB (saved {npy_size_mb - wav_size_mb:.1f}MB)'
            )

            return wav_filepath

        except Exception as e:
            print(f'[WAV] Error converting to audio: {e}')
            return None

    def cleanup_after_analysis(self, recording_id, analysis_results):
        """Clean up recording based on analysis results and band
        Also transcribes voice signals if detected
        """
        try:
            # Get recording info
            recording = self.db.get_recording_by_id(recording_id)
            if not recording:
                return

            filepath = f"recordings/audio/{recording['filename']}"
            if not os.path.exists(filepath):
                return

            freq = recording['frequency_hz']
            band = recording['band']

            decision = self.should_keep_recording(freq, band)

            if decision == False:
                # ISM band - delete immediately
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                os.remove(filepath)
                logger.info(
                    f"Deleted {recording['filename']} ({size_mb:.1f}MB) - ISM band, no replay value"
                )

            elif decision == 'convert_to_wav':
                # Voice band - convert to WAV then delete .npy
                wav_file = self.demodulate_to_wav(filepath)
                if wav_file:
                    # Update database with WAV filename
                    self.db.update_recording_audio(recording_id, os.path.basename(wav_file))

                    # AUTO-TRANSCRIBE VOICE SIGNALS
                    self.transcribe_voice_recording(recording_id, wav_file)

                    # Delete the large .npy file
                    npy_size_mb = os.path.getsize(filepath) / (1024 * 1024)
                    os.remove(filepath)
                    logger.info(f'Converted to WAV and deleted .npy ({npy_size_mb:.1f}MB saved)')
                else:
                    logger.warning('WAV conversion failed, keeping .npy for manual review')

            else:
                # Keep for manual review
                logger.info(f"Keeping {recording['filename']} for manual review")

        except Exception as e:
            logger.error(f'Cleanup error: {e}')

    def transcribe_voice_recording(self, recording_id, wav_filepath):
        """Auto-transcribe voice recording using Whisper"""
        try:
            # Check if already transcribed
            existing = self.db.get_transcript(recording_id)
            if existing:
                logger.info(f'Recording {recording_id} already transcribed, skipping')
                return

            transcriber = self._get_transcriber()
            if not transcriber:
                logger.warning('Transcriber not available, skipping transcription')
                return

            logger.info(f'Transcribing {os.path.basename(wav_filepath)}...')
            result = transcriber.transcribe_file(wav_filepath)

            if 'error' in result:
                logger.error(f"Transcription failed: {result['error']}")
                return

            # Save to database
            text = result.get('text', '')
            if text:
                self.db.add_transcript(
                    recording_id=recording_id,
                    text=text,
                    language=result.get('language'),
                    confidence=result.get('confidence', 0.0),
                    duration=result.get('duration', 0.0),
                    segments=result.get('segments', []),
                )
                logger.info(f"Transcription saved: '{text[:50]}...'")
            else:
                logger.info('No speech detected in recording')

        except Exception as e:
            logger.error(f'Transcription error: {e}')


def cleanup_old_recordings(db, days_old=7):
    """Bulk cleanup of old unanalyzed recordings"""
    manager = RecordingManager(db)

    recordings = db.get_recordings()
    cleaned = 0
    saved_mb = 0

    for rec in recordings:
        if rec['analyzed']:
            continue  # Skip already analyzed

        # Check age
        from datetime import timedelta

        captured = datetime.fromisoformat(rec['captured_at'])
        if datetime.now() - captured > timedelta(days=days_old):
            # Old and unanalyzed - probably not important
            filepath = f"recordings/audio/{rec['filename']}"
            if os.path.exists(filepath):
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                os.remove(filepath)
                saved_mb += size_mb
                cleaned += 1

    print(f'[Bulk Cleanup] Deleted {cleaned} old recordings, saved {saved_mb:.1f}MB')
    return cleaned, saved_mb


if __name__ == '__main__':
    from reconraven.core.database import get_db

    db = get_db()

    # Run bulk cleanup
    cleaned, saved = cleanup_old_recordings(db, days_old=7)
    print(f'\nTotal: {cleaned} files, {saved:.1f}MB freed')
