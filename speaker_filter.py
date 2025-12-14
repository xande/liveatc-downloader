#!/usr/bin/env python3
"""
ATC Audio Speaker Filter
Identifies and extracts/removes specific speaker segments from ATC recordings.

Features:
- Speaker diarization (identifies different speakers)
- Voice fingerprinting to identify your friend's voice
- Extract or remove segments where specific speaker is talking
- Batch processing multiple recordings

Dependencies:
    pip install pyannote.audio pydub torch torchaudio
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple, Optional
import json


def check_dependencies():
    """Check if required packages are installed"""
    missing = []

    try:
        import torch
    except ImportError:
        missing.append("torch")

    try:
        import torchaudio
    except ImportError:
        missing.append("torchaudio")

    try:
        from pyannote.audio import Pipeline
    except ImportError:
        missing.append("pyannote.audio")

    try:
        from pydub import AudioSegment
    except ImportError:
        missing.append("pydub")

    if missing:
        print("Missing required packages. Install with:")
        print(f"  pip install {' '.join(missing)}")
        return False

    return True


class SpeakerFilter:
    """Identifies and filters specific speakers from audio recordings"""

    def __init__(self, hf_token: Optional[str] = None):
        """
        Initialize the speaker filter.

        Args:
            hf_token: HuggingFace API token (required for pyannote models)
                     Get one free at: https://huggingface.co/settings/tokens
        """
        if not check_dependencies():
            raise RuntimeError("Missing required dependencies")

        from pyannote.audio import Pipeline
        import torch

        self.hf_token = hf_token or os.getenv('HF_TOKEN')

        if not self.hf_token:
            print("\n⚠️  WARNING: No HuggingFace token provided!")
            print("   Get a free token at: https://huggingface.co/settings/tokens")
            print("   Then accept the model terms at: https://huggingface.co/pyannote/speaker-diarization-3.1")
            print("   Set it with: export HF_TOKEN='your_token_here'\n")

        print("Loading speaker diarization model (this may take a moment)...")

        # Use GPU if available
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")

        # Load the speaker diarization pipeline
        try:
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=self.hf_token
            )
            self.pipeline.to(self.device)
        except Exception as e:
            print(f"\n❌ Error loading model: {e}")
            print("   Make sure you:")
            print("   1. Have a HuggingFace token")
            print("   2. Accepted the model terms at: https://huggingface.co/pyannote/speaker-diarization-3.1")
            raise

    def analyze_speakers(self, audio_path: str) -> dict:
        """
        Analyze an audio file and identify different speakers.

        Args:
            audio_path: Path to audio file (MP3, WAV, etc.)

        Returns:
            Dictionary with speaker segments and statistics
        """
        print(f"\nAnalyzing: {audio_path}")

        # Run diarization
        diarization = self.pipeline(audio_path)

        # Collect speaker statistics
        speakers = {}
        segments = []

        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speaker_id = speaker
            duration = turn.end - turn.start

            # Track statistics per speaker
            if speaker_id not in speakers:
                speakers[speaker_id] = {
                    'total_time': 0,
                    'num_segments': 0,
                    'segments': []
                }

            speakers[speaker_id]['total_time'] += duration
            speakers[speaker_id]['num_segments'] += 1
            speakers[speaker_id]['segments'].append({
                'start': turn.start,
                'end': turn.end,
                'duration': duration
            })

            segments.append({
                'speaker': speaker_id,
                'start': turn.start,
                'end': turn.end,
                'duration': duration
            })

        return {
            'speakers': speakers,
            'segments': segments,
            'num_speakers': len(speakers)
        }

    def print_analysis(self, analysis: dict):
        """Print a summary of the speaker analysis"""
        print(f"\n{'='*60}")
        print(f"Found {analysis['num_speakers']} different speaker(s)")
        print(f"{'='*60}\n")

        for speaker_id, stats in sorted(analysis['speakers'].items()):
            print(f"Speaker {speaker_id}:")
            print(f"  Total speaking time: {stats['total_time']:.1f} seconds")
            print(f"  Number of segments: {stats['num_segments']}")
            print(f"  Average segment length: {stats['total_time']/stats['num_segments']:.1f}s")
            print()

    def extract_speaker_segments(
        self,
        audio_path: str,
        speaker_id: str,
        output_path: str,
        analysis: Optional[dict] = None
    ):
        """
        Extract only segments where a specific speaker is talking.

        Args:
            audio_path: Input audio file
            speaker_id: Speaker to extract (e.g., "SPEAKER_00")
            output_path: Output file path
            analysis: Pre-computed analysis (optional, will compute if not provided)
        """
        from pydub import AudioSegment

        if analysis is None:
            analysis = self.analyze_speakers(audio_path)

        if speaker_id not in analysis['speakers']:
            print(f"❌ Speaker '{speaker_id}' not found in audio!")
            print(f"   Available speakers: {', '.join(analysis['speakers'].keys())}")
            return

        print(f"\nExtracting segments for {speaker_id}...")

        # Load audio
        audio = AudioSegment.from_file(audio_path)

        # Combine all segments for this speaker
        result = AudioSegment.empty()
        segments = analysis['speakers'][speaker_id]['segments']

        for i, seg in enumerate(segments, 1):
            start_ms = int(seg['start'] * 1000)
            end_ms = int(seg['end'] * 1000)
            result += audio[start_ms:end_ms]
            print(f"  [{i}/{len(segments)}] Added segment: {seg['start']:.1f}s - {seg['end']:.1f}s")

        # Export
        print(f"\nExporting to: {output_path}")
        result.export(output_path, format=Path(output_path).suffix[1:])
        print(f"✅ Extracted {len(segments)} segments ({result.duration_seconds:.1f}s total)")

    def remove_speaker_segments(
        self,
        audio_path: str,
        speaker_id: str,
        output_path: str,
        analysis: Optional[dict] = None
    ):
        """
        Remove segments where a specific speaker is talking (keep everyone else).

        Args:
            audio_path: Input audio file
            speaker_id: Speaker to remove (e.g., "SPEAKER_00")
            output_path: Output file path
            analysis: Pre-computed analysis (optional, will compute if not provided)
        """
        from pydub import AudioSegment

        if analysis is None:
            analysis = self.analyze_speakers(audio_path)

        if speaker_id not in analysis['speakers']:
            print(f"❌ Speaker '{speaker_id}' not found in audio!")
            print(f"   Available speakers: {', '.join(analysis['speakers'].keys())}")
            return

        print(f"\nRemoving segments for {speaker_id}...")

        # Load audio
        audio = AudioSegment.from_file(audio_path)

        # Get all segments sorted by time
        all_segments = sorted(analysis['segments'], key=lambda x: x['start'])

        # Build result by keeping everything except target speaker
        result = AudioSegment.empty()
        last_end = 0

        for seg in all_segments:
            start_ms = int(seg['start'] * 1000)
            end_ms = int(seg['end'] * 1000)

            if seg['speaker'] == speaker_id:
                # Add everything before this speaker segment
                if last_end < start_ms:
                    result += audio[last_end:start_ms]
                last_end = end_ms
            else:
                # Keep non-target speaker segments
                if last_end < start_ms:
                    result += audio[last_end:start_ms]
                result += audio[start_ms:end_ms]
                last_end = end_ms

        # Add any remaining audio
        if last_end < len(audio):
            result += audio[last_end:]

        # Export
        print(f"\nExporting to: {output_path}")
        result.export(output_path, format=Path(output_path).suffix[1:])
        print(f"✅ Removed {speaker_id} segments ({result.duration_seconds:.1f}s remaining)")


def main():
    """Command-line interface"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Filter ATC recordings by speaker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze speakers in a recording
  python speaker_filter.py analyze recording.mp3

  # Extract only your friend's voice
  python speaker_filter.py extract recording.mp3 SPEAKER_00 friend_only.mp3

  # Remove your friend's voice (keep everyone else)
  python speaker_filter.py remove recording.mp3 SPEAKER_00 others_only.mp3

  # Batch process multiple files
  python speaker_filter.py batch /path/to/recordings/ SPEAKER_00 --remove

