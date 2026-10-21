"""Trim/pad every rendered segment to its exact T1-T0 slot, concat, mux the narration.
Usage: python3 assemble.py <audio> <out.mp4> file1:SceneA file1:SceneB ...
Resumable: finished segments leave a .ok marker, so rerun after a timeout.
Run detached (setsid nohup ... &) if there are many segments."""
import subprocess, glob, importlib, sys, os
sys.path.insert(0, ".")
audio, out_path, specs = sys.argv[1], sys.argv[2], sys.argv[3:]
lines = []
for spec in specs:
    mod, s = spec.split(":")
    cls = getattr(importlib.import_module(mod), s)
    dur = cls.T1 - cls.T0
    # prefer 1080p30; a stale 1080p60 render of the same scene may also exist
    cands = sorted(glob.glob(f"media/videos/{mod}/1080p30/HQ_{s}.mp4")) or \
            sorted(glob.glob(f"media/videos/{mod}/1080p*/HQ_{s}.mp4"))
    src = cands[0]
    seg = f"seg_{s}.mp4"
    lines.append(f"file '{seg}'\n")
    if os.path.exists(seg + ".ok"):
        continue
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src,
                    "-vf", "fps=30,tpad=stop_mode=clone:stop_duration=2", "-t", f"{dur:.3f}",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", seg],
                   check=True)
    open(seg + ".ok", "w").close()
    print(s, "ok", flush=True)
open("list.txt", "w").writelines(lines)
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt",
                "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", "-movflags", "+faststart", out_path], check=True)
print("wrote", out_path)
