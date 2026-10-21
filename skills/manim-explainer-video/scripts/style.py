from manim import *
import numpy as np
import os

BG    = "#14161A"
INK   = "#E6E3DC"
MUTE  = "#7C828C"
FAINT = "#3A3F47"
TX    = "#6CB4EE"   # outgoing / radar
RX    = "#F0A04B"   # echo
BRAKE = "#E5534B"
AMBER = "#F5C542"
# Optional accents, one meaning each per video (the same hexes as blender_lineart.py)
GREEN = "#8FD16A"   # requirement, budget, footprint
FORCE = "#B497F0"   # force, torque, command
VEL   = "#38C7C0"   # velocity
FONT  = "Caladea"

config.background_color = BG

# manim's Indicate paints every part in the highlight colour, so an opaque box (a hash node, a
# card) turns solid and its label vanishes into it. This one recolours outlines and unstroked
# shapes (text glyphs, dots) only; a filled box keeps its fill.
_ManimIndicate = Indicate


class Indicate(_ManimIndicate):
    def create_target(self):
        target = self.mobject.copy()
        target.scale(self.scale_factor)
        for m in target.family_members_with_points():
            if m.get_stroke_width() > 0:
                m.set_stroke(self.color)
            else:
                m.set_fill(self.color)
        return target


# T() lays text out at 8x (see below), and manim hands Pango a wrap width of
# config.pixel_width, so lines wider than ~4.7 units wrapped at -ql and ~10.6 at -qh
# (and the text cache ignores the width, so a wrapped -ql layout leaked into -qh).
# Never wrap: line breaks are always explicit ("\n").
import manimpango as _mp
if not getattr(_mp.text2svg, "_nowrap", False):
    _t2s = _mp.text2svg
    def _t2s_nowrap(settings, size, ls, liga, fn, sx, sy, width, height, txt, pango_width=None):
        return _t2s(settings, size, ls, liga, fn, sx, sy, 200000, height, txt, pango_width)
    _t2s_nowrap._nowrap = True
    _mp.text2svg = _t2s_nowrap

KERN = 8
def T(s, size=26, color=INK, **kw):
    """Always make text with T(), never Text(). Pango snaps glyph advances to whole pixels
    at the small sizes manim lays text out at, which wrecks kerning ("Ar ray", "Workfl ow").
    Laying out at 8x and scaling down gives correct spacing.
    Pango wraps at the render's pixel width (854 px at -ql), and at 8x that wrapped long lines
    at low quality only; widen the layout box while the text is built. Split lines yourself."""
    pw, ph = config.pixel_width, config.pixel_height
    config.pixel_width, config.pixel_height = 64000, 36000
    try:
        t = Text(s, font=FONT, font_size=size*KERN, color=color, **kw)
    finally:
        config.pixel_width, config.pixel_height = pw, ph
    return t.scale(1/KERN)

def M(s, size=34, color=INK):
    return MathTex(s, font_size=size, color=color)

def Ms(*parts, size=34, color=INK):
    """MathTex built from parts, so each stays addressable: Ms("E", "=", "P t").
    Use it for any equation that will be stacked (eq_stack aligns on the "=" part)."""
    return MathTex(*parts, font_size=size, color=color)

ICON_DIRS = [os.environ.get("ICON_DIR", ""), "icons",
             os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "icons")]

def icon(name, h=1.0, color=INK, fill=None, sw=2):
    """Recognizable object from the bundled Phosphor set (assets/icons, MIT): outline in
    `color`, opaque dark fill so nothing behind shows through. Never hand-plot polygons
    for planes, cars, people, servers...; see SKILL.md."""
    for d in ICON_DIRS:
        p = os.path.join(d, name + ".svg")
        if d and os.path.exists(p):
            m = SVGMobject(p)
            return m.set_fill(fill or "#1E2127", 1).set_stroke(color, sw).scale_to_fit_height(h)
    raise FileNotFoundError(f"icon {name!r}: not in {ICON_DIRS}")

