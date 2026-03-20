#!/usr/bin/env python3
"""
Smoke-test Deepgram REST API (same key as live STT).

Usage (from project root):
  .venv/bin/python scripts/test_deepgram.py
  .venv/bin/python scripts/test_deepgram.py --url 'https://example.com/audio.wav'

Loads DEEPGRAM_API_KEY from .env in the project root (python-dotenv).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Project root = parent of scripts/
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

DEFAULT_SAMPLE_URL = (
    "https://static.deepgram.com/examples/Bueller-Life-moves-pretty-fast.wav"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Deepgram transcribe_url")
    parser.add_argument(
        "--url",
        default=DEFAULT_SAMPLE_URL,
        help="Publicly reachable audio URL (wav/mp3/etc.)",
    )
    parser.add_argument(
        "--model",
        default="nova-2",
        help="Deepgram model (default: nova-2, matches voice stack)",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("DEEPGRAM_API_KEY", "").strip()
    if not api_key:
        print("ERROR: DEEPGRAM_API_KEY is missing or empty in .env")
        return 1

    try:
        from deepgram import DeepgramClient
    except ImportError:
        print("ERROR: deepgram-sdk not installed. Use: pip install deepgram-sdk")
        return 1

    print("Calling Deepgram transcribe_url …")
    print(f"  url:   {args.url}")
    print(f"  model: {args.model}")

    client = DeepgramClient(api_key=api_key)
    resp = client.listen.v1.media.transcribe_url(
        url=args.url,
        model=args.model,
        smart_format=True,
        punctuate=True,
    )

    # ListenV1AcceptedResponse is async job — unlikely for URL prerecorded path
    if not hasattr(resp, "results") or resp.results is None:
        print("Unexpected response (no results):", resp)
        return 2

    channels = getattr(resp.results, "channels", None) or []
    if not channels:
        print("OK (HTTP) but empty channels — check URL / format.")
        return 0

    alts = getattr(channels[0], "alternatives", None) or []
    transcript = (alts[0].transcript or "").strip() if alts else ""
    duration = getattr(resp.metadata, "duration", None) if resp.metadata else None

    print()
    print("SUCCESS — Deepgram API key is valid and transcription works.")
    if duration is not None:
        print(f"  duration: {duration}s")
    print(f"  transcript: {transcript!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
