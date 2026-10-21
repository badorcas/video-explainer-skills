"""Shared Blender helpers for line-art stills in the house 2D style.

Imported by the per-video shot scripts (run inside `nix develop <skill dir>#blender`, or via blender_stills.sh):
  blender -b -P <shots>.py -- --shot NAME --out DIR [--w 1920 --h 1080 --samples 16 --force]

Look (creative-devices.md, Blender line art): near-black background, Freestyle ink edges, dark flat fills from
emission shaders (no lights, no shading gradients), colour only where the 2D encoding puts it.  Colour management
is 'Standard', so a flat fill's PNG pixel equals its hex value.

What a shot script gets from here:
  * reset(): empty scene, Cycles CPU, BG world, Standard view transform
  * flat(hex[, alpha]) and two_tone(day, night, sun_dir) materials (two_tone is a hard terminator, not a ramp)
  * collections with Freestyle linesets: coll(name, line=hex, px=2.0, alpha=1.0, crease=None) (line=None: no edges)
  * geometry: tube, dashed, arrow, arc_arrow, sphere, disk, ring_band, box, cylinder, plane, billboard_rect
  * cameras: ortho_cam(target, az, el, width) and persp_cam(...); px() = world units per pixel at the target
  * render(out_png, anchors): renders to a temporary file and renames it, so a killed render never leaves a
    half-written PNG; writes the 2D anchors (pixel coordinates, origin top left) beside it as JSON.
"""
import bpy, bmesh, sys, os, math, json, time
from mathutils import Vector, Matrix

# ------------------------------------------------------------------ palette (matches scripts/style.py)
BG = "#14161A"; INK = "#E6E3DC"; MUTE = "#7C828C"; FAINT = "#3A3F47"
TX = "#6CB4EE"          # the subject of the video (one hero object or path)
RX = "#F0A04B"          # a second actor or returned signal
BRAKE = "#E5534B"       # disturbance, error, danger
SUN = "#F5C542"         # Sun and sunlight; the same hex as AMBER in style.py
GREEN = "#8FD16A"       # requirement, footprint, "good"
FORCE = "#B497F0"       # torque, force
VEL = "#38C7C0"         # velocity
OLIVE = "#9AA86B"       # spare accent (a damping layer, a second material)
PINK = "#CC79A7"        # spare accent (an alternative or candidate option)
DAYF = "#353B45"; NIGHT = "#0B0D11"; GRAT = "#4A515C"; COAST = "#5E6570"
FILL = "#1B2733"        # dark flat fill for structure (the 2D scenes' structure fill)
FILL2 = "#22303F"       # second structure tone (a face that must separate from FILL)
METAL = "#262A31"       # dark gray fill for context parts


def argv():
    return sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []


def arg(name, default, cast=str):
    a = argv()
    return cast(a[a.index(name)+1]) if name in a else default


def flag(name):
    return name in argv()


def lin(h):
    h = h.lstrip("#"); c = [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]
    f = lambda v: v/12.92 if v <= 0.04045 else ((v+0.055)/1.055)**2.4
    return (f(c[0]), f(c[1]), f(c[2]))


def mix(h0, h1, t):
    a = [int(h0.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)]
    b = [int(h1.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(int(round(a[i]+(b[i]-a[i])*t)) for i in range(3))


# ------------------------------------------------------------------ scene
W = H = None


def reset(w=None, h=None, samples=None):
    global W, H, _CAM_W
    W = w or arg("--w", 1920, int); H = h or arg("--h", 1080, int)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
    sc.cycles.samples = samples or arg("--samples", 16, int); sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 0; sc.cycles.pixel_filter_type = "BLACKMAN_HARRIS"; sc.cycles.filter_width = 1.5
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.compression = 15
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
    sc.display_settings.display_device = "sRGB"
    world = bpy.data.worlds.new("bg"); sc.world = world; world.use_nodes = True
    bg = world.node_tree.nodes["Background"]; bg.inputs[0].default_value = (*lin(BG), 1); bg.inputs[1].default_value = 1.0
    sc.render.use_freestyle = True; sc.render.line_thickness_mode = "ABSOLUTE"
    vl = sc.view_layers[0]; vl.use_freestyle = True
    fs = vl.freestyle_settings
    for ls in list(fs.linesets): fs.linesets.remove(ls)
    fs.crease_angle = math.radians(134)
    COLLS.clear(); MATS.clear()
    return sc


# ------------------------------------------------------------------ materials
MATS = {}


def flat(hexc, alpha=1.0, name=None):
    key = ("flat", hexc, round(alpha, 3))
    if key in MATS: return MATS[key]
    m = bpy.data.materials.new(name or f"flat{hexc}{alpha}"); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); N, L = nt.nodes, nt.links
    out = N.new("ShaderNodeOutputMaterial"); em = N.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*lin(hexc), 1); em.inputs["Strength"].default_value = 1.0
    if alpha < 1.0:
        tr = N.new("ShaderNodeBsdfTransparent"); mx = N.new("ShaderNodeMixShader")
        mx.inputs[0].default_value = alpha
        L.new(tr.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], out.inputs["Surface"])
        m.blend_method = "BLEND" if hasattr(m, "blend_method") else None
    else:
        L.new(em.outputs[0], out.inputs["Surface"])
    MATS[key] = m
    return m


