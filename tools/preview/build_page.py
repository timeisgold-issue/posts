# 대기열(queue)의 실제 업로드 파일로 휴대폰용 미리보기 페이지를 만든다
# python3 build_page.py <queue폴더> <출력폴더> "<페이지 제목>"
import json, sys, glob, os, html, shutil
from PIL import Image
q, out, title = sys.argv[1], sys.argv[2], sys.argv[3]
shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
posts = []
for d in sorted(glob.glob(os.path.join(q, "*/"))):
    name = os.path.basename(d.rstrip("/"))
    meta = json.load(open(d + "post.json"))
    cap = open(d + "caption.txt", encoding="utf-8").read().strip()
    imgs = sorted(glob.glob(d + "*.jpg"), key=lambda p: int(os.path.basename(p)[:-4]))
    os.makedirs(os.path.join(out, "img", name), exist_ok=True)
    rel = []
    for i, p in enumerate(imgs, 1):
        im = Image.open(p).convert("RGB"); im = im.resize((900, int(900 * im.height / im.width)), Image.LANCZOS)
        r = f"img/{name}/{i}.jpg"; im.save(os.path.join(out, r), quality=84, optimize=True); rel.append(r)
    posts.append(dict(id=name, time=meta["publish_at"][11:16], date=meta["publish_at"][5:10].replace("-", "/"),
                      approved=meta.get("approved", False), title=cap.splitlines()[0], cap=cap, imgs=rel))
cards = []
for p in posts:
    slides = "".join(f'<img src="{s}" alt="{i+1}장" loading="lazy" onclick="zoom(this)">' for i, s in enumerate(p["imgs"]))
    dots = "".join('<i></i>' for _ in p["imgs"])
    badge = "승인됨" if p["approved"] else "승인 대기"
    cards.append(f'''<section class="post">
<div class="head"><span class="time">{p["date"]} {p["time"]}</span><span class="badge {'ok' if p['approved'] else ''}">{badge}</span></div>
<h2>{html.escape(p["title"])}</h2>
<div class="car" onscroll="dot(this)">{slides}</div>
<div class="dots">{dots}</div>
<p class="hint">옆으로 넘기기 · 사진을 누르면 크게 보기</p>
<pre class="cap">{html.escape(p["cap"])}</pre></section>''')
page = f'''<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap" rel="stylesheet">
<style>
:root{{--bg:#0f1115;--card:#181b21;--line:#2a2e36;--txt:#eceef2;--sub:#9aa0aa;--acc:#FF6A3D}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--txt);font-family:'Noto Sans KR',sans-serif}}
header{{padding:20px 16px 8px}} header h1{{font-size:20px;margin:0 0 4px;font-weight:900}} header p{{margin:0;color:var(--sub);font-size:13px}}
.post{{background:var(--card);margin:14px 0;padding:14px 0 16px;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}}
.head{{display:flex;justify-content:space-between;align-items:center;padding:0 16px}}
.time{{font-weight:700;color:var(--acc);font-size:15px}} .badge{{font-size:12px;padding:3px 8px;border-radius:99px;background:#333;color:#ddd}} .badge.ok{{background:#1f3b2a;color:#7fe0a3}}
h2{{font-size:17px;line-height:1.4;margin:8px 16px 12px}}
.car{{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;scrollbar-width:none}} .car::-webkit-scrollbar{{display:none}}
.car img{{flex:0 0 100%;width:100%;scroll-snap-align:center;display:block;cursor:zoom-in}}
.dots{{display:flex;gap:6px;justify-content:center;margin-top:10px}} .dots i{{width:6px;height:6px;border-radius:50%;background:#444}} .dots i.on{{background:var(--acc)}}
.hint{{text-align:center;color:var(--sub);font-size:12px;margin:6px 0 0}}
.cap{{white-space:pre-wrap;font-family:inherit;font-size:14.5px;line-height:1.65;margin:14px 16px 0;padding:12px 14px;background:#11141a;border-radius:10px;border:1px solid var(--line)}}
#lb{{position:fixed;inset:0;background:#000;display:none;z-index:9;overflow:auto}} #lb.show{{display:flex;align-items:center}} #lb.show.big{{display:block}}
#lb img{{width:100%;display:block}} #lb.big img{{width:220%}}
#lb .bar{{position:fixed;left:0;right:0;bottom:0;display:flex;gap:8px;padding:12px;background:linear-gradient(transparent,#000)}}
#lb button{{flex:1;padding:12px;border:0;border-radius:10px;font-size:15px;font-weight:700;background:#222;color:#fff}} #lb button.acc{{background:var(--acc)}}
</style></head><body>
<header><h1>{html.escape(title)}</h1><p>실제로 올라갈 파일 그대로 · {len(posts)}편</p></header>
{''.join(cards)}
<div id="lb"><img id="lbi" alt=""><div class="bar"><button class="acc" onclick="tog()">확대 / 원래대로</button><button onclick="cls()">닫기</button></div></div>
<script>
function dot(c){{const n=Math.round(c.scrollLeft/c.clientWidth);const ds=c.nextElementSibling.children;for(let i=0;i<ds.length;i++)ds[i].className=i===n?'on':'';}}
document.querySelectorAll('.car').forEach(dot);
const lb=document.getElementById('lb'),lbi=document.getElementById('lbi');
function zoom(im){{lbi.src=im.src;lb.className='show';lb.scrollTo(0,0);}}
function tog(){{lb.classList.toggle('big');}}
function cls(){{lb.className='';}}
</script></body></html>'''
open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(page)
print(len(posts), "posts", sum(len(p["imgs"]) for p in posts), "images")
