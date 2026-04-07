# Sonos YTMusic 🎵

Play literally any song from YouTube directly on your Sonos speakers using a single terminal command. No YouTube Music subscription, broken Go CLIs, or complex API keys required.

## Features that make it great

- **Universal Library**: If it's on YouTube, you can play it on your Sonos.
- **High Quality**: Automatically grabs the highest quality `m4a` audio stream available.
- **Direct SOAP Commands**: Bypasses the notoriously buggy Sonos developer APIs and talks directly to your speaker over your local network.
- **Full Playback Control**: Play, pause, skip, and change the volume right from the command line.

## Getting Started

### Requirements
- Python 3
- `yt-dlp` (`brew install yt-dlp` or `pip install yt-dlp`)
- `curl`
- A Sonos speaker on your local Wi-Fi network

### Installation
```bash
git clone https://github.com/0xCosmosly/Sonos-YTMusic.git
cd Sonos-YTMusic
```

### Usage
It's as simple as typing what you want to hear:
```bash
# Play a track
python3 sonos-ytmusic.py "play Dreams by Beck"

# Control the speaker
python3 sonos-ytmusic.py "pause"
python3 sonos-ytmusic.py "next"
python3 sonos-ytmusic.py "volume 50"
```

*Optional: Set your default speaker name in your shell profile so you don't have to specify it:*
`export SONOS_SPEAKER="Living Room"`

## Under the Hood

When you ask for a song, the script uses `yt-dlp` to search YouTube and extract the direct audio URL. It then spins up an ephemeral local HTTP server to host the stream, and fires a raw XML SOAP payload via `curl` straight to your Sonos speaker's IP address, telling it to play your local stream. 

It's fast, reliable, and completely local.

---
*Because playing music shouldn't require three subscriptions and a broken API.*
