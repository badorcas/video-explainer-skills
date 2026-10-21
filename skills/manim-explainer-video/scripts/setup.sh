#!/bin/bash
# One-time environment setup for manim + transcription in a Debian or Ubuntu container
# without Nix (run as root). With Nix, use `nix develop` instead.
set -e
apt-get update -q >/dev/null
apt-get install -y -q libpango1.0-dev pkg-config dvisvgm >/dev/null
pip install manim faster-whisper spacy --break-system-packages -q
python3 -m spacy download en_core_web_sm -q  # script_lint.py grammar checks (Nix shell has them pinned)
python3 -c "import manim, faster_whisper, spacy; spacy.load('en_core_web_sm'); print('manim', manim.__version__, 'ok')"
