// Bangun preview HTML terang & gelap untuk tiap varian. Tidak memakai browser.
//
// Dependensi dev (tidak masuk ke profilmu), pasang sekali di folder mana pun:
//   npm i --no-save marked@12 github-markdown-css@5
// Pemakaian dari akar repo:
//   PREVIEW_DEPS=/folder/tempat/node_modules/..  node scripts/buat-preview.mjs
// (PREVIEW_DEPS = folder yang berisi node_modules; bawaan: folder kerja saat ini)
//
// Catatan: github-markdown-css (MIT, (c) Sindre Sorhus) disematkan ke HTML preview saja.
import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const deps = resolve(process.env.PREVIEW_DEPS ?? process.cwd());
const req = createRequire(resolve(deps, 'noop.js'));
const { marked } = req('marked');
const css = (n) => readFileSync(req.resolve(`github-markdown-css/github-markdown-${n}.css`), 'utf8');

const THEMES = [['light', '#ffffff', '#1f2328', '#d0d7de'], ['dark', '#0d1117', '#e6edf3', '#30363d']];

// varian: sumber README, folder aset relatif dari preview/, nama berkas keluaran
const VARIANTS = [
  { src: 'template/README.md', assets: '../template/assets/', out: (t) => `preview-${t}.html`, label: 'Varian dasar (terminal)' },
  { src: 'galaxy/README.md', assets: '../galaxy/assets/', out: (t) => `preview-galaxy-${t}.html`, label: 'Varian galaxy', extra: 'galaxy' },
];

const PINE_BLOCK = (assets, theme) => `
<hr>
<p><strong>Hanya di preview:</strong> pilihan pohon. <code>tree.style</code> = <code>"sakura"</code> (kiri) atau <code>"pine"</code> (kanan).</p>
<p><img src="${assets}tree-sakura-${theme}.svg" alt="Opsi pohon sakura" width="48%"> <img src="${assets}tree-pine-${theme}.svg" alt="Opsi pohon pine" width="48%"></p>`;

// Meniru <picture> + prefers-color-scheme: pilih sumber sesuai tema yang sedang dipreview,
// persis seperti yang dilakukan browser/GitHub. <picture> tanpa <source> dark memakai <img> apa adanya.
const resolvePictures = (html, theme) =>
  html.replace(/<picture>([\s\S]*?)<\/picture>/g, (_m, inner) => {
    const dark = /<source[^>]*prefers-color-scheme:\s*dark[^>]*srcset="([^"]+)"/.exec(inner)?.[1];
    let img = /<img[^>]*>/.exec(inner)?.[0] ?? '';
    if (theme === 'dark' && dark) img = img.replace(/\ssrc="[^"]*"/, ` src="${dark}"`);
    return img;
  });

for (const v of VARIANTS) {
  const body = marked.parse(readFileSync(resolve(root, v.src), 'utf8'), { gfm: true });
  for (const [theme, page, fg, line] of THEMES) {
    let html = body;
    html = resolvePictures(html, theme);
    html = html.replaceAll('src="assets/', `src="${v.assets}`);
    if (v.extra === 'galaxy') html += PINE_BLOCK(v.assets, theme);
    const page_html = `<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Preview ${v.label} — ${theme}</title>
<style>/* github-markdown-css, MIT, (c) Sindre Sorhus */
${css(theme)}
body{margin:0;background:${page};color:${fg}}
.wrap{max-width:896px;margin:0 auto;padding:32px 16px}
.markdown-body{box-sizing:border-box;padding:32px;border:1px solid ${line};border-radius:6px;background:${page}}
@media(max-width:600px){.markdown-body{padding:16px}}
</style></head><body><div class="wrap"><article class="markdown-body">${html}</article></div></body></html>`;
    writeFileSync(resolve(root, 'preview', v.out(theme)), page_html);
    console.log('tulis preview/' + v.out(theme));
  }
}

// Halaman preview animasi: SVG animasi (docs/previews) di halaman bergaya GitHub, terang dan gelap.
for (const [theme, page, fg, line] of THEMES) {
  const html = `<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Preview animasi — ${theme}</title>
<style>/* github-markdown-css, MIT, (c) Sindre Sorhus */
${css(theme)}
body{margin:0;background:${page};color:${fg}}
.wrap{max-width:896px;margin:0 auto;padding:32px 16px}
.markdown-body{box-sizing:border-box;padding:32px;border:1px solid ${line};border-radius:6px;background:${page}}
.markdown-body img{max-width:100%;height:auto}
</style></head><body><div class="wrap"><article class="markdown-body">
<h2>Preview varian galaxy (animasi, data demo)</h2>
<p><img src="../docs/previews/galaxy-animated-${theme}.svg" alt="Preview animasi varian galaxy"></p>
<p>Gambar dimuat lewat <code>&lt;img&gt;</code>, sama seperti di README GitHub. Animasi hanya CSS dan berhenti bila sistem meminta gerak minimal.</p>
</article></div></body></html>`;
  writeFileSync(resolve(root, 'preview', `preview-animated-${theme}.html`), html);
  console.log('tulis preview/preview-animated-' + theme + '.html');
}
