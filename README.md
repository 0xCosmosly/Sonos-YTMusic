# Sonos YTMusic 🎵

Bring on-demand YouTube Music playback to your Sonos speakers. Sonos's built-in YouTube Music integration doesn't let you just ask for a specific song and hear it right away — this tool fills that gap with a single terminal command.

## Features that make it great

- **True On-Demand Playback**: Name a song, and it starts playing on your Sonos.
- **High Quality**: Automatically picks the highest-quality `m4a` audio stream available.
- **Local Control**: Talks to your speaker directly over your home network using Sonos's standard UPnP/SOAP interface — no cloud account linking or developer API keys.
- **Full Playback Control**: Play, pause, skip, and change the volume right from the command line.
- **Agent-Friendly**: Plain-English commands make it easy to drive from scripts or AI agents.

## Getting Started

### Requirements
- Python 3
- `yt-dlp` (`brew install yt-dlp` or `pip install yt-dlp`)
- `curl`
- A Sonos speaker on your local Wi-Fi network

### Installation
```bash
git clone https://github.com/0xCosmosly/sonos-ytmusic.git
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

When you request a song, the script uses `yt-dlp` to find the track and resolve its audio stream. It then starts a short-lived local HTTP server to serve that stream and sends a SOAP command to your Sonos speaker on your local network, telling it to play from that server.

Everything runs on your own machine and network.

---
*Ask for a song, hear it on your Sonos.*

<!-- contributor stats refresh -->
