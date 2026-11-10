#!/usr/bin/env python3
"""Buat header terminal (SVG terang + gelap) untuk README profil GitHub.

Hanya memakai pustaka standar Python 3.8+. Tanpa font eksternal, tanpa gambar,
tanpa skrip di dalam SVG, sehingga aman dirender GitHub lewat <img>.

Pemakaian:
    python3 scripts/buat-header.py                  # tulis ke template/assets/
    python3 scripts/buat-header.py --out folder/    # tulis ke folder lain

Ubah nilai pada KONTEN di bawah, lalu jalankan ulang skrip ini.
Teks bertanda ‹...› adalah data contoh yang HARUS diganti.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from xml.sax.saxutils import escape

# --- KONTEN (GANTI) ---------------------------------------------------------
KONTEN = {
    "judul_jendela": "‹nama-kamu› — zsh",
    "user": "‹nama-kamu›",
    "host": "dev",
    "nama": "‹Nama Kamu›",
    "peran": "‹peran singkat, mis. backend developer›",
    "fokus": "‹fokus 1› · ‹fokus 2› · ‹fokus 3›",
    "status": "‹status singkat, mis. sedang belajar Rust›",
    "alt": "Header terminal: perkenalan singkat",
}
# ---------------------------------------------------------------------------

# Warna mengikuti palet netral GitHub (kontras teks >= 4.5:1 pada latar jendela).
TEMA = {
    "light": {
        "halaman": "#f6f8fa", "jendela": "#ffffff", "garis": "#d0d7de",
        "bar": "#f6f8fa", "teks": "#1f2328", "redup": "#59636e",
        "prompt": "#1a7f37", "aksen": "#0969da",
        "dot": ("#ff5f57", "#febc2e", "#28c840"),
    },
    "dark": {
        "halaman": "#0d1117", "jendela": "#161b22", "garis": "#30363d",
        "bar": "#1c2128", "teks": "#e6edf3", "redup": "#8b949e",
        "prompt": "#3fb950", "aksen": "#58a6ff",
        "dot": ("#ff5f57", "#febc2e", "#28c840"),
    },
}

LEBAR, TINGGI = 880, 292
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"


def baris_prompt(y: int, k: dict, perintah: str) -> str:
    return (
        f'<text x="36" y="{y}" xml:space="preserve">'
        f'<tspan class="p">{escape(k["user"])}@{escape(k["host"])}</tspan>'
        f'<tspan class="m">:~$ </tspan>'
        f'<tspan class="t">{escape(perintah)}</tspan></text>'
    )


def baris_keluaran(y: int, isi: str, kelas: str = "t") -> str:
    return f'<text x="36" y="{y}" xml:space="preserve" class="{kelas}">{escape(isi)}</text>'


def bangun(nama_tema: str, k: dict) -> str:
    c = TEMA[nama_tema]
    d1, d2, d3 = c["dot"]
    y0, step = 92, 30
    isi = [
        baris_prompt(y0, k, "whoami"),
        f'<text x="36" y="{y0 + step}" xml:space="preserve">'
        f'<tspan class="a" font-weight="700">{escape(k["nama"])}</tspan>'
        f'<tspan class="m"> — </tspan><tspan class="t">{escape(k["peran"])}</tspan></text>',
        baris_prompt(y0 + step * 2 + 6, k, "cat fokus.txt"),
        baris_keluaran(y0 + step * 3 + 6, k["fokus"]),
        baris_prompt(y0 + step * 4 + 12, k, "echo $STATUS"),
        baris_keluaran(y0 + step * 5 + 12, k["status"]),
        f'<text x="36" y="{y0 + step * 6 + 18}" xml:space="preserve">'
        f'<tspan class="p">{escape(k["user"])}@{escape(k["host"])}</tspan>'
        f'<tspan class="m">:~$ </tspan>'
        f'<tspan class="kursor">▌</tspan></text>',
    ]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{LEBAR}" height="{TINGGI}" viewBox="0 0 {LEBAR} {TINGGI}" role="img" aria-labelledby="t d">
  <title id="t">{escape(k["alt"])}</title>
  <desc id="d">{escape(k["nama"])}, {escape(k["peran"])}. Fokus: {escape(k["fokus"])}. Status: {escape(k["status"])}.</desc>
  <!-- GANTI: teks di bawah dibuat oleh scripts/buat-header.py. Ubah KONTEN di skrip itu, jangan edit manual. -->
  <style>
    text {{ font-family: {FONT}; font-size: 16px; }}
    .t {{ fill: {c["teks"]}; }}
    .m {{ fill: {c["redup"]}; }}
    .p {{ fill: {c["prompt"]}; font-weight: 700; }}
    .a {{ fill: {c["aksen"]}; }}
    .judul {{ font-size: 13px; fill: {c["redup"]}; }}
    .kursor {{ fill: {c["aksen"]}; }}
    @media (prefers-reduced-motion: no-preference) {{
      .kursor {{ animation: kedip 1.2s steps(1) infinite; }}
      @keyframes kedip {{ 50% {{ opacity: 0; }} }}
    }}
  </style>
  <rect width="{LEBAR}" height="{TINGGI}" rx="12" fill="{c["halaman"]}"/>
  <rect x="8.5" y="8.5" width="{LEBAR - 17}" height="{TINGGI - 17}" rx="10" fill="{c["jendela"]}" stroke="{c["garis"]}"/>
  <path d="M9 44V19a10 10 0 0 1 10-10h{LEBAR - 38}a10 10 0 0 1 10 10v25z" fill="{c["bar"]}"/>
  <line x1="9" y1="44.5" x2="{LEBAR - 9}" y2="44.5" stroke="{c["garis"]}"/>
  <circle cx="34" cy="27" r="6" fill="{d1}"/>
  <circle cx="56" cy="27" r="6" fill="{d2}"/>
  <circle cx="78" cy="27" r="6" fill="{d3}"/>
  <text x="{LEBAR // 2}" y="32" text-anchor="middle" class="judul">{escape(k["judul_jendela"])}</text>
  {chr(10).join("  " + b for b in isi).strip()}
</svg>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "template" / "assets"))
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    for nama in TEMA:
        f = out / f"header-{nama}.svg"
        f.write_text(bangun(nama, KONTEN), encoding="utf-8")
        print("tulis", f)


if __name__ == "__main__":
    main()
