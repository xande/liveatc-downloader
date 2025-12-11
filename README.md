# LiveATC Downloader

A Python tool for downloading and processing archived Air Traffic Control (ATC) recordings from [LiveATC.net](https://www.liveatc.net).

## Features

- 🖥️ **GUI Application**: User-friendly graphical interface for easy downloads
- 🔍 **Search Stations**: List all available ATC frequencies for any airport by ICAO code
- 📥 **Download Archives**: Download individual 30-minute MP3 archives
- 📦 **Bulk Downloads**: Download multiple archives across a date/time range
- 🔊 **Audio Processing**: Normalize amplitude, chunk audio, and reduce noise
- 🔒 **SSL Fixed**: Handles certificate verification issues automatically

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [GUI Application](#gui-application)
- [Usage](#usage)
  - [List Available Stations](#list-available-stations)
  - [Download Single Archive](#download-single-archive)
  - [Download Date Range](#download-date-range)
- [How It Works](#how-it-works)
- [Audio Processing](#audio-processing)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yanjz124/liveatc-downloader.git
cd liveatc-downloader
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `numpy` - Numerical computing library
- `pydub` - Audio manipulation
- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- `noisereduce` - Audio noise reduction
- `certifi` - SSL certificate bundle

### Step 3: Verify Installation

```bash
python main.py --help
```

You should see the command usage information.

## Quick Start

### Using the GUI (Recommended for Beginners)

```bash
python gui.py
```

This will launch a graphical interface where you can:
1. Enter an airport ICAO code (e.g., KPDX)
2. Search for available stations
3. Select a station from the list
4. Set start and end times (UTC/Zulu)
5. Choose output folder
6. Click "Download Archives"

### Using the Command Line

```bash
# List all ATC stations for Portland International Airport
python main.py stations KPDX

# Download the most recent 30-minute archive for Portland Approach
python main.py download kpdx_app

# Download all archives from Dec 10, 2025 00:00Z to Dec 11, 2025 15:00Z
python main.py download-range kpdx_app Dec-10-2025-0000Z -e Dec-11-2025-1500Z
```

## GUI Application

The GUI provides a user-friendly interface with the following features:

### Features

- **Airport Search**: Enter ICAO code and search for all available stations
- **Station List**: View all stations with online/offline status (● = online, ○ = offline)
- **Station Details**: See frequencies and status when selecting a station
- **Time Range**: Set start and end times in UTC/Zulu format
- **Output Folder**: Browse and select where to save downloaded files
- **Download Progress**: Real-time log showing download status
- **Summary**: Shows successful and failed downloads when complete

### Running the GUI

```bash
python gui.py
```

### GUI Screenshot Description

The interface includes:
- **Airport ICAO Code** input field with Search button
- **Available Stations** list showing all stations for the airport
- **Selected Station** info showing frequencies and status
- **Time Range** inputs for start/end date and time (UTC)
- **Output Folder** selector with browse button
- **Download Archives** button to start the process
- **Download Log** showing real-time progress
- **Status Bar** at the bottom showing current operation

### GUI Tips

- All times are in **UTC/Zulu** (no timezone conversion needed)
- Date format: `Dec-11-2025`
- Time format: `1430Z` (24-hour format with Z suffix)
- Default output folder is `~/Downloads`
- Downloads run in background thread so the UI stays responsive
- Close the window to cancel an ongoing download

## Usage

### List Available Stations

Display all available ATC stations and frequencies for an airport:

```bash
python main.py stations <ICAO_CODE>
```

**Example:**
```bash
python main.py stations KCHO
```

**Output:**
```
[kcho3_app] - KCHO App/Dep
        potomac approach/departure - 132.850

[kcho3_twr] - KCHO Tower
        charlottesville tower - 124.500

[kcho3_zdc_121675] - ZDC Sector 60 #2
        washington center (sector 60 montebello) - 121.675
```

The **station identifier** (e.g., `kcho3_app`, `kcho3_zdc_121675`) is what you'll use for downloads.

### Download Single Archive

Download a single 30-minute MP3 archive:

```bash
python main.py download <STATION_ID> [-d DATE] [-t TIME]
```

**Parameters:**
- `STATION_ID`: Station identifier from the stations list
- `-d, --date`: Archive date (format: `Oct-01-2021`), defaults to current date
- `-t, --time`: Zulu time (format: `0000Z`), defaults to current time

**Examples:**

```bash
# Download most recent archive (defaults to current date/time)
python main.py download kcho3_app

# Download specific date and time
python main.py download kcho3_app -d Dec-11-2025 -t 1200Z

# Download specific date (current time)
python main.py download kcho3_app -d Dec-10-2025
```

**Note:** LiveATC typically keeps archives for 30 days only.

### Download Date Range

Download multiple archives across a time period:

```bash
python main.py download-range <STATION_ID> <START_TIME> [-e END_TIME]
```

**Parameters:**
- `STATION_ID`: Station identifier
- `START_TIME`: Start date and time (format: `Dec-10-2025-0000Z`)
- `-e, --end`: End date and time (format: `Dec-11-2025-1500Z`), defaults to now

**Examples:**

```bash
# Download from Dec 10 midnight to Dec 11 3PM (all times in Zulu/UTC)
python main.py download-range kcho3_zdc_121675 Dec-10-2025-0000Z -e Dec-11-2025-1500Z

# Download from specific start time to now
python main.py download-range kcho3_app Dec-11-2025-0000Z
```

**Progress Output:**
```
Downloading archives from 2025-12-10 00:00:00 to 2025-12-11 15:00:00
Station: kcho3_zdc_121675

[OK] Downloaded Dec-10-2025 0000Z
[OK] Downloaded Dec-10-2025 0030Z
[FAIL] Failed to download Dec-10-2025 0100Z: HTTP Error 404

=== Summary ===
Successfully downloaded: 47 files
Failed: 2 files
```

Files are saved to `/tmp/` directory by default.

## How It Works

### 1. **Station Discovery**

The tool scrapes LiveATC.net's search page to find available stations:

```python
# Queries: https://www.liveatc.net/search/?icao=KPDX
# Parses HTML tables to extract:
# - Station identifiers (e.g., kpdx_app)
# - Frequency information
# - Online status
```

### 2. **Archive URL Construction**

For each download, the tool:
1. Fetches the station's archive page
2. Extracts the archive identifier (handles station naming variations)
3. Constructs the download URL:
   ```
   https://archive.liveatc.net/{airport_code}/{ARCHIVE_ID}-{date}-{time}.mp3
   ```

### 3. **Download Process**

- **SSL Handling**: Automatically tries SSL verification with certifi, falls back to unverified if needed
- **Retry Logic**: Retries failed downloads up to 3 times with exponential backoff
- **Error Handling**: Catches and reports connection timeouts, 404s, and other errors

### 4. **Time Intervals**

LiveATC archives are stored in **30-minute intervals** aligned to Zulu time:
- 00:00Z - 00:30Z
- 00:30Z - 01:00Z
- 01:00Z - 01:30Z
- etc.

The `download-range` command automatically segments the requested time period into these intervals.

## Audio Processing

The `audio_utils.py` module provides additional audio processing capabilities:

### Features

- **Amplitude Normalization**: Standardize audio levels to a target dBFS
- **Silence Detection**: Split audio on silence to extract individual transmissions
- **Noise Reduction**: Remove background noise using spectral gating
- **Export Chunks**: Save individual transmissions as separate files

### Example Usage

```python
from audio_utils import load_audio, chunk_audio

# Load an MP3 file
audio = load_audio('/tmp/KCHO3-ZDC-121675-Dec-11-2025-1200Z.mp3')

# Split into chunks based on silence
chunk_audio(audio, 
    min_silence_len=200,      # Minimum silence length (ms)
    keep_silence=500,         # Keep some silence padding (ms)
    silence_thresh=-48        # Silence threshold (dBFS)
)
```

## Troubleshooting

### SSL Certificate Errors

If you encounter SSL certificate verification errors:

```
SSL: CERTIFICATE_VERIFY_FAILED
```

**Solution:** The code automatically handles this by falling back to unverified HTTPS. If issues persist:

```bash
pip install --upgrade certifi
```

### Connection Timeouts

If downloads consistently time out:

1. **Check your internet connection**
2. **Verify the station is online**: Use `stations` command and check for `'up': True`
3. **Try recent dates**: LiveATC only keeps archives for ~30 days
4. **Archive server may be busy**: Try again later

### No Archives Found (404 Errors)

Possible causes:
- **Archive too old**: LiveATC typically keeps 30 days
- **Station was offline**: No recording was made for that time period
- **Wrong time format**: Ensure times are in Zulu (UTC) and properly formatted

### Unicode Display Issues (Windows)

If you see encoding errors in PowerShell, the output uses ASCII-safe markers (`[OK]`, `[FAIL]`) instead of Unicode symbols.

## File Structure

```
liveatc-downloader/
├── main.py              # Main entry point and CLI handlers
├── gui.py               # GUI application (tkinter)
├── cli.py               # Command-line argument parsing
├── liveatc.py           # Core download and scraping logic
├── audio_utils.py       # Audio processing utilities
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Requirements

See `requirements.txt` for the complete list:

```
numpy
pydub
requests
beautifulsoup4
noisereduce
certifi
```

## Contributing

Contributions are welcome! This is a fork of [andrewda/liveatc-downloader](https://github.com/andrewda/liveatc-downloader) with additional features.

### To Contribute:

1. Fork this repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "Add my feature"`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

## Known Limitations

- LiveATC archives are only available for ~30 days
- Some stations may be offline or not recording
- Archive server can be slow or rate-limit requests
- Audio processing features are experimental

## License

This project builds upon the original work by andrewda. Please respect LiveATC's terms of service when using this tool.

## Changelog

### Recent Improvements (Dec 2025)

- ✅ Fixed SSL certificate verification issues
- ✅ Added `download-range` command for bulk downloads
- ✅ Improved error handling with retry logic
- ✅ Fixed archive URL path extraction
- ✅ Added progress reporting and summary statistics
- ✅ Better Windows PowerShell compatibility

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing issues for similar problems
- Provide error messages and system details when reporting bugs

---

**Note:** This tool is for personal use. Please respect LiveATC.net's bandwidth and terms of service. Consider [donating to LiveATC](https://www.liveatc.net/donate.php) to support their service.
