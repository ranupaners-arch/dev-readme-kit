#!/usr/bin/env python3
"""dev-readme-kit · varian galaxy — renderer SVG orisinal (hanya pustaka standar Python 3.8+).

Menghasilkan SVG dalam dua tema (dark dan light) dan memperbarui blok Markdown di README:

    assets/hero-{dark,light}.svg           nama + spiral galaksi dengan label proyek
    assets/constellation-{dark,light}.svg  kalender kontribusi 12 bulan sebagai konstelasi
    assets/tree-{dark,light}.svg           pohon pertumbuhan (sakura atau pine, sesuai config)

Mode data
    --demo   data contoh deterministik, tanpa jaringan, tanpa token (bawaan di repo kit)
    --live   data nyata dari api.github.com; butuh env GITHUB_TOKEN (token bawaan Actions cukup)

Tema (config `appearance`, atau flag --theme)
    auto     tulis kedua tema; README memakai <picture> dengan prefers-color-scheme (bawaan)
    dark     hanya tema dark; README memakai gambar tunggal
    light    hanya tema light; README memakai gambar tunggal

Preview animasi untuk README repo kit (hanya data demo)
    python3 scripts/render.py --preview-svg ../docs/previews
    -> galaxy-animated-{dark,light}.svg: hero + konstelasi + pohon dalam satu gambar, dengan kelip
       bintang dan gerakan orbit halus. Hanya CSS (tanpa JavaScript); semua animasi berada di dalam
       @media (prefers-reduced-motion: no-preference), jadi pengguna yang meminta gerak minimal
       melihat gambar diam.

Pemakaian
    python3 scripts/render.py --demo
    GITHUB_TOKEN=... python3 scripts/render.py --live
    python3 scripts/render.py --check          # cek config siap live, tanpa jaringan

Keluaran deterministik: data yang sama menghasilkan SVG yang sama persis, sehingga
workflow harian hanya membuat commit saat datanya benar-benar berubah.

Seluruh kode ini ditulis dari nol. Tidak ada kode atau aset dari proyek lain.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape as _xesc

API = "https://api.github.com"
UA = "dev-readme-kit-galaxy"
PLACEHOLDERS = ("YOUR NAME", "YOUR-USERNAME", "example.com")

# Palet per tema. Dark: midnight/cyan/amber. Light: kertas bintang (latar pucat, tinta indigo,
# cyan/amber/pink diperdalam supaya kontras di atas latar terang).
THEMES = {
    "dark": {
        "bg2": "#142058", "bg1": "#0A1433", "bg0": "#040A1C", "edge": "",
        "cyan": "#4FD8FF", "cyan_text": "#4FD8FF", "star": "#EAF6FF",
        "amber": "#FFB84D", "amber2": "#FFD99A", "pink": "#FF8FC0",
        "mute": "#9FB3D9", "text": "#F4FAFF", "dim": "#4A5E8F",
        "pill": "#040A1C", "pill_op": 0.78, "badge_fill": "#0A1433", "badge_text": "#FFD99A",
        "core": "#FFFFFF", "core_ring": 0.0,
        "star_k": 1.0, "star_b": 0.0, "halo": 0.12, "dot_op": 0.40, "line_op": 0.30,
        "neb_mid": "#142058", "neb_mid_op": 0.35, "neb_cyan_op": 0.20,
        "moon": "#EAF6FF", "moon_glow": "#4FD8FF", "moon_glow_op": 0.35,
        "hill0": "#101C4A", "hill1": "#040A1C", "crown_op": 0.30,
        "bark0": "#2A2450", "bark1": "#4B3862", "bark2": "#7A5468", "branch": "#5A4170",
        "tier_a": "#0B4A63", "tier_b": "#1BA8C9", "lamp_a": "#4FD8FF", "lamp_b": "#FF8FC0",
        "flower_core": "#FFE2A8",
    },
    "light": {
        "bg2": "#FFFFFF", "bg1": "#EEF4FF", "bg0": "#DCE7FA", "edge": "#C5D3EC",
        "cyan": "#0B7FA8", "cyan_text": "#075F82", "star": "#1F2F66",
        "amber": "#E08A00", "amber2": "#F3B04A", "pink": "#DB3F7C",
        "mute": "#46567C", "text": "#0B1B3F", "dim": "#8190B8",
        "pill": "#FFFFFF", "pill_op": 0.90, "badge_fill": "#FFFFFF", "badge_text": "#8A4B00",
        "core": "#FFF3D1", "core_ring": 0.9,
        "star_k": 0.78, "star_b": 0.22, "halo": 0.10, "dot_op": 0.55, "line_op": 0.40,
        "neb_mid": "#A9C1F2", "neb_mid_op": 0.30, "neb_cyan_op": 0.16,
        "moon": "#FFE7A8", "moon_glow": "#F3B04A", "moon_glow_op": 0.45,
        "hill0": "#BCCDEB", "hill1": "#9DB3DB", "crown_op": 0.24,
        "bark0": "#4A3B6B", "bark1": "#6B4D7E", "bark2": "#9A6482", "branch": "#6B4D7E",
        "tier_a": "#0F6F8F", "tier_b": "#35B7D3", "lamp_a": "#DDF8FF", "lamp_b": "#FFD2E5",
        "flower_core": "#FFF1C9",
    },
}
C: dict = {}


def use_theme(name: str) -> None:
    C.clear()
    C.update(THEMES[name])


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
SANS = 'system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif'
SERIF = 'Georgia,"Times New Roman",serif'


# --------------------------------------------------------------------------- util
def xesc(s) -> str:
    return _xesc(str(s), {'"': "&quot;"})


def num(x: float) -> str:
    s = f"{x:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    return "0" if s == "-0" else s


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(c1: str, c2: str, t: float) -> str:
    a, b, t = _rgb(c1), _rgb(c2), clamp(t, 0, 1)
    return "#%02X%02X%02X" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Rng:
    """PRNG splitmix64: sama di semua platform dan versi Python (tidak memakai `random`)."""

    M = (1 << 64) - 1

    def __init__(self, seed: str):
        self.s = int.from_bytes(hashlib.sha256(seed.encode("utf-8")).digest()[:8], "big")

    def random(self) -> float:
        self.s = (self.s + 0x9E3779B97F4A7C15) & self.M
        z = self.s
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & self.M
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & self.M
        z ^= z >> 31
        return (z >> 11) / float(1 << 53)

    def uniform(self, a: float, b: float) -> float:
        return a + (b - a) * self.random()

    def bell(self) -> float:
        """Mendekati lonceng, rentang [-1, 1]."""
        return (self.random() + self.random() + self.random() - 1.5) / 1.5


def wrap(text: str, maxchars: int):
    lines, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > maxchars:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines or [""]


def overlap(a, b, pad=6) -> bool:
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0] or a[3] + pad <= b[1] or b[3] + pad <= a[1])


# --------------------------------------------------------------------------- config
class ConfigError(Exception):
    pass


def clean(s, maxlen: int, field: str) -> str:
    if not isinstance(s, str):
        raise ConfigError(f"{field}: harus teks")
    s = re.sub(r"[\x00-\x1f\x7f]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        raise ConfigError(f"{field}: tidak boleh kosong")
    return s if len(s) <= maxlen else s[: maxlen - 1].rstrip() + "…"


def safe_url(u, field: str) -> str:
    if not isinstance(u, str) or not re.fullmatch(r"(https?://|mailto:)[^\s<>\"'()]+", u):
        raise ConfigError(f"{field}: URL harus http(s):// atau mailto: tanpa spasi/tanda kutip/kurung")
    return u


def load_config(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ConfigError(f"tidak bisa membaca {path}: {e}")
    env_user = os.environ.get("GALAXY_USER", "").strip()
    user = env_user or raw.get("username", "")
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", user or ""):
        raise ConfigError("username: nama pengguna GitHub tidak valid")
    ident = raw.get("identity", {})
    cfg = {
        "username": user,
        "name": clean(ident.get("name", ""), 48, "identity.name"),
        "role": clean(ident.get("role", ""), 64, "identity.role"),
        "tagline": clean(ident.get("tagline", ""), 110, "identity.tagline"),
        "projects": [],
        "beyond": [clean(x, 24, "beyond[]") for x in raw.get("beyond", [])][:6],
        "connect": [],
        "tree_style": raw.get("tree", {}).get("style", "sakura"),
        "appearance": raw.get("appearance", "auto"),
        "mode": raw.get("data", {}).get("mode", "demo"),
        "demo_end_date": raw.get("data", {}).get("demo_end_date", "2026-10-31"),
    }
    if cfg["tree_style"] not in ("sakura", "pine"):
        raise ConfigError("tree.style harus 'sakura' atau 'pine'")
    if cfg["appearance"] not in ("auto", "dark", "light"):
        raise ConfigError("appearance harus 'auto', 'dark', atau 'light'")
    if cfg["mode"] not in ("demo", "live"):
        raise ConfigError("data.mode harus 'demo' atau 'live'")
    for i, p in enumerate(raw.get("projects", [])[:6]):
        repo = p.get("repo", "")
        if repo and not re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", repo):
            raise ConfigError(f"projects[{i}].repo: format harus pemilik/nama-repo")
        title = clean(p.get("title", ""), 40, f"projects[{i}].title")
        cfg["projects"].append({
            "title": title,
            "label": clean(p.get("label", title), 28, f"projects[{i}].label"),
            "repo": repo,
            "url": safe_url(p["url"], f"projects[{i}].url") if p.get("url") else (f"https://github.com/{repo}" if repo else ""),
            "description": clean(p.get("description", ""), 120, f"projects[{i}].description"),
        })
    for i, c in enumerate(raw.get("connect", [])[:6]):
        cfg["connect"].append({
            "label": clean(c.get("label", ""), 24, f"connect[{i}].label"),
            "url": safe_url(c.get("url", ""), f"connect[{i}].url"),
        })
    return cfg


def check_live_ready(cfg: dict) -> list:
    """Kembalikan daftar masalah bila config masih berisi data contoh."""
    flat = json.dumps(cfg, ensure_ascii=False)
    return [p for p in PLACEHOLDERS if p in flat]


# --------------------------------------------------------------------------- data
@dataclass
class Data:
    days: list           # [(date, count)] naik, tanpa celah
    stars_total: int
    repo_stars: dict     # "pemilik/repo" -> bintang
    demo: bool


def demo_data(cfg: dict) -> Data:
    end = dt.date.fromisoformat(cfg["demo_end_date"])
    n = 365
    start = end - dt.timedelta(days=n - 1)
    rng = Rng("dev-readme-kit/galaxy/demo")
    days = []
    for i in range(n):
        d = start + dt.timedelta(days=i)
        phase = 0.55 + 0.35 * math.sin(i / 365 * 2 * math.pi * 2.1 + 0.8) + 0.10 * math.sin(i / 9)
        p = clamp(phase * 0.85 * (0.35 if d.weekday() >= 5 else 1.0), 0.05, 0.9)
        if (i // 17) % 7 == 5:   # jeda panjang, supaya konstelasi punya celah
            p *= 0.1
        r1, r2 = rng.random(), rng.random()
        count = (1 + int(r2 ** 2.2 * 14 * phase)) if r1 < p else 0
        days.append((d, count))
    stars = {p["repo"]: v for p, v in zip(cfg["projects"], (48, 27, 12)) if p["repo"]}
    return Data(days, 87, stars, True)


def _request(url: str, token: str, payload=None):
    if not url.startswith(API + "/"):
        raise RuntimeError("URL di luar api.github.com ditolak")
    headers = {"User-Agent": UA, "Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}"}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub API {e.code} untuk {url.replace(API, '')}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"gagal terhubung ke GitHub: {e.reason}") from None


def live_data(cfg: dict, token: str) -> Data:
    end = dt.datetime.now(dt.timezone.utc).date()
    start = end - dt.timedelta(days=364)
    query = """query($login:String!,$from:DateTime!,$to:DateTime!){
      user(login:$login){
        contributionsCollection(from:$from,to:$to){contributionCalendar{weeks{contributionDays{date contributionCount}}}}
        repositories(first:100,privacy:PUBLIC,ownerAffiliations:OWNER,isFork:false){nodes{nameWithOwner stargazerCount}}
      }}"""
    res = _request(f"{API}/graphql", token, {"query": query, "variables": {
        "login": cfg["username"], "from": f"{start}T00:00:00Z", "to": f"{end}T23:59:59Z"}})
    if res.get("errors") or not (res.get("data") or {}).get("user"):
        msg = "; ".join(e.get("message", "?") for e in res.get("errors", [])) or "pengguna tidak ditemukan"
        raise RuntimeError(f"GraphQL: {msg}")
    user = res["data"]["user"]
    counts = {}
    for w in user["contributionsCollection"]["contributionCalendar"]["weeks"]:
        for d in w["contributionDays"]:
            counts[dt.date.fromisoformat(d["date"])] = int(d["contributionCount"])
    days = [(start + dt.timedelta(days=i), counts.get(start + dt.timedelta(days=i), 0)) for i in range(365)]
    nodes = user["repositories"]["nodes"]
    by_repo = {n["nameWithOwner"].lower(): int(n["stargazerCount"]) for n in nodes}
    stars = {}
    for p in cfg["projects"]:
        if not p["repo"]:
            continue
        key = p["repo"].lower()
        if key in by_repo:
            stars[p["repo"]] = by_repo[key]
        else:
            try:
                stars[p["repo"]] = int(_request(f"{API}/repos/{p['repo']}", token).get("stargazers_count", 0))
            except RuntimeError as e:
                print(f"peringatan: {e}; bintang {p['repo']} dianggap 0", file=sys.stderr)
                stars[p["repo"]] = 0
    return Data(days, sum(by_repo.values()), stars, False)


def month_buckets(data: Data, k: int = 12):
    """Bagi jendela data jadi k irisan sama rata. Kembalikan [(total_kontribusi, hari_aktif)]."""
    n = len(data.days)
    out = [[0, 0] for _ in range(k)]
    for i, (_, c) in enumerate(data.days):
        b = min(k - 1, i * k // n)
        out[b][0] += c
        out[b][1] += 1 if c > 0 else 0
    return [tuple(x) for x in out]


def nstars_to_count(stars_total: int, cap: int = 12) -> int:
    return int(clamp(round(2.5 * math.log10(1 + max(0, stars_total))), 0, cap))


# --------------------------------------------------------------------------- svg umum
STYLE = (
    f"text{{font-family:{SANS}}}.serif{{font-family:{SERIF};font-style:italic}}"
    "@media (prefers-reduced-motion:no-preference){"
    ".tw{animation:tw 4s ease-in-out infinite}.tw2{animation-duration:5.5s;animation-delay:-1.3s}"
    ".tw3{animation-duration:3.3s;animation-delay:-2.2s}"
    "@keyframes tw{0%,100%{opacity:.25}50%{opacity:1}}}"
)

# Mode animasi (hanya dipakai --preview-svg). rng terpisah agar tata letak bintang tidak berubah
# dibanding aset statis yang sudah disetujui.
ANIM = {"on": False, "rng": None}

STYLE_ANIM = (
    f"text{{font-family:{SANS}}}.serif{{font-family:{SERIF};font-style:italic}}"
    "@media (prefers-reduced-motion:no-preference){"
    ".tw{animation:tw 4s ease-in-out infinite}.tw2{animation-duration:5.5s}.tw3{animation-duration:3.3s}.tw4{animation-duration:7.2s}"
    "@keyframes tw{0%,100%{opacity:.2}50%{opacity:1}}"
    ".sway{animation:sway 28s ease-in-out infinite}"
    "@keyframes sway{0%,100%{transform:rotate(-3.5deg)}50%{transform:rotate(3.5deg)}}"
    ".o1{animation:spin 18s linear infinite}.o2{animation:spin 29s linear infinite reverse}.o3{animation:spin 44s linear infinite}"
    "@keyframes spin{to{transform:rotate(360deg)}}"
    ".pulse{animation:pulse 4.6s ease-in-out infinite}"
    "@keyframes pulse{0%,100%{fill-opacity:.10}50%{fill-opacity:.38}}}"
)


def twinkle_attrs(base: str) -> str:
    """Kelas kelip + jeda acak (mode animasi) supaya bintang tidak berkedip serempak."""
    if not ANIM["on"]:
        return f' class="{base}"'
    return f' class="{base}" style="animation-delay:-{ANIM["rng"].uniform(0, 7):.1f}s"'


def extra_twinkle(prob: float) -> str:
    """Kelip tambahan untuk bintang yang pada aset statis diam (hanya mode animasi)."""
    if not ANIM["on"] or ANIM["rng"].random() >= prob:
        return ""
    return twinkle_attrs(("tw", "tw tw2", "tw tw3", "tw tw4")[int(ANIM["rng"].random() * 4)])


def pulse_cls() -> str:
    return ' class="pulse"' if ANIM["on"] else ""


BADGE_RECT = lambda w: (w - 132, 12, w - 14, 40)   # area lencana DEMO (x0, y0, x1, y1), untuk hindari tabrakan


def svg_doc(w, h, title, desc, body, demo, defs="") -> str:
    badge = ""
    if demo:
        x0, y0, x1, y1 = BADGE_RECT(w)
        badge = (f'<g><rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="14" fill="{C["badge_fill"]}" fill-opacity=".92" '
                 f'stroke="{C["amber"]}" stroke-opacity=".9"/><text x="{(x0 + x1) // 2}" y="{y0 + 20}" text-anchor="middle" font-size="15" '
                 f'font-weight="700" letter-spacing="1.2" fill="{C["badge_text"]}">DEMO DATA</text></g>')
    edge = f' stroke="{C["edge"]}"' if C["edge"] else ""
    off = 0.5 if C["edge"] else 0
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">\n'
        f'<title id="t">{xesc(title)}</title>\n<desc id="d">{xesc(desc)}</desc>\n'
        f'<defs><linearGradient id="bg" x1="0" y1="0" x2=".5" y2="1"><stop offset="0" stop-color="{C["bg2"]}"/>'
        f'<stop offset=".55" stop-color="{C["bg1"]}"/><stop offset="1" stop-color="{C["bg0"]}"/></linearGradient>{defs}</defs>\n'
        f'<style>{STYLE_ANIM if ANIM["on"] else STYLE}</style>\n<rect x="{off}" y="{off}" width="{w - 2 * off:g}" height="{h - 2 * off:g}" rx="14" fill="url(#bg)"{edge}/>\n{body}\n{badge}\n</svg>\n'
    )


def star(x, y, r, col, op, rng, twinkle=True) -> str:
    cls = ""
    if twinkle and rng.random() < 0.10:
        cls = twinkle_attrs("tw" if rng.random() < 0.4 else ("tw tw2" if rng.random() < 0.5 else "tw tw3"))
    elif twinkle:
        cls = extra_twinkle(0.16)
    op = clamp(op * C["star_k"] + C["star_b"], 0, 1)
    out = ""
    if r > 1.6:
        out += f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(r * 3)}" fill="{col}" fill-opacity="{C["halo"]:.2f}"/>'
    return out + f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(r)}" fill="{col}" fill-opacity="{op:.2f}"{cls}/>'


# --------------------------------------------------------------------------- hero
def orbit_layer() -> str:
    """Tiga cincin orbit tipis dengan satu titik tiap cincin (hanya mode animasi).

    Digambar di bidang galaksi (di dalam grup yang sudah dimiringkan), jadi gerakannya mengikuti
    kemiringan piringan. Titik diberi skala balik agar tetap bulat.
    """
    out = []
    for radius, cls, col, r in ((78, "o1", C["amber2"], 3.4), (128, "o2", C["star"], 2.8), (176, "o3", C["cyan"], 2.4)):
        out.append(f'<circle r="{radius}" fill="none" stroke="{col}" stroke-opacity=".18" stroke-width="1" '
                   f'stroke-dasharray="2 7" vector-effect="non-scaling-stroke"/>')
        out.append(f'<g class="{cls}"><g transform="translate({radius} 0) scale(1 1.5625)">'
                   f'<circle r="{num(r * 3)}" fill="{col}" fill-opacity=".18"/><circle r="{r}" fill="{col}"/></g></g>')
    return "".join(out)


def render_hero(cfg: dict, data: Data):
    W, H = 1000, 420
    rng = Rng("hero:" + cfg["username"])
    cx, cy, a, squash, rot = 745, 212, 232, 0.64, math.radians(-20)

    def proj(x, y):
        ys = y * squash
        return cx + x * math.cos(rot) - ys * math.sin(rot), cy + x * math.sin(rot) + ys * math.cos(rot)

    out, warn = [], []
    out.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{a * 1.08:.0f}" ry="{a * squash * 1.08:.0f}" '
               f'transform="rotate(-20 {cx} {cy})" fill="url(#neb)"/>')
    for _ in range(90):
        x, y, r, o = rng.uniform(14, W - 14), rng.uniform(14, H - 14), rng.uniform(0.4, 1.1), rng.uniform(0.25, 0.7)
        if x < 520 and rng.random() < 0.7:
            continue
        out.append(star(x, y, r, C["star"], o, rng))
    plane = []
    tgt = plane if ANIM["on"] else out
    arms = [(0.0, 1.0, 340), (math.pi, 1.0, 340), (math.pi / 2, 0.55, 110), (3 * math.pi / 2, 0.55, 110)]
    for th0, strength, count in arms:
        for _ in range(count):
            t = rng.random() ** 1.25
            th = th0 + 3.0 * math.pi * t
            r = a * (0.05 + 0.95 * t)
            off = rng.bell() * (5 + 26 * t) * 1.6 * math.sqrt(strength)
            px = r * math.cos(th) + off * math.cos(th + math.pi / 2)
            py = r * math.sin(th) + off * math.sin(th + math.pi / 2)
            sx, sy = (px, py) if ANIM["on"] else proj(px, py)   # animasi: koordinat bidang galaksi
            u = rng.random()
            if u < 0.10:
                col = C["amber2"] if t < 0.5 else C["amber"]
            elif t < 0.25:
                col = C["amber2"] if u < 0.4 else C["star"]
            elif u < 0.55:
                col = C["star"]
            else:
                col = mix(C["star"], C["cyan"], 0.35 + 0.65 * t)
            rad = 0.5 + rng.random() ** 3 * (1.9 - 0.8 * t)
            op = 0.45 + 0.55 * rng.random() * (1 - 0.4 * t)
            tgt.append(star(sx, sy, rad, col, op, rng))
    for _ in range(260):
        r = a * 0.2 * rng.random() ** 1.6
        ang = rng.uniform(0, 2 * math.pi)
        sx, sy = (r * math.cos(ang), r * math.sin(ang)) if ANIM["on"] else proj(r * math.cos(ang), r * math.sin(ang))
        col = (C["amber2"], C["star"], C["amber"])[int(rng.random() * 3)]
        tgt.append(star(sx, sy, rng.uniform(0.5, 1.6), col, rng.uniform(0.55, 1.0), rng, False))
    if ANIM["on"]:   # piringan menggoyang pelan; cincin orbit berputar penuh
        out.append(f'<g transform="translate({cx} {cy}) rotate(-20) scale(1 {squash})"><g class="sway">{"".join(plane)}</g>{orbit_layer()}</g>')
    out.append(f'<ellipse cx="{cx}" cy="{cy}" rx="64" ry="{64 * squash:.0f}" transform="rotate(-20 {cx} {cy})" fill="url(#core)"/>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="4.5" fill="{C["core"]}" stroke="{C["amber"]}" stroke-width="1.2" stroke-opacity="{C["core_ring"]}"/>')

    # blok teks kiri (ukuran dinaikkan agar terbaca saat gambar diperkecil ke lebar README)
    maxw = 450
    name = cfg["name"]
    lines = [name]
    size = min(60.0, maxw / (max(1, len(name)) * 0.70))
    if size < 40 and " " in name:
        words = name.split()
        best = min(range(1, len(words)), key=lambda k: max(len(" ".join(words[:k])), len(" ".join(words[k:]))))
        lines = [" ".join(words[:best]), " ".join(words[best:])]
        size = min(60.0, maxw / (max(len(x) for x in lines) * 0.70))
    size = max(size, 28.0)
    rsize = clamp(maxw / (len(cfg["role"]) * 0.50), 18, 30)
    tag_lines = wrap(cfg["tagline"], 36)
    total = size * 1.05 * len(lines) + 18 + rsize * 1.3 + 16 + 31 * len(tag_lines)
    y = (H - total) / 2 + 6
    text_rect = (40, y - 28, 56 + maxw, y + total)
    out.append(f'<rect x="56" y="{num(y - 22)}" width="48" height="3" rx="1.5" fill="{C["amber"]}"/>')
    for ln in lines:
        y += size * 0.95
        out.append(f'<text x="56" y="{num(y)}" font-size="{num(size)}" font-weight="800" letter-spacing="1.5" fill="{C["text"]}">{xesc(ln)}</text>')
        y += size * 0.10
    y += 18 + rsize * 0.9
    out.append(f'<text class="serif" x="56" y="{num(y)}" font-size="{num(rsize)}" fill="{C["cyan_text"]}">{xesc(cfg["role"])}</text>')
    y += 16 + 8
    for ln in tag_lines:
        y += 31
        out.append(f'<text x="56" y="{num(y - 8)}" font-size="21" fill="{C["mute"]}">{xesc(ln)}</text>')
    if data.demo:
        out.append(f'<text x="56" y="{H - 24}" font-size="15" letter-spacing="1.2" fill="{C["mute"]}">DESIGN CONCEPT · EXAMPLE CONTENT</text>')

    # label proyek pada lengan spiral
    placed = [text_rect, BADGE_RECT(W)]
    labels = []
    for j, p in enumerate(cfg["projects"][:6]):
        arm = j % 2
        lt = 0.50 + 0.36 * ((j * 0.618) % 1)
        label = p["label"]
        bw, bh = len(label) * 9.6 + 36, 34
        for _attempt in range(14):
            th = arm * math.pi + 3.0 * math.pi * lt
            r = a * (0.05 + 0.95 * lt)
            sx, sy = proj(r * math.cos(th), r * math.sin(th))
            dx, dy = sx - cx, sy - cy
            d = math.hypot(dx, dy) or 1
            ax, ay = sx + dx / d * 34, sy + dy / d * 34
            x0 = ax if dx >= 0 else ax - bw
            x0 = clamp(x0, 16, W - 16 - bw)
            y0 = clamp(ay - bh / 2, 56, H - 56)
            rect = (x0, y0, x0 + bw, y0 + bh)
            if not any(overlap(rect, q) for q in placed):
                break
            lt = lt + 0.04 if lt < 0.9 else 0.42
        else:
            warn.append(f"label '{label}' mungkin bertumpuk")
        placed.append(rect)
        labels.append((sx, sy, rect, label, data.repo_stars.get(p["repo"], 0)))
    for sx, sy, rect, label, st in labels:
        x0, y0, x1, y1 = rect
        nx, ny = clamp(sx, x0, x1), clamp(sy, y0, y1)
        mr = 3.6 + clamp(math.log10(1 + st), 0, 2.5) * 0.9
        out.append(f'<line x1="{num(sx)}" y1="{num(sy)}" x2="{num(nx)}" y2="{num(ny)}" stroke="{C["amber"]}" stroke-opacity=".75" stroke-width="1.2"/>')
        out.append(f'<circle cx="{num(sx)}" cy="{num(sy)}" r="{num(mr * 3)}" fill="{C["amber"]}" fill-opacity=".18"{pulse_cls()}/>')
        out.append(f'<circle cx="{num(sx)}" cy="{num(sy)}" r="{num(mr)}" fill="{C["amber2"]}" stroke="{C["amber"]}" stroke-width="1" stroke-opacity="{C["core_ring"]}"/>')
        out.append(f'<rect x="{num(x0)}" y="{num(y0)}" width="{num(x1 - x0)}" height="{num(y1 - y0)}" rx="17" fill="{C["pill"]}" '
                   f'fill-opacity="{C["pill_op"]}" stroke="{C["cyan"]}" stroke-opacity=".7"/>')
        out.append(f'<text x="{num((x0 + x1) / 2)}" y="{num(y0 + 22.5)}" text-anchor="middle" font-size="17" font-weight="600" fill="{C["text"]}">{xesc(label)}</text>')

    defs = (f'<radialGradient id="neb"><stop offset="0" stop-color="{C["cyan"]}" stop-opacity="{C["neb_cyan_op"]}"/>'
            f'<stop offset=".55" stop-color="{C["neb_mid"]}" stop-opacity="{C["neb_mid_op"]}"/><stop offset="1" stop-color="{C["neb_mid"]}" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="core"><stop offset="0" stop-color="{C["amber2"]}" stop-opacity=".95"/>'
            f'<stop offset=".4" stop-color="{C["amber"]}" stop-opacity=".45"/><stop offset="1" stop-color="{C["amber"]}" stop-opacity="0"/></radialGradient>')
    title = f"{cfg['name']} — {cfg['role']}"
    desc = f"{cfg['tagline']} Spiral galaksi berisi proyek: " + ", ".join(p["label"] for p in cfg["projects"][:6]) + "."
    return svg_doc(W, H, title, desc, "\n".join(out), data.demo, defs), warn


# --------------------------------------------------------------------------- konstelasi
def render_constellation(cfg: dict, data: Data):
    W, H = 1000, 330
    days = data.days
    off0 = (days[0][0].weekday() + 1) % 7            # kolom dimulai hari Minggu, seperti kalender GitHub
    cols = (off0 + len(days) - 1) // 7 + 1
    x0, x1, y0, y1 = 80, 972, 62, 208
    dx, dy = (x1 - x0) / max(1, cols - 1), (y1 - y0) / 6
    nz = sorted(c for _, c in days if c > 0)

    def q(p):
        return nz[min(len(nz) - 1, int(p * len(nz)))] if nz else 0

    t1, t2, t3 = q(.25), q(.5), q(.75)
    pts, active = [], 0
    for i, (d, c) in enumerate(days):
        idx = off0 + i
        r = Rng(f"c:{cfg['username']}:{d.isoformat()}")
        x = x0 + (idx // 7) * dx + (r.random() - .5) * dx * 0.7
        y = y0 + (idx % 7) * dy + (r.random() - .5) * dy * 0.7
        lv = 0 if c == 0 else 1 if c <= t1 else 2 if c <= t2 else 3 if c <= t3 else 4
        active += 1 if c else 0
        pts.append((i, d, c, lv, x, y))
    out = []
    segs, prev = [], None
    for p in pts:
        if p[3] == 0:
            continue
        if prev and p[0] - prev[0] <= 4:
            segs.append(f"M{num(prev[4])},{num(prev[5])}L{num(p[4])},{num(p[5])}")
        prev = p
    out.append(f'<path d="{"".join(segs)}" fill="none" stroke="{C["cyan"]}" stroke-opacity="{C["line_op"]}" stroke-width="1"/>')
    rng = Rng("cs:" + cfg["username"])
    radius = {1: 1.8, 2: 2.5, 3: 3.3, 4: 4.3}
    col = {1: mix(C["cyan"], C["star"], .3), 2: C["cyan"], 3: C["star"], 4: C["amber"]}
    for i, d, c, lv, x, y in pts:
        if lv == 0:
            out.append(f'<circle cx="{num(x)}" cy="{num(y)}" r=".8" fill="{C["dim"]}" fill-opacity="{C["dot_op"]}"/>')
            continue
        r = radius[lv]
        if lv >= 3:
            out.append(f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(r * 3.2)}" fill="{col[lv]}" fill-opacity="{C["halo"] + 0.02:.2f}"/>')
        tw = ""
        if lv >= 2 and rng.random() < 0.12:
            tw = twinkle_attrs("tw" if rng.random() < 0.5 else "tw tw3")
        elif lv >= 3:
            tw = extra_twinkle(0.35)
        if lv == 4:    # bintang empat sudut
            s, k = r * 2.1, r * 0.55
            out.append(f'<path d="M{num(x)},{num(y - s)}L{num(x + k)},{num(y - k)}L{num(x + s)},{num(y)}L{num(x + k)},{num(y + k)}'
                       f'L{num(x)},{num(y + s)}L{num(x - k)},{num(y + k)}L{num(x - s)},{num(y)}L{num(x - k)},{num(y - k)}Z" fill="{col[lv]}"{tw}/>')
        else:
            out.append(f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(r)}" fill="{col[lv]}"{tw}/>')
    # sumbu hari & bulan (ukuran dinaikkan agar terbaca pada lebar README)
    for row, nm in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text x="64" y="{num(y0 + row * dy + 5)}" text-anchor="end" font-size="15" fill="{C["mute"]}">{nm}</text>')
    marks = []
    for p in pts:
        if p[1].day == 1 or p[0] == 0:
            marks.append((x0 + ((off0 + p[0]) // 7) * dx, MONTHS[p[1].month - 1], p[0] == 0 and p[1].day > 20))
    last = -99
    for x, nm, partial in marks:
        if partial or x - last < 42:
            continue
        out.append(f'<line x1="{num(x)}" y1="232" x2="{num(x)}" y2="239" stroke="{C["dim"]}"/>')
        out.append(f'<text x="{num(x)}" y="260" font-size="16" fill="{C["mute"]}">{nm}</text>')
        last = x
    total = sum(c for _, c in days)
    out.append(f'<text x="64" y="304" font-size="17" fill="{C["mute"]}">{total:,} contributions · {active} active days · last 12 months</text>')
    lx = 972
    out.append(f'<text x="{lx}" y="304" text-anchor="end" font-size="15" fill="{C["mute"]}">More</text>')
    xs = lx - 54
    for lv in (4, 3, 2, 1):
        xs -= 20
        out.append(f'<circle cx="{xs}" cy="299" r="{radius[lv]}" fill="{col[lv]}"/>')
    out.append(f'<text x="{xs - 14}" y="304" text-anchor="end" font-size="15" fill="{C["mute"]}">Less</text>')
    desc = f"{total} kontribusi pada {active} hari aktif dalam 12 bulan terakhir; hari aktif adalah bintang, hari berdekatan dihubungkan garis."
    return svg_doc(W, H, "Konstelasi kontribusi 12 bulan", desc, "\n".join(out), data.demo), []


# --------------------------------------------------------------------------- pohon
def flower_def() -> str:
    core = C["flower_core"]
    return ('<g id="fl"><ellipse cx="0" cy="-3.3" rx="2.3" ry="3.5"/><ellipse cx="0" cy="-3.3" rx="2.3" ry="3.5" transform="rotate(72)"/>'
            '<ellipse cx="0" cy="-3.3" rx="2.3" ry="3.5" transform="rotate(144)"/><ellipse cx="0" cy="-3.3" rx="2.3" ry="3.5" transform="rotate(216)"/>'
            f'<ellipse cx="0" cy="-3.3" rx="2.3" ry="3.5" transform="rotate(288)"/><circle r="1.3" fill="{core}"/></g>')


def _bez(p0, p1, p2, t):
    u = 1 - t
    return (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0], u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1])


def _scene(W, H, gy, rng):
    s = []
    for _ in range(46):
        s.append(star(rng.uniform(16, W - 16), rng.uniform(16, gy - 160), rng.uniform(0.4, 1.2), C["star"], rng.uniform(0.25, 0.75), rng))
    s.append(f'<circle cx="150" cy="104" r="62" fill="url(#moon)"/><circle cx="150" cy="104" r="26" fill="{C["moon"]}" fill-opacity=".92"/>')
    s.append(f'<path d="M0,{gy + 2} Q250,{gy - 28} 500,{gy - 8} T1000,{gy - 16} L1000,{H} L0,{H}Z" fill="url(#hill)"/>')
    return s


def tree_defs() -> str:
    return (f'<radialGradient id="moon"><stop offset="0" stop-color="{C["moon_glow"]}" stop-opacity="{C["moon_glow_op"]}"/><stop offset="1" stop-color="{C["moon_glow"]}" stop-opacity="0"/></radialGradient>'
            f'<linearGradient id="hill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C["hill0"]}"/><stop offset="1" stop-color="{C["hill1"]}"/></linearGradient>'
            f'<radialGradient id="crown"><stop offset="0" stop-color="{C["pink"]}" stop-opacity="{C["crown_op"]}"/><stop offset=".55" stop-color="{C["cyan"]}" stop-opacity=".10"/>'
            f'<stop offset="1" stop-color="{C["cyan"]}" stop-opacity="0"/></radialGradient>'
            f'<linearGradient id="bark" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{C["bark0"]}"/><stop offset=".7" stop-color="{C["bark1"]}"/><stop offset="1" stop-color="{C["bark2"]}"/></linearGradient>')


def render_tree(cfg: dict, data: Data, style: str):
    W, H, gy, cx = 1000, 560, 500, 500
    rng = Rng(f"tree:{style}:{cfg['username']}")
    m = month_buckets(data)
    total = sum(x[0] for x in m)
    maxm = max(1, max(x[0] for x in m))
    g = clamp(math.log10(1 + total) / math.log10(1 + 3000), 0, 1)
    Ht = 170 + 130 * g
    n_amber = nstars_to_count(data.stars_total)
    out = _scene(W, H, gy, rng)
    defs = tree_defs()
    if style == "sakura":
        defs += flower_def()
        body, desc = _sakura(m, maxm, g, Ht, n_amber, rng, cx, gy)
    else:
        body, desc = _pine(m, maxm, g, Ht, n_amber, data.stars_total, rng, cx, gy)
    out += body
    fallen = int(min(45, round(sum(x[1] for x in m) / 8)))
    for _ in range(fallen):
        x, y = cx + rng.bell() * 190, gy + rng.uniform(-2, 26)
        out.append(f'<ellipse cx="{num(x)}" cy="{num(y)}" rx="3" ry="1.6" fill="{mix(C["cyan"], C["pink"], rng.random())}" fill-opacity=".7" transform="rotate({int(rng.uniform(-30, 30))} {num(x)} {num(y)})"/>')
    title = f"Pohon {'sakura' if style == 'sakura' else 'pine'} dari aktivitas GitHub"
    return svg_doc(W, H, title, desc, "\n".join(out), data.demo, defs), []


def _sakura(m, maxm, g, Ht, n_amber, rng, cx, gy):
    out = []
    wb = 16 + 12 * g

    def tx(u):
        return cx + 16 * math.sin(u * 2.6 + 0.6) * u

    def tw(u):
        return wb * (1 - 0.78 * u) + 2.5

    N = 28
    left = [(tx(i / N) - tw(i / N) / 2, gy + 6 - (i / N) * Ht) for i in range(N + 1)]
    right = [(tx(i / N) + tw(i / N) / 2, gy + 6 - (i / N) * Ht) for i in range(N + 1)]
    path = "M" + "L".join(f"{num(x)},{num(y)}" for x, y in left + right[::-1]) + "Z"
    branches, ends = [], []
    for i, (mm, aa) in enumerate(m):
        u = 0.28 + 0.64 * i / 11
        side = 1 if i % 2 else -1
        P = (tx(u), gy + 6 - u * Ht)
        L = (55 + 150 * math.sqrt(mm / maxm)) * (1 - 0.35 * u) if mm else 30
        ang = math.radians(18 + 30 * u)
        E = (P[0] + side * L * math.cos(ang), P[1] - L * math.sin(ang))
        Cc = ((P[0] + E[0]) / 2 + side * 6, (P[1] + E[1]) / 2 - L * 0.22)
        branches.append((P, Cc, E, 5.4 * (1 - 0.3 * u) if mm else 2.6, side, L))
        ends.append(E)
    br = C["branch"]
    crown_cx = sum(e[0] for e in ends) / 12
    crown_cy = sum(e[1] for e in ends) / 12
    out.append(f'<ellipse cx="{num(crown_cx)}" cy="{num(crown_cy)}" rx="270" ry="180" fill="url(#crown)"/>')
    for (P, Cc, E, w, side, L), (mm, aa) in zip(branches, m):
        out.append(f'<path d="M{num(P[0])},{num(P[1])}Q{num(Cc[0])},{num(Cc[1])} {num(E[0])},{num(E[1])}" fill="none" stroke="{br}" stroke-width="{num(w)}" stroke-linecap="round"/>')
    out.append(f'<path d="{path}" fill="url(#bark)" stroke="{C["amber"]}" stroke-opacity=".22"/>')
    twig_tips, flowers = [], []
    max_a = max(1, max(x[1] for x in m))
    for i, ((P, Cc, E, w, side, L), (mm, aa)) in enumerate(zip(branches, m)):
        anchors = [_bez(P, Cc, E, t) for t in (0.45, 0.6, 0.75, 0.9, 1.0)]
        k = 2 + int(round(2 * aa / max_a))
        for j in range(k):
            t = 0.42 + 0.5 * j / max(1, k)
            px, py = _bez(P, Cc, E, t)
            tdx = 2 * (1 - t) * (Cc[0] - P[0]) + 2 * t * (E[0] - Cc[0])
            tdy = 2 * (1 - t) * (Cc[1] - P[1]) + 2 * t * (E[1] - Cc[1])
            base = math.atan2(tdy, tdx) + (1 if j % 2 else -1) * math.radians(rng.uniform(30, 52))
            ln = L * rng.uniform(0.22, 0.4)
            ex, ey = px + ln * math.cos(base), py + ln * math.sin(base)
            out.append(f'<line x1="{num(px)}" y1="{num(py)}" x2="{num(ex)}" y2="{num(ey)}" stroke="{br}" stroke-width="1.8" stroke-linecap="round"/>')
            anchors += [(ex, ey), ((px + ex) / 2, (py + ey) / 2)]
            twig_tips.append((ex, ey))
        n_fl = int(min(60, 2 * aa + round(6 * mm / maxm)))
        for _ in range(n_fl):
            ax, ay = anchors[int(rng.random() * len(anchors))]
            r, th = rng.random() ** 0.7 * 17, rng.uniform(0, 2 * math.pi)
            colr = mix(C["cyan"], C["pink"], clamp(i / 11 + (rng.random() - .5) * 0.3, 0, 1))
            flowers.append(f'<use xlink:href="#fl" href="#fl" fill="{colr}" fill-opacity="{rng.uniform(.72, .95):.2f}" '
                           f'transform="translate({num(ax + r * math.cos(th))},{num(ay + r * math.sin(th))}) scale({rng.uniform(.7, 1.4):.2f}) rotate({int(rng.uniform(0, 72))})"/>')
    out += flowers
    tips = ends + twig_tips
    for k in range(n_amber):
        tx_, ty_ = tips[int(rng.random() * len(tips))]
        ln = rng.uniform(14, 26)
        out.append(f'<line x1="{num(tx_)}" y1="{num(ty_)}" x2="{num(tx_)}" y2="{num(ty_ + ln)}" stroke="{C["amber"]}" stroke-opacity=".7"/>')
        out.append(f'<circle cx="{num(tx_)}" cy="{num(ty_ + ln + 3)}" r="9" fill="{C["amber"]}" fill-opacity=".22"{pulse_cls()}/>')
        out.append(f'<circle cx="{num(tx_)}" cy="{num(ty_ + ln + 3)}" r="3.6" fill="{C["amber2"]}" stroke="{C["amber"]}" stroke-opacity="{C["core_ring"]}"/>')
    desc = (f"Pohon sakura: batang setinggi {int(Ht)} unit, 12 cabang (satu per irisan bulan), "
            f"{len(flowers)} bunga, {n_amber} lentera amber.")
    return out, desc


def _pine(m, maxm, g, Ht, n_amber, stars_total, rng, cx, gy):
    out = []
    out.append(f'<rect x="{cx - 7}" y="{num(gy - Ht * 0.3)}" width="14" height="{num(Ht * 0.3 + 6)}" fill="url(#bark)"/>')
    tiers = 12
    step = Ht * 0.92 / tiers
    th = step * 2.2
    tier_geo = []
    for i, (mm, aa) in enumerate(m):
        yc = gy - 18 - i * step - th * 0.3
        w = (46 + 150 * math.sqrt(mm / maxm)) * (1 - 0.5 * i / (tiers - 1)) * (0.75 + 0.25 * g)
        apex = (cx, yc - th * 0.62)
        base_y = yc + th * 0.38
        d = f"M{num(apex[0])},{num(apex[1])}L{num(cx + w)},{num(base_y)}"
        n = 5
        seg = 2 * w / n
        for s in range(n):
            d += f"Q{num(cx + w - seg * (s + .5))},{num(base_y + th * .16)} {num(cx + w - seg * (s + 1))},{num(base_y)}"
        d += "Z"
        out.append(f'<path d="{d}" fill="{mix(C["tier_a"], C["tier_b"], i / 11)}" stroke="{C["cyan"]}" stroke-opacity=".35"/>')
        for _ in range(int(min(22, aa))):
            f = rng.uniform(0.45, 0.95)
            px = cx + (rng.random() * 2 - 1) * w * f * 0.9
            py = apex[1] + f * (base_y - apex[1])
            out.append(f'<circle cx="{num(px)}" cy="{num(py)}" r="{rng.uniform(1.4, 2.4):.1f}" fill="{mix(C["lamp_a"], C["lamp_b"], clamp(i / 11 + (rng.random() - .5) * .3, 0, 1))}"/>')
        tier_geo.append((apex, base_y, w))
    for _ in range(n_amber):
        apex, base_y, w = tier_geo[int(rng.random() * tiers)]
        f = rng.uniform(0.5, 0.92)
        px, py = cx + (rng.random() * 2 - 1) * w * f * 0.85, apex[1] + f * (base_y - apex[1])
        out.append(f'<circle cx="{num(px)}" cy="{num(py)}" r="9" fill="{C["amber"]}" fill-opacity=".22"{pulse_cls()}/><circle cx="{num(px)}" cy="{num(py)}" r="3.6" fill="{C["amber2"]}" stroke="{C["amber"]}" stroke-opacity="{C["core_ring"]}"/>')
    top = tier_geo[-1][0]
    sz = 10 + 8 * clamp(math.log10(1 + stars_total) / 4, 0, 1)
    pts = []
    for k in range(10):
        r = sz if k % 2 == 0 else sz * 0.42
        ang = -math.pi / 2 + k * math.pi / 5
        pts.append(f"{num(top[0] + r * math.cos(ang))},{num(top[1] - 4 + r * math.sin(ang))}")
    col = C["amber2"] if stars_total > 0 else C["cyan"]
    out.append(f'<circle cx="{num(top[0])}" cy="{num(top[1] - 4)}" r="{num(sz * 2)}" fill="{col}" fill-opacity=".2"/>')
    out.append(f'<polygon points="{" ".join(pts)}" fill="{col}" stroke="{C["amber"]}" stroke-opacity="{C["core_ring"]}"/>')
    lights = sum(min(22, x[1]) for x in m)
    desc = f"Pohon pine: 12 tingkat (satu per irisan bulan), {lights} lampu aktivitas, {n_amber} ornamen amber, bintang puncak."
    return out, desc


# --------------------------------------------------------------------------- preview animasi
_IDS = ("bg", "neb", "core", "moon", "hill", "crown", "bark", "fl")


def _namespace(frag: str, pre: str) -> str:
    """Beri awalan unik pada id agar tiga kartu bisa berbagi satu dokumen SVG."""
    for n in _IDS:
        frag = frag.replace(f'id="{n}"', f'id="{pre}{n}"').replace(f"url(#{n})", f"url(#{pre}{n})").replace(f'href="#{n}"', f'href="#{pre}{n}"')
    return frag


def build_animated_preview(cfg: dict, data: Data, theme: str) -> str:
    """Hero + konstelasi + pohon dalam satu SVG beranimasi untuk README repo kit."""
    use_theme(theme)
    ANIM["on"], ANIM["rng"] = True, Rng("anim:" + cfg["username"])
    try:
        cards = [("h-", render_hero(cfg, data)[0], 1000, 420),
                 ("c-", render_constellation(cfg, data)[0], 1000, 330),
                 ("t-", render_tree(cfg, data, cfg["tree_style"])[0], 1000, 560)]
        edge_style = STYLE_ANIM
    finally:
        ANIM["on"], ANIM["rng"] = False, None
    gap = 28
    H = sum(c[3] for c in cards) + gap * (len(cards) - 1)
    defs, bodies, y = [], [], 0
    for pre, svg, w, h in cards:
        d = re.search(r"<defs>(.*?)</defs>", svg, re.S).group(1)
        body = svg.split("</style>\n", 1)[1].rsplit("</svg>", 1)[0]
        defs.append(_namespace(d, pre))
        bodies.append(f'<g transform="translate(0 {y})">{_namespace(body, pre)}</g>')
        y += h + gap
    title = "Preview varian galaxy dev-readme-kit (animasi, data demo)"
    desc = ("Hero dengan spiral galaksi dan label proyek, konstelasi kontribusi 12 bulan, dan pohon pertumbuhan. "
            "Bintang berkelip dan cincin orbit berputar pelan. Semua data adalah demo.")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1000" height="{H}" '
            f'viewBox="0 0 1000 {H}" role="img" aria-labelledby="t d">\n<title id="t">{xesc(title)}</title>\n<desc id="d">{xesc(desc)}</desc>\n'
            f'<defs>{"".join(defs)}</defs>\n<style>{edge_style}</style>\n' + "\n".join(bodies) + "\n</svg>\n")


# --------------------------------------------------------------------------- markdown
def md_esc(s: str) -> str:
    return re.sub(r"([\\`*_{}\[\]<>|#])", r"\\\1", s)


def image_block(name: str, alt: str, themes: tuple) -> str:
    """Gambar README: <picture> bila dua tema, Markdown biasa bila satu tema."""
    if len(themes) == 2:
        return ("<picture>\n"
                f'  <source media="(prefers-color-scheme: dark)" srcset="assets/{name}-dark.svg">\n'
                f'  <img src="assets/{name}-light.svg" alt="{xesc(alt)}">\n'
                "</picture>")
    return f"![{md_esc(alt)}](assets/{name}-{themes[0]}.svg)"


def build_blocks(cfg: dict, data: Data, themes: tuple) -> dict:
    hero_alt = f"{cfg['name']} — {cfg['role']} {cfg['tagline']}"
    projects = []
    for p in cfg["projects"]:
        title = f"**[{md_esc(p['title'])}]({p['url']})**" if p["url"] else f"**{md_esc(p['title'])}**"
        line = f"- {title} — {md_esc(p['description'])}"
        if not data.demo and p["repo"]:           # bintang hanya ditampilkan bila datanya nyata
            line += f" · ★ {data.repo_stars.get(p['repo'], 0)}"
        projects.append(line)
    blocks = {
        "hero": image_block("hero", hero_alt, themes),
        "constellation": image_block("constellation", "Contribution calendar of the last 12 months drawn as a constellation", themes),
        "tree": image_block("tree", "A tree grown from the last 12 months of GitHub activity", themes),
        "projects": "\n".join(projects),
        "beyond": " · ".join(md_esc(x) for x in cfg["beyond"]),
        "connect": " · ".join(f"[{md_esc(c['label'])}]({c['url']})" for c in cfg["connect"]),
    }
    if data.demo:
        blocks["notice"] = ("> **Data demo.** Nama, proyek, angka, dan gambar di halaman ini hanyalah contoh, bukan statistik nyata. "
                            "Jalankan `render.py --live` untuk memakai data akun sendiri.")
        blocks["footer"] = "_DESIGN CONCEPT · EXAMPLE CONTENT_"
    else:
        blocks["notice"] = ""
        blocks["footer"] = "_Built with dev-readme-kit (MIT)_"
    return blocks


def apply_blocks(text: str, blocks: dict):
    missing = []
    for name, content in blocks.items():
        pat = re.compile(rf"(<!-- galaxy:{name}:start -->)(.*?)(<!-- galaxy:{name}:end -->)", re.S)
        if not pat.search(text):
            missing.append(name)
            continue
        body = f"\n{content}\n" if content else "\n"
        text = pat.sub(lambda mo: mo.group(1) + body + mo.group(3), text, count=1)
    return text, missing


def write_if_changed(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


# --------------------------------------------------------------------------- main
def main() -> int:
    here = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description="Renderer SVG varian galaxy (dev-readme-kit).")
    ap.add_argument("--config", default=str(here / "galaxy.config.json"))
    ap.add_argument("--out", help="folder keluaran SVG (bawaan: <folder config>/assets)")
    ap.add_argument("--readme", help="README yang blok galaxy-nya diperbarui (bawaan: <folder config>/README.md)")
    ap.add_argument("--theme", choices=("auto", "dark", "light"), help="menimpa `appearance` di config")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--demo", action="store_true", help="paksa data demo (tanpa jaringan)")
    g.add_argument("--live", action="store_true", help="paksa data nyata (butuh GITHUB_TOKEN)")
    ap.add_argument("--all-trees", action="store_true", help="tulis juga tree-sakura-*.svg dan tree-pine-*.svg")
    ap.add_argument("--preview-svg", metavar="FOLDER", help="tulis galaxy-animated-{dark,light}.svg (data demo) ke FOLDER, lalu keluar")
    ap.add_argument("--check", action="store_true", help="validasi config dan cek sisa data contoh, lalu keluar")
    args = ap.parse_args()

    cfg_path = Path(args.config).resolve()
    try:
        cfg = load_config(cfg_path)
    except ConfigError as e:
        print(f"config tidak valid: {e}", file=sys.stderr)
        return 2
    mode = "live" if args.live else "demo" if args.demo else cfg["mode"]
    appearance = args.theme or cfg["appearance"]
    themes = ("dark", "light") if appearance == "auto" else (appearance,)

    if args.preview_svg:
        out = Path(args.preview_svg)
        data = demo_data(cfg)
        changed = [f"galaxy-animated-{th}.svg" for th in ("dark", "light")
                   if write_if_changed(out / f"galaxy-animated-{th}.svg", build_animated_preview(cfg, data, th))]
        print("preview animasi (demo) · berubah:", ", ".join(changed) if changed else "tidak ada")
        return 0

    left = check_live_ready(cfg)
    if args.check:
        if left:
            print("Masih ada data contoh:", ", ".join(left), file=sys.stderr)
            return 1
        print("Config bersih dan siap mode live.")
        return 0
    if mode == "live" and left:
        print("Mode live ditolak: config masih berisi data contoh (" + ", ".join(left) + ").", file=sys.stderr)
        return 1

    try:
        if mode == "demo":
            data = demo_data(cfg)
        else:
            token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
            if not token:
                print("Mode live butuh env GITHUB_TOKEN (di Actions: secrets.GITHUB_TOKEN). Tidak ada fallback ke demo.", file=sys.stderr)
                return 1
            data = live_data(cfg, token)
    except RuntimeError as e:
        print(f"gagal mengambil data: {e}", file=sys.stderr)
        return 1

    out_dir = Path(args.out) if args.out else cfg_path.parent / "assets"
    readme = Path(args.readme) if args.readme else cfg_path.parent / "README.md"
    files, warns = {}, []
    for th in themes:
        use_theme(th)
        for name, fn in ((f"hero-{th}.svg", lambda: render_hero(cfg, data)),
                         (f"constellation-{th}.svg", lambda: render_constellation(cfg, data)),
                         (f"tree-{th}.svg", lambda: render_tree(cfg, data, cfg["tree_style"]))):
            svg, w = fn()
            files[name] = svg
            warns += w
        if args.all_trees:
            for st in ("sakura", "pine"):
                files[f"tree-{st}-{th}.svg"] = render_tree(cfg, data, st)[0]
    changed = [n for n, s in files.items() if write_if_changed(out_dir / n, s)]

    if readme.exists():
        text, missing = apply_blocks(readme.read_text(encoding="utf-8"), build_blocks(cfg, data, themes))
        if write_if_changed(readme, text):
            changed.append(readme.name)
        if missing:
            print("catatan: penanda tidak ditemukan di README untuk blok: " + ", ".join(missing), file=sys.stderr)
    for w in sorted(set(warns)):
        print("peringatan:", w, file=sys.stderr)
    print(f"mode={mode} · tema={'+'.join(themes)} · berubah: {', '.join(changed) if changed else 'tidak ada'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
