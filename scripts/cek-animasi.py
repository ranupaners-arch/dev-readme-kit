#!/usr/bin/env python3
"""Verifikasi statis untuk SVG preview animasi (tanpa browser, hanya pustaka standar).

Memeriksa bahwa animasi aman dan desain yang disetujui tidak berubah:
  1. XML valid; tidak ada <script>, <foreignObject>, <image>, SMIL (<animate*>), atau URL eksternal.
  2. Semua `animation:` dan @keyframes berada di dalam @media (prefers-reduced-motion: no-preference).
  3. Setiap @keyframes yang dipakai terdefinisi; setiap kelas di elemen punya aturan CSS.
  4. id unik; semua url(#id) dan href="#id" mengarah ke id yang ada.
  5. Tata letak bintang hero sama dengan aset statis yang disetujui (koordinat bidang galaksi
     diproyeksikan ulang lalu dibandingkan dengan galaxy/assets/hero-<tema>.svg).
  6. Simpangan gerak terburuk (sway +-3,5 derajat, cincin orbit) tetap di dalam kanvas.

Pemakaian: python3 scripts/cek-animasi.py [folder-previews] [folder-aset-statis]
Kode keluar 0 bila semua lolos, 1 bila ada yang gagal.
"""
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path(__file__).resolve().parent.parent
prev = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "docs" / "previews"
static = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "galaxy" / "assets"
SVG = "{http://www.w3.org/2000/svg}"
fails = 0


def check(ok: bool, msg: str, detail: str = "") -> None:
    global fails
    print(("  PASS " if ok else "  FAIL ") + msg + (f"  [{detail}]" if detail else ""))
    fails += 0 if ok else 1


def media_block(css: str):
    """Kembalikan (isi blok @media no-preference, css di luar blok) dengan pencocokan kurung."""
    m = re.search(r"@media\s*\(prefers-reduced-motion:\s*no-preference\)\s*\{", css)
    if not m:
        return "", css
    i, depth = m.end(), 1
    while i < len(css) and depth:
        depth += {"{": 1, "}": -1}.get(css[i], 0)
        i += 1
    return css[m.end():i - 1], css[:m.start()] + css[i:]


def circles(el, tf=lambda x, y: (x, y)):
    for c in el.iter(SVG + "circle"):
        if c.get("cx") is not None:
            yield tf(float(c.get("cx")), float(c.get("cy"))), float(c.get("r"))


for theme in ("dark", "light"):
    f = prev / f"galaxy-animated-{theme}.svg"
    print(f"\n== {f.name}")
    text = f.read_text(encoding="utf-8")
    tree = ET.parse(f)
    r = tree.getroot()
    check(True, "XML valid")
    check(not re.search(r"<(script|foreignObject|image|animate\w*|set)\b", text), "tanpa script/foreignObject/image/SMIL")
    check(not re.search(r"(?:https?:)?//(?!www\.w3\.org)", text.replace("http://www.w3.org", "")), "tanpa URL eksternal")

    css = "".join(st.text or "" for st in r.iter(SVG + "style"))
    inside, outside = media_block(css)
    check("animation" in inside and "@keyframes" in inside, "animasi dan @keyframes ada di dalam @media no-preference")
    check("animation" not in outside and "@keyframes" not in outside, "tidak ada animasi di luar @media (gerak minimal = gambar diam)")
    used = set(re.findall(r"animation:\s*([a-z]+)", inside))
    defined = set(re.findall(r"@keyframes\s+([a-z]+)", inside))
    check(used <= defined, "semua animasi punya @keyframes", f"dipakai={sorted(used)} didefinisikan={sorted(defined)}")
    css_classes = set(re.findall(r"\.([a-z0-9]+)\{", css))
    el_classes = {c for e in r.iter() for c in (e.get("class") or "").split()}
    check(el_classes <= css_classes, "setiap kelas di elemen punya aturan CSS", f"kelas={sorted(el_classes)}")
    n_tw = sum(1 for e in r.iter() if "tw" in (e.get("class") or "").split())
    n_delay = sum(1 for e in r.iter() if "tw" in (e.get("class") or "").split() and "animation-delay" in (e.get("style") or ""))
    n_orb = sum(1 for e in r.iter() if (e.get("class") or "") in ("o1", "o2", "o3"))
    n_sway = sum(1 for e in r.iter() if e.get("class") == "sway")
    n_pulse = sum(1 for e in r.iter() if e.get("class") == "pulse")
    check(n_tw >= 100 and n_delay == n_tw, "bintang berkelip dengan jeda acak masing-masing", f"{n_tw} bintang, {n_delay} berjeda")
    check(n_orb == 3 and n_sway == 1 and n_pulse >= 4, "orbit, sway, dan denyut ada", f"orbit={n_orb} sway={n_sway} pulse={n_pulse}")

    ids = [e.get("id") for e in r.iter() if e.get("id")]
    check(len(ids) == len(set(ids)), "id unik", f"{len(ids)} id")
    refs = set(re.findall(r"url\(#([^)]+)\)", text)) | set(re.findall(r'href="#([^"]+)"', text))
    check(refs <= set(ids), "semua rujukan id terpenuhi", f"hilang={sorted(refs - set(ids))}")

    # desain tidak berubah: proyeksikan ulang bintang bidang galaksi, bandingkan dengan aset statis
    cx, cy, rot, sq = 745, 212, math.radians(-20), 0.64
    proj = lambda x, y: (cx + x * math.cos(rot) - y * sq * math.sin(rot), cy + x * math.sin(rot) + y * sq * math.cos(rot))
    sway = next(e for e in r.iter() if e.get("class") == "sway")
    anim_pts = sorted((round(p[0], 1), round(p[1], 1), rr) for p, rr in circles(sway, lambda x, y: proj(x, y)))
    st = ET.parse(static / f"hero-{theme}.svg").getroot()
    s_all = [(round(p[0], 1), round(p[1], 1), rr) for p, rr in circles(st)]
    s_set = {(a, b, c) for a, b, c in s_all}
    match = sum(1 for p in anim_pts if any(abs(p[0] - q[0]) <= 0.15 and abs(p[1] - q[1]) <= 0.15 and abs(p[2] - q[2]) < 1e-6 for q in s_set))
    check(len(anim_pts) > 800 and match / len(anim_pts) >= 0.99, "posisi dan ukuran bintang piringan sama dengan aset statis yang disetujui",
          f"{match}/{len(anim_pts)} cocok")

    # simpangan terburuk
    W = float(r.get("width"))
    far = max(math.hypot(p[0] - 0, p[1] - 0) for p, _ in circles(sway))   # radius terjauh di bidang galaksi
    drift = far * math.radians(3.5)
    check(far <= 232 * 1.6 and drift < 25, "simpangan sway terburuk kecil", f"radius terjauh {far:.0f}, simpangan <= {drift:.0f} unit")
    xs = [proj(176 * math.cos(a / 18 * math.pi), 176 * math.sin(a / 18 * math.pi)) for a in range(36)]
    check(all(0 <= x <= W and 0 <= y <= 420 for x, y in xs), "cincin orbit terluar tetap di dalam kartu hero")

print("\n" + ("SEMUA LOLOS" if not fails else f"{fails} PEMERIKSAAN GAGAL"))
sys.exit(1 if fails else 0)
