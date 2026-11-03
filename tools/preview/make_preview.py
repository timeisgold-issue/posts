# 대기열의 실제 업로드 파일(jpg + caption.txt)로 확인용 미리보기 이미지를 만든다
import json, sys, glob, os
from PIL import Image, ImageDraw, ImageFont
REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
BLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
def font(p, s):
    return ImageFont.truetype(p, s, index=1)  # index 1 = KR
W, C, PAD = 1080, 3, 24
cw = (W - PAD * (C + 1)) // C; ch = int(cw * 1350 / 1080)
for d in sorted(glob.glob(sys.argv[1] + "/*/")):
    imgs = sorted(glob.glob(d + "*.jpg"), key=lambda p: int(os.path.basename(p)[:-4]))
    cap = open(d + "caption.txt", encoding="utf-8").read().strip()
    meta = json.load(open(d + "post.json"))
    f_cap, f_head, f_num = font(REG, 34), font(BLD, 40), font(BLD, 30)
    # 캡션 줄바꿈
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines = []
    for para in cap.split("\n"):
        cur = ""
        for chx in para:
            if tmp.textlength(cur + chx, font=f_cap) > W - 2 * PAD - 20 and chx not in ".,?!)%":
                lines.append(cur); cur = chx
            else:
                cur += chx
        lines.append(cur)
    rows = (len(imgs) + C - 1) // C
    grid_h = rows * (ch + PAD) + PAD
    H = 110 + grid_h + 40 + len(lines) * 50 + 40
    im = Image.new("RGB", (W, H), "#FFFFFF"); dr = ImageDraw.Draw(im)
    t = meta["publish_at"][11:16]
    dr.rectangle([0, 0, W, 100], fill="#111318")
    dr.text((PAD, 28), f"{os.environ.get('IG_HANDLE','@timeisgold_issue')}  ·  {meta['publish_at'][5:10]} {t} 예약  ·  {len(imgs)}장", font=f_head, fill="#FFFFFF")
    for i, p in enumerate(imgs):
        x = PAD + (i % C) * (cw + PAD); y = 110 + PAD + (i // C) * (ch + PAD)
        im.paste(Image.open(p).convert("RGB").resize((cw, ch), Image.LANCZOS), (x, y))
        dr.rounded_rectangle([x + 10, y + 10, x + 58, y + 52], 8, fill="#FF6A3D")
        dr.text((x + 34, y + 31), str(i + 1), font=f_num, fill="#FFFFFF", anchor="mm")
    y = 110 + grid_h + 30
    dr.line([PAD, y - 10, W - PAD, y - 10], fill="#DDDDDD", width=2)
    for ln in lines:
        dr.text((PAD + 10, y), ln, font=f_cap, fill="#2A6CCB" if ln.startswith("#") else "#111318")
        y += 50
    out = os.path.join(sys.argv[2], f"{t.replace(':','')}_" + os.path.basename(d.rstrip('/')).split('_', 1)[1] + ".jpg")
    im.save(out, quality=90); print(out, im.size)
