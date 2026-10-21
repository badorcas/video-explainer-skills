"""Voice a narration script with VibeVoice-1.5B (MIT, runs locally on CPU or Apple MPS), one paragraph per call, then
lay the paragraphs, breaths and think-time pauses out on one timeline.

Usage: python voice.py <script.txt> [<outdir>]              (outdir defaults to the current directory)
       python voice.py <script.txt> [<outdir>] --redo ID ...   re-voice paragraphs with the next seed
       VOICE=Carter python voice.py ...                       speaker preset (default Frank)
       python voice.py ... --device cpu                       torch device (default mps when available, else cpu)
       VV_SAY="quinoa=>KEEN-wah" python voice.py ...          respell for the voice only
Runs in its own venv, not the Nix shell (see SKILL.md, "Self-voiced narration"):
       PYTHONPATH=$VIBEVOICE_DIR $VIBEVOICE_VENV/bin/python voice.py ...
VIBEVOICE_DIR is the VibeVoice code checkout (default /opt/vibevoice; speaker presets are read from
its demo/voices), VIBEVOICE_MODEL the weights (default microsoft/VibeVoice-1.5B from Hugging Face).

Script format: "## S01 Title" starts a scene, a blank line starts a new paragraph (a longer breath),
"[PAUSE 8]" is 8 s of think time (a soft pad, no voice), and lines starting "# " are comments.
Spell numbers and symbols the way they should be spoken ("three point five", "L-E-D").

Writes <outdir>/voice/<VOICE>/<id>.wav (cache: a paragraph is only re-voiced when its text changes or
it is named in --redo), narration.wav, narration.mp3 (-16 LUFS) and timeline.json (every scene,
paragraph and pause with its start and end in seconds). Then run align.py for word timings.

VibeVoice is trained on long-form speech, so a whole paragraph per call keeps the natural rise and
fall across sentences. About 6x slower than real time on 4 CPU cores and about 11 GB of RAM: run one
instance at a time, detached (setsid nohup ... &), and poll its log."""
import json, os, re, subprocess, sys
import numpy as np
import soundfile as sf

SR = 24000
GAP = {"para": 0.75, "scene": 1.30, "pre_pause": 0.45, "post_pause": 0.35}   # silences, seconds
VOICE = os.environ.get("VOICE", "Frank")
VV = os.environ.get("VIBEVOICE_DIR", "/opt/vibevoice")
MODEL = os.environ.get("VIBEVOICE_MODEL", "microsoft/VibeVoice-1.5B")
CFG = 1.3
DEVICE = None   # set from --device in __main__; None picks mps when available, else cpu


def parse(path):
    """-> [{id, title, items: [{kind: "para", id, text} | {kind: "pause", sec}]}]; ids are S01_001, ..."""
    scenes, cur, buf = [], None, []

    def flush():
        if buf and cur is not None:
            cur["items"].append({"kind": "para", "text": " ".join(buf)})
        buf.clear()

    for raw in open(path):
        line = raw.strip()
        if line.startswith("# ") or line == "#":
            continue
        if line.startswith("## "):
            flush()
            sid, title = (line[3:] + " ").split(" ", 1)
            cur = {"id": sid, "title": title.strip(), "items": []}
            scenes.append(cur)
            continue
        m = re.fullmatch(r"\[PAUSE (\d+(?:\.\d+)?)\]", line)
        if not line or m:
            flush()
            if m and cur is not None:
                cur["items"].append({"kind": "pause", "sec": float(m.group(1))})
            continue
        buf.append(line)
    flush()
    n = 0
    for sc in scenes:
        for it in sc["items"]:
            if it["kind"] == "para":
                n += 1
                it["id"] = f"{sc['id']}_{n:03d}"
    return scenes


def pad(sec):
    """Quiet major-triad pad with a slow swell, so think time is not dead air."""
    t = np.arange(int(sec * SR)) / SR
    f = [220.0, 277.18, 329.63]
    x = sum(np.sin(2 * np.pi * fi * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.25 * t + i)) for i, fi in enumerate(f))
    env = np.minimum(1, np.minimum(t / 0.8, (sec - t) / 0.8))
    return (0.018 * x * env).astype(np.float32)


def trim(a, thr_db=-45, keep=0.05):
    """Cut leading and trailing silence, keep a short tail, fade the cut edges."""
    fr = int(0.01 * SR)
    e = np.array([np.sqrt(np.mean(a[i:i + fr] ** 2) + 1e-12) for i in range(0, len(a), fr)])
    on = np.where(20 * np.log10(e) > thr_db + 20 * np.log10(e.max()))[0]
    if not len(on):
        return a
    i0 = max(0, on[0] * fr - int(keep * SR))
    i1 = min(len(a), (on[-1] + 1) * fr + int(keep * SR))
    b = a[i0:i1].copy()
    b[:fr] *= np.linspace(0, 1, fr)
    b[-fr:] *= np.linspace(1, 0, fr)
    return b


_m = {}


