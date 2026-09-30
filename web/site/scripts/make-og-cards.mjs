// Las tarjetas que se ven al compartir un enlace, una por tipo de página y lengua (30-sep-2026).
//
// El operador: «las tarjetas que aparecen con el enlace me siguen pareciendo bastante pobres.
// Deberían ser más visuales, con letras grandes, iconos, que se muestre de un vistazo qué hace
// esa página. La de herramientas debe ser la más importante, es la que quiero enlazar en
// Twitter». Hasta hoy había UNA tarjeta para las 2.900 páginas: el logo y una frase.
//
// Se pintan con el navegador y no con PIL, como la de antes, por tres razones: las fuentes de
// la web (Nunito, Atkinson, Noto Sans Arabic) y el hindi del sistema salen igual que en la web;
// el árabe se escribe de derecha a izquierda sin hacer nada; y los iconos son los mismos SVG de
// la página de herramientas (src/icons.ts). Los textos, de src/i18n.ts: ni una frase nueva.
//
//   node scripts/make-og-cards.mjs            # las 8 lenguas → public/og/<lang>/<tipo>.jpg
//
// Se genera en el PC (hace falta Chrome) y los PNG se suben con el código; el servidor no los
// dibuja. Base.astro elige la tarjeta por la dirección de la página.
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const RAIZ = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const { t, LANGS, dirFor } = await import(pathToFileURL(join(RAIZ, 'src/i18n.ts')).href);
const { ICON } = await import(pathToFileURL(join(RAIZ, 'src/icons.ts')).href);

const CHROME = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
].find((p) => existsSync(p));
if (!CHROME) throw new Error('hace falta Chrome o Edge para pintar las tarjetas');

// La hoja de fuentes de la web apunta a /fonts/…, que desde un fichero local no lleva a ninguna
// parte: la primera tanda salió con la letra del sistema. Se mete entera con la ruta completa.
const FONTS_CSS = readFileSync(join(RAIZ, 'public/fonts/fonts.css'), 'utf8')
  .replaceAll('url(/fonts/', `url(${pathToFileURL(join(RAIZ, 'public/fonts')).href}/`);
const LOGO = pathToFileURL(join(RAIZ, 'public/logo.png')).href;
const TONE = { mint: '#E3F4EF', sky: '#E6F1FA', lavender: '#EDEAF8', peach: '#FFE8DC', amber: '#FBF0D8', coral: '#FBE3DD' };

// tipo → icono, color, nombre y qué hace (siempre de i18n)
const CARDS = {
  home: { icon: 'chat', tone: 'mint', name: (s) => s.tools.ask, tip: (s) => s.tools.ask_tip },
  emergency: { icon: 'er', tone: 'coral', urgent: true, name: (s) => s.nav_emergency, tip: (s) => s.tools.t_er },
  'warning-signs': { icon: 'signs', tone: 'coral', urgent: true, name: (s) => s.ws_eyebrow, tip: (s) => s.tools.t_signs },
  numbers: { icon: 'phone', tone: 'coral', urgent: true, name: (s) => s.tools.numbers, tip: (s) => s.tools.t_numbers },
  dose: { icon: 'dose', tone: 'mint', name: (s) => s.nav_dose, tip: (s) => s.tools.t_dose },
  growth: { icon: 'growth', tone: 'sky', name: (s) => s.nav_growth, tip: (s) => s.tools.t_growth },
  vaccines: { icon: 'vax', tone: 'lavender', name: (s) => s.nav_vaccines, tip: (s) => s.tools.t_vax },
  muac: { icon: 'muac', tone: 'amber', name: (s) => s.muac.h, tip: (s) => s.tools.t_muac },
  diary: { icon: 'diary', tone: 'peach', name: (s) => s.nav_diary, tip: (s) => s.tools.t_diary },
  family: { icon: 'kids', tone: 'mint', name: (s) => s.fam.h1, tip: (s) => s.tools.t_kids },
  kit: { icon: 'home', tone: 'sky', name: (s) => s.nav_kit, tip: (s) => s.tools.t_home },
  guides: { icon: 'guides', tone: 'lavender', name: (s) => s.nav_guides, tip: (s) => s.tools.t_guides },
  sources: { icon: 'sources', tone: 'peach', name: (s) => s.nav_sources, tip: (s) => s.tools.t_sources },
  about: { icon: 'about', tone: 'mint', name: (s) => s.about.eyebrow, tip: (s) => s.tools.t_about },
};
// el anillo de la tarjeta de herramientas, en el mismo orden que la página
const RING = [['er', 'coral', 1], ['signs', 'coral', 1], ['dose', 'mint'], ['growth', 'sky'], ['vax', 'lavender'],
  ['muac', 'amber'], ['diary', 'peach'], ['kids', 'mint'], ['home', 'sky'], ['phone', 'coral', 1]];
