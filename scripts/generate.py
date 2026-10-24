"""Render theme-aware profile artwork from public GitHub data."""
import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from xml.sax.saxutils import escape

from artwork import THEMES, pill, profile, radar

USER = "AryamanSharma14"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
CACHE = OUT / "stats.json"
RAW = f"https://raw.githubusercontent.com/{USER}/{USER}/main/assets/"
HIDDEN = re.compile(r"quantum|pqc|qsetu|shield", re.I)
LINKS = [
    ("linkedin", "https://www.linkedin.com/in/aryamansharma14/"),
    ("portfolio", "https://aryamansharma14.vercel.app/"),
    ("email", "mailto:aryamansharma4810@gmail.com"),
    ("pull-requests", "https://github.com/pulls?" + urlencode({"q": f"is:pr author:{USER} is:public"})),
]
CALENDAR = 'query { user(login: "%s") { contributionsCollection { contributionCalendar { totalContributions } } } }' % USER


def request(url, payload=None, headers=None):
    data = json.dumps(payload).encode() if payload else None
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers or {}), timeout=30) as response:
        return response.status, json.loads(response.read() or b"null")


def headers():
    return {"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"], "Accept": "application/vnd.github+json", "User-Agent": USER + "-profile"}


def gh(path, payload=None):
    return request("https://api.github.com" + path, payload, headers())[1]


def code_lines(repos):
    """Own additions/deletions per repo; GitHub answers 202 while it computes, so retry and fall back to the last run."""
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}

    def one(repo):
        for _ in range(6):
            status, authors = request(f"https://api.github.com/repos/{USER}/{repo['name']}/stats/contributors", headers=headers())
            if status == 200:
                mine = [a for a in authors or [] if a["author"] and a["author"]["login"] == USER]
                return repo["name"], [sum(w["a"] for a in mine for w in a["weeks"]), sum(w["d"] for a in mine for w in a["weeks"])]
            time.sleep(4)
        return repo["name"], cache.get(repo["name"], [0, 0])

    with ThreadPoolExecutor(max_workers=6) as pool:
        result = dict(pool.map(one, repos))
    CACHE.write_text(json.dumps(result, indent=1, sort_keys=True))
    return sum(a for a, _ in result.values()), sum(d for _, d in result.values())


def uptime(created):
    start, today = datetime.fromisoformat(created.replace("Z", "+00:00")).date(), date.today()
    years, months, days = today.year - start.year, today.month - start.month, today.day - start.day
    if days < 0:
        months -= 1
        previous = date(today.year - (today.month == 1), (today.month - 2) % 12 + 1, 1)
        days += (date(today.year, today.month, 1) - previous).days
    if months < 0:
        years, months = years - 1, months + 12
    return f"{years} years, {months} months, {days} days"


def last_push():
    for event in gh(f"/users/{USER}/events/public?per_page=100"):
        name = event["repo"]["name"]
        if event["type"] == "PushEvent" and name != f"{USER}/{USER}" and not HIDDEN.search(name):
            return f"{name} · {event['created_at'][:10]}"
    return "—"


def pr_count(extra):
    response = gh("/search/issues?" + urlencode({"q": f"is:pr author:{USER} is:public {extra}", "per_page": 1}))
    if response.get("incomplete_results"):
        raise RuntimeError("GitHub PR search returned incomplete results; retry the refresh.")
    return response["total_count"]


def languages(repos):
    if key := os.environ.get("WAKATIME_API_KEY"):
        auth = base64.b64encode(key.encode()).decode()
        stats = request("https://wakatime.com/api/v1/users/current/stats/last_7_days", headers={"Authorization": "Basic " + auth})[1]
        totals = {row["name"]: row["total_seconds"] for row in stats["data"]["languages"]}
        if sum(totals.values()):
            return [name for name, _ in sorted(totals.items(), key=lambda p: -p[1])[:3]]
    totals = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for langs in pool.map(lambda r: gh(f"/repos/{USER}/{r['name']}/languages"), repos):
            for name, size in langs.items():
                totals[name] = totals.get(name, 0) + size
    return [name for name, _ in sorted(totals.items(), key=lambda p: -p[1])[:3]]


def collect():
    user = gh(f"/users/{USER}")
    repos, page = [], 1
    while True:
        batch = gh(f"/users/{USER}/repos?per_page=100&sort=pushed&page={page}")
        repos += [r for r in batch if not r["fork"] and r["name"].lower() != USER.lower() and not HIDDEN.search(r["name"] + " " + (r.get("description") or ""))]
        if len(batch) < 100:
            break
        page += 1
    result = gh("/graphql", {"query": CALENDAR})
    if result.get("errors"):
        raise RuntimeError("GitHub contributions query failed: " + result["errors"][0]["message"])
    return dict(
        user=user, repos=repos, calendar=result["data"]["user"]["contributionsCollection"]["contributionCalendar"],
        prs=(pr_count(""), pr_count("is:merged")), frappe=(pr_count("org:frappe"), pr_count("org:frappe is:merged")),
        langs=languages(repos), loc=code_lines(repos), last_push=last_push(), updated=datetime.now(timezone.utc).date().isoformat(),
    )


