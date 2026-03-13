# Sonos YouTube Music Player

Play any song from YouTube on your Sonos speakers with a simple command.

## What It Does

- Searches YouTube for your song
- Downloads the highest quality audio
- Streams it directly to your Sonos speaker
- No YouTube Music subscription needed

## Requirements

- Python 3
- `yt-dlp` (install: `brew install yt-dlp` or `pip install yt-dlp`)
- `curl` (built-in on macOS/Linux)
- Sonos speaker on your local network

## Installation

```bash
git clone https://github.com/yourusername/sonos-ytmusic.git
cd sonos-ytmusic
```

## Usage

```bash
# Play a song
python3 sonos-ytmusic.py "play Dreams by Beck"

# Play with artist
python3 sonos-ytmusic.py "play Loser by Beck"

# Control playback
python3 sonos-ytmusic.py "pause"
python3 sonos-ytmusic.py "next"
python3 sonos-ytmusic.py "volume 50"
```

## Configuration (Optional)

Set environment variables in your shell:

```bash
# Default speaker name
export SONOS_SPEAKER="Sonos Living Room"

# Or hardcode the IP (faster, skips discovery)
export SONOS_IP="192.168.1.100"

# Port for local audio server
export SONOS_SERVE_PORT="8765"
```

## How It Works

1. **Search**: Uses `yt-dlp` to search YouTube directly
2. **Download**: Grabs highest quality audio (m4a format)
3. **Serve**: Starts a temporary local HTTP server
4. **Play**: Sends SOAP commands directly to your Sonos speaker

No Go CLI, no YouTube Music API keys, no complexity.

## Why This Exists

Other Sonos tools rely on a broken Go CLI that fails with "no route to host" errors. This tool bypasses that entirely using direct SOAP commands via curl.

## License

MIT. See `LICENSE`.
