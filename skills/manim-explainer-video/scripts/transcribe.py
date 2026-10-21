"""Timestamped transcript of an audio file.
Usage: python3 transcribe.py <audio> <outdir>
Writes <outdir>/transcript.txt ("[start-end] text") and transcript.json.
Decodes to raw PCM with ffmpeg first: faster-whisper's own decoder breaks
on the container's PyAV version. ~4 min for 13 min of audio on 1 CPU.
WHISPER_MODEL (set by the Nix flake) points at pinned local weights;
otherwise "base.en" is downloaded. Run with setsid nohup in the background; tool calls time out at 300 s."""
import json, subprocess, sys, os
import numpy as np
from faster_whisper import WhisperModel
audio, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
raw = os.path.join(out, "a.raw")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", audio, "-ac", "1", "-ar", "16000",
                "-f", "f32le", raw], check=True)
a = np.fromfile(raw, dtype=np.float32)
m = WhisperModel(os.environ.get("WHISPER_MODEL", "base.en"), device="cpu", compute_type="int8", cpu_threads=1)
segs, _ = m.transcribe(a, vad_filter=True, beam_size=1)
rows = []
with open(os.path.join(out, "transcript.txt"), "w") as f:
    for s in segs:
        rows.append({"s": round(s.start, 1), "e": round(s.end, 1), "t": s.text.strip()})
        f.write(f"[{s.start:7.1f}-{s.end:7.1f}] {s.text.strip()}\n"); f.flush()
json.dump(rows, open(os.path.join(out, "transcript.json"), "w"), indent=0)
print("done")