const BENDS = [[0.22, 0.1], [-0.06, 0.12], [0.02, -0.02], [-0.24, -0.08], [0.16, -0.14],
  [-0.1, -0.2], [0.05, 0.25], [-0.18, 0.06], [0.28, 0.04], [-0.03, -0.12]];

const svg = (k, size, stroke = 1.8) =>
  `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="${stroke}" stroke-linecap="round" stroke-linejoin="round">${ICON[k]}</svg>`;
const esc = (x) => String(x).replace(/&/g, '&amp;').replace(/</g, '&lt;');

const CSS = `
  *{box-sizing:border-box;margin:0}
  html,body{width:1200px;height:630px;overflow:hidden}
  body{background:radial-gradient(900px 600px at 18% 30%,#2A5E4E 0%,#1B4538 45%,#122E26 100%);color:#FFF6EA;
    font-family:'Atkinson Hyperlegible','Noto Sans Arabic','Nirmala UI',sans-serif}
  .brand{display:flex;align-items:center;gap:14px;font-family:Nunito,'Noto Sans Arabic','Nirmala UI',sans-serif;
    font-weight:800;font-size:34px;color:#FFF6EA}
  .brand img{width:58px;height:58px}
  .url{font-size:28px;color:#8DD1BE;letter-spacing:.01em}
  h1{font-family:Nunito,'Noto Sans Arabic','Nirmala UI',sans-serif;font-weight:900;line-height:1.02;text-wrap:balance}
  .tip{font-size:36px;line-height:1.3;color:#C8E9E0;text-wrap:pretty}
  .tile{display:grid;place-items:center;border-radius:60px;color:#1F4F40;flex:none}
  .tile.u{color:#CE432D}
`;

function card(lang, s, c) {
  const name = c.name(s), tip = c.tip(s);
  const n = [...name].length;
  const size = n <= 12 ? 104 : n <= 20 ? 88 : n <= 30 ? 74 : 62;
  return `<main style="position:absolute;inset:0;padding:56px 70px;display:flex;flex-direction:column;justify-content:space-between">
    <div class="brand"><img src="${LOGO}" alt="">pedibot</div>
    <div style="display:flex;align-items:center;gap:60px">
      <div class="tile${c.urgent ? ' u' : ''}" style="width:260px;height:260px;background:${TONE[c.tone]}">${svg(c.icon, 150, 1.7)}</div>
      <div style="display:flex;flex-direction:column;gap:22px;min-width:0">
        <h1 style="font-size:${size}px">${esc(name)}</h1>
        <p class="tip">${esc(tip)}</p>
      </div>
    </div>
    <div style="display:flex;justify-content:space-between;align-items:center">
      <span class="url">pedibot.xyz</span>
      ${c.urgent ? `<span style="background:#CE432D;color:#FFF6EA;font-weight:700;font-size:26px;padding:8px 22px;border-radius:999px">${esc(s.tools.legend_u)}</span>` : ''}
    </div>
  </main>`;
}

