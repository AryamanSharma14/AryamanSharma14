"""Render the profile SVGs (neofetch card, repo radar, language bars) into assets/."""
import base64
import hashlib
import json
import math
import os
import re
import urllib.request
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

USER = "AryamanSharma14"
HIDDEN = re.compile(r"quantum|pqc|qsetu|shield", re.I)
OUT = Path(__file__).resolve().parent.parent / "assets"
FONT = "'JetBrains Mono','Fira Code',Consolas,'Courier New',monospace"
ROLE = ["Security · quantum-safe crypto", "dev tooling · cloud · infra · CLI · Frappe"]
LINKS = [
    ("LinkedIn", "linkedin.com/in/aryamansharma14"),
    ("Web", "aryamansharma14.vercel.app"),
    ("Email", "aryamansharma4810@gmail.com"),
]
GLYPHS = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
}
CRT = """
  <defs>
    <filter id="glow"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" opacity=".35"/></pattern>
  </defs>"""


def get(url, headers):
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return json.load(r)


def gh(path):
    headers = {"Accept": "application/vnd.github+json"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    return get(f"https://api.github.com{path}", headers)


def visible_repos():
    repos = gh(f"/users/{USER}/repos?per_page=100&sort=pushed")
    return [
        r for r in repos
        if not r["fork"]
        and r["name"].lower() != USER.lower()
        and not HIDDEN.search(r["name"] + " " + (r.get("description") or ""))
    ]


def languages(repos):
    """Top 5 languages as (name, percent, label); WakaTime hours when WAKATIME_API_KEY is set."""
    if key := os.environ.get("WAKATIME_API_KEY"):
        auth = base64.b64encode(key.encode()).decode()
        stats = get("https://wakatime.com/api/v1/users/current/stats/last_7_days", {"Authorization": f"Basic {auth}"})
        return [(l["name"], l["percent"], l["text"]) for l in stats["data"]["languages"][:5]], "wakatime --this-week"
    totals = {}
    for r in repos:
        for lang, size in gh(f"/repos/{USER}/{r['name']}/languages").items():
            totals[lang] = totals.get(lang, 0) + size
    total = sum(totals.values()) or 1
    top = sorted(totals.items(), key=lambda kv: -kv[1])[:5]
    return [(name, size * 100 / total, f"{size * 100 / total:.1f}%") for name, size in top], "langs --public-repos"


def neofetch(user, repos, langs):
    px, gap, x0, y0 = 16, 3, 48, 92
    pixels = []
    for li, letter in enumerate("AS"):
        for row, bits in enumerate(GLYPHS[letter]):
            for col, bit in enumerate(bits):
                if bit == "#":
                    x = x0 + li * 6 * (px + gap) + col * (px + gap)
                    y = y0 + row * (px + gap)
                    pixels.append(f'<rect class="px" style="animation-delay:{row * .08:.2f}s" x="{x}" y="{y}" width="{px}" height="{px}" rx="2"/>')
    rows = [
        ("Role", ROLE[0]), ("", ROLE[1]),
        ("Langs", " · ".join(name for name, _, _ in langs[:4])),
        ("Repos", f"{user['public_repos']} public"),
        ("OSS", "Frappe contributor"),
        *LINKS,
    ]
    lines = []
    for i, (k, v) in enumerate(rows):
        y = 112 + i * 27
        lines.append(f'<g class="ln" style="animation-delay:{.5 + i * .14:.2f}s"><text x="300" y="{y}" class="k">{escape(k)}</text><text x="410" y="{y}" class="v">{escape(v)}</text></g>')
    end = 112 + len(rows) * 27
    swatch = "".join(f'<rect x="{300 + i * 30}" y="{end - 6}" width="24" height="12" fill="{c}"/>' for i, c in enumerate(["#FF8A3D", "#FFB547", "#FFCF7A", "#7A4A12", "#3A2508"]))
    height = end + 60
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{height}" viewBox="0 0 900 {height}" font-family="{FONT}">{CRT}
  <style>
    .px{{fill:#FFB547;animation:on .05s steps(1) backwards}}
    .ln{{animation:on .05s steps(1) backwards}}
    .k{{fill:#FF8A3D;font-size:16px;font-weight:700}} .v{{fill:#FFCF7A;font-size:16px}}
    .head{{fill:#FFCF7A;font-size:20px;font-weight:700}}
    .caret{{fill:#FFB547;animation:blink 1s steps(1) infinite}}
    @keyframes on{{from{{opacity:0}}}} @keyframes blink{{50%{{opacity:0}}}}
  </style>
  <rect width="900" height="{height}" rx="14" fill="#0B0905"/>
  <g filter="url(#glow)">
    {''.join(pixels)}
    <text x="48" y="262" class="v" style="font-size:14px;opacity:.7">security · tooling · infra</text>
    <g class="ln" style="animation-delay:.3s"><text x="300" y="58" class="head">aryaman<tspan fill="#FF8A3D">@</tspan>github</text><rect x="300" y="72" width="560" height="2" fill="#7A4A12"/></g>
    {''.join(lines)}
    <g class="ln" style="animation-delay:{.5 + len(rows) * .14:.2f}s">{swatch}</g>
    <text x="300" y="{end + 36}" class="v">&gt;</text><rect class="caret" x="318" y="{end + 22}" width="10" height="18"/>
  </g>
  <rect width="900" height="{height}" rx="14" fill="url(#scan)"/>
</svg>"""


def radar(repos):
    w, h, cx, cy, R, period = 900, 440, 450, 225, 185, 6.0
    contacts = repos[:8]
    rings = "".join(f'<circle cx="{cx}" cy="{cy}" r="{R * k / 4}" class="ring"/>' for k in range(1, 5))
    wedges = []
    for k in range(16):
        a1, a2 = math.radians(-(k + 1) * 3), math.radians(-k * 3)
        wedges.append(
            f'<path d="M{cx},{cy} L{cx + R * math.cos(a1):.1f},{cy + R * math.sin(a1):.1f} '
            f'A{R},{R} 0 0 1 {cx + R * math.cos(a2):.1f},{cy + R * math.sin(a2):.1f} Z" fill="#40E0D0" opacity="{.28 * (1 - k / 16):.3f}"/>'
        )
    blips = []
    for i, r in enumerate(contacts):
        digest = hashlib.md5(r["name"].encode()).digest()
        theta = (i / len(contacts)) * 2 * math.pi + digest[0] / 255 * .5
        dist = R * (.3 + .62 * digest[1] / 255)
        bx, by = cx + dist * math.cos(theta), cy + dist * math.sin(theta)
        delay = theta % (2 * math.pi) / (2 * math.pi) * period
        right = bx >= cx
        label = escape(r["name"])
        blips.append(
            f'<circle class="ping" style="animation-delay:{delay:.2f}s" cx="{bx:.1f}" cy="{by:.1f}" r="4"/>'
            f'<circle class="blip" style="animation-delay:{delay:.2f}s" cx="{bx:.1f}" cy="{by:.1f}" r="4"/>'
            f'<text class="lb" style="animation-delay:{delay:.2f}s" x="{bx + (10 if right else -10):.1f}" y="{by - 8:.1f}" text-anchor="{"start" if right else "end"}">{label}</text>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}">{CRT}
  <style>
    .ring{{fill:none;stroke:#40E0D0;stroke-opacity:.22}}
    .sweep{{transform-origin:{cx}px {cy}px;animation:spin {period}s linear infinite}}
    .blip{{fill:#5FFBE6;opacity:.2;animation:blip {period}s linear infinite}}
    .ping{{fill:none;stroke:#5FFBE6;opacity:0;transform-box:fill-box;transform-origin:center;animation:ping {period}s linear infinite}}
    .lb{{fill:#9FFFF2;font-size:14px;font-weight:600;opacity:.4;animation:lb {period}s linear infinite}}
    .hud{{fill:#5FFBE6;font-size:13px;opacity:.75;letter-spacing:.06em}}
    @keyframes spin{{to{{transform:rotate(360deg)}}}}
    @keyframes blip{{0%{{opacity:1}}70%,100%{{opacity:.2}}}}
    @keyframes ping{{0%{{opacity:.9;transform:scale(1)}}35%,100%{{opacity:0;transform:scale(6)}}}}
    @keyframes lb{{0%{{opacity:1}}70%,100%{{opacity:.4}}}}
  </style>
  <rect width="{w}" height="{h}" rx="14" fill="#031417"/>
  <g filter="url(#glow)">
    {rings}
    <path d="M{cx - R},{cy} H{cx + R} M{cx},{cy - R} V{cy + R}" stroke="#40E0D0" stroke-opacity=".22"/>
    <g class="sweep">{''.join(wedges)}<line x1="{cx}" y1="{cy}" x2="{cx + R}" y2="{cy}" stroke="#5FFBE6" stroke-width="2"/></g>
    {''.join(blips)}
    <text x="24" y="34" class="hud">CONTACTS {len(contacts):02d}</text>
    <text x="24" y="54" class="hud">SWEEP {period:.1f} s</text>
    <text x="{w - 24}" y="34" class="hud" text-anchor="end">OPERATOR aryaman</text>
    <text x="{w - 24}" y="54" class="hud" text-anchor="end">SCAN public repos</text>
    <text x="24" y="{h - 22}" class="hud">UPDATED {date.today().isoformat()}</text>
    <text x="{w - 24}" y="{h - 22}" class="hud" text-anchor="end">github.com/{USER}</text>
  </g>
  <rect width="{w}" height="{h}" rx="14" fill="url(#scan)" opacity=".5"/>
</svg>"""


def lang_bars(langs, command):
    w, top, row = 900, 82, 36
    h = top + len(langs) * row + 24
    peak = max(p for _, p, _ in langs) or 1
    rows = []
    for i, (name, pct, label) in enumerate(langs):
        y = top + i * row
        rows.append(
            f'<text x="40" y="{y + 14}" class="v">{escape(name)}</text>'
            f'<rect class="bar" style="animation-delay:{.3 + i * .15:.2f}s" x="210" y="{y}" width="{560 * pct / peak:.1f}" height="18" rx="2" fill="url(#amber)"/>'
            f'<text x="{w - 40}" y="{y + 14}" class="v" text-anchor="end">{escape(label)}</text>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}">{CRT}
  <defs><linearGradient id="amber"><stop offset="0" stop-color="#FF8A3D"/><stop offset="1" stop-color="#FFB547"/></linearGradient></defs>
  <style>
    .v{{fill:#FFCF7A;font-size:16px}} .k{{fill:#FF8A3D;font-size:16px;font-weight:700}}
    .bar{{transform-box:fill-box;transform-origin:left;animation:grow 1.1s ease-out backwards}}
    @keyframes grow{{from{{transform:scaleX(0)}}}}
  </style>
  <rect width="{w}" height="{h}" rx="14" fill="#0B0905"/>
  <g filter="url(#glow)">
    <text x="40" y="46" class="k">$ {escape(command)}</text>
    {''.join(rows)}
  </g>
  <rect width="{w}" height="{h}" rx="14" fill="url(#scan)"/>
</svg>"""


def main():
    OUT.mkdir(exist_ok=True)
    user = gh(f"/users/{USER}")
    repos = visible_repos()
    langs, command = languages(repos)
    (OUT / "neofetch.svg").write_text(neofetch(user, repos, langs), encoding="utf-8")
    (OUT / "radar.svg").write_text(radar(repos), encoding="utf-8")
    (OUT / "langs.svg").write_text(lang_bars(langs, command), encoding="utf-8")


if __name__ == "__main__":
    main()
