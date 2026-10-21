"""Layout checks for manim scenes, run at every TL.till() when QA=1 (lq renders set it).

Writes qa/<Scene>.txt, one line per problem (first occurrence only):
  text-x-line    a line or outline passes through a text label
  text-x-text    two labels overlap
  text-x-fill    a filled shape partly covers a label, or sits on top of it
  see-through    a line crosses into a shape that does not hide it (the shape's fill is
                 translucent or missing, or the line is drawn on top of it): layered
                 graphics read as a tangle. Unoutlined translucent shading (the area under
                 a curve, a range band) is exempt. Give the top layer an opaque fill (plate()),
                 fade what is underneath, or move one of them.
  eq-align       equations stacked one above another whose "=" signs are not in one
                 column: use eq_stack() (build "=" as its own substring)
  tips-collide   two arrowheads overlap (arrows converging on one point stack into a blob):
                 end each arrow at its own point on the target's edge, or merge the shafts
                 at a junction and draw one arrow from there
  off-frame      something visible lies outside the 16:9 frame (text within 0.25 of the edge)

Opt a mobject out with `m.qa_ok = True` (it and its children are skipped), e.g. a label
deliberately set on a bar of the same color family."""
import os
import numpy as np
from manim import Text, MarkupText, SingleStringMathTex, VMobject, ArrowTip, config

TEXT_TYPES = (Text, MarkupText, SingleStringMathTex)
FW, FH = config.frame_width / 2, config.frame_height / 2
SAMPLES = np.linspace(0, 1, 6)


def _walk(m, texts, shapes, anc=()):
    if getattr(m, "qa_ok", False):
        return
    if isinstance(m, TEXT_TYPES):
        texts.append(m)
        return
    if isinstance(m, VMobject) and len(m.points) >= 4:
        m._qa_anc = anc[-2:]          # nearest two groups: parts of one icon share them
        shapes.append(m)
    for s in m.submobjects:
        _walk(s, texts, shapes, anc + (id(m),))


def _sample(m):
    p = m.points
    n = len(p) // 4
    if n == 0:
        return np.zeros((0, 3))
    c = p[:n*4].reshape(n, 4, 3)
    t = SAMPLES[None, :, None]
    a, b, cc, d = (c[:, i][:, None, :] for i in range(4))
    pts = (1-t)**3*a + 3*(1-t)**2*t*b + 3*(1-t)*t**2*cc + t**3*d
    return pts.reshape(-1, 3)


def _stroke_vis(m):
    try:
        return m.get_stroke_width() > 0.3 and m.get_stroke_opacity() > 0.08
    except Exception:
        return False


def _fill(m):
    try:
        return float(m.get_fill_opacity())
    except Exception:
        return 0.0


def _bbox(m, pad=0.0):
    lo, hi = m.get_critical_point([-1, -1, 0]), m.get_critical_point([1, 1, 0])
    return lo[0] - pad, hi[0] + pad, lo[1] - pad, hi[1] + pad


def _inside_box(pts, b):
    return (pts[:, 0] > b[0]) & (pts[:, 0] < b[1]) & (pts[:, 1] > b[2]) & (pts[:, 1] < b[3])


def _inside_poly(pts, poly):
    """Even-odd test of pts (k,3) against closed polygon poly (n,3)."""
    x, y = pts[:, 0][:, None], pts[:, 1][:, None]
    x1, y1 = poly[:, 0][None, :], poly[:, 1][None, :]
    x2, y2 = np.roll(poly[:, 0], -1)[None, :], np.roll(poly[:, 1], -1)[None, :]
    cond = (y1 > y) != (y2 > y)
    with np.errstate(divide="ignore", invalid="ignore"):
        xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
    return np.sum(cond & (x < xi), axis=1) % 2 == 1


def _closed(m):
    p = m.points
    return len(p) >= 8 and np.linalg.norm(p[0] - p[-1]) < 1e-3


def _name(m):
    if isinstance(m, Text):
        return repr(m.text[:24])
    if isinstance(m, SingleStringMathTex):
        return "$" + m.get_tex_string()[:24] + "$"
    col = m.get_stroke_color() if _stroke_vis(m) else m.get_fill_color()
    return f"{type(m).__name__}({col})"


def _shrink(poly, d=0.06):
    c = poly.mean(axis=0)
    v = poly - c
    n = np.linalg.norm(v, axis=1, keepdims=True) + 1e-9
    return c + v * np.maximum(n - d, 0) / n


