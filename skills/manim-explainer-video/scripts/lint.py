"""Timing and composition lint for rendered scenes: the checks a reviewer would otherwise have to
catch by watching. Run after lq.sh (it needs the 480p15 renders and qa/<Scene>.tl.json).

Usage: python3 lint.py <transcript.json> file:Scene file:Scene ...   (scenes in playback order)
       add --host=intercut.py to read its HOST windows (narration seconds): a blank, static-hold or
       lopsided stretch that the host is on camera for is reported as HOST, not counted
       add --sheets to also write lint/<Scene>_beats.png (the settled frame of every beat, with the
       narration spoken while it is on screen underneath; 12 per page, then _beats2.png, ...)
A timeline.json from voice.py next to the transcript masks its [PAUSE] windows (pad only, no voice).
Writes lint/<Scene>.txt and lint/summary.txt; prints the summary. Exit code 1 if any ERROR.

ERROR lines are defects: fix them. CHECK lines need a judgment: look at the frame at that time and
either fix it or waive it in the scene class with a reason:
    LINT_OK = {"static-hold@221": "equation is being discussed", "wordy": "small-multiple titles"}
(a key is a code, or code@second to waive one occurrence).

  slot          the render is longer or shorter than T1-T0 (assemble.py trims or freezes it)
  label-gone    a label leaves the screen before the narration has finished saying it
  label-late    a label appears more than 2 s after the narration says it
  label-flash   a label is on screen for under 1.5 s (too short to read)
  blank         an empty frame for 0.8 s or more inside a scene (or a long empty head/tail)
  fade-flicker  a scene fades out and the next fades the same picture back in: cut across instead
  static-hold   no animation starts for 6 s or more (an updater ripple is not a beat) while the narration
                keeps going: check that every thing it names in that window is shown or highlighted
  lopsided      for 5 s or more everything sits in one side of the frame, the rest is empty
  wordy         more than 12 words of label text on screen for 3 s or more (principle 1)
  text-only     only text on screen, no graphic, for 3 s or more
"""
import ast, glob, json, os, re, subprocess, sys, unicodedata
import numpy as np

FPS = 5                     # analysis frame rate
W, H = 160, 90              # analysis frame size
STOP = set("the a an and or of to in on at by for with from as is are be this that these those it its "
           "into over under per vs".split())


# ---------- narration ----------

def norm(w):
    w = unicodedata.normalize("NFKD", w).encode("ascii", "ignore").decode().lower()
    w = re.sub(r"[^a-z0-9]", "", w)
    return w[:-1] if len(w) > 3 and w.endswith("s") else w


def _pause_windows(path):
    """[PAUSE] windows from a voice.py timeline.json next to the transcript (think time: pad only, no voice)."""
    tl = os.path.join(os.path.dirname(os.path.abspath(path)), "timeline.json")
    try:
        return [(p["start"], p["end"]) for p in json.load(open(tl)).get("pauses", [])]
    except (OSError, ValueError, KeyError, TypeError):
        return []


def load_words(path):
    """Whisper segments -> word list with times interpolated by character offset. Words whose midpoint
    falls inside a [PAUSE] window are hallucinations over the pad and are dropped."""
    pw = _pause_windows(path)
    words = []
    for seg in json.load(open(path)):
        txt, s, e = seg["t"], seg["s"], seg["e"]
        n = max(len(txt), 1)
        for m in re.finditer(r"\S+", txt):
            a = s + (e - s) * m.start() / n
            b = s + (e - s) * m.end() / n
            if any(p0 <= (a + b) / 2 <= p1 for p0, p1 in pw):
                continue
            words.append((norm(m.group()), a, b, m.group()))
    return words


def said(words, t0, t1):
    return " ".join(w[3] for w in words if w[1] < t1 and w[2] > t0)


