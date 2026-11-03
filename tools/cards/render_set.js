// 카드뉴스 세트 렌더러: node render_set.js <spec.json>
// 사진 꽉 + 아래 어두운 그라데이션 + 흰 글씨 / 반응 장은 흐린 사진 + 흰 말풍선
const path = require('path');
const fs = require('fs');
const { chromium } = require('playwright');

const spec = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const base = path.dirname(path.resolve(process.argv[2]));   // spec 파일 기준 상대경로
const IMG = path.resolve(base, spec.imgDir);
const OUT = path.resolve(base, spec.outDir);
fs.mkdirSync(OUT, { recursive: true });
const ACC = spec.accent || '#FF6A3D';
const HANDLE = spec.handle || '@timeisgold_issue';

const hl = t => t.replace(/<b>/g, `<span style="color:${ACC}">`).replace(/<\/b>/g, '</span>');

function html(c) {
  const img = 'file://' + path.join(IMG, c.img);
  const title = (c.title || []).map(t => `<div>${hl(t)}</div>`).join('');
  const sub = (c.sub || []).map(s => `<div>${hl(s)}</div>`).join('');
  const comments = (c.comments || []).map(t => `<div class="cm"><div class="cmh">익명</div><div class="cmt">${t}</div></div>`).join('');
  const body = c.react
    ? `<div class="blur"></div>
       <div class="rbox"><div class="handle">${HANDLE}</div><div class="title">${title}</div>${comments}</div>`
    : `<div class="fade"></div>
       <div class="box">
         <div class="handle">${HANDLE}</div>
         ${c.chip ? `<div class="chip">${c.chip}</div>` : ''}
         ${c.pre ? `<div class="pre">${c.pre}</div>` : ''}
         <div class="title">${title}</div>
         ${sub ? `<div class="sub">${sub}</div>` : ''}
       </div>`;
  return `<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>
  body{margin:0}
  .card{width:1080px;height:1350px;position:relative;overflow:hidden;font-family:'Noto Sans CJK KR',sans-serif;color:#fff;
    background:#000 url('${img}') ${c.pos || '50% 50%'}/${c.size || 'cover'} no-repeat}
  .fade{position:absolute;left:0;right:0;bottom:0;height:${c.fade || 820}px;
    background:linear-gradient(to bottom,rgba(0,0,0,0) 0%,rgba(0,0,0,.72) 38%,rgba(0,0,0,.9) 100%)}
  .box{position:absolute;left:84px;right:84px;bottom:110px;display:flex;flex-direction:column;align-items:flex-start;gap:26px}
  .handle{font-size:28px;font-weight:500;color:rgba(255,255,255,.85)}
  .chip{background:${ACC};font-size:34px;font-weight:700;padding:8px 22px;border-radius:6px}
  .pre{font-size:36px;font-weight:500;color:#E9EAEE;line-height:1.45}
  .title{font-size:${c.titleSize || 88}px;font-weight:900;line-height:1.2;letter-spacing:-2px}
  .sub{font-size:36px;font-weight:500;color:#E9EAEE;line-height:1.55;letter-spacing:-.5px}
  .blur{position:absolute;inset:-40px;background:url('${img}') ${c.pos || '50% 50%'}/cover;filter:blur(18px) brightness(.45)}
  .rbox{position:absolute;left:84px;right:84px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;gap:30px}
  .cm{background:#fff;color:#111318;border-radius:22px;padding:26px 34px;display:flex;flex-direction:column;gap:8px}
  .cmh{font-size:26px;font-weight:500;color:#6A707B}
  .cmt{font-size:40px;font-weight:700;line-height:1.4;letter-spacing:-.5px}
  .foot{position:absolute;left:84px;right:84px;bottom:48px;display:flex;justify-content:space-between;gap:24px;font-size:24px;color:rgba(255,255,255,.7)}
  </style></head><body><div class="card">${body}
  <div class="foot"><div>${c.source || ''}</div><div style="white-space:nowrap">${c.cue ? '넘겨보기 →' : ''}</div></div>
  </div></body></html>`;
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1350 } });
  for (const c of spec.cards) {
    const f = path.join(OUT, c.file.replace('.png', '.html'));
    fs.writeFileSync(f, html(c));
    await page.goto('file://' + f);
    await page.evaluate(() => document.fonts.ready);
    const issues = await page.evaluate(() => {
      const bad = [];
      document.querySelectorAll('.title div, .sub div, .pre, .handle, .foot div').forEach(el => {
        const r = el.getBoundingClientRect();
        const lh = parseFloat(getComputedStyle(el).lineHeight) || parseFloat(getComputedStyle(el).fontSize) * 1.3;
        if (r.height > lh * 1.5) bad.push('줄바뀜: ' + el.textContent.slice(0, 20));
        if (r.right > 1080 - 60 || r.top < 0) bad.push('넘침: ' + el.textContent.slice(0, 20));
      });
      const box = document.querySelector('.box, .rbox');
      if (box) { const b = box.getBoundingClientRect(); if (b.top < 60) bad.push('글이 너무 위까지 올라감 top=' + Math.round(b.top)); }
      return bad;
    });
    await page.screenshot({ path: path.join(OUT, c.file) });
    console.log(c.file, issues.length ? issues.join(' | ') : 'ok');
  }
  await browser.close();
})();
