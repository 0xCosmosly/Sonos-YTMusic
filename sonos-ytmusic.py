#!/usr/bin/env python3
"""
Sonos YouTube Music Controller — Lean Edition
Searches YouTube via yt-dlp, downloads audio, streams to Sonos via SOAP.
"""

import sys
import subprocess
import json
import re
import os
import signal
import socket
import tempfile
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

DEFAULT_SPEAKER = os.environ.get("SONOS_SPEAKER", "Sonos Living Room")
SONOS_IP = os.environ.get("SONOS_IP", "")
SERVE_PORT = int(os.environ.get("SONOS_SERVE_PORT", "8765"))
CACHE_DIR = Path(tempfile.gettempdir()) / "sonos-ytmusic"


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_sonos_ip():
    """Get Sonos IP from env or discover via multicast."""
    if SONOS_IP:
        return SONOS_IP
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-t", "2", "239.255.255.250"],
            capture_output=True, text=True, timeout=5,
        )
        local_ip = get_local_ip()
        for line in result.stdout.split("\n"):
            m = re.search(r'from\s+([\d.]+)', line)
            if m and m.group(1) != local_ip:
                return m.group(1)
    except Exception:
        pass
    return None


# ── SOAP commands (direct curl, bypasses broken Go CLI) ──

def soap_request(ip, action, body):
    """Send a SOAP request to Sonos AVTransport."""
    try:
        r = subprocess.run([
            "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
            "-X", "POST",
            f"http://{ip}:1400/MediaRenderer/AVTransport/Control",
            "-H", "Content-Type: text/xml; charset=\"utf-8\"",
            "-H", f'SOAPAction: "urn:schemas-upnp-org:service:AVTransport:1#{action}"',
            "-d", body
        ], capture_output=True, text=True, timeout=10)
        code = r.stdout.strip()
        return code == "200", f"HTTP {code}"
    except Exception as e:
        return False, str(e)


def sonos_play_uri(ip, uri):
    escaped = uri.replace("&", "&amp;")
    body = f'''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
  s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:SetAVTransportURI xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
      <CurrentURI>{escaped}</CurrentURI>
      <CurrentURIMetaData></CurrentURIMetaData>
    </u:SetAVTransportURI>
  </s:Body>
</s:Envelope>'''
    ok, err = soap_request(ip, "SetAVTransportURI", body)
    if not ok:
        return False, f"SetAVTransportURI: {err}"

    play_body = '''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
  s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:Play xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
      <Speed>1</Speed>
    </u:Play>
  </s:Body>
</s:Envelope>'''
    ok, err = soap_request(ip, "Play", play_body)
    if not ok:
        return False, f"Play: {err}"
    return True, None


def sonos_stop(ip):
    body = '''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
  s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:Stop xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
    </u:Stop>
  </s:Body>
</s:Envelope>'''
    return soap_request(ip, "Stop", body)


def sonos_volume(ip, level):
    body = f'''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
  s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:SetVolume xmlns:u="urn:schemas-upnp-org:service:RenderingControl:1">
      <InstanceID>0</InstanceID>
      <Channel>Master</Channel>
      <DesiredVolume>{level}</DesiredVolume>
    </u:SetVolume>
  </s:Body>
</s:Envelope>'''
    try:
        r = subprocess.run([
            "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
            "-X", "POST",
            f"http://{ip}:1400/MediaRenderer/RenderingControl/Control",
            "-H", "Content-Type: text/xml; charset=\"utf-8\"",
            "-H", 'SOAPAction: "urn:schemas-upnp-org:service:RenderingControl:1#SetVolume"',
            "-d", body
        ], capture_output=True, text=True, timeout=10)
        code = r.stdout.strip()
        return code == "200", f"HTTP {code}"
    except Exception as e:
        return False, str(e)


def sonos_next(ip):
    body = '''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
  s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:Next xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
    </u:Next>
  </s:Body>
</s:Envelope>'''
    return soap_request(ip, "Next", body)


# ── Search & Download ──

def search_youtube(query):
    """Search YouTube directly via yt-dlp — single search, no YT Music detour."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--print", "%(title)s\t%(id)s\t%(uploader)s",
             f"ytsearch3:{query}", "--no-download", "--quiet"],
            capture_output=True, text=True, timeout=20,
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split("\n")
            parts = lines[0].split("\t")
            if len(parts) >= 2:
                return {
                    "title": parts[0],
                    "artist": parts[2] if len(parts) > 2 else "Unknown",
                    "video_id": parts[1],
                }, None
    except Exception as e:
        return None, str(e)
    return None, "No results found"


def download_audio(video_id, output_path):
    """Download audio — try native m4a first, transcode as fallback."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    result = subprocess.run(
        [
            "yt-dlp",
            "-f", "bestaudio[ext=m4a]/bestaudio",
            "--extract-audio",
            "--audio-format", "m4a",
            "--audio-quality", "0",  # highest quality
            "-o", str(output_path),
            "--no-playlist",
            "--quiet",
            url,
        ],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        return f"Download failed: {result.stderr.strip()}"
    return None