def _plated(x, bx, s, vis, pos):
    """True if an opaque shape drawn above s (and below x) covers the label: a plate()."""
    for c in vis:
        if _fill(c) >= 0.95 and _closed(c) and pos.get(id(s), 0) < pos.get(id(c), 0) < pos.get(id(x), 1e9):
            cb = _bbox(c)
            if cb[0] <= bx[0] and cb[1] >= bx[1] and cb[2] <= bx[2] and cb[3] >= bx[3]:
                return True
    return False


def _covered(pts, top, s, closed, pos, samp):
    """True if an opaque shape drawn between `top` and `s` covers all of pts."""
    for c in closed:
        if c is top or c is s or _fill(c) < 0.95:
            continue
        if pos.get(id(top), 0) < pos.get(id(c), 0) < pos.get(id(s), 0):
            if _inside_poly(pts, samp[id(c)]).all():
                return True
    return False


def check(scene, t, log):
    texts, shapes = [], []
    for m in scene.mobjects:
        _walk(m, texts, shapes)
    texts = [x for x in texts if _fill(x) > 0.08 and x.width > 0.01]
    allm = []
    for m in scene.mobjects:
        allm.extend(m.get_family())
    allm.sort(key=lambda m: getattr(m, "z_index", 0))      # draw order as the renderer sees it (stable)
    pos = {id(m): i for i, m in enumerate(allm)}
    found = []
    samp = {id(s): _sample(s) for s in shapes}
    vis = [s for s in shapes if _stroke_vis(s) or _fill(s) > 0.1]   # 10% or less reads as gone

    # off-frame
    for s in vis:
        p = samp[id(s)]
        if len(p) and (np.abs(p[:, 0]).max() > FW + 0.02 or np.abs(p[:, 1]).max() > FH + 0.02):
            found.append(("off-frame", _name(s)))
    for x in texts:
        b = _bbox(x)
        if b[0] < -FW + 0.25 or b[1] > FW - 0.25 or b[2] < -FH + 0.25 or b[3] > FH - 0.25:
            found.append(("off-frame", _name(x)))

    # text vs text
    for i, a in enumerate(texts):
        ba = _bbox(a, 0.02)
        for b in texts[i+1:]:
            bb = _bbox(b, 0.02)
            if ba[0] < bb[1] and bb[0] < ba[1] and ba[2] < bb[3] and bb[2] < ba[3]:
                found.append(("text-x-text", f"{_name(a)} / {_name(b)}"))

    # text vs shapes
    for x in texts:
        bx = _bbox(x, 0.04)
        fam = {id(f) for f in x.get_family()}
        for s in vis:
            if id(s) in fam:
                continue
            p = samp[id(s)]
            ins = _inside_box(p, bx)
            if not ins.any():
                continue
            if _stroke_vis(s) and ins.sum() >= 1:
                sb = _bbox(s)
                contains = sb[0] <= bx[0] and sb[1] >= bx[1] and sb[2] <= bx[2] and sb[3] >= bx[3]
                if not contains or not _closed(s):
                    if not _plated(x, bx, s, vis, pos):
                        found.append(("text-x-line", f"{_name(x)} x {_name(s)}"))
                    continue
            if _fill(s) > 0.05:
                sb = _bbox(s)
                contains = sb[0] <= bx[0] + 0.04 and sb[1] >= bx[1] - 0.04 and sb[2] <= bx[2] + 0.04 and sb[3] >= bx[3] - 0.04
                if not contains:
                    found.append(("text-x-fill", f"{_name(x)} x {_name(s)}"))
                elif pos.get(id(s), 0) > pos.get(id(x), 0):
                    found.append(("text-x-fill", f"{_name(x)} under {_name(s)}"))

    # see-through: a stroke that crosses into a closed shape it does not belong to
    # a fill-only translucent region (area under a curve, a range band) is shading, not a layer
    closed = [s for s in vis if _closed(s) and s.width > 0.15 and s.height > 0.15
              and (_stroke_vis(s) or _fill(s) >= 0.5)]
    for top in closed:
        poly = _shrink(samp[id(top)])
        tfam = {id(f) for f in top.get_family()}
        tb = _bbox(top)
        for s in vis:
            if s is top or id(s) in tfam or id(top) in {id(f) for f in s.get_family()} or not _stroke_vis(s):
                continue
            p = samp[id(s)]
            box = _inside_box(p, tb)
            if box.sum() < 2:
                continue
            ins = _inside_poly(p[box], poly)
            n_in = int(ins.sum())
            if n_in < 2 or n_in == len(p):
                continue          # touches only, or wholly inside (an icon's own detail)
            if set(getattr(s, "_qa_anc", ())) & set(getattr(top, "_qa_anc", ())):
                continue          # parts of the same drawn object (a fridge's door line)
            above = pos.get(id(s), 0) > pos.get(id(top), 0)
            if above and _closed(s) and _fill(s) >= 0.95:
                continue          # an opaque card laid on top hides what it covers
            if above and _covered(p[box][ins], top, s, closed, pos, samp):
                continue          # the line sits on its own opaque card, which hides `top`
            if above or _fill(top) < 0.95:
                found.append(("see-through", f"{_name(s)} {'over' if above else 'through'} {_name(top)}"))

    # stacked equations must share the column of their "=" sign
    def _eq_x(m):
        try:
            p = m.get_part_by_tex("=")
        except Exception:
            return None
        if p is None or p is m:
            return None
        try:
            if p.get_tex_string().strip() != "=":
                return None
        except Exception:
            return None
        return p.get_center()[0]
    eqs = [(m, _eq_x(m)) for m in texts if isinstance(m, SingleStringMathTex)]
    eqs = [(m, x) for m, x in eqs if x is not None]
    for i, (a, xa) in enumerate(eqs):
        for b, xb in eqs[i+1:]:
            ba, bb = _bbox(a), _bbox(b)
            overlap_x = min(ba[1], bb[1]) - max(ba[0], bb[0]) > 0.3 * min(a.width, b.width)
            gap_y = max(ba[2], bb[2]) - min(ba[3], bb[3])
            if overlap_x and gap_y < 1.6 and abs(xa - xb) > 0.06:
                found.append(("eq-align", f"{_name(a)} / {_name(b)}: '=' off by {abs(xa - xb):.2f}"))

    # arrowheads that overlap each other
    tips = [s for s in vis if isinstance(s, ArrowTip)]
    for i, a in enumerate(tips):
        pa = _sample(a)
        for b in tips[i+1:]:
            pb = _sample(b)
            if np.linalg.norm(a.get_center() - b.get_center()) > a.width + b.width:
                continue
            if _inside_poly(pa, pb).any() or _inside_poly(pb, pa).any() or \
                    np.linalg.norm(a.get_center() - b.get_center()) < 0.5 * min(a.width, b.width):
                found.append(("tips-collide", f"{_name(a)} / {_name(b)} at "
                              f"({a.get_center()[0]:.1f}, {a.get_center()[1]:.1f})"))

    for k, d in found:
        key = (k, d)
        if key not in log["seen"]:
            log["seen"].add(key)
            log["lines"].append(f"{t:7.1f} {k}: {d}")


