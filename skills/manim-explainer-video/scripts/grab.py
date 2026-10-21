"""Contact sheet of frames from a rendered scene, for visual review.
Usage: python3 grab.py <scene_output_name> t1 t2 ... -> sheets/<name>.png (2 columns)
Frames go to a private temp dir and the sheet next to the scenes, so agents rendering
same-named scenes in parallel (or in other projects) never read each other's frames."""
import sys, subprocess, glob, os, tempfile
from PIL import Image
name, times = sys.argv[1], [float(x) for x in sys.argv[2:]]
# newest render of the scene, whatever its quality (a stale HQ file must not win)
f = max(glob.glob(f"media/videos/**/{name}.mp4", recursive=True), key=os.path.getmtime)
tmp = tempfile.mkdtemp(prefix="grab_")
ims = []
for i, t in enumerate(times):
    p = os.path.join(tmp, f"g{i}.png")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(t), "-i", f, "-frames:v", "1", p])
    ims.append(Image.open(p))
w, h = ims[0].size
o = Image.new("RGB", (w * 2, h * ((len(ims) + 1) // 2)))
for i, im in enumerate(ims):
    o.paste(im, ((i % 2) * w, (i // 2) * h))
os.makedirs("sheets", exist_ok=True)
out = os.path.abspath(f"sheets/{name}.png")
o.save(out); print(out)