def two_tone(day, night, sun_dir, name="earth"):
    """Hard day/night split on the surface normal against the Sun direction: two flat tones, no ramp."""
    key = ("two", day, night, tuple(round(v, 4) for v in sun_dir))
    if key in MATS: return MATS[key]
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); N, L = nt.nodes, nt.links
    out = N.new("ShaderNodeOutputMaterial"); em = N.new("ShaderNodeEmission")
    geo = N.new("ShaderNodeNewGeometry")
    dot = N.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"; dot.inputs[1].default_value = Vector(sun_dir).normalized()
    gt = N.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0.0
    mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"
    mx.inputs["A"].default_value = (*lin(night), 1); mx.inputs["B"].default_value = (*lin(day), 1)
    L.new(geo.outputs["Normal"], dot.inputs[0]); L.new(dot.outputs["Value"], gt.inputs[0])
    L.new(gt.outputs[0], mx.inputs["Factor"]); L.new(mx.outputs["Result"], em.inputs["Color"])
    L.new(em.outputs[0], out.inputs["Surface"])
    MATS[key] = m
    return m


# ------------------------------------------------------------------ collections and Freestyle linesets
COLLS = {}


def coll(name, line=None, px=2.0, alpha=1.0, crease=False, contour=True):
    """A collection; with line=hex its objects get Freestyle edges (silhouette, border, contour; crease optional)."""
    if name in COLLS: return COLLS[name]
    c = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c); COLLS[name] = c
    if line:
        fs = bpy.context.scene.view_layers[0].freestyle_settings
        ls = fs.linesets.new(name); ls.select_by_collection = True; ls.collection = c
        ls.select_by_visibility = True; ls.visibility = "VISIBLE"
        ls.select_silhouette = contour; ls.select_border = True; ls.select_contour = contour
        ls.select_crease = bool(crease); ls.select_external_contour = contour
        st = ls.linestyle; st.color = lin(line); st.thickness = px; st.alpha = alpha; st.caps = "ROUND"
        st.chaining = "PLAIN"
    return c


def put(o, c):
    for u in list(o.users_collection): u.objects.unlink(o)
    (coll(c) if isinstance(c, str) else c).objects.link(o)      # an unknown name becomes a collection with no edges
    return o


def _mesh(name, verts, faces, mat, c, smooth=False):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    o = bpy.data.objects.new(name, me); o.data.materials.append(mat)
    for p in me.polygons: p.use_smooth = smooth
    return put(o, c)


# ------------------------------------------------------------------ cameras
CAM = {}


def ortho_cam(target, az, el, width, roll=0.0, dist=60.0):
    """Orthographic camera looking at target from azimuth az, elevation el (deg, world z up); width = frame width."""
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.cos(e)*math.cos(a), math.cos(e)*math.sin(a), math.sin(e)))
    return _cam(Vector(target), d, dist, roll, ortho=width)


def persp_cam(target, az, el, dist, lens=50.0, roll=0.0):
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.cos(e)*math.cos(a), math.cos(e)*math.sin(a), math.sin(e)))
    return _cam(Vector(target), d, dist, roll, lens=lens)


def _cam(target, d, dist, roll, ortho=None, lens=50.0):
    up0 = Vector((0, 0, 1)) if abs(d.z) < 0.999 else Vector((0, 1, 0))
    right = up0.cross(d).normalized(); up = d.cross(right).normalized()
    if roll:
        R = Matrix.Rotation(math.radians(roll), 3, d); right = R @ right; up = R @ up
    cd = bpy.data.cameras.new("cam")
    if ortho:
        cd.type = "ORTHO"; cd.ortho_scale = ortho
    else:
        cd.lens = lens
    cd.sensor_fit = "HORIZONTAL"; cd.clip_start = 0.01; cd.clip_end = dist*4 + 200
    cam = bpy.data.objects.new("cam", cd)
    p = target + d*dist
    cam.matrix_world = Matrix(((right.x, up.x, d.x, p.x), (right.y, up.y, d.y, p.y), (right.z, up.z, d.z, p.z), (0, 0, 0, 1)))
    bpy.context.scene.collection.objects.link(cam); bpy.context.scene.camera = cam
    CAM.update(obj=cam, right=right, up=up, d=d, target=target, ortho=ortho, dist=dist, lens=lens)
    return cam