def find_spoken(label, words, t0, t1):
    """Times (start, end) where the label's content words are spoken in order, within [t0, t1]."""
    toks = [norm(x) for x in re.findall(r"[^\s,;:()/-]+", label)]
    toks = [x for x in toks if x and x not in STOP and (len(x) >= 3 or x.isdigit())]
    if not toks or all(x.isdigit() for x in toks):
        return []
    hits = []
    for i, w in enumerate(words):
        if w[1] < t0 or w[1] > t1 or w[0] != toks[0]:
            continue
        j, k = i, 1
        while k < len(toks) and j < i + 2 + 3 * len(toks) and j + 1 < len(words):
            j += 1
            if words[j][0] == toks[k]:
                k += 1
        if k == len(toks):
            hits.append((w[1], words[j][2]))
    return hits


# ---------- timeline (qa/<Scene>.tl.json) ----------

def shown_elsewhere(lab, snaps, t):
    """True if, at time t, another on-screen label already contains all of lab's words."""
    key = re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", lab).lower())
    prior = [sn for sn in snaps if sn["t"] <= t + 1e-6]
    if not prior or not key:
        return False
    # Text() drops spaces ("EOF mode 1" is logged as "EOFmode1"), so compare as substrings
    return any(r[1] != lab and key in re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", r[1]).lower())
               for r in prior[-1]["texts"])


def label_intervals(snaps):
    """{label: [(appear_lo, appear_hi, gone_lo, gone_hi)]}: each change happens inside one play()."""
    out, cur = {}, {}
    for i, sn in enumerate(snaps):
        vis = {r[1] for r in sn["texts"] if r[0] == "text"}
        prev_t = snaps[i - 1]["t"] if i else sn["t"]
        for lab in vis - set(cur):
            cur[lab] = (prev_t, sn["t"])
        for lab in set(cur) - vis:
            a = cur.pop(lab)
            out.setdefault(lab, []).append((a[0], a[1], prev_t, sn["t"]))
    end = snaps[-1]["t"] if snaps else 0
    for lab, a in cur.items():
        out.setdefault(lab, []).append((a[0], a[1], end, end))
    return out


# ---------- video ----------

def frames(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-vf", f"fps={FPS},scale={W}:{H},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.int16)


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def runs(mask, min_len):
    """(start_idx, end_idx_exclusive) of True runs at least min_len frames long."""
    out, s = [], None
    for i, v in enumerate(list(mask) + [False]):
        if v and s is None:
            s = i
        if not v and s is not None:
            if i - s >= min_len:
                out.append((s, i))
            s = None
    return out


def video_stats(F):
    bg = np.median(F[:, :4, :4])                       # frame corners are background in this style
    ink = F > bg + 18
    frac = ink.mean(axis=(1, 2))
    side = []
    for k in ink:
        ys, xs = np.nonzero(k)
        if len(xs) < 20:
            side.append(None)
            continue
        x0, x1 = np.percentile(xs, [2, 98]); y0, y1 = np.percentile(ys, [2, 98])
        side.append(((x0 + x1) / 2 / W - 0.5, (y0 + y1) / 2 / H - 0.5, (x1 - x0) / W, (y1 - y0) / H))
    return frac, side


# ---------- per-scene lint ----------

