// Build the presentation from the files in slides/.
//
// To prepare the tools once, do these steps in this folder:
//   1. npm install --no-save playwright
//   2. npx playwright install chromium
//
// The command "node build.js" writes deck.html, deck.pdf and one preview image for each slide.
// The command "node build.js 07 12" writes only the preview images of slides 07 and 12.
//
// Each file in slides/ has one section of the class "slide". The order of the files gives the page number.
// If the variable CHROME_PATH is set, the script uses this Chromium. Otherwise it uses the Chromium of Playwright.
//
// The full build also writes layout.json. This file has the position, the color and the font of each box, image and text.
// The script make_pptx.py makes deck.pptx from layout.json.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const dir = __dirname;
const only = process.argv.slice(2);
const files = fs.readdirSync(path.join(dir, 'slides')).filter((f) => f.endsWith('.html')).sort();

const sections = files.map((f, i) => {
  const html = fs.readFileSync(path.join(dir, 'slides', f), 'utf8');
  const pn = i === 0 ? '' : `<div class="pn">${i + 1}</div>`;
  return html.replace(/<\/section>\s*$/, `${pn}</section>`);
});

const page = `<!doctype html><html lang="pl"><head><meta charset="utf-8"><title>KIOsk</title>
<link rel="stylesheet" href="theme.css"></head><body>
${sections.join('\n')}
</body></html>`;
fs.writeFileSync(path.join(dir, 'deck.html'), page);

(async () => {
  const b = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {});
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  await p.goto('file://' + path.join(dir, 'deck.html'));
  await p.waitForLoadState('networkidle');
  await p.evaluate(() => document.fonts.ready);
  fs.mkdirSync(path.join(dir, 'preview'), { recursive: true });
  const slides = await p.$$('.slide');
  for (let i = 0; i < slides.length; i++) {
    const nn = String(i + 1).padStart(2, '0');
    if (only.length && !only.includes(nn)) continue;
    await slides[i].screenshot({ path: path.join(dir, 'preview', `${nn}.png`) });
  }
  if (!only.length) {
    await p.pdf({ path: path.join(dir, 'deck.pdf'), width: '1920px', height: '1080px', printBackground: true });
    fs.writeFileSync(path.join(dir, 'layout.json'), JSON.stringify(await p.evaluate(extractLayout)));
  }
  await b.close();
  console.log(only.length ? `preview: ${only.join(', ')}` : `deck.pdf: ${slides.length} slides`);
})();