def card_rows(data):
    added, removed = data["loc"]
    return [
        ("Name", "Aryaman Sharma"), ("Focus", "Security · Dev tooling · Infra · CLI"),
        ("Uptime", uptime(data["user"]["created_at"])), ("Languages", " · ".join(data["langs"])),
        None, ("section", "Projects"),
        ("Walflow", "Local-first background jobs"), ("Portscope", "Local runtime & port tooling"),
        None, ("section", "Frappe"),
        ("Pilot", "Processes · builds · security"), ("Press / Central", "Deployment tooling"),
        ("PRs", f"{data['frappe'][0]} opened | {data['frappe'][1]} merged"),
        None, ("section", "Contact"),
        ("LinkedIn", "in/aryamansharma14"), ("Portfolio", "aryamansharma14.vercel.app"), ("Email", "aryamansharma4810@gmail.com"),
        None, ("section", "GitHub Stats"),
        ("Pull requests", f"{data['prs'][0]} opened | {data['prs'][1]} merged"),
        ("Contributions", f"{data['calendar']['totalContributions']:,} in the past year"),
        ("Lines of code", [(f"{added - removed:,} ( ", "value"), (f"+{added:,}", "add"), (", ", "value"), (f"-{removed:,}", "remove"), (" )", "value")]),
        ("Last push", data["last_push"]),
    ]


def picture(stem, alt, href=None, mobile=True):
    sources = ""
    if mobile:
        sources += "".join(f'    <source media="(max-width: 600px) and (prefers-color-scheme: {m})" srcset="{RAW}{stem}-{m}-mobile.svg" />\n' for m in ["dark", "light"])
        sources += f'    <source media="(max-width: 600px)" srcset="{RAW}{stem}-light-mobile.svg" />\n'
    sources += f'    <source media="(prefers-color-scheme: dark)" srcset="{RAW}{stem}-dark.svg" />\n'
    body = f'  <picture>\n{sources}    <img src="{RAW}{stem}-light.svg" width="900" alt="{escape(alt)}" />\n  </picture>\n'
    return '<p align="center">\n' + (f'  <a href="{href}">\n{body}  </a>\n' if href else body) + '</p>\n'


def pills():
    items = "\n".join(
        f'  <a href="{escape(url, {chr(34): "&quot;"})}"><picture><source media="(prefers-color-scheme: dark)" srcset="{RAW}pill-{name}-dark.svg" />'
        f'<img src="{RAW}pill-{name}-light.svg" height="34" alt="{name}" /></picture></a>'
        for name, url in LINKS)
    return f'<p align="center">\n{items}\n</p>\n'


def readme():
    return "\n".join([
        picture("profile", "Aryaman Sharma — ASCII portrait with a neofetch-style card: security, dev tooling, infra, Frappe work, contact details and live GitHub stats.", f"https://github.com/{USER}"),
        pills(),
        picture("radar", "Radar sweeping over my most recently updated public repositories."),
        picture("snake", "Snake eating my GitHub contributions.", f"https://github.com/{USER}?tab=overview", mobile=False),
    ])


def render(data):
    OUT.mkdir(exist_ok=True)
    rows = card_rows(data)
    for mode, theme in THEMES.items():
        for mobile in [False, True]:
            suffix = mode + ("-mobile" if mobile else "")
            (OUT / f"profile-{suffix}.svg").write_text(profile(rows, theme, mobile), encoding="utf-8")
            (OUT / f"radar-{suffix}.svg").write_text(radar(data["repos"], data["updated"], theme, mobile), encoding="utf-8")
        for name, _ in LINKS:
            (OUT / f"pill-{name}-{mode}.svg").write_text(pill(name, theme), encoding="utf-8")
    (ROOT / "README.md").write_text(readme(), encoding="utf-8")


def main():
    if not os.environ.get("GITHUB_TOKEN"):
        raise SystemExit("GITHUB_TOKEN is required. Set it to a GitHub token with read access to public profile data.")
    try:
        data = collect()
    except (urllib.error.URLError, KeyError, RuntimeError) as error:
        raise SystemExit(f"Could not refresh profile data: {error}") from error
    render(data)
    print("Rendered profile, radar and link pills (dark/light, desktop/mobile) and README.md.")


if __name__ == "__main__":
    main()