def plate(mob, buff=0.1, color=None):
    """Opaque backing behind a label or panel that sits on top of other graphics."""
    bg = SurroundingRectangle(mob, buff=buff, corner_radius=0.06, stroke_width=0,
                              fill_color=color or BG, fill_opacity=1)
    return VGroup(bg, mob)

def eq_stack(rows, buff=0.6, at="=", x=None):
    """Stack equations with equal gaps and their relation symbols in one column, the way
    an align* block sets them. Build each row with the symbol as its own substring:
    Ms("M_2", "=", r"\frac{a}{b}"). `x` pins the column of the "=" signs."""
    g = VGroup(*rows).arrange(DOWN, buff=buff)
    def rel(r):
        try:
            p = r.get_part_by_tex(at)
        except Exception:
            p = None
        return p if p is not None else r
    x0 = rel(rows[0]).get_center()[0] if x is None else x
    for r in rows:
        r.shift(RIGHT*(x0 - rel(r).get_center()[0]))
    return g

def header(s):
    return T(s, 22, MUTE).to_corner(UL, buff=0.45)

# ---------- road geometry (top-down, travel left->right) ----------
LANE_Y, ROAD_BOT, ROAD_TOP, CENTER_Y, SHEET_Y = -0.5, -1.2, 1.4, 0.1, -1.6
X0, X1 = -7.1, 7.1
TAN20 = np.tan(np.radians(20))

def road(sheet=False):
    g = VGroup(
        Line([X0, ROAD_BOT, 0], [X1, ROAD_BOT, 0], color=MUTE, stroke_width=2),
        Line([X0, ROAD_TOP, 0], [X1, ROAD_TOP, 0], color=MUTE, stroke_width=2),
        DashedLine([X0, CENTER_Y, 0], [X1, CENTER_Y, 0], color=FAINT, stroke_width=2, dash_length=0.25),
    )
    if sheet:
        g.add(metal_sheet())
    return g

def metal_sheet(x0=X0, x1=X1, y=SHEET_Y):
    return Line([x0, y, 0], [x1, y, 0], color="#B8C2CC", stroke_width=6)

def car(x, y=LANE_Y, L=0.95, W=0.5, fill=None, label=None, lsize=22):
    body = RoundedRectangle(corner_radius=0.08, width=L, height=W, stroke_color=INK,
                            stroke_width=2, fill_color=fill or BG, fill_opacity=1).move_to([x, y, 0])
    g = VGroup(body)
    if label:
        g.add(T(label, lsize, INK).move_to(body))
    return g

def brake_lights(c):
    b = c[0]
    l = b.get_left()
    h = b.height
    return VGroup(*[Rectangle(width=0.06, height=h*0.22, stroke_width=0, fill_color=BRAKE,
                              fill_opacity=1).move_to(l + RIGHT*0.05 + UP*s*h*0.33) for s in (1, -1)])

def blinker(c):
    b = c[0]
    return Dot(b.get_corner(UL) + RIGHT*0.12 + DOWN*0.06, radius=0.05, color=AMBER)

def zigzag(xc_front, xa_rear, y_lane=LANE_Y, y_sheet=SHEET_Y):
    xm = (xc_front + xa_rear) / 2
    return [np.array([xc_front, y_lane, 0]), np.array([xm, y_sheet, 0]), np.array([xa_rear, y_lane, 0])]

def corner_icon(scale=0.18, color=INK):
    tri = Triangle(color=color, stroke_width=2).scale(scale)
    c = tri.get_center()
    spokes = VGroup(*[Line(c, v, color=color, stroke_width=1.5) for v in tri.get_vertices()])
    return VGroup(tri, spokes)

def spectrum_axes(w=6, h=2.0, xmax=10):
    ax = Axes(x_range=[0, xmax, 1], y_range=[0, 1.1, 1], x_length=w, y_length=h,
              axis_config={"include_tip": False, "stroke_color": MUTE, "stroke_width": 2,
                           "include_ticks": False})
    return ax

def peaks(ax, spec, xmax=10, noise=0.0, color=INK):
    def f(x):
        return noise + sum(a*np.exp(-((x-m)/s)**2) for m, a, s in spec)
    return ax.plot(f, x_range=[0, xmax, 0.02], color=color, stroke_width=2.5)

