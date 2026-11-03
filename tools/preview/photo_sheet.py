import sys, glob, os
from PIL import Image, ImageDraw, ImageFont
fs = sorted(glob.glob(sys.argv[1]))
f = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 22, index=1)
W, H, C = 300, 375, 4
rows = (len(fs) + C - 1) // C
s = Image.new("RGB", (W * C, (H + 30) * rows), "white"); d = ImageDraw.Draw(s)
for i, p in enumerate(fs):
    im = Image.open(p).convert("RGB"); r = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1)); l = (im.width - W) // 2; t = (im.height - H) // 2
    x, y = (i % C) * W, (i // C) * (H + 30)
    s.paste(im.crop((l, t, l + W, t + H)), (x, y)); d.text((x + 5, y + H + 2), os.path.basename(p)[:22], font=f, fill="black")
s.save(sys.argv[2], quality=85)