def model():
    if not _m:
        import torch
        torch.set_num_threads(int(os.environ.get("VV_THREADS", "4")))
        sys.path.insert(0, VV)
        from vibevoice.modular.modeling_vibevoice_inference import VibeVoiceForConditionalGenerationInference
        from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor
        dev = DEVICE or ("mps" if torch.backends.mps.is_available() else "cpu")
        print(f"device {dev}", flush=True)
        _m["proc"] = VibeVoiceProcessor.from_pretrained(MODEL)
        m = VibeVoiceForConditionalGenerationInference.from_pretrained(
            MODEL, torch_dtype=torch.float32, device_map=dev, attn_implementation="sdpa")
        m.eval()
        m.set_ddpm_inference_steps(num_steps=10)
        _m["model"], _m["torch"], _m["dev"] = m, torch, dev
        vdir = os.path.join(VV, "demo", "voices")
        refs = sorted(f for f in os.listdir(vdir) if f.startswith(f"en-{VOICE}_"))
        if not refs:
            raise SystemExit(f"no speaker preset en-{VOICE}_*.wav in {vdir}")
        _m["ref"] = os.path.join(vdir, refs[0])
    return _m


def say(text):
    """Respell phrases for the voice only (VV_SAY="quinoa=>KEEN-wah;..."): the script,
    the cache key and timeline.json keep the written text."""
    for pair in filter(None, os.environ.get("VV_SAY", "").split(";")):
        a, b = pair.split("=>")
        text = re.sub(re.escape(a.strip()), b.strip(), text, flags=re.I)
    return text


def speak(text, seed):
    text = say(text)
    m = model()
    m["torch"].manual_seed(seed)
    inp = m["proc"](text=["Speaker 1: " + text.replace("\u2019", "'")], voice_samples=[[m["ref"]]],
                    padding=True, return_tensors="pt", return_attention_mask=True)
    inp = {k: v.to(m["dev"]) if hasattr(v, "to") else v for k, v in inp.items()}
    out = m["model"].generate(**inp, max_new_tokens=None, cfg_scale=CFG, tokenizer=m["proc"].tokenizer,
                              generation_config={"do_sample": False}, verbose=False, is_prefill=True)
    return out.speech_outputs[0].float().cpu().numpy().reshape(-1)


def voice(script, out_dir, redo=()):
    vdir = os.path.join(out_dir, "voice", VOICE)
    os.makedirs(vdir, exist_ok=True)
    seeds_p = os.path.join(vdir, "seeds.json")
    seeds = json.load(open(seeds_p)) if os.path.exists(seeds_p) else {}
    scenes = parse(script)
    paras = [it for sc in scenes for it in sc["items"] if it["kind"] == "para"]
    unknown = set(redo) - {it["id"] for it in paras}
    if unknown:
        raise SystemExit(f"--redo: no paragraph {sorted(unknown)} in {script}")
    todo = [it for it in paras if it["id"] in redo or not os.path.exists(os.path.join(vdir, it["id"] + ".wav"))
            or seeds.get(it["id"], {}).get("text") != it["text"]]
    for k, it in enumerate(todo):
        seed = seeds.get(it["id"], {}).get("seed", 1000) + (1 if it["id"] in redo else 0)
        a = trim(speak(it["text"], seed))
        sf.write(os.path.join(vdir, it["id"] + ".wav"), a, SR)
        seeds[it["id"]] = {"seed": seed, "text": it["text"]}
        json.dump(seeds, open(seeds_p, "w"), indent=1)
        print(f"[{k + 1}/{len(todo)}] {it['id']} {len(a) / SR:.1f}s {it['text'][:50]}", flush=True)

    out, tl = [], {"voice": VOICE, "scenes": [], "paragraphs": [], "pauses": []}
    t = 0.0

    def put(a):
        nonlocal t
        out.append(a)
        t += len(a) / SR

    def gap(sec):
        put(np.zeros(int(sec * SR), np.float32))

    for si, sc in enumerate(scenes):
        if si:
            gap(GAP["scene"])
        s0, prev = t, None
        for it in sc["items"]:
            if it["kind"] == "pause":
                gap(GAP["pre_pause"])
                p0 = t
                put(pad(it["sec"]))
                tl["pauses"].append({"scene": sc["id"], "start": round(p0, 3), "end": round(t, 3), "sec": it["sec"]})
                gap(GAP["post_pause"])
                prev = "pause"
                continue
            if prev == "para":
                gap(GAP["para"])
            a, sr = sf.read(os.path.join(vdir, it["id"] + ".wav"), dtype="float32")
            assert sr == SR
            a0 = t
            put(a)
            tl["paragraphs"].append({"id": it["id"], "scene": sc["id"], "start": round(a0, 3), "end": round(t, 3),
                                     "text": it["text"]})
            prev = "para"
        tl["scenes"].append({"id": sc["id"], "title": sc["title"], "start": round(s0, 3), "end": round(t, 3)})
    gap(1.5)
    tl["total"] = round(t, 3)
    wav = os.path.join(out_dir, "narration.wav")
    sf.write(wav, np.concatenate(out), SR)
    subprocess.run([os.environ.get("FFMPEG", "ffmpeg"), "-loglevel", "error", "-y", "-i", wav,
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-ac", "1", "-b:a", "160k",
                    os.path.join(out_dir, "narration.mp3")], check=True)
    json.dump(tl, open(os.path.join(out_dir, "timeline.json"), "w"), indent=1)
    print(f"total {t:.1f} s, {len(tl['paragraphs'])} paragraphs, {len(tl['pauses'])} pauses", flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--device" in args:
        i = args.index("--device")
        DEVICE = args[i + 1]
        del args[i:i + 2]
    redo = args[args.index("--redo") + 1:] if "--redo" in args else []
    pos = args[:args.index("--redo")] if redo else args
    voice(pos[0], os.path.abspath(pos[1] if len(pos) > 1 else "."), set(redo))
    print("DONE", flush=True)