function toolsCard(lang, s) {
  // el anillo: 560 × 560 a la derecha; cables con la forma de cada uno, como en la página
  const W = 600, H = 560, CX = W / 2, CY = H / 2, RX = 235, RY = 212, n = RING.length;
  const start = -Math.PI / 2 - (Math.PI * 2) / n;
  let paths = '', tiles = '';
  RING.forEach(([k, tone, u], i) => {
    const a = start + (i * Math.PI * 2) / n;
    const x = CX + RX * Math.cos(a), y = CY + RY * Math.sin(a);
    const sx = CX + 88 * Math.cos(a), sy = CY + 88 * Math.sin(a), ex = x - 46 * Math.cos(a), ey = y - 46 * Math.sin(a);
    const [b1, b2] = BENDS[i];
    const dx = ex - sx, dy = ey - sy, len = Math.hypot(dx, dy), nx = -dy / len, ny = dx / len;
    const c1 = [sx + dx * 0.33 + nx * len * b1, sy + dy * 0.33 + ny * len * b1];
    const c2 = [sx + dx * 0.66 + nx * len * b2, sy + dy * 0.66 + ny * len * b2];
    paths += `<path d="M${sx} ${sy} C${c1[0]} ${c1[1]} ${c2[0]} ${c2[1]} ${ex} ${ey}" stroke="${u ? '#E58C7C' : '#6FB8A3'}"/>`;
    tiles += `<div class="tile${u ? ' u' : ''}" style="position:absolute;left:${x - 42}px;top:${y - 42}px;width:84px;height:84px;border-radius:26px;background:${TONE[tone]}">${svg(k, 44)}</div>`;
  });
  return `<main style="position:absolute;inset:0;display:flex;align-items:center;padding:0 40px 0 70px;gap:10px">
    <div style="flex:1;display:flex;flex-direction:column;gap:30px;min-width:0">
      <div class="brand"><img src="${LOGO}" alt="">pedibot</div>
      <h1 style="font-size:80px">${esc(s.tools.h1)}</h1>
      <p class="url" style="font-size:30px">pedibot.xyz/${lang === 'en' ? '' : lang + '/'}tools</p>
    </div>
    <div style="position:relative;width:${W}px;height:${H}px;flex:none">
      <svg width="${W}" height="${H}" style="position:absolute;inset:0" fill="none" stroke-width="3" stroke-linecap="round" stroke-dasharray="2 8">${paths}</svg>
      <div style="position:absolute;left:${CX - 82}px;top:${CY - 82}px;width:164px;height:164px;border-radius:50%;background:#FFF6EA;
        display:grid;place-items:center;box-shadow:0 0 0 12px rgba(200,233,224,.18)"><img src="${LOGO}" alt="" style="width:120px;height:120px"></div>
      ${tiles}
    </div>
  </main>`;
}

const tmp = mkdtempSync(join(tmpdir(), 'pedibot-og-'));
let hechas = 0;
try {
  for (const lang of LANGS) {
    const s = t(lang);
    const tipos = [['tools', () => toolsCard(lang, s)], ...Object.entries(CARDS).map(([k, c]) => [k, () => card(lang, s, c)])];
    for (const [tipo, pinta] of tipos) {
      const html = `<!doctype html><html lang="${lang}" dir="${dirFor(lang)}"><head><meta charset="utf-8">
        <style>${FONTS_CSS}${CSS}</style></head><body>${pinta()}</body></html>`;
      const f = join(tmp, `${lang}-${tipo}.html`);
      writeFileSync(f, html, 'utf8');
      execFileSync(CHROME, ['--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1',
        '--window-size=1200,630', '--virtual-time-budget=3000', `--screenshot=${join(tmp, `${lang}__${tipo}.png`)}`,
        pathToFileURL(f).href], { stdio: 'ignore' });
      hechas++;
    }
  }
  // A JPEG: un degradado en PNG pesaba 300 kB por tarjeta (32 MB las 120). Con calidad 86 no
  // se ve la diferencia y cada una queda en unos 60 kB. Lo hace Python porque ya tiene PIL.
  const py = `
import pathlib, sys
from PIL import Image
tmp, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
for p in tmp.glob("*.png"):
    lang, tipo = p.stem.split("__")
    d = out / lang
    d.mkdir(parents=True, exist_ok=True)
    Image.open(p).convert("RGB").save(d / f"{tipo}.jpg", "JPEG", quality=86, optimize=True, progressive=True)
`;
  writeFileSync(join(tmp, 'a_jpeg.py'), py, 'utf8');
  execFileSync('uv', ['run', '--project', resolve(RAIZ, '../..'), 'python', join(tmp, 'a_jpeg.py'), tmp, join(RAIZ, 'public/og')], { stdio: 'inherit' });
} finally {
  rmSync(tmp, { recursive: true, force: true });
}
console.log(`tarjetas: ${hechas} → public/og/<lang>/<tipo>.jpg`);
