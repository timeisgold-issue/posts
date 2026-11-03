// 카드 spec(JSON)을 세로 릴스용 레이어(배경 PNG + 글자 PNG)로 렌더링
// node render_layers.js <spec.json> <outDir>
const path = require('path'); const fs = require('fs'); const { chromium } = require('playwright');
const spec = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const OUT = process.argv[3]; fs.mkdirSync(OUT, { recursive: true });
const base = path.dirname(path.resolve(process.argv[2]));
const IMG = path.resolve(base, spec.imgDir), ACC = spec.accent || '#FF6A3D', HANDLE = spec.handle || '@timeisgold_issue', W = 1080, H = 1920;
const hl = t => t.replace(/<b>/g, `<span style="color:${ACC}">`).replace(/<\/b>/g, '</span>');
const css = (c, img) => `
body{margin:0;background:transparent}
.card{width:${W}px;height:${H}px;position:relative;overflow:hidden;font-family:'Noto Sans CJK KR',sans-serif;color:#fff}
.bgimg{position:absolute;inset:0;background:#000 url('${img}') ${c.pos || '50% 50%'}/cover no-repeat}
.fade{position:absolute;left:0;right:0;bottom:0;height:1250px;background:linear-gradient(to bottom,rgba(0,0,0,0) 0%,rgba(0,0,0,.7) 35%,rgba(0,0,0,.92) 100%)}
.blur{position:absolute;inset:-40px;background:url('${img}') ${c.pos || '50% 50%'}/cover;filter:blur(18px) brightness(.42)}
.box{position:absolute;left:84px;right:120px;bottom:470px;display:flex;flex-direction:column;align-items:flex-start;gap:26px}
.handle{font-size:28px;font-weight:500;color:rgba(255,255,255,.85)}
.chip{background:${ACC};font-size:34px;font-weight:700;padding:8px 22px;border-radius:6px}
.pre{font-size:36px;font-weight:500;color:#E9EAEE;line-height:1.45}
.title{font-size:${c.titleSize || 86}px;font-weight:900;line-height:1.2;letter-spacing:-2px}
.sub{font-size:35px;font-weight:500;color:#E9EAEE;line-height:1.55;letter-spacing:-.5px}
.rbox{position:absolute;left:84px;right:120px;top:300px;bottom:470px;display:flex;flex-direction:column;justify-content:center;gap:30px}
.cm{background:#fff;color:#111318;border-radius:22px;padding:26px 34px;display:flex;flex-direction:column;gap:8px}
.cm.hide{visibility:hidden}
.cmh{font-size:26px;font-weight:500;color:#6A707B}
.cmt{font-size:37px;font-weight:700;line-height:1.4;letter-spacing:-.5px}
.src{position:absolute;left:84px;right:120px;bottom:440px;line-height:1.4;font-size:24px;color:rgba(255,255,255,.7)}`;
function bgHtml(c) {
  const img = 'file://' + path.join(IMG, c.img);
  return `<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>${css(c, img)}</style></head><body><div class="card">${c.react ? '<div class="blur"></div>' : '<div class="bgimg"></div><div class="fade"></div>'}</div></body></html>`;
}
function txtHtml(c, shown) {
  const img = 'file://' + path.join(IMG, c.img);
  const title = (c.title || []).map(t => `<div>${hl(t)}</div>`).join('');
  const sub = (c.sub || []).map(s => `<div>${hl(s)}</div>`).join('');
  let body;
  if (c.react) {
    const cms = (c.comments || []).map((t, i) => `<div class="cm ${i < shown ? '' : 'hide'}"><div class="cmh">익명</div><div class="cmt">${t}</div></div>`).join('');
    body = `<div class="rbox"><div class="handle">${HANDLE}</div><div class="title">${title}</div>${cms}</div>`;
  } else {
    body = `<div class="box"${c.source ? ' style="bottom:560px"' : ''}><div class="handle">${HANDLE}</div>${c.chip ? `<div class="chip">${c.chip}</div>` : ''}${c.pre ? `<div class="pre">${c.pre}</div>` : ''}<div class="title">${title}</div>${sub ? `<div class="sub">${sub}</div>` : ''}</div>${c.source ? `<div class="src">${c.source}</div>` : ''}`;
  }
  return `<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>${css(c, img)}</style></head><body><div class="card">${body}</div></body></html>`;
}
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  const shot = async (html, file, transparent) => {
    const f = path.join(OUT, file.replace('.png', '.html')); fs.writeFileSync(f, html);
    await page.goto('file://' + f); await page.evaluate(() => document.fonts.ready);
    const wraps = await page.evaluate(() => [...document.querySelectorAll('.title div,.sub div,.pre,.cmt,.src')].filter(e => e.getBoundingClientRect().height > parseFloat(getComputedStyle(e).lineHeight) * 1.5).map(e => e.innerText));
    if (wraps.length) console.log(file, '줄바뀜:', wraps.join(' / '));
    await page.screenshot({ path: path.join(OUT, file), omitBackground: transparent });
  };
  for (let i = 0; i < spec.cards.length; i++) {
    const c = spec.cards[i], n = i + 1;
    await shot(bgHtml(c), `${n}_bg.png`, false);
    if (c.react) { for (let k = 0; k <= (c.comments || []).length; k++) await shot(txtHtml(c, k), `${n}_txt${k}.png`, true); }
    else await shot(txtHtml(c, 0), `${n}_txt.png`, true);
  }
  await browser.close(); console.log('done');
})();
