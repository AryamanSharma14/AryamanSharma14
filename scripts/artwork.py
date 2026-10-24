"""SVG renderers for the profile card, repo radar and link pills."""
import json
import math
import random
from pathlib import Path
from xml.sax.saxutils import escape

FONT = "Consolas,'Liberation Mono',Menlo,monospace"
CHAR = .6  # glyph advance per font size; textLength pins every line to it so columns align on any OS
RAMP = " .:-=+*#%@"
USER_PROMPT = "aryaman@github ~ $ "
THEMES = {
    "dark": dict(bg="#161b22", border="#30363d", text="#c9d1d9", muted="#8b949e", dim="#616e7f", key="#ffa657",
                 value="#a5d6ff", add="#3fb950", remove="#f85149"),
    "light": dict(bg="#f6f8fa", border="#d0d7de", text="#1f2328", muted="#59636e", dim="#8c959f", key="#bc4c00",
                  value="#0a3069", add="#1a7f37", remove="#cf222e"),
}
BASE_CSS = (".in{animation:in .2s ease-out backwards}@keyframes in{from{opacity:0}}"
            ".cur{animation:blink 1s steps(1) infinite}@keyframes blink{50%{opacity:0}}")
data_dir = Path(__file__).parent
PORTRAIT = json.loads((data_dir / "portrait.json").read_text(encoding="utf-8"))


def anim(cls, delay):
    return f' class="{cls}" style="animation-delay:{delay:.2f}s"'


def line(x, y, spans, size, length=None, attrs="", anchor=None):
    content = "".join(f'<tspan fill="{color}">{escape(part)}</tspan>' for part, color in spans if part)
    width = length or sum(len(part) for part, _ in spans) * size * CHAR
    align = f' text-anchor="{anchor}"' if anchor else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" textLength="{width:.1f}" lengthAdjust="spacingAndGlyphs"'
            f' xml:space="preserve"{align}{attrs}>{content}</text>')


def svg(w, h, t, title, body, css=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}" role="img">'
            f'<title>{escape(title)}</title><style>{BASE_CSS}{css}</style>'
            f'<rect width="{w}" height="{h}" rx="15" fill="{t["bg"]}"/>{body}</svg>')


def prompt(x, y, command, t, size):
    return line(x, y, [("aryaman@github", t["value"]), (" ~ ", t["muted"]), ("$ ", t["dim"]), (command, t["text"])], size)


def typed_prompt(x, y, command, t, size, delay):
    """Prompt line whose command types itself out, revealed by a bg-coloured cover stepping right."""
    cw = size * CHAR
    start, width = x + len(USER_PROMPT) * cw, len(command) * cw
    css = (f".type{{transform:translateX({width:.1f}px);animation:type {len(command) * .09:.2f}s steps({len(command)}) {delay}s backwards}}"
           f"@keyframes type{{from{{transform:translateX(0)}}}}")
    cover = f'<rect class="type" x="{start:.1f}" y="{y - size:.1f}" width="{width + cw:.1f}" height="{size * 1.4:.1f}" fill="{t["bg"]}"/>'
    return prompt(x, y, command, t, size) + cover, css


def cursor_prompt(x, y, t, size, delay):
    cw = size * CHAR
    return (line(x, y, [("aryaman@github", t["value"]), (" ~ ", t["muted"]), ("$", t["dim"])], size, attrs=anim("in", delay))
            + f'<rect class="cur" x="{x + len(USER_PROMPT) * cw:.1f}" y="{y - size * .8:.1f}" width="{cw:.1f}" height="{size:.1f}" fill="{t["text"]}"/>')


def tone(ch, t):
    level = RAMP.find(ch)
    return t["dim"] if level <= 1 else t["muted"] if level <= 3 else t["text"]


def toned(row, t):
    spans, current, color = [], "", None
    for ch in row:
        c = color if ch == " " and color else tone(ch, t)
        if c != color and current:
            spans.append((current, color))
            current = ""
        current, color = current + ch, c
    return spans + [(current, color)] if current else spans