def lint_scene(mod, scene, words, out, cache):
    vids = glob.glob(f"media/videos/{mod}/480p15/{scene}.mp4")
    tlp = f"qa/{scene}.tl.json"
    if not vids or not os.path.exists(tlp):
        out.append(("ERROR", "missing", 0, f"no 480p15 render or {tlp}: run lq.sh (QA=1) first"))
        return None
    tl = json.load(open(tlp))
    T0, T1, snaps = tl["T0"], tl["T1"], tl["snaps"]
    if snaps and "phase" not in snaps[0]:
        out.append(("ERROR", "missing", T0, f"{tlp} is from an older qa.py: re-render with lq.sh"))
        return None
    dur = duration(vids[0])
    if abs(dur - (T1 - T0)) > 0.15:
        out.append(("ERROR", "slot", T0 + dur, f"render is {dur:.2f} s, slot T1-T0 is {T1 - T0:.2f} s "
                    f"({'runs past T1; the end gets cut' if dur > T1 - T0 else 'ends early; the last frame is frozen'})"))

    # labels vs narration
    for lab, ivs in label_intervals(snaps).items():
        shown = sum(g_hi - a_lo for a_lo, a_hi, g_lo, g_hi in ivs)
        if shown < 1.5 and len(lab.split()) <= 6:
            out.append(("CHECK", "label-flash", ivs[0][0], f"{lab!r} is on screen for only {shown:.1f} s"))
        for s, e in find_spoken(lab, words, T0 - 0.5, T1 + 0.5):
            covering = [iv for iv in ivs if iv[0] <= s + 0.3 and iv[3] >= s]
            if covering:
                g_hi = max(iv[3] for iv in covering)
                if g_hi < e + 0.7 and g_hi < T1 - 0.2:
                    out.append(("ERROR", "label-gone", g_hi, f"{lab!r} is gone by {g_hi:.1f} s while it is being "
                                f"said ({s:.1f}-{e:.1f} s): hold it until about {e + 1.0:.1f} s"))
                continue
            later = [iv for iv in ivs if iv[0] > s]
            # an earlier mention far back, or the word already up inside another label ("EOF mode 1"), is not late
            if later and 2.0 < later[0][0] - s <= 12.0 and not shown_elsewhere(lab, snaps, s):
                out.append(("CHECK", "label-late", later[0][0], f"{lab!r} is said at {s:.1f} s but appears at "
                            f"{later[0][0]:.1f} s: bring it in on the word"))

    # wordy / text-only (state between consecutive snapshots)
    for i in range(len(snaps) - 1):
        a, b = snaps[i], snaps[i + 1]
        held = b["t"] - a["t"]
        if held < 3.0:
            continue
        txt = [r[1] for r in a["texts"] if r[0] == "text"]
        nw = sum(len(re.findall(r"(?<![\w°])[A-Za-z]{2,}(?![\w°])", x)) for x in txt)   # not "10°W", "5DMD"
        if nw > 12:
            out.append(("CHECK", "wordy", a["t"], f"{nw} words of labels held {held:.1f} s: " + " | ".join(txt)[:160]))
        if a["texts"] and a["graphics"] == 0:
            out.append(("CHECK", "text-only", a["t"], f"only text on screen for {held:.1f} s"))

    # video: blank, static, lopsided
    F = frames(vids[0])
    cache[scene] = F
    frac, side = video_stats(F)
    n = len(F)
    t_of = lambda i: T0 + i / FPS
    for s, e in runs(frac < 0.0015, int(0.8 * FPS)):
        head, tail = s == 0, e >= n - 1
        if head and (e - s) / FPS <= 1.0 or tail and (e - s) / FPS <= 1.5:
            continue
        where = "at the start" if head else "at the end" if tail else "mid-scene"
        out.append(("ERROR", "blank", t_of(s), f"empty frame {where} for {(e - s) / FPS:.1f} s "
                    f"({t_of(s):.1f}-{t_of(e):.1f} s)", t_of(e)))
    # static hold: no animation starts for 6 s or more (updater ripples don't count as a new beat)
    posts = [sn["t"] for sn in snaps if sn.get("phase") == "post"]
    pres = [sn["t"] for sn in snaps if sn.get("phase") == "pre"]
    last_play = posts[-1] if posts else T0
    for a in [T0] + posts:
        nxt = min([p for p in pres if p >= a - 1e-6] + [T1])
        if nxt - a >= 6.0 and not (nxt >= T1 - 0.05 and a >= last_play - 1e-6):
            out.append(("CHECK", "static-hold", a, f"no animation {a:.1f}-{nxt:.1f} s ({nxt - a:.1f} s). Narration: "
                        f"\"{said(words, a, nxt)[:220]}\" -> is each thing named here shown or highlighted as it is said?", nxt))
    lop = []
    for k in side:
        if k is None:
            lop.append(None)
            continue
        cx, cy, w, h = k
        lop.append("left" if cx < -0.2 and w < 0.6 else "right" if cx > 0.2 and w < 0.6 else
                   "top" if cy < -0.22 and h < 0.55 else "bottom" if cy > 0.22 and h < 0.55 else None)
    for d in ("left", "right", "top", "bottom"):
        for s, e in runs([x == d for x in lop], int(5 * FPS)):
            out.append(("CHECK", "lopsided", t_of(s), f"everything sits in the {d} of the frame "
                        f"{t_of(s):.1f}-{t_of(e):.1f} s; the opposite side is empty: centre it or use that space", t_of(e)))
    return tl


