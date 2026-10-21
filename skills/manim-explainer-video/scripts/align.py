"""Word-level transcript of a voice.py narration, and a check that the voice said what the script says.

Usage: python3 align.py <dir> [--prompt "Nyquist, klystron, ..." | --prompt-file terms.txt]
       python3 align.py <dir> --check-only        (redo voicecheck.txt from the existing words.json)
Run inside the Nix shell (faster-whisper). Reads <dir>/narration.wav and <dir>/timeline.json, writes
  <dir>/transcript.json   segments [{s, e, t}] in the format lint.py reads
  <dir>/words.json        every word [{w, s, e}], which timing.py maps script phrases onto
  <dir>/voicecheck.txt    per paragraph: how well what was heard matches the script.
The prompt is a comma-separated list of the jargon and names in the script; it biases the
transcriber toward spelling them right. ALIGN_MODEL picks the Whisper model (default small.en,
downloaded on first use; base.en word times are rougher). About 1/3 real time on 2 CPUs.

voicecheck.txt: LOW lines need a listen. Words heard that are not in the script ("+ ...") are
real defects (a repeated phrase, a stray syllable, a hallucinated word): re-voice the paragraph with
voice.py --redo <id>. Missing words ("- ...") are often only spelling ("on to" heard as "onto").
Numbers are left out of the comparison, since the script spells them out and the transcript uses digits."""
import difflib, json, os, re, subprocess, sys

NUMS = set("zero oh one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
           "sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred "
           "thousand million billion point and a half quarter".split())


def transcribe(d, prompt):
    import numpy as np
    from faster_whisper import WhisperModel
    raw = os.path.join(d, "a.raw")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(d, "narration.wav"), "-ac", "1",
                    "-ar", "16000", "-f", "f32le", raw], check=True)
    a = np.fromfile(raw, dtype=np.float32)
    os.remove(raw)
    m = WhisperModel(os.environ.get("ALIGN_MODEL", "small.en"), device="cpu", compute_type="int8", cpu_threads=2)
    segs, _ = m.transcribe(a, word_timestamps=True, beam_size=1, initial_prompt=prompt or None)
    rows, words = [], []
    for s in segs:
        rows.append({"s": round(s.start, 2), "e": round(s.end, 2), "t": s.text.strip()})
        words += [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)} for w in s.words]
    json.dump(rows, open(os.path.join(d, "transcript.json"), "w"), indent=0)
    json.dump(words, open(os.path.join(d, "words.json"), "w"), indent=0)
    return words


def toks(text):
    """Words to compare: lower case, no punctuation or hyphens, British -tre spelled -ter, numbers left out."""
    out = []
    for w in re.split("[\\s\u2013\u2014]+", text.lower()):       # hyphens join: L-E-D = LED
        w = re.sub(r"tre(s?)$", r"ter\1", re.sub(r"[^a-z0-9]", "", w))
        if w and w not in NUMS and not re.search(r"\d", w):
            out.append(w)
    return out


def voicecheck(d, words):
    tl = json.load(open(os.path.join(d, "timeline.json")))
    lines, n_low = [], 0
    for p in tl["paragraphs"]:
        heard = " ".join(w["w"] for w in words if p["start"] - 0.2 <= (w["s"] + w["e"]) / 2 <= p["end"] + 0.2)
        a, b = toks(p["text"]), toks(heard)
        sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
        extra = [" ".join(b[j1:j2]) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag in ("insert", "replace")]
        gone = [" ".join(a[i1:i2]) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag in ("delete", "replace")]
        r = sm.ratio() if a or b else 1.0
        low = r < 0.9 or any(tag == "insert" for tag, *_ in sm.get_opcodes())
        n_low += low
        lines.append(f"{'LOW ' if low else 'ok  '}{r:.2f} {p['id']}\n  script: {p['text']}\n  heard:  {heard}\n"
                     + (f"  + {' | '.join(extra)}\n" if extra else "") + (f"  - {' | '.join(gone)}\n" if gone else ""))
    open(os.path.join(d, "voicecheck.txt"), "w").write("".join(lines))
    return n_low, len(lines)


if __name__ == "__main__":
    args = sys.argv[1:]
    d = os.path.abspath(args[0])
    opt = lambda k: args[args.index(k) + 1] if k in args else None
    if "--check-only" in args:
        words = json.load(open(os.path.join(d, "words.json")))
    else:
        pf = opt("--prompt-file")
        prompt = opt("--prompt") or (" ".join(open(pf).read().split()) if pf else None)
        words = transcribe(d, prompt)
    n_low, n = voicecheck(d, words)
    print(f"{len(words)} words; {n_low} of {n} paragraphs LOW (see {os.path.join(d, 'voicecheck.txt')})")
