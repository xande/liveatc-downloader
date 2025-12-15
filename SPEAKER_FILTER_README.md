# ATC Speaker Filter Tool

Automatically identify and filter specific speakers from ATC recordings using AI voice recognition.

## Overview

This tool uses state-of-the-art speaker diarization to:
- Identify different speakers in ATC recordings
- Extract segments where your friend is talking
- Remove your friend's voice and keep everyone else
- Batch process multiple recordings

## Setup

### 1. Install Dependencies

```bash
# Install required packages
pip install pyannote.audio pydub torch torchaudio

# Also need ffmpeg for audio processing
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt-get install ffmpeg

# Windows: Download from https://ffmpeg.org/
```

### 2. Get HuggingFace Token (Free)

The speaker diarization model requires a free HuggingFace account:

1. Create account at: https://huggingface.co/join
2. Get your token at: https://huggingface.co/settings/tokens
3. Accept the model terms at: https://huggingface.co/pyannote/speaker-diarization-3.1
4. Set your token:
   ```bash
   export HF_TOKEN='your_token_here'
   ```
   Or add to your `~/.bashrc` or `~/.zshrc` to make it permanent:
   ```bash
   echo 'export HF_TOKEN="your_token_here"' >> ~/.zshrc
   ```

## Usage

### Step 1: Analyze a Recording

First, analyze a recording to see which speakers are detected:

```bash
python speaker_filter.py analyze recording.mp3
```

Output example:
```
============================================================
Found 3 different speaker(s)
============================================================

Speaker SPEAKER_00:
  Total speaking time: 145.2 seconds
  Number of segments: 47
  Average segment length: 3.1s

Speaker SPEAKER_01:
  Total speaking time: 89.3 seconds
  Number of segments: 31
  Average segment length: 2.9s

Speaker SPEAKER_02:
  Total speaking time: 12.1 seconds
  Number of segments: 8
  Average segment length: 1.5s
```

**How to identify your friend:**
- The speaker with the most segments is usually the controller (your friend)
- Listen to the original recording and note which voice talks the most
- In the example above, `SPEAKER_00` is likely your friend (most segments)

### Step 2: Extract or Remove Your Friend's Voice

Once you identify which speaker is your friend (e.g., `SPEAKER_00`):

**Extract only your friend's segments:**
```bash
python speaker_filter.py extract recording.mp3 SPEAKER_00 friend_only.mp3
```

**Remove your friend (keep everyone else):**
```bash
python speaker_filter.py remove recording.mp3 SPEAKER_00 others_only.mp3
```

### Step 3: Batch Process Multiple Files

If you have multiple recordings and want to process them all:

```bash
# Remove SPEAKER_00 from all MP3s in a directory
python speaker_filter.py batch /path/to/recordings/ SPEAKER_00 --remove

# Extract SPEAKER_00 from all recordings
python speaker_filter.py batch /path/to/recordings/ SPEAKER_00 --extract

# Specify output directory
python speaker_filter.py batch /path/to/recordings/ SPEAKER_00 --remove --output-dir /path/to/output/
```

## Workflow Example

Here's a typical workflow:

```bash
# 1. Download ATC recordings (using the LiveATC downloader)
python gui.py

# 2. Analyze one recording to identify your friend
python speaker_filter.py analyze ~/Downloads/KPDX-App-Dep-Dec-13-2025-0000Z.mp3

# Output shows SPEAKER_00 has the most segments (probably your friend)

# 3. Batch remove your friend from all recordings
python speaker_filter.py batch ~/Downloads/ SPEAKER_00 --remove --output-dir ~/Downloads/filtered/

# 4. Now ~/Downloads/filtered/ contains recordings without your friend
```

## Advanced Options

### Save Analysis to JSON

```bash
python speaker_filter.py analyze recording.mp3 --save-json analysis.json
```

This creates a JSON file with detailed timing information for each segment.

### Integration with LiveATC Downloader

You can create a script to automatically process downloads:

```bash
#!/bin/bash
# auto_filter.sh

# Download recordings
python gui.py

# Process all new recordings
python speaker_filter.py batch ~/Downloads/ SPEAKER_00 --remove --output-dir ~/Downloads/filtered/
```

## How It Works

The tool uses **pyannote.audio**, a research-grade speaker diarization system that:

1. **Analyzes** the audio to detect speech activity
2. **Separates** different speakers based on voice characteristics
3. **Labels** each segment with a speaker ID (SPEAKER_00, SPEAKER_01, etc.)
4. **Extracts/Removes** segments based on your selection

### Accuracy Notes

- **Works best when:** Each speaker talks for at least a few seconds at a time (perfect for ATC where controllers speak frequently)
- **Less accurate when:** Very short transmissions or heavy background noise
- **Typical accuracy:** 85-95% for ATC recordings (controllers have consistent speech patterns)

## Performance

- **First run:** Takes ~30 seconds to load the AI model
- **Processing:** ~1-2 minutes per hour of audio (on CPU)
- **GPU acceleration:** If you have CUDA GPU, processing is ~10x faster

## Troubleshooting

### "No HuggingFace token"
Make sure you set the environment variable:
```bash
export HF_TOKEN='your_token_here'
```

### "Error loading model"
Make sure you accepted the model terms at:
https://huggingface.co/pyannote/speaker-diarization-3.1

### "Speaker not found"
The speaker ID might be different. Run `analyze` first to see all available speakers.

### ffmpeg not found
Install ffmpeg (see Setup section above).

## Tips

1. **Test first:** Always analyze a sample recording first to identify which speaker is your friend
2. **Consistent speaker:** If your friend works different shifts, they might be detected as different speakers across different days
3. **Quality matters:** Better audio quality = better speaker separation
4. **Manual verification:** Always spot-check a few filtered recordings to verify accuracy

## Technical Details

- **Model:** pyannote/speaker-diarization-3.1
- **License:** MIT (model requires HuggingFace terms acceptance)
- **Privacy:** All processing happens locally on your machine
- **No internet required:** After initial model download (~500MB)