def seam(a, b, Fa, Fb, tla, tlb, out):
    """Scene a fades to black and scene b fades the same picture back in -> flicker."""
    if Fa is None or Fb is None or abs(tla["T1"] - tlb["T0"]) > 0.05:
        return
    fa, _ = video_stats(Fa)
    fb, _ = video_stats(Fb)
    if fa[-1] > 0.5 * max(fa[-int(3 * FPS):].max(), 1e-6):
        return                                    # A does not fade out: a straight cut or a hand-off
    i = len(fa) - 1
    while i > 0 and fa[i] < 0.8 * fa[-int(3 * FPS):].max():
        i -= 1
    j = 0
    while j < len(fb) - 1 and fb[j] < 0.8 * fb[:int(3 * FPS)].max():
        j += 1
    bg = np.median(Fa[:, :4, :4])
    A, B = Fa[i] > bg + 18, Fb[j] > bg + 18
    if (A & B).sum() > 0.6 * max((A | B).sum(), 1):          # same picture on both sides of the dip
        out.append(("ERROR", "fade-flicker", tla["T1"], f"{a} fades out and {b} fades the same picture back in: "
                    f"drop {a}'s fade-out and start {b} on its last frame"))


def beat_sheet(mod, scene, tl, words, F):
    """One frame per hold (the settled picture between two animations), captioned with what is said
    during that hold, plus one frame every ~3 s inside any animation longer than 3 s (marked "moving").
    12 frames per page: lint/<Scene>_beats.png, _beats2.png, ..."""
    from PIL import Image, ImageDraw, ImageFont
    T0, T1, snaps = tl["T0"], tl["T1"], tl["snaps"]
    pres = [sn["t"] for sn in snaps if sn["phase"] == "pre"]
    posts = [sn["t"] for sn in snaps if sn["phase"] == "post"]
    inked = lambda t: (lambda i: i >= 0 and (F[i] > np.median(F[:, :4, :4]) + 18).mean() >= 0.0015)(
        min(int((t - T0) * FPS), len(F) - 1))
    shots = []                                   # (caption start, caption end, sample time, tag)
    for a in pres:
        b = min([p for p in posts if p >= a - 1e-6] + [T1])
        n = int((b - a) // 3.0)
        for k in range(1, n + 1):
            t = a + (b - a) * k / (n + 1)
            if inked(t):
                shots.append((t - 1.5, t + 1.5, t, "moving "))
    # settled frames: every hold of 0.8 s or more, plus a short hold whenever 2.5 s have passed
    # since the last frame kept (a run of quick beats with brief pauses must not vanish from the sheet)
    last = T0 - 99
    for a in sorted(set([T0] + posts)):
        b = min([p for p in pres if p >= a - 1e-6] + [T1])
        if b - a < 0.05:
            continue
        last = max([last] + [s[2] for s in shots if s[3] and s[2] <= a])
        ts = b - min(0.15, (b - a) / 2)
        if (b - a >= 0.8 or a - last >= 2.5) and inked(ts):
            shots.append((a, b, ts, ""))
            last = ts
    shots.sort(key=lambda r: r[2])
    vid = glob.glob(f"media/videos/{mod}/480p15/{scene}.mp4")[0]
    try:
        font = ImageFont.load_default(size=15)
    except TypeError:
        font = ImageFont.load_default()
    tiles = []
    for a, b, ts, tag in shots:
        p = "lint/_f.png"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{ts - T0:.2f}", "-i", vid,
                        "-frames:v", "1", p], check=True)
        im = Image.open(p).convert("RGB")
        cap = Image.new("RGB", (im.width, 64), (0, 0, 0))
        d = ImageDraw.Draw(cap)
        txt = (f"{tag}{ts:.1f}s" if tag else f"{a:.1f}-{b:.1f}s") + f"  \"{said(words, a - 0.3, b)}\""
        lines, line = [], ""
        for w in txt.split():
            if d.textlength(line + " " + w, font=font) > im.width - 12:
                lines.append(line); line = w
            else:
                line = (line + " " + w).strip()
        lines.append(line)
        if len(lines) > 3:
            lines = lines[:3]; lines[2] += " ..."
        d.multiline_text((6, 4), "\n".join(lines), fill=(255, 220, 0), font=font, spacing=3)
        tile = Image.new("RGB", (im.width, im.height + 64))
        tile.paste(im, (0, 0)); tile.paste(cap, (0, im.height))
        tiles.append(tile)
    if os.path.exists("lint/_f.png"):
        os.remove("lint/_f.png")
    for old in glob.glob(f"lint/{scene}_beats*.png"):
        os.remove(old)
    cols, per = 3, 12
    for k in range(0, len(tiles), per):
        page = tiles[k:k + per]
        w, h = page[0].size
        sheet = Image.new("RGB", (w * cols, h * ((len(page) + cols - 1) // cols)))
        for i, tile in enumerate(page):
            sheet.paste(tile, ((i % cols) * w, (i // cols) * h))
        sheet.save(f"lint/{scene}_beats{'' if k == 0 else k // per + 1}.png")


def host_windows(path):
    """HOST = [(a, b), ...] from the intercut script, without importing it."""
    src = open(path).read()
    m = re.search(r"^HOST\s*=\s*(\[.*?\])", src, re.S | re.M)
    return [tuple(map(float, p)) for p in re.findall(r"\(\s*([\d.]+)\s*,\s*([\d.]+)\s*\)", m.group(1))] if m else []


def covered(a, b, host):
    if b <= a:
        return False
    return sum(max(0.0, min(b, hb) - max(a, ha)) for ha, hb in host) >= 0.8 * (b - a)


def lint_ok_from_source(mod, scene):
    """LINT_OK as written in <mod>.py now, so a new waiver needs no re-render (None if not found)."""
    try:
        tree = ast.parse(open(f"{mod}.py").read())
    except (OSError, SyntaxError):
        return None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == scene:
            for st in node.body:
                if isinstance(st, ast.Assign) and any(getattr(t, "id", "") == "LINT_OK" for t in st.targets):
                    try:
                        return ast.literal_eval(st.value)
                    except ValueError:
                        return None
            return {}
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sheets = "--sheets" in sys.argv
    hostarg = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--host=")]
    host = host_windows(hostarg[0]) if hostarg else []
    words = load_words(args[0])
    specs = [tuple(x.split(":")) for x in args[1:]]
    os.makedirs("lint", exist_ok=True)
    cache, tls, report = {}, {}, []
    n_err = 0
    for mod, scene in specs:
        out = []
        tls[scene] = lint_scene(mod, scene, words, out, cache)
        report.append((scene, out))
        if sheets and tls[scene]:
            beat_sheet(mod, scene, tls[scene], words, cache[scene])
    for (a, b) in zip(specs, specs[1:]):
        if tls.get(a[1]) and tls.get(b[1]):
            seam(a[1], b[1], cache.get(a[1]), cache.get(b[1]), tls[a[1]], tls[b[1]], dict(report)[a[1]])
    lines = []
    for scene, out in report:
        mod = dict((sc, m) for m, sc in specs)[scene]
        ok = lint_ok_from_source(mod, scene)
        if ok is None:
            ok = (tls.get(scene) or {}).get("lint_ok", {})
        rows = []
        for sev, code, t, msg, *end in sorted(out, key=lambda r: r[2]):
            why = ok.get(f"{code}@{int(t)}") or ok.get(f"{code}@{round(t)}") or ok.get(code)   # 382.97 prints as 383.0
            if not why and end and covered(t, end[0], host):
                sev, why = "HOST", "host on camera (intercut)"
            rows.append(f"{scene:5s} {'WAIVED' if why and sev != 'HOST' else sev:6s} {code:12s} t={t:6.1f}  {msg}"
                        + (f"  [{'waived: ' if sev != 'HOST' else ''}{why}]" if why else ""))
            n_err += sev == "ERROR" and not why
        open(f"lint/{scene}.txt", "w").write("\n".join(rows) + ("\n" if rows else ""))
        lines += rows or [f"{scene:5s} clean"]
    open("lint/summary.txt", "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