def portrait(x, y, size, step, t):
    """ASCII portrait that decodes from noise row by row, then gets a scan line and an occasional blink."""
    rng = random.Random(14)
    cw, body = size * CHAR, []
    for i, row in enumerate(PORTRAIT["rows"]):
        if not row.strip():
            continue
        noise = "".join(rng.choice(RAMP[2:]) if ch != " " else " " for ch in row)
        body.append(line(x, y + i * step, [(noise, t["dim"])], size, attrs=anim("scr", .02 * i)))
        body.append(line(x, y + i * step, toned(row, t), size, attrs=anim("in", .02 * i + .3)))
    width, height = max(map(len, PORTRAIT["rows"])) * cw, len(PORTRAIT["rows"]) * step
    for row, first, last in PORTRAIT["eyes"]:
        top = y + row * step - size * .85
        body.append(f'<g class="lid"><rect x="{x + first * cw:.1f}" y="{top:.1f}" width="{(last - first + 1) * cw:.1f}" height="{step * 1.2:.1f}" fill="{t["bg"]}"/>'
                    f'<rect x="{x + first * cw:.1f}" y="{top + step * .55:.1f}" width="{(last - first + 1) * cw:.1f}" height="1.4" fill="{t["muted"]}"/></g>')
    body.append(f'<defs><linearGradient id="scan" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["value"]}" stop-opacity="0"/>'
                f'<stop offset=".5" stop-color="{t["value"]}" stop-opacity=".1"/><stop offset="1" stop-color="{t["value"]}" stop-opacity="0"/></linearGradient></defs>'
                f'<rect class="scan" x="{x:.1f}" y="{y - step * 3:.1f}" width="{width:.1f}" height="{step * 4:.1f}" fill="url(#scan)"/>')
    css = (".scr{opacity:0;animation:scr .45s steps(1) backwards}@keyframes scr{from{opacity:1}}"
           ".lid{opacity:0;animation:lid 9s steps(1) 4s infinite}@keyframes lid{0%{opacity:1}1.5%{opacity:0}3%{opacity:1}4.5%,100%{opacity:0}}"
           f".scan{{opacity:0;animation:scan 7s linear 2.4s infinite}}"
           f"@keyframes scan{{0%{{opacity:1;transform:translateY(0)}}45%{{opacity:1;transform:translateY({height:.0f}px)}}46%,100%{{opacity:0;transform:translateY({height:.0f}px)}}}}")
    return "".join(body), css


def card_lines(rows, t, cols=60):
    out = []
    for row in rows:
        if row is None:
            out.append(None)
        elif row[0] == "section":
            out.append([("- " + row[1] + " ", t["text"]), ("─" * (cols - len(row[1]) - 3), t["dim"])])
        else:
            key, value = row
            value = [(value, "value")] if isinstance(value, str) else value
            dots = cols - len(key) - sum(len(v) for v, _ in value) - 5
            out.append([(". ", t["dim"]), (key, t["key"]), (":", t["text"]), (" " + "." * dots + " ", t["dim"])]
                       + [(v, t[c]) for v, c in value])
    return out


def profile(rows, t, mobile=False):
    lines = card_lines(rows, t)
    size, gap, width = (13, 19, 436) if mobile else (16, 20, 570)
    total = len(lines) + 2
    rows_n, pstep, psize = len(PORTRAIT["rows"]), 8.4, 8
    if mobile:
        w = 480
        px, py = (w - max(map(len, PORTRAIT["rows"])) * psize * CHAR) / 2, 26
        x, y = 22, py + rows_n * pstep + 26
        h = int(y + total * gap + 8)
    else:
        w, x, y = 985, 390, 34
        h = int(y + total * gap + 8)
        px, py = 372 - max(map(len, PORTRAIT["rows"])) * psize * CHAR, (h - rows_n * pstep) / 2 + 8
    art, art_css = portrait(px, py, psize, pstep, t)
    head, type_css = typed_prompt(x, y, "neofetch", t, size, .3)
    body = [art, head]
    for i, spans in enumerate(lines, start=1):
        if spans:
            body.append(line(x, y + i * gap, spans, size, width, anim("in", 1.1 + i * .05)))
    body.append(cursor_prompt(x, y + (total - 1) * gap, t, size, 1.1 + total * .05))
    return svg(w, h, t, "Aryaman Sharma — security, dev tooling and infra; Frappe contributor", "".join(body), art_css + type_css)