class TL(Scene):
    T0 = 0.0
    T1 = 0.0
    def setup(self):
        self.camera.background_color = BG
    def now(self):
        return self.T0 + self.renderer.time
    def till(self, t):
        self._qa()
        dt = t - self.now()
        if dt > 0.04:
            self.wait(dt)
        elif dt < -0.15 and os.environ.get("QA") == "1":
            # the previous animation overran this cue: log it so it can be shortened
            os.makedirs("qa", exist_ok=True)
            with open(f"qa/{type(self).__name__}.late.txt", "a") as f:
                f.write(f"{t:.2f} reached at {self.now():.2f} ({-dt:.2f} s late)\n")
    def close(self, run=1.0):
        """Fade everything out so the fade ends 0.05 s before T1, shortened if the scene runs late."""
        run = max(0.2, min(run, self.T1 - self.now() - 0.05))
        if self.mobjects:
            self.play(*[FadeOut(m) for m in self.mobjects], run_time=run)
        self.end()
    def play(self, *args, **kwargs):
        # QA=1: log what text is on screen before and after every animation, for lint.py
        wait = all(isinstance(a, Wait) for a in args)       # self.wait() comes through here too
        self._tl_snap("wait" if wait else "pre")
        super().play(*args, **kwargs)
        self._tl_snap("wait" if wait else "post")
    def end(self):
        self.till(self.T1)
        if os.environ.get("QA") == "1":
            import qa
            qa.flush(self, self._qalog())
            qa.flush_timeline(self)
    def _tl_snap(self, phase):
        if os.environ.get("QA") == "1":
            import qa
            qa.snap_timeline(self, self.now(), phase)
    def _qalog(self):
        if not hasattr(self, "_qa_log"):
            self._qa_log = {"seen": set(), "lines": []}
        return self._qa_log
    def _qa(self):
        """Layout check of the current frame (QA=1, set by the low-quality render script)."""
        if os.environ.get("QA") == "1":
            import qa
            qa.check(self, self.now(), self._qalog())

# ---------- think-time countdown (self-voiced narration, [PAUSE n]) ----------
class Countdown(VGroup):
    """Thin ring, bottom right, whose arc shrinks as the seconds run out, with the seconds left
    inside. Countdown(8).at(3.0) shows the state 3 s in. Small and dim: it marks time, it is not
    the subject of the frame."""
    def __init__(self, seconds, r=0.34, **kw):
        super().__init__(**kw)
        self.seconds, self.r = seconds, r
        self.track = Circle(radius=r, stroke_color=FAINT, stroke_width=1.5)
        self.arc = Arc(radius=r, start_angle=PI/2, angle=-TAU, stroke_color=INK, stroke_width=2.5)
        self.num = T(str(int(np.ceil(seconds))), 20, INK)
        self.add(self.track, self.arc, self.num)
        self.to_corner(DR, buff=0.45)

    def at(self, t):
        frac = max(0.0, 1 - t/self.seconds)
        c = self.track.get_center()
        self.arc.become(Arc(radius=self.r, start_angle=PI/2, angle=-TAU*frac, stroke_color=INK,
                            stroke_width=2.5).move_arc_center_to(c))
        if frac == 0:
            self.arc.set_stroke(opacity=0)
        self.num.become(T(str(max(0, int(np.ceil(self.seconds - t)))), 20, INK).move_to(c))
        return self


def countdown_play(scene, start, end, cd=None):
    """Show a Countdown over exactly one pause window and fade it as the pause ends, so the answer
    that follows starts on a clean corner: countdown_play(self, *tm.pause("S03"))."""
    secs = end - start
    cd = cd or Countdown(round(secs))
    scene.till(start)
    cd.at(0)
    scene.add(cd)
    scene.play(UpdateFromAlphaFunc(cd, lambda m, a: m.at(a*secs)), run_time=secs, rate_func=linear)
    scene.play(FadeOut(cd), run_time=0.3)
    scene.remove(cd)

