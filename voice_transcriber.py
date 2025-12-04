#!/usr/bin/env python3
"""
Voice Transcription Engine
Uses OpenAI Whisper for speech-to-text transcription
"""

import json
import logging
import os
import wave
from datetime import datetime
from typing import Optional


logger = logging.getLogger(__name__)


class VoiceTranscriber:
    """Transcribes voice recordings using Whisper"""

    def __init__(self, model_size: str = 'base'):
        """Initialize transcriber

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
                       tiny: ~39M params, fastest
                       base: ~74M params, good balance (RECOMMENDED)
                       small: ~244M params, better accuracy
                       medium: ~769M params, very accurate
                       large: ~1550M params, best accuracy, slowest
        """
        self.model_size = model_size
        self.model = None
        self._check_whisper_installed()

    def _check_whisper_installed(self):
        """Check if Whisper is installed"""
        try:
            import whisper

            self.whisper = whisper
            logger.info(f'Whisper installed, using model: {self.model_size}')
        except ImportError:
            logger.warning('Whisper not installed. Install with: pip install openai-whisper')
            self.whisper = None

    def _load_model(self):
        """Lazy load Whisper model (only when needed)"""
        if self.model is None and self.whisper:
            logger.info(f'Loading Whisper {self.model_size} model...')
            self.model = self.whisper.load_model(self.model_size)
            logger.info('Model loaded successfully')

    def transcribe_file(self, audio_file: str, language: Optional[str] = None) -> dict:
        """Transcribe an audio file

        Args:
            audio_file: Path to WAV file
            language: Optional language code (en, es, fr, etc). Auto-detect if None

        Returns:
            {
                'text': 'full transcription',
                'segments': [{'start': 0.0, 'end': 2.5, 'text': 'hello'}],
                'language': 'en',
                'confidence': 0.95,
                'duration': 10.5
            }
        """
        if not self.whisper:
            return {'error': 'Whisper not installed'}

        if not os.path.exists(audio_file):
            return {'error': f'File not found: {audio_file}'}

        try:
            self._load_model()

            logger.info(f'Transcribing: {audio_file}')

            # Transcribe with Whisper
            result = self.model.transcribe(
                audio_file, language=language, task='transcribe', verbose=False
            )

            # Get audio duration
            duration = self._get_audio_duration(audio_file)

            # Calculate average confidence
            confidence = self._calculate_confidence(result)

            transcript = {
                'text': result['text'].strip(),
                'segments': [
                    {'start': seg['start'], 'end': seg['end'], 'text': seg['text'].strip()}
                    for seg in result.get('segments', [])
                ],
                'language': result.get('language', 'unknown'),
                'confidence': confidence,
                'duration': duration,
                'transcribed_at': datetime.now().isoformat(),
            }

            logger.info(f"Transcription complete: '{transcript['text'][:100]}...'")

            return transcript

        except Exception as e:
            logger.exception(f'Transcription error: {e}')
            return {'error': str(e)}

    def transcribe_batch(
        self, audio_files: list[str], progress_callback: Optional[callable] = None
    ) -> dict[str, dict]:
        """Transcribe multiple files

        Args:
            audio_files: List of audio file paths
            progress_callback: Optional callback(current, total, filename)

        Returns:
            {filename: transcript_dict}
        """
        results = {}
        total = len(audio_files)

        for i, audio_file in enumerate(audio_files, 1):
            if progress_callback:
                progress_callback(i, total, audio_file)

            filename = os.path.basename(audio_file)
            results[filename] = self.transcribe_file(audio_file)

        return results

    def _get_audio_duration(self, audio_file: str) -> float:
        """Get duration of WAV file"""
        try:
            with wave.open(audio_file, 'rb') as wav:
                frames = wav.getnframes()
                rate = wav.getframerate()
                return frames / float(rate)
        except:
            return 0.0

    def _calculate_confidence(self, result: dict) -> float:
        """Calculate average confidence from Whisper result"""
        try:
            segments = result.get('segments', [])
            if not segments:
                return 0.0

            # Whisper doesn't directly provide confidence, but we can estimate
            # based on segment probabilities if available
            confidences = []
            for seg in segments:
                if 'avg_logprob' in seg:
                    # Convert log probability to confidence (0-1)
                    conf = min(1.0, max(0.0, (seg['avg_logprob'] + 1.0) / 1.0))
                    confidences.append(conf)

            return sum(confidences) / len(confidences) if confidences else 0.8
        except:
            return 0.8  # Default confidence

    def search_transcripts(
        self, transcripts: list[dict], keywords: list[str], case_sensitive: bool = False
    ) -> list[dict]:
        """Search transcripts for keywords

        Args:
            transcripts: List of transcript dictionaries
            keywords: List of keywords to search for
            case_sensitive: Whether search is case sensitive

        Returns:
            List of matching transcripts with highlighted keywords
        """
        matches = []

        for transcript in transcripts:
            text = transcript.get('text', '')
            if not text:
                continue

            search_text = text if case_sensitive else text.lower()
            search_keywords = keywords if case_sensitive else [k.lower() for k in keywords]

            # Check if any keyword matches
            found_keywords = []
            for keyword in search_keywords:
                if keyword in search_text:
                    found_keywords.append(keyword)

            if found_keywords:
                match = transcript.copy()
                match['matched_keywords'] = found_keywords
                match['match_count'] = len(found_keywords)
                matches.append(match)

        # Sort by number of matches
        matches.sort(key=lambda x: x['match_count'], reverse=True)

        return matches

    def export_transcripts(self, transcripts: list[dict], output_file: str, format: str = 'json'):
        """Export transcripts to file

        Args:
            transcripts: List of transcript dictionaries
            output_file: Output file path
            format: Export format (json, txt, srt, csv)
        """
        if format == 'json':
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(transcripts, f, indent=2, ensure_ascii=False)

        elif format == 'txt':
            with open(output_file, 'w', encoding='utf-8') as f:
                for t in transcripts:
                    f.write(f"=== {t.get('filename', 'Unknown')} ===\n")
                    f.write(f"Time: {t.get('transcribed_at', 'Unknown')}\n")
                    f.write(f"Language: {t.get('language', 'Unknown')}\n")
                    f.write(f"Duration: {t.get('duration', 0):.1f}s\n")
                    f.write(f"\n{t.get('text', '')}\n\n")

        elif format == 'srt':
            # SRT subtitle format
            with open(output_file, 'w', encoding='utf-8') as f:
                counter = 1
                for t in transcripts:
                    for seg in t.get('segments', []):
                        f.write(f'{counter}\n')
                        f.write(
                            f"{self._format_timestamp(seg['start'])} --> {self._format_timestamp(seg['end'])}\n"
                        )
                        f.write(f"{seg['text']}\n\n")
                        counter += 1

        elif format == 'csv':
            import csv

            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Filename', 'Timestamp', 'Language', 'Duration', 'Text'])
                for t in transcripts:
                    writer.writerow(
                        [
                            t.get('filename', ''),
                            t.get('transcribed_at', ''),
                            t.get('language', ''),
                            t.get('duration', 0),
                            t.get('text', ''),
                        ]
                    )

        logger.info(f'Exported {len(transcripts)} transcripts to {output_file}')

    def _format_timestamp(self, seconds: float) -> str:
        """Format timestamp for SRT (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f'{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}'


# ========== CLI INTERFACE ==========

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Voice Transcription Tool')
    parser.add_argument('--file', type=str, help='Audio file to transcribe')
    parser.add_argument('--batch', type=str, help='Directory of audio files to transcribe')
    parser.add_argument(
        '--model',
        type=str,
        default='base',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        help='Whisper model size',
    )
    parser.add_argument('--language', type=str, help='Language code (en, es, fr, etc)')
    parser.add_argument('--output', type=str, help='Output file for transcript')
    parser.add_argument(
        '--format',
        type=str,
        default='json',
        choices=['json', 'txt', 'srt', 'csv'],
        help='Output format',
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    transcriber = VoiceTranscriber(model_size=args.model)

    if args.file:
        # Single file transcription
        print(f'\nTranscribing: {args.file}')
        result = transcriber.transcribe_file(args.file, language=args.language)

        if 'error' in result:
            print(f"Error: {result['error']}")
        else:
            print(f"\n{'='*70}")
            print('TRANSCRIPTION')
            print(f"{'='*70}")
            print(f"Language: {result['language']}")
            print(f"Duration: {result['duration']:.1f}s")
            print(f"Confidence: {result['confidence']*100:.1f}%")
            print(f"\n{result['text']}\n")

            if args.output:
                transcriber.export_transcripts([result], args.output, format=args.format)
                print(f'Saved to: {args.output}')

    elif args.batch:
        # Batch transcription
        import glob

        audio_files = glob.glob(os.path.join(args.batch, '*.wav'))

        print(f'\nFound {len(audio_files)} audio files')
        print(f'Using model: {args.model}')
        print('Starting batch transcription...\n')

        def progress(current, total, filename):
            print(f'[{current}/{total}] {os.path.basename(filename)}')

        results = transcriber.transcribe_batch(audio_files, progress_callback=progress)

        # Count successful transcriptions
        successful = sum(1 for r in results.values() if 'error' not in r)
        print(f'\nCompleted: {successful}/{len(results)} successful')

        if args.output:
            transcripts_list = [
                {**v, 'filename': k} for k, v in results.items() if 'error' not in v
            ]
            transcriber.export_transcripts(transcripts_list, args.output, format=args.format)
            print(f'Saved to: {args.output}')

    else:
        parser.print_help()