def radar(repos, updated, t, mobile=False):
    w, h = (480, 470) if mobile else (985, 440)
    cx, cy, R, period = w / 2, h / 2 + 12, (125 if mobile else 160), 6.0
    contacts = repos[:6] if mobile else repos[:8]
    rings = "".join(f'<circle cx="{cx}" cy="{cy}" r="{R * k / 4:.1f}" fill="none" stroke="{t["border"]}"/>' for k in range(1, 5))
    cross = f'<path d="M{cx - R},{cy} H{cx + R} M{cx},{cy - R} V{cy + R}" stroke="{t["border"]}"/>'
    wedges = "".join(
        f'<path d="M{cx},{cy} L{cx + R * math.cos(math.radians(-(k + 1) * 3)):.1f},{cy + R * math.sin(math.radians(-(k + 1) * 3)):.1f} '
        f'A{R},{R} 0 0 1 {cx + R * math.cos(math.radians(-k * 3)):.1f},{cy + R * math.sin(math.radians(-k * 3)):.1f} Z" fill="{t["value"]}" opacity="{.2 * (1 - k / 18):.3f}"/>'
        for k in range(18))
    blips = []
    for i, repo in enumerate(contacts):
        theta = math.radians(-70 + i * 360 / len(contacts))
        dist = R * (.5 if i % 2 else .84)
        bx, by = cx + dist * math.cos(theta), cy + dist * math.sin(theta)
        delay = theta % (2 * math.pi) / (2 * math.pi) * period
        anchor = "start" if math.cos(theta) > .3 else "end" if math.cos(theta) < -.3 else "middle"
        lx = bx + {"start": 11, "end": -11, "middle": 0}[anchor]
        ly = by + (4 if anchor != "middle" else -11 if math.sin(theta) < 0 else 19)
        blips.append(f'<circle class="ping" style="animation-delay:{delay:.2f}s" cx="{bx:.1f}" cy="{by:.1f}" r="4" fill="none" stroke="{t["add"]}"/>'
                     f'<circle class="blip" style="animation-delay:{delay:.2f}s" cx="{bx:.1f}" cy="{by:.1f}" r="4" fill="{t["add"]}"/>'
                     f'<text class="lb" style="animation-delay:{delay:.2f}s" x="{lx:.1f}" y="{ly:.1f}" font-size="{12 if mobile else 13}" text-anchor="{anchor}">{escape(repo["name"])}</text>')
    css = (f".sweep{{transform-origin:{cx}px {cy}px;animation:sw {period}s linear infinite}}@keyframes sw{{to{{transform:rotate(360deg)}}}}"
           f".blip{{opacity:.35;animation:bl {period}s linear infinite}}@keyframes bl{{0%{{opacity:1}}60%,100%{{opacity:.35}}}}"
           f".ping{{opacity:0;transform-box:fill-box;transform-origin:center;animation:pg {period}s ease-out infinite}}@keyframes pg{{0%{{opacity:.8;transform:scale(1)}}30%,100%{{opacity:0;transform:scale(5)}}}}"
           f".lb{{fill:{t['muted']};animation:lb {period}s linear infinite}}@keyframes lb{{0%{{fill:{t['text']}}}60%,100%{{fill:{t['muted']}}}}}")
    size = 13 if mobile else 15
    footer = line(w - 28, h - 20, [(f"{len(contacts)} public repos · updated {updated}", t["dim"])], 12, anchor="end")
    body = (prompt(28, 38, "scan --repos", t, size) + rings + cross
            + f'<g class="sweep">{wedges}<line x1="{cx}" y1="{cy}" x2="{cx + R}" y2="{cy}" stroke="{t["value"]}" stroke-width="1.5"/></g>'
            + "".join(blips) + footer)
    return svg(w, h, t, "Radar of my most recently updated public repositories", body, css)


def pill(label, t):
    size, h = 14, 34
    spans = [("~/", t["dim"]), (label, t["key"]), (" →", t["dim"])]
    w = int(sum(len(s) for s, _ in spans) * size * CHAR + 34)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}" role="img">'
            f'<title>{escape(label)}</title><rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{h / 2 - .5}" fill="{t["bg"]}" stroke="{t["border"]}"/>'
            f'{line(17, 22, spans, size)}</svg>')