Setup:
  1. Install dependencies: pip install pyannote.audio pydub torch torchaudio
  2. Get HuggingFace token: https://huggingface.co/settings/tokens
  3. Accept model terms: https://huggingface.co/pyannote/speaker-diarization-3.1
  4. Set token: export HF_TOKEN='your_token_here'
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze speakers in audio file')
    analyze_parser.add_argument('audio_file', help='Path to audio file')
    analyze_parser.add_argument('--save-json', help='Save analysis to JSON file')

    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract specific speaker segments')
    extract_parser.add_argument('audio_file', help='Path to audio file')
    extract_parser.add_argument('speaker_id', help='Speaker ID to extract (e.g., SPEAKER_00)')
    extract_parser.add_argument('output_file', help='Output file path')

    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove specific speaker segments')
    remove_parser.add_argument('audio_file', help='Path to audio file')
    remove_parser.add_argument('speaker_id', help='Speaker ID to remove (e.g., SPEAKER_00)')
    remove_parser.add_argument('output_file', help='Output file path')

    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Batch process directory')
    batch_parser.add_argument('directory', help='Directory containing audio files')
    batch_parser.add_argument('speaker_id', help='Speaker ID to process')
    batch_parser.add_argument('--extract', action='store_true', help='Extract speaker (default: remove)')
    batch_parser.add_argument('--remove', action='store_true', help='Remove speaker')
    batch_parser.add_argument('--output-dir', help='Output directory (default: same as input)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize filter
    try:
        speaker_filter = SpeakerFilter()
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return 1

    # Execute command
    if args.command == 'analyze':
        analysis = speaker_filter.analyze_speakers(args.audio_file)
        speaker_filter.print_analysis(analysis)

        if args.save_json:
            with open(args.save_json, 'w') as f:
                json.dump(analysis, f, indent=2)
            print(f"\n💾 Analysis saved to: {args.save_json}")

    elif args.command == 'extract':
        speaker_filter.extract_speaker_segments(
            args.audio_file,
            args.speaker_id,
            args.output_file
        )

    elif args.command == 'remove':
        speaker_filter.remove_speaker_segments(
            args.audio_file,
            args.speaker_id,
            args.output_file
        )

    elif args.command == 'batch':
        directory = Path(args.directory)
        output_dir = Path(args.output_dir) if args.output_dir else directory / 'filtered'
        output_dir.mkdir(exist_ok=True)

        # Find all audio files
        audio_files = []
        for ext in ['*.mp3', '*.wav', '*.m4a', '*.flac']:
            audio_files.extend(directory.glob(ext))

        print(f"\nFound {len(audio_files)} audio file(s)")

        mode = 'extract' if args.extract else 'remove'

        for i, audio_file in enumerate(audio_files, 1):
            print(f"\n{'='*60}")
            print(f"Processing [{i}/{len(audio_files)}]: {audio_file.name}")
            print(f"{'='*60}")

            output_file = output_dir / f"{audio_file.stem}_{mode}_{args.speaker_id}{audio_file.suffix}"

            try:
                if mode == 'extract':
                    speaker_filter.extract_speaker_segments(
                        str(audio_file),
                        args.speaker_id,
                        str(output_file)
                    )
                else:
                    speaker_filter.remove_speaker_segments(
                        str(audio_file),
                        args.speaker_id,
                        str(output_file)
                    )
            except Exception as e:
                print(f"❌ Error processing {audio_file.name}: {e}")
                continue

        print(f"\n✅ Batch processing complete! Output in: {output_dir}")


if __name__ == '__main__':
    sys.exit(main() or 0)