// Runs in the page. It returns one list of items for each slide, in the order of drawing.
function extractLayout() {
  const num = (v) => parseFloat(v) || 0;
  const color = (c) => {
    const m = c && c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(',').map(parseFloat);
    const a = p.length > 3 ? p[3] : 1;
    return a === 0 ? null : { r: p[0], g: p[1], b: p[2], a };
  };
  const angleOf = (el) => {
    let a = 0;
    for (let e = el; e && !e.classList.contains('slide'); e = e.parentElement) {
      const m = getComputedStyle(e).transform.match(/matrix\(([^)]+)\)/);
      if (m) { const v = m[1].split(',').map(Number); a += Math.atan2(v[1], v[0]) * 180 / Math.PI; }
    }
    return a;
  };
  const radiusOf = (cs, w, h) => {
    const r = cs.borderTopLeftRadius;
    return r.endsWith('%') ? (num(r) / 100) * Math.min(w, h) : num(r);
  };
  const inter = (a, b) => {
    const x = Math.max(a.x, b.x), y = Math.max(a.y, b.y);
    const x2 = Math.min(a.x + a.w, b.x + b.w), y2 = Math.min(a.y + a.h, b.y + b.h);
    return { x, y, w: Math.max(0, x2 - x), h: Math.max(0, y2 - y) };
  };
  const slides = [];
  for (const slide of document.querySelectorAll('.slide')) {
    const S = slide.getBoundingClientRect();
    const rel = (r) => ({ x: r.left - S.left, y: r.top - S.top, w: r.width, h: r.height });
    const box = (el) => {
      const r = el.getBoundingClientRect();
      const rot = angleOf(el);
      if (Math.abs(rot) < 0.1) return { ...rel(r), rot: 0 };
      const w = el.offsetWidth, h = el.offsetHeight;
      return { x: r.left - S.left + r.width / 2 - w / 2, y: r.top - S.top + r.height / 2 - h / 2, w, h, rot };
    };
    const items = [];

    const textOf = (el, cs) => {
      // The runs of the inline content of el, with the line breaks of the browser.
      const runs = [];
      const pre = cs.whiteSpace.startsWith('pre');
      let lastBottom = null, firstRect = null, minLeft = Infinity;
      const lh = cs.lineHeight === 'normal' ? num(cs.fontSize) * 1.26 : num(cs.lineHeight);
      const styleOf = (e) => {
        const s = getComputedStyle(e);
        const a = e.closest('a');
        return {
          font: s.fontFamily.split(',')[0].replace(/["']/g, '').trim(),
          size: num(s.fontSize), weight: num(s.fontWeight), italic: s.fontStyle === 'italic',
          color: color(s.color), ls: s.letterSpacing === 'normal' ? 0 : num(s.letterSpacing),
          upper: s.textTransform === 'uppercase', href: a ? a.href : null,
        };
      };
      const push = (t, st) => {
        const last = runs[runs.length - 1];
        if (last && !last.br && JSON.stringify(last.st) === JSON.stringify(st)) last.t += t; else runs.push({ t, st });
      };
      const visit = (node) => {
        for (const c of node.childNodes) {
          if (c.nodeType === 3) {
            const st = styleOf(c.parentElement);
            const parts = pre ? c.textContent.split(/(\n)/) : c.textContent.split(/(\s+)/);
            let off = 0;
            for (const part of parts) {
              const start = off; off += part.length;
              if (!part) continue;
              if (pre && part === '\n') { runs.push({ br: true }); lastBottom = null; continue; }
              if (!pre && /^\s+$/.test(part)) { if (runs.length && !runs[runs.length - 1].br) push(' ', st); continue; }
              const rg = document.createRange(); rg.setStart(c, start); rg.setEnd(c, off);
              const rect = rg.getClientRects()[0];
              if (!rect) continue;
              if (lastBottom !== null && rect.bottom > lastBottom + lh * 0.6) {
                const last = runs[runs.length - 1];
                if (last && !last.br) last.t = last.t.replace(/ $/, '');
                runs.push({ br: true });
              }
              if (lastBottom === null || rect.bottom > lastBottom + lh * 0.6) lastBottom = rect.bottom;
              if (!firstRect) firstRect = rect;
              minLeft = Math.min(minLeft, rect.left);
              push(part, st);
            }
          } else if (c.nodeType === 1) {
            if (c.tagName === 'BR') { runs.push({ br: true }); lastBottom = null; continue; }
            const s = getComputedStyle(c);
            if (s.display === 'inline' && s.visibility !== 'hidden') visit(c);
          }
        }
      };
      visit(el);
      while (runs.length && runs[runs.length - 1].br) runs.pop();
      if (!runs.some((r) => !r.br && r.t.trim())) return null;
      for (const r of runs) if (!r.br && r.st.upper) r.t = r.t.toUpperCase();
      const lines = runs.filter((r) => r.br).length + 1;
      const r = el.getBoundingClientRect();
      const left = r.left + num(cs.paddingLeft) + num(cs.borderLeftWidth) - S.left;
      const width = r.width - num(cs.paddingLeft) - num(cs.paddingRight) - num(cs.borderLeftWidth) - num(cs.borderRightWidth);
      const align = ['center', 'right', 'end'].includes(cs.textAlign) ? (cs.textAlign === 'end' ? 'right' : cs.textAlign) : 'left';
      const top = firstRect.top - S.top - (lh - firstRect.height) / 2;
      const slack = 60;
      const x = align === 'left' ? minLeft - S.left : align === 'center' ? left - slack / 2 : left - slack;
      const b = box(el);
      return { type: 'text', x, y: top, w: width + slack, h: lines * lh, lh, align, runs, rot: b.rot };
    };

    const walk = (el, clips) => {
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden' || num(cs.opacity) === 0) return;
      if (cs.display === 'inline') return;
      const b = box(el);
      const rad = radiusOf(cs, b.w, b.h);
      const rings = [...cs.boxShadow.matchAll(/(rgba?\([^)]+\)) 0px 0px 0px ([\d.]+)px/g)]
        .map((m) => ({ c: color(m[1]), s: num(m[2]) })).sort((p, q) => q.s - p.s);
      for (const g of rings) if (g.c) items.push({ type: 'rect', x: b.x - g.s, y: b.y - g.s, w: b.w + 2 * g.s, h: b.h + 2 * g.s, r: rad + g.s, fill: g.c, rot: b.rot });
      const bg = color(cs.backgroundColor);
      const sides = ['Top', 'Right', 'Bottom', 'Left'].map((s) => ({ s, w: num(cs[`border${s}Width`]), c: color(cs[`border${s}Color`]) }));
      const full = sides.every((s) => s.w > 0 && s.c && s.w === sides[0].w);
      if (bg || full) items.push({ type: 'rect', ...b, r: rad, fill: bg, line: full ? { w: sides[0].w, c: sides[0].c } : null });
      if (!full) {
        for (const s of sides) {
          if (!(s.w > 0 && s.c)) continue;
          const t = s.w;
          const g = s.s === 'Top' ? { x: b.x, y: b.y, w: b.w, h: t } : s.s === 'Bottom' ? { x: b.x, y: b.y + b.h - t, w: b.w, h: t }
            : s.s === 'Left' ? { x: b.x, y: b.y, w: t, h: b.h } : { x: b.x + b.w - t, y: b.y, w: t, h: b.h };
          items.push({ type: 'rect', ...g, r: 0, fill: s.c, rot: 0 });
        }
      }
      if (el.tagName === 'IMG') {
        const nw = el.naturalWidth, nh = el.naturalHeight;
        let drawn = { x: b.x, y: b.y, w: b.w, h: b.h };
        if (cs.objectFit === 'cover') {
          const sc = Math.max(b.w / nw, b.h / nh);
          const pos = cs.objectPosition.split(' ').map((v) => num(v) / 100);
          drawn = { x: b.x + (b.w - nw * sc) * pos[0], y: b.y + (b.h - nh * sc) * pos[1], w: nw * sc, h: nh * sc };
        }
        let vis = inter(drawn, cs.objectFit === 'cover' ? b : drawn);
        let oval = false;
        for (const c of clips) { vis = inter(vis, c.r); if (c.oval) oval = true; }
        if (vis.w > 0 && vis.h > 0) {
          items.push({
            type: 'img', src: el.src, x: vis.x, y: vis.y, w: vis.w, h: vis.h, oval, rot: b.rot,
            crop: { l: (vis.x - drawn.x) / drawn.w, t: (vis.y - drawn.y) / drawn.h, r: (drawn.x + drawn.w - vis.x - vis.w) / drawn.w, b: (drawn.y + drawn.h - vis.y - vis.h) / drawn.h },
          });
        }
        return;
      }
      const t = textOf(el, cs);
      if (t) items.push(t);
      const next = cs.overflow === 'hidden' ? [...clips, { r: { x: b.x, y: b.y, w: b.w, h: b.h }, oval: rad >= Math.min(b.w, b.h) / 2 - 1 }] : clips;
      for (const c of el.children) walk(c, next);
    };
    walk(slide, []);
    slides.push(items);
  }
  return slides;
}