def clean_cache():
    """Delete all previous audio files."""
    if CACHE_DIR.exists():
        for f in CACHE_DIR.iterdir():
            try:
                f.unlink()
            except Exception:
                pass


def kill_existing_server():
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{SERVE_PORT}"],
            capture_output=True, text=True,
        )
        for pid in result.stdout.strip().split("\n"):
            if pid:
                try:
                    os.kill(int(pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
        import time
        time.sleep(0.3)
    except Exception:
        pass


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)
    def log_message(self, format, *args):
        pass


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True
    allow_reuse_port = True


def serve_file(file_path):
    kill_existing_server()
    local_ip = get_local_ip()
    directory = str(file_path.parent)
    filename = file_path.name
    handler = lambda *args, **kwargs: QuietHandler(*args, directory=directory, **kwargs)
    server = ReusableHTTPServer(("0.0.0.0", SERVE_PORT), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"http://{local_ip}:{SERVE_PORT}/{filename}"


def parse_request(text):
    m = re.match(r'play\s+(.+?)\s+by\s+(.+?)\s+on\s+(.+)$', text, re.IGNORECASE)
    if m:
        return {"song": m.group(1), "artist": m.group(2), "speaker": m.group(3)}
    m = re.match(r'play\s+(.+?)\s+by\s+(.+)$', text, re.IGNORECASE)
    if m:
        return {"song": m.group(1), "artist": m.group(2), "speaker": None}
    m = re.match(r'play\s+(.+?)\s+on\s+(.+)$', text, re.IGNORECASE)
    if m:
        return {"song": m.group(1), "artist": None, "speaker": m.group(2)}
    m = re.match(r'play\s+(.+)$', text, re.IGNORECASE)
    if m:
        return {"song": m.group(1), "artist": None, "speaker": None}
    return None


def require_ip():
    ip = get_sonos_ip()
    if not ip:
        print("Could not find Sonos speaker. Set SONOS_IP env var.")
        sys.exit(1)
    return ip


def main():
    if len(sys.argv) < 2:
        print("Usage: sonos-ytmusic.py 'play Dreams by Beck'")
        sys.exit(1)

    request = " ".join(sys.argv[1:])
    request_lower = request.lower().strip()

    # ── Control commands ──
    if request_lower in ("pause", "stop"):
        ip = require_ip()
        ok, err = sonos_stop(ip)
        print("Paused" if ok else f"Error: {err}")
        return

    if request_lower in ("next", "skip"):
        ip = require_ip()
        ok, err = sonos_next(ip)
        print("Next track" if ok else f"Error: {err}")
        return

    vol_match = re.match(r'volume\s+(\d+)', request_lower)
    if vol_match:
        ip = require_ip()
        level = vol_match.group(1)
        ok, err = sonos_volume(ip, level)
        print(f"Volume set to {level}" if ok else f"Error: {err}")
        return

    # ── Play request ──
    parsed = parse_request(request)
    if not parsed:
        print(f"Could not parse: {request}")
        print("Try: 'play Dreams by Beck'")
        sys.exit(1)

    ip = require_ip()

    song = parsed["song"]
    artist = parsed["artist"]
    query = f"{song} {artist}" if artist else song
    label = f"{song} by {artist}" if artist else song

    print(f"Searching: {label}...")
    track, err = search_youtube(query)
    if err:
        print(f"Search failed: {err}")
        sys.exit(1)
    print(f"Found: {track['title']} by {track['artist']}")

    # Clean old files, download new
    clean_cache()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    audio_file = CACHE_DIR / "now-playing.m4a"

    print("Downloading...")
    err = download_audio(track["video_id"], audio_file)
    if err:
        print(err)
        sys.exit(1)

    # yt-dlp may append .m4a again
    actual = audio_file
    if not actual.exists():
        candidates = list(CACHE_DIR.glob("now-playing*"))
        actual = candidates[0] if candidates else None
        if not actual:
            print("Download succeeded but file not found")
            sys.exit(1)

    # Serve & play
    print("Serving audio...")
    url = serve_file(actual)
    print(f"Playing on Sonos...")
    ok, err = sonos_play_uri(ip, url)
    if not ok:
        print(f"Playback failed: {err}")
        sys.exit(1)

    print(f"Now playing: {track['title']} by {track['artist']}")

    # Keep server alive
    try:
        import time
        while True:
            time.sleep(30)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