def px(at=None):
    """World units per output pixel (at the target distance for a perspective camera)."""
    if CAM["ortho"]: return CAM["ortho"]/W
    dist = CAM["dist"] if at is None else (Vector(at) - CAM["obj"].matrix_world.translation).dot(-CAM["d"])
    return dist*36.0/CAM["lens"]/W


def to_px(p):
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    v = world_to_camera_view(sc, CAM["obj"], Vector(p))
    return [round(v.x*W, 1), round((1 - v.y)*H, 1)]


# ------------------------------------------------------------------ geometry
def tube(pts, r, mat, c="nolines", closed=False, name="tube", res=4):
    cd = bpy.data.curves.new(name, "CURVE"); cd.dimensions = "3D"
    cd.bevel_depth = r; cd.bevel_resolution = res; cd.fill_mode = "FULL"; cd.use_fill_caps = True
    sp = cd.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts): sp.points[i].co = (*p, 1)
    sp.use_cyclic_u = closed
    o = bpy.data.objects.new(name, cd); o.data.materials.append(mat)
    return put(o, c)


def dashed(pts, r, mat, dash, gap, c="nolines", name="dash"):
    """Split a polyline into dashes of fixed world length (dash, gap) along its arc length."""
    pts = [Vector(p) for p in pts]
    seg = []; s = 0.0; on = True; cur = [pts[0]]; left = dash
    for a, b in zip(pts[:-1], pts[1:]):
        L = (b - a).length; t = 0.0
        while L - t > 1e-9:
            step = min(left, L - t); t += step; left -= step
            p = a + (b - a)*(t/L)
            if on: cur.append(p)
            if left <= 1e-9:
                if on and len(cur) > 1: seg.append(cur)
                on = not on; left = dash if on else gap; cur = [p]
    if on and len(cur) > 1: seg.append(cur)
    return [tube(sg, r, mat, c, name=name) for sg in seg]


def cone(p0, p1, r0, r1, mat, c="nolines", n=24, name="cone"):
    p0, p1 = Vector(p0), Vector(p1); a = (p1 - p0).normalized()
    e1 = a.orthogonal().normalized(); e2 = a.cross(e1)
    vs = [p0 + r0*(math.cos(2*math.pi*k/n)*e1 + math.sin(2*math.pi*k/n)*e2) for k in range(n)]
    vs += [p1 + r1*(math.cos(2*math.pi*k/n)*e1 + math.sin(2*math.pi*k/n)*e2) for k in range(n)]
    fs = [[k, (k+1) % n, n + (k+1) % n, n + k] for k in range(n)]
    if r0 > 1e-9: fs.append(list(range(n))[::-1])
    if r1 > 1e-9: fs.append([n + k for k in range(n)])
    return _mesh(name, vs, fs, mat, c)


def arrow(p0, p1, r, mat, head=None, head_r=None, c="nolines", name="arrow"):
    """Straight arrow: shaft tube plus cone head (head length and radius default to 6 r and 2.6 r)."""
    p0, p1 = Vector(p0), Vector(p1); a = (p1 - p0).normalized()
    head = head or 6*r; head_r = head_r or 2.6*r
    tube([p0, p1 - a*head*0.9], r, mat, c, name=name)
    return cone(p1 - a*head, p1, head_r, 0.0, mat, c, name=name + "_head")


def arc_pts(center, axis, start, a0, a1, n=64):
    """Points on a circular arc: start vector from the centre, rotated about axis from a0 to a1 (deg)."""
    center, axis, start = Vector(center), Vector(axis).normalized(), Vector(start)
    return [center + Matrix.Rotation(math.radians(a0 + (a1 - a0)*i/(n - 1)), 3, axis) @ start for i in range(n)]


def arc_arrow(center, axis, start, a0, a1, r, mat, c="nolines", head=None, head_r=None, name="arc"):
    """Curved arrow along an arc, head at a1 (sense follows the right hand rule about axis when a1 > a0)."""
    head = head or 6*r; head_r = head_r or 2.6*r
    rad = Vector(start).length
    dang = math.degrees(head/rad)*(1 if a1 > a0 else -1)
    pts = arc_pts(center, axis, start, a0, a1 - dang*0.9)
    tube(pts, r, mat, c, name=name)
    tip = arc_pts(center, axis, start, a1, a1, 2)[0]
    base = arc_pts(center, axis, start, a1 - dang, a1 - dang, 2)[0]
    return cone(base, tip, head_r, 0.0, mat, c, name=name + "_head")