# ---------- vehicles that read without labels (top-down, facing +x) ----------
def sedan(x=0, y=0, L=1.0, W=0.48, color=INK, fill="#1E2127"):
    body = RoundedRectangle(corner_radius=W * 0.32, width=L, height=W, stroke_color=color,
                            stroke_width=2, fill_color=fill, fill_opacity=1)
    ws = Polygon([L*0.12, W*0.36, 0], [L*0.22, W*0.30, 0], [L*0.22, -W*0.30, 0], [L*0.12, -W*0.36, 0],
                 stroke_width=0, fill_color=color, fill_opacity=0.35)          # windshield
    rw = Polygon([-L*0.30, W*0.33, 0], [-L*0.36, W*0.28, 0], [-L*0.36, -W*0.28, 0], [-L*0.30, -W*0.33, 0],
                 stroke_width=0, fill_color=color, fill_opacity=0.25)          # rear window
    roof = Line([L*0.10, 0, 0], [-L*0.28, 0, 0], stroke_width=0)
    return VGroup(body, ws, rw).move_to([x, y, 0])

def van(x=0, y=0, L=1.6, W=0.95, color=INK, fill="#2B2F36"):
    body = RoundedRectangle(corner_radius=0.06, width=L, height=W, stroke_color=color,
                            stroke_width=2, fill_color=fill, fill_opacity=1)
    cab = Rectangle(width=L*0.16, height=W*0.86, stroke_width=0, fill_color=color,
                    fill_opacity=0.3).move_to([L*0.36, 0, 0])
    seam = Line([L*0.26, W/2, 0], [L*0.26, -W/2, 0], color=color, stroke_width=1.2, stroke_opacity=0.5)
    return VGroup(body, cab, seam).move_to([x, y, 0])

def turn_signal(vehicle, side=1):
    """Amber wedge at the front corner; animate with Flash-like opacity pulses at ~1.5 Hz."""
    b = vehicle[0]
    c = b.get_corner(UR if side > 0 else DR)
    return Polygon(c, c + LEFT*0.14, c + (DOWN if side > 0 else UP)*0.12,
                   stroke_width=0, fill_color=AMBER, fill_opacity=1)

# ---------- standard block diagram (controls convention) ----------
def block(text_or_mob, w=1.9, h=0.8):
    box = Rectangle(width=w, height=h, stroke_color=INK, stroke_width=2)
    inner = text_or_mob if isinstance(text_or_mob, Mobject) else T(text_or_mob, 20)
    inner.move_to(box).scale_to_fit_width(min(inner.width, w * 0.85))
    return VGroup(box, inner)

def chain(blocks, buff=0.55, y=0):
    """Left-to-right forward path with arrows. Returns (VGroup(blocks), VGroup(arrows))."""
    g = VGroup(*blocks).arrange(RIGHT, buff=buff).set_y(y)
    arrows = VGroup(*[Arrow(a.get_right(), b.get_left(), buff=0.05, stroke_width=2, color=MUTE,
                            max_tip_length_to_length_ratio=0.25) for a, b in zip(blocks, blocks[1:])])
    return g, arrows

def feedback(src, dst, drop=0.9, color=MUTE):
    """Return path drawn under the forward chain: down from src, left, up into dst."""
    p0 = src.get_bottom(); p3 = dst.get_bottom()
    p1 = p0 + DOWN * drop; p2 = np.array([p3[0], p1[1], 0])
    path = VMobject(color=color, stroke_width=2).set_points_as_corners([p0, p1, p2, p3 + DOWN * 0.12])
    tip = Triangle(color=color, fill_opacity=1, stroke_width=0).scale(0.08).move_to(p3 + DOWN * 0.08)
    return VGroup(path, tip)

def pulse_along(scene, path_mob, color=TX, run_time=1.5):
    """A dot travelling a path: use to animate a signal moving through a diagram."""
    d = Dot(path_mob.get_start(), radius=0.07, color=color)
    scene.play(MoveAlongPath(d, path_mob), run_time=run_time, rate_func=linear)
    scene.remove(d)