def flush(scene, log):
    os.makedirs("qa", exist_ok=True)
    with open(os.path.join("qa", f"{type(scene).__name__}.txt"), "w") as f:
        f.write("\n".join(log["lines"]) + ("\n" if log["lines"] else ""))


# ---------- timeline for lint.py: which labels are on screen when ----------

def _texts_all(m, out):
    if isinstance(m, TEXT_TYPES):
        out.append(m)
        return
    for s in m.submobjects:
        _texts_all(s, out)


try:
    from style import BG as BG_HEX      # opaque plates behind labels are not graphics
except ImportError:
    BG_HEX = "#14161A"
BG_HEX = BG_HEX.upper()


def snap_timeline(scene, t, phase="post"):
    """Record the visible labels (string, centre) and whether any non-text graphic is visible."""
    texts, shapes = [], []
    for m in scene.mobjects:
        _texts_all(m, texts)
        for s in m.get_family():
            if not isinstance(s, TEXT_TYPES) and isinstance(s, VMobject) and len(s.points) >= 4 \
                    and (_stroke_vis(s) or (_fill(s) > 0.08 and s.get_fill_color().to_hex().upper() != BG_HEX)):
                shapes.append(s)
    rows = []
    for x in texts:
        if _fill(x) <= 0.15 or x.width < 0.01:
            continue
        c = x.get_center()
        if abs(c[0]) > FW or abs(c[1]) > FH:
            continue
        if isinstance(x, SingleStringMathTex):
            rows.append(["math", x.get_tex_string(), round(c[0], 2), round(c[1], 2)])
        else:
            rows.append(["text", x.text, round(c[0], 2), round(c[1], 2)])
    on_frame = [s for s in shapes if abs(s.get_center()[0]) < FW and abs(s.get_center()[1]) < FH]
    tl = scene.__dict__.setdefault("_qa_timeline", [])
    tl.append({"t": round(t, 2), "phase": phase, "texts": rows, "graphics": len(on_frame)})


def flush_timeline(scene):
    import json
    os.makedirs("qa", exist_ok=True)
    cls = type(scene)
    json.dump({"T0": cls.T0, "T1": cls.T1, "lint_ok": getattr(cls, "LINT_OK", {}),
               "snaps": scene.__dict__.get("_qa_timeline", [])},
              open(os.path.join("qa", f"{cls.__name__}.tl.json"), "w"))
