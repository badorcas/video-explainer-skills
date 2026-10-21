"""Move hard-coded beat times in scene files after the narration was re-voiced or re-cut.

    python3 retime.py OLD_DIR NEW_DIR scenes.py [more.py ...] [--write]
                      [--min 0] [--max 1e9] [--bad LO:HI ...] [--no-anchors] [--tol 0.6]

OLD_DIR and NEW_DIR each hold the words.json (from align.py) of one voicing; timeline.json (from
voice.py) is used too when both have it.  The words of the two voicings are matched with difflib, and
the matched (old time, new time) pairs become a monotone piecewise-linear map old -> new.  Every float
literal in the scene files that lies in [--min, --max] is then moved through that map.  Without
--write it only prints the edits.

Anchors: with timeline.json in both dirs, each paragraph's start and end are added as pairs, and a word
pair that disagrees with its paragraph's shift by more than --tol seconds is dropped (a misheard word).
--bad LO:HI drops every word pair whose new time falls in that window (a stretch where words.json is
known to be misaligned); repeat it for several windows.

Only literals with a decimal point are touched (650.0 moves, 650 and 6.5e2 do not), so integer
constants are safe.  Set --min above the largest non-time float in the files (font sizes, buffers),
or use a timing.py lookup instead of literals and skip this tool altogether.
"""
import argparse, difflib, io, json, os, re, sys, tokenize
import numpy as np


def load_words(d):
    w = json.load(open(os.path.join(d, "words.json")))
    return [(re.sub(r"\W", "", x["w"]).lower(), x["s"], x["e"]) for x in w]


def load_paras(d):
    p = os.path.join(d, "timeline.json")
    return json.load(open(p))["paragraphs"] if os.path.exists(p) else None


def build_map(od, nd, bad=(), anchors=True, tol=0.6):
    a, b = load_words(od), load_words(nd)
    is_bad = lambda t: any(lo <= t <= hi for lo, hi in bad)
    sm = difflib.SequenceMatcher(None, [x[0] for x in a], [x[0] for x in b], autojunk=False)
    pairs = []
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            i, j = blk.a + k, blk.b + k
            if is_bad(b[j][1]) or is_bad(b[j][2]):
                continue
            pairs += [(a[i][1], b[j][1]), (a[i][2], b[j][2])]
    po, pn = (load_paras(od), load_paras(nd)) if anchors else (None, None)
    anch = []
    if po and pn:
        if [x["id"] for x in po] != [y["id"] for y in pn]:
            sys.exit("timeline.json paragraph ids differ between OLD_DIR and NEW_DIR; use --no-anchors")
        for x, y in zip(po, pn):
            anch += [(x["start"], y["start"]), (x["end"], y["end"])]

        def para_shift(t):
            for x, y in zip(po, pn):
                if x["start"] - 0.3 <= t <= x["end"] + 0.3:
                    return y["start"] - x["start"], y["end"] - x["end"]
            return None
        keep = []
        for t, u in pairs:
            r = para_shift(t)
            if r is None or min(abs(u - t - r[0]), abs(u - t - r[1])) <= tol:
                keep.append((t, u))
        pairs = keep
    xs, ys = [], []
    for t, u in sorted(set(pairs + anch)):      # keep it monotone
        if xs and (t <= xs[-1] or u < ys[-1]):
            continue
        xs.append(t); ys.append(u)
    if not xs:
        sys.exit("no matching words between the two voicings")
    xs, ys = np.array(xs), np.array(ys)
    return lambda t: float(np.interp(t, xs, ys, left=t + ys[0] - xs[0], right=t + ys[-1] - xs[-1]))


def retime_file(path, f, lo, hi, write):
    src = open(path).read()
    lines = src.split("\n")
    edits = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        s = tok.string
        if tok.type == tokenize.NUMBER and "." in s and "e" not in s.lower() and "j" not in s.lower():
            v = float(s)
            if lo <= v <= hi:
                ns = f"{f(v):.{max(1, len(s.split('.')[1]))}f}"
                if ns != s:
                    edits.append((tok.start, tok.end, s, ns))
    for (r, c0), (_, c1), s, ns in sorted(edits, reverse=True):
        L = lines[r - 1]
        lines[r - 1] = L[:c0] + ns + L[c1:]
        print(f"  {path}:{r} {s} -> {ns}")
    print(f"{path}: {len(edits)} literals {'moved' if write else 'would move'}")
    if write and edits:
        open(path, "w").write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("old"); ap.add_argument("new"); ap.add_argument("files", nargs="+")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--min", type=float, default=0.0)
    ap.add_argument("--max", type=float, default=1e9)
    ap.add_argument("--bad", action="append", default=[], metavar="LO:HI")
    ap.add_argument("--no-anchors", action="store_true")
    ap.add_argument("--tol", type=float, default=0.6)
    a = ap.parse_args()
    bad = [tuple(float(v) for v in w.split(":")) for w in a.bad]
    f = build_map(a.old, a.new, bad, not a.no_anchors, a.tol)
    for p in a.files:
        retime_file(p, f, a.min, a.max, a.write)


if __name__ == "__main__":
    main()