def sphere(center, r, mat, c, n=96, name="sphere", flatten=0.0):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=n, v_segments=n//2, radius=r)
    if flatten:
        for v in bm.verts: v.co.z *= (1 - flatten)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.data.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    o.location = Vector(center)
    return put(o, c)


def disk(center, normal, r, mat, c, n=64, r_in=0.0, name="disk"):
    center, a = Vector(center), Vector(normal).normalized()
    e1 = a.orthogonal().normalized(); e2 = a.cross(e1)
    ring = [center + r*(math.cos(2*math.pi*k/n)*e1 + math.sin(2*math.pi*k/n)*e2) for k in range(n)]
    if r_in <= 0:
        return _mesh(name, ring, [list(range(n))], mat, c)
    inner = [center + r_in*(math.cos(2*math.pi*k/n)*e1 + math.sin(2*math.pi*k/n)*e2) for k in range(n)]
    return _mesh(name, ring + inner, [[k, (k+1) % n, n + (k+1) % n, n + k] for k in range(n)], mat, c)


def cylinder(p0, p1, r, mat, c, n=48, caps=True, name="cyl"):
    return cone(p0, p1, r, r, mat, c, n=n, name=name) if caps else _open_cyl(p0, p1, r, mat, c, n, name)


def _open_cyl(p0, p1, r, mat, c, n, name):
    p0, p1 = Vector(p0), Vector(p1); a = (p1 - p0).normalized()
    e1 = a.orthogonal().normalized(); e2 = a.cross(e1)
    vs = [p + r*(math.cos(2*math.pi*k/n)*e1 + math.sin(2*math.pi*k/n)*e2) for p in (p0, p1) for k in range(n)]
    return _mesh(name, vs, [[k, (k+1) % n, n + (k+1) % n, n + k] for k in range(n)], mat, c)


def box(center, half, mat, c, R=None, name="box", drop=()):
    """Box with half extents; drop = face names to leave open ('+x', '-y', ...) for a cutaway."""
    hx, hy, hz = half
    v = [Vector((sx*hx, sy*hy, sz*hz)) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    F = {"-x": [0, 1, 3, 2], "+x": [4, 6, 7, 5], "-y": [0, 4, 5, 1], "+y": [2, 3, 7, 6], "-z": [0, 2, 6, 4], "+z": [1, 5, 7, 3]}
    R = R if R is not None else Matrix.Identity(3)
    vs = [Vector(center) + R @ p for p in v]
    return _mesh(name, vs, [f for k, f in F.items() if k not in drop], mat, c)


def plane(center, u, v, mat, c, name="plane"):
    center, u, v = Vector(center), Vector(u), Vector(v)
    return _mesh(name, [center - u - v, center + u - v, center + u + v, center - u + v], [[0, 1, 2, 3]], mat, c)


def billboard_rect(x0, y0, x1, y1, mat, c="nolines", depth=1.0, name="bb"):
    """Screen-space rectangle (pixel coordinates, origin top left) on a plane just in front of the target."""
    def P(x, y):
        o = CAM["obj"].matrix_world.translation
        if CAM["ortho"]:
            sx = (x/W - 0.5)*CAM["ortho"]; sy = (0.5 - y/H)*CAM["ortho"]*H/W
            return CAM["target"] + CAM["right"]*sx + CAM["up"]*sy + CAM["d"]*depth
        raise NotImplementedError
    return _mesh(name, [P(x0, y1), P(x1, y1), P(x1, y0), P(x0, y0)], [[0, 1, 2, 3]], mat, c)


# ------------------------------------------------------------------ render
def render(out_png, anchors=None, meta=None):
    """Render to out_png atomically (temporary name, then rename) and write the anchors JSON beside it."""
    if os.path.exists(out_png) and not flag("--force"):
        print(f"SKIP {out_png}", flush=True); return
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    sc = bpy.context.scene
    tmp = out_png[:-4] + ".partial.png"
    sc.render.filepath = tmp
    t0 = time.time(); bpy.ops.render.render(write_still=True)
    js = dict(meta or {}); js["size"] = [W, H]
    js["anchors_px"] = {k: to_px(v) for k, v in (anchors or {}).items()}
    with open(out_png[:-4] + ".json.partial", "w") as f: json.dump(js, f, indent=1)
    os.replace(out_png[:-4] + ".json.partial", out_png[:-4] + ".json")
    os.replace(tmp, out_png)
    print(f"RENDERED {out_png} in {time.time()-t0:.1f}s", flush=True)
