"""Splice short insert clips (a predict question, a recall check, an end quiz) into a finished video,
frame-exact, without re-rendering the original.

    python3 splice.py shipped.mp4 out.mp4 CUT=insert.mp4 [CUT=a.mp4+b.mp4 ...] [--fps 30] [--sr 48000]

Each CUT is a time in seconds in the original; the clip(s) after "=" play there, and the original
resumes where it stopped.  Several clips joined with "+" play back to back at one cut.  Cut on scene
boundaries, in silence (voice.py leaves a gap between scenes and a tail at the end).

Every time is snapped to the frame grid (at 30 fps and 48 kHz, one frame is 1600 audio samples):
- the original is cut at round(cut*fps) frames and at the matching sample, so the narration after each
  splice stays in sync with its pictures;
- each insert keeps its own frame count, and its audio track is padded with silence or trimmed to
  exactly that many frames (a clip with no audio gets silence);
- a 5 ms fade at each join stops any click.
Output: H.264 High yuv420p, AAC LC mono, plus out.mp4.plan.json with the frame counts and how far each
cut moves the rest of the video (use that to move chapter marks or captions)."""
import argparse, json, os, subprocess, sys


def probe(p, sel):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", sel, "-count_packets", "-show_entries",
                        "stream=nb_read_packets,duration,width,height", "-of", "json", p],
                       capture_output=True, text=True, check=True)
    s = json.loads(r.stdout).get("streams", [])
    return s[0] if s else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("inserts", nargs="+", metavar="CUT=clip.mp4[+clip2.mp4]")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--sr", type=int, default=48000)
    a = ap.parse_args()
    FPS, SR = a.fps, a.sr
    if SR % FPS:
        sys.exit("--sr must be a multiple of --fps")
    SPF = SR // FPS
    fr = lambda t: int(round(t * FPS))

    ins = []
    for spec in a.inserts:
        cut, _, clips = spec.partition("=")
        if not clips:
            sys.exit(f"bad insert {spec!r}: use CUT=clip.mp4")
        ins.append((float(cut), clips.split("+")))
    ins.sort()
    v0 = probe(a.src, "v:0")
    W, H = v0["width"], v0["height"]
    orig_frames = int(v0["nb_read_packets"])

    args = ["ffmpeg", "-loglevel", "error", "-y", "-i", a.src]
    fc, parts, plan = [], [], []
    FADE = "afade=t=in:d=0.005,afade=t=out:st={st}:d=0.005"
    AF = f"aresample={SR},aformat=sample_rates={SR}:channel_layouts=mono"
    n_in, prev = 1, 0
    for k, (cut, clips) in enumerate(ins):
        c = fr(cut)
        if c < prev:
            sys.exit("cuts overlap")
        n = c - prev
        fc.append(f"[0:v]trim=start_frame={prev}:end_frame={c},setpts=PTS-STARTPTS,setsar=1[ov{k}]")
        fc.append(f"[0:a]{AF},atrim=start_sample={prev * SPF}:end_sample={c * SPF},asetpts=PTS-STARTPTS,"
                  + FADE.format(st=n / FPS - 0.005) + f"[oa{k}]")
        parts.append(f"[ov{k}][oa{k}]")
        frames_k = 0
        for j, clip in enumerate(clips):
            cv = probe(clip, "v:0")
            nb = fr(float(cv["duration"]))
            frames_k += nb
            args += ["-i", clip]
            lab = f"{k}_{j}"
            fc.append(f"[{n_in}:v]fps={FPS},scale={W}:{H},format=yuv420p,setsar=1,"
                      f"tpad=stop_mode=clone:stop_duration=2,trim=end_frame={nb},setpts=PTS-STARTPTS[iv{lab}]")
            if probe(clip, "a:0"):
                fc.append(f"[{n_in}:a]{AF},apad,atrim=end_sample={nb * SPF},asetpts=PTS-STARTPTS,"
                          + FADE.format(st=nb / FPS - 0.005) + f"[ia{lab}]")
            else:
                fc.append(f"anullsrc=r={SR}:cl=mono,atrim=end_sample={nb * SPF}[ia{lab}]")
            parts.append(f"[iv{lab}][ia{lab}]")
            n_in += 1
        plan.append({"cut": cut, "cut_snapped": c / FPS, "clips": clips, "frames": frames_k, "sec": frames_k / FPS})
        prev = c
    k = len(ins)
    fc.append(f"[0:v]trim=start_frame={prev},setpts=PTS-STARTPTS,setsar=1[ov{k}]")
    fc.append(f"[0:a]{AF},atrim=start_sample={prev * SPF},asetpts=PTS-STARTPTS,afade=t=in:d=0.005[oa{k}]")
    parts.append(f"[ov{k}][oa{k}]")
    fc.append("".join(parts) + f"concat=n={len(parts)}:v=1:a=1[v][a]")
    tmp = a.out + ".part.mp4"
    subprocess.run(args + ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
                           "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "18",
                           "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "160k",
                           "-ar", str(SR), "-ac", "1", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, a.out)
    added = sum(p["frames"] for p in plan)
    shift = 0.0
    for p in plan:
        shift += p["sec"]
        p["shift_after"] = shift
    rep = json.dumps({"orig_frames": orig_frames, "insert_frames": added, "expect_frames": orig_frames + added,
                      "out_frames": int(probe(a.out, "v:0")["nb_read_packets"]), "plan": plan}, indent=1)
    open(a.out + ".plan.json", "w").write(rep)
    print(rep)


if __name__ == "__main__":
    main()
