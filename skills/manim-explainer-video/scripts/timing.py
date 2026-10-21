"""Beat times from the narration itself, for self-voiced videos (voice.py + align.py). Scenes never
hard-code seconds, so a re-voiced paragraph needs only a re-render:

    import timing as tm
    tm.scene("S04")                        -> (T0, T1): scene start, next scene's start (no gaps in the cut)
    tm.pause("S03", 1)                     -> (start, end) of the 2nd [PAUSE] in S03
    tm.pauses("S03")                       -> every [PAUSE] window in S03
    tm.at("S06", "the echo comes back")    -> start of "the" (first occurrence in S06)
    tm.end_of("S06", "comes back")         -> end of "back"
    tm.at("S06", "zero", nth=1)            -> occurrences are counted within the scene

    class S04(TL):
        T0, T1 = tm.scene("S04")
        def construct(self):
            self.till(tm.at("S04", "twice as far")); ...

Reads timeline.json (voice.py) and words.json (align.py) from $TIMING_DIR, else the current
directory, else this file's directory; tm.load(dir) picks another.

A phrase is found in the script text (the timeline's paragraphs), then mapped onto the spoken words
by sequence alignment, so transcription slips ("1990" for "nineteen ninety", "metres" for
"meters", "LED" for "L-E-D", a misheard word) do not break it. A phrase written in digits ("3.5")
that is not in the script is matched literally in the transcript. Words heard inside a [PAUSE] window are dropped:
the pause holds only the pad, so anything transcribed there is a hallucination.

    python3 timing.py [dir] [S03 "some phrase" ...]   lists scenes and pauses, then resolves phrases"""
import json, os, re, unicodedata, difflib

_D = {}


def load(d=None):
    """Read timeline.json and words.json from d (see the module docstring for the default)."""
    if d is None:
        here = os.path.dirname(os.path.abspath(__file__))
        cands = [os.environ.get("TIMING_DIR", ""), os.getcwd(), here]
        d = next((c for c in cands if c and os.path.exists(os.path.join(c, "timeline.json"))), None)
        if d is None:
            raise FileNotFoundError("timing: no timeline.json in $TIMING_DIR, the current directory or " + here)
    tl = json.load(open(os.path.join(d, "timeline.json")))
    words = json.load(open(os.path.join(d, "words.json")))
    windows = [(p["start"], p["end"]) for p in tl["pauses"]]
    heard = [w for w in words if not any(a <= (w["s"] + w["e"]) / 2 <= b for a, b in windows)]
    _D.update(tl=tl, spoken=_merge_spoken(heard))
    return _D


def _tl():
    return (_D or load())["tl"]


def _norm(w):
    w = unicodedata.normalize("NFKD", w).encode("ascii", "ignore").decode().lower()
    w = re.sub(r"[^a-z0-9.]", "", w)          # apostrophes and hyphens go: "L-E-D" matches "LED"
    return re.sub(r"tre(s?)$", r"ter\1", w.strip("."))     # "metres" (British transcript) = "meters"


DASHES = "[\\s\u2013\u2014]+"                 # spaces, en and em dashes separate words; hyphens join them


def _toks(text):
    return [t for t in (_norm(w) for w in re.split(DASHES, text)) if t]


def _merge_spoken(words):
    """Transcribed words -> [(tok, s, e, raw)]. The transcriber splits "1.1" into "1" ".1", "1,100"
    into "1" ",100" and "low-pass" into "low" "-pass": glue those back together."""
    out = []
    for x in words:
        tok, raw = _norm(x["w"]), x["w"].strip()
        if not tok:
            continue
        num = raw[:1] in ".," and out and re.fullmatch(r"[\d.]+", out[-1][0]) and tok.isdigit()
        if num or (out and re.match(r"-[a-zA-Z]", raw)):
            t0, s0, _, r0 = out[-1]
            out[-1] = (_norm(r0 + raw.replace(",", "")), s0, x["e"], r0 + raw)
        else:
            out.append((tok, x["s"], x["e"], raw))
    return out


def scene(sid):
    sc = _tl()["scenes"]
    i = [s["id"] for s in sc].index(sid)
    return sc[i]["start"], (sc[i + 1]["start"] if i + 1 < len(sc) else _tl()["total"])


def pauses(sid):
    return [(p["start"], p["end"]) for p in _tl()["pauses"] if p["scene"] == sid]


def pause(sid, k=0):
    return pauses(sid)[k]


def _spoken_in(t0, t1):
    return [w for w in _D["spoken"] if t0 - 0.3 <= w[1] <= t1 + 0.3]


def _align(ptoks, sp):
    """-> [(start, end)] for each script token, from the spoken words sp. Where the two differ
    ("three hundred and twelve" heard as "312") the script words share the spoken span in proportion."""
    sm = difflib.SequenceMatcher(a=ptoks, b=[w[0] for w in sp], autojunk=False)
    out = [None] * len(ptoks)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                out[i1 + k] = sp[j1 + k][1:3]
        elif tag == "replace":
            S, E, n = sp[j1][1], sp[j2 - 1][2], i2 - i1
            for k in range(n):
                out[i1 + k] = (S + (E - S) * k / n, S + (E - S) * (k + 1) / n)
        elif tag == "delete":                     # nothing heard for these words: pin to the next one
            t = sp[j1][1] if j1 < len(sp) else sp[-1][2]
            for k in range(i2 - i1):
                out[i1 + k] = (t, t)
    return out


def _hits(seq, toks):
    return [i for i in range(len(seq) - len(toks) + 1) if seq[i:i + len(toks)] == toks]


def _locate(sid, phrase, nth=0):
    """-> (start, end) in seconds of the phrase's nth occurrence in the scene."""
    toks = _toks(phrase)
    if not toks:
        raise ValueError("timing: empty phrase")
    count = 0
    for p in [p for p in _tl()["paragraphs"] if p["scene"] == sid]:
        pt = _toks(p["text"])
        for i in _hits(pt, toks):
            if count == nth:
                sp = _spoken_in(p["start"], p["end"])
                if not sp:                # nothing transcribed: interpolate by position in the paragraph
                    a = p["start"] + (p["end"] - p["start"]) * i / len(pt)
                    b = p["start"] + (p["end"] - p["start"]) * (i + len(toks)) / len(pt)
                    return a, b
                span = _align(pt, sp)
                return span[i][0], span[i + len(toks) - 1][1]
            count += 1
    sp = _spoken_in(*scene(sid))          # not in the script as written: literal match in the transcript
    h = _hits([w[0] for w in sp], toks)
    if len(h) > nth:
        return sp[h[nth]][1], sp[h[nth] + len(toks) - 1][2]
    raise KeyError(f"timing: {phrase!r} (occurrence {nth}) not found in {sid}")


def at(sid, phrase, nth=0):
    """Start time of the phrase's first word."""
    return _locate(sid, phrase, nth)[0]


def end_of(sid, phrase, nth=0):
    """End time of the phrase's last word."""
    return _locate(sid, phrase, nth)[1]


if __name__ == "__main__":
    import sys
    a = sys.argv[1:]
    load(a.pop(0) if len(a) % 2 else None)
    for s in _tl()["scenes"]:
        print(s["id"], "%.2f-%.2f" % scene(s["id"]), s["title"], pauses(s["id"]) or "")
    for sid, ph in zip(a[::2], a[1::2]):
        print(f"{sid} {ph!r}: {at(sid, ph):.2f} -> {end_of(sid, ph):.2f}")
