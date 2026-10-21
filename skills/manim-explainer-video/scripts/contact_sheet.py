"""Contact sheet of every PNG in a folder: thumbnails in a grid, file name under each.

  python3 contact_sheet.py STILLS_DIR OUT.png [--cols 2 --thumb 900]
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1], sys.argv[2]
cols = int(sys.argv[sys.argv.index("--cols") + 1]) if "--cols" in sys.argv else 2
tw = int(sys.argv[sys.argv.index("--thumb") + 1]) if "--thumb" in sys.argv else 900
names = sorted(f for f in os.listdir(src) if f.endswith(".png") and ".partial" not in f
               and not f.startswith("contact_sheet"))
if not names:
    sys.exit(f"no PNGs in {src}")
ims = [Image.open(os.path.join(src, n)).convert("RGB") for n in names]
th = round(tw*ims[0].height/ims[0].width)
pad, cap = 24, 40
rows = (len(ims) + cols - 1)//cols
sheet = Image.new("RGB", (cols*tw + (cols + 1)*pad, rows*(th + cap) + (rows + 1)*pad), "#0B0C0F")
draw = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("DejaVuSans.ttf", 22)
except OSError:
    font = ImageFont.load_default()
for k, (n, im) in enumerate(zip(names, ims)):
    r, c = divmod(k, cols)
    x, y = pad + c*(tw + pad), pad + r*(th + cap + pad)
    sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
    draw.text((x, y + th + 8), n, fill="#E6E3DC", font=font)
tmp = out + ".partial.png"
sheet.save(tmp); os.replace(tmp, out)
print("SHEET", out, len(names), "stills")
