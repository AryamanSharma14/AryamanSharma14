"""Render theme-aware profile artwork from public GitHub data."""
import base64
import json
import os
import re
import urllib.error
import urllib.request
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from artwork import THEMES, profile

USER = "AryamanSharma14"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
HIDDEN = re.compile(r"quantum|pqc|qsetu|shield", re.I)


def request(url, payload=None, headers=None):
    data = json.dumps(payload).encode() if payload else None
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers or {}), timeout=30) as response:
        return json.load(response)


def gh(path, payload=None):
    return request("https://api.github.com" + path, payload, {"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"], "Accept": "application/vnd.github+json", "User-Agent": USER + "-profile"})


def collect():
    user = gh(f"/users/{USER}")
    repos, page = [], 1
    while True:
        batch = gh(f"/users/{USER}/repos?per_page=100&sort=pushed&page={page}")
        repos.extend(r for r in batch if not r["fork"] and not r.get("private") and r["name"].lower() != USER.lower() and not HIDDEN.search(r["name"] + " " + (r.get("description") or "")))
        if len(batch) < 100:
            break
        page += 1
    query = 'query { user(login: "' + USER + '") { contributionsCollection { contributionCalendar { totalContributions } } } }'
    result = gh("/graphql", {"query": query})
    if result.get("errors"):
        raise RuntimeError("GitHub contributions query failed: " + result["errors"][0]["message"])
    contributions = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    def pr_count(extra):
        response = gh("/search/issues?" + urlencode({"q": f"is:pr author:{USER} is:public {extra}", "per_page": 1}))
        if response.get("incomplete_results"):
            raise RuntimeError("GitHub PR search returned incomplete results; retry the refresh.")
        return response["total_count"]
    counts = {"opened": pr_count(""), "merged": pr_count("is:merged"), "frappe_opened": pr_count("org:frappe"), "frappe_merged": pr_count("org:frappe is:merged")}
    source = "PUBLIC REPOSITORIES / BY CODE SIZE"
    totals = {}
    if key := os.environ.get("WAKATIME_API_KEY"):
        auth = base64.b64encode(key.encode()).decode()
        stats = request("https://wakatime.com/api/v1/users/current/stats/last_7_days", headers={"Authorization": "Basic " + auth})
        totals = {row["name"]: row["total_seconds"] for row in stats["data"]["languages"]}
        source = "CODING TIME / LAST 7 DAYS"
    if not sum(totals.values()):
        with ThreadPoolExecutor(max_workers=6) as pool:
            for languages in pool.map(lambda r: gh(f"/repos/{USER}/{r['name']}/languages"), repos):
                for language, size in languages.items():
                    totals[language] = totals.get(language, 0) + size
        source = "PUBLIC REPOSITORIES / BY CODE SIZE"
    total = sum(totals.values()) or 1
    langs = [(name, size / total * 100) for name, size in sorted(totals.items(), key=lambda p: -p[1])[:6]]
    return dict(user=user, repos=repos, contributions=contributions, counts=counts, langs=langs, source=source, updated=datetime.now(timezone.utc).date().isoformat())


def picture(stem, alt, href=None, responsive=True):
    raw = f"https://raw.githubusercontent.com/{USER}/{USER}/main/assets/"
    result = '<p align="center">\n' + (f'  <a href="{href}">\n' if href else '') + '  <picture>\n'
    if responsive:
        for mode in ["dark", "light"]:
            result += f'    <source media="(max-width: 600px) and (prefers-color-scheme: {mode})" srcset="{raw}{stem}-{mode}-mobile.svg" />\n'
        result += f'    <source media="(max-width: 600px)" srcset="{raw}{stem}-light-mobile.svg" />\n'
    result += f'    <source media="(prefers-color-scheme: dark)" srcset="{raw}{stem}-dark.svg" />\n'
    result += f'    <img src="{raw}{stem}-light.svg" width="900" alt="{escape(alt)}" />\n  </picture>\n'
    return result + ('  </a>\n' if href else '') + '</p>\n'


def link(value, url):
    return f'<a href="{escape(url, {chr(34): "&quot;"})}">{escape(value)}</a>'


def readme(data):
    result=picture("profile","Aryaman Sharma — ASCII portrait; Frappe, backend infrastructure, CLI tooling, Walflow, Portscope, contact details, and public PR counts.",f"https://github.com/{USER}")
    result+='\n<p align="center">'+" &nbsp;·&nbsp; ".join(link(label,url) for label,url in [("LinkedIn","https://www.linkedin.com/in/aryamansharma14/"),("Portfolio","https://aryamansharma14.vercel.app/"),("Email","mailto:aryamansharma4810@gmail.com"),("Walflow",f"https://github.com/{USER}/walflow"),("Portscope",f"https://github.com/{USER}/portscope"),("Pull requests","https://github.com/pulls?"+urlencode({"q":f"is:pr author:{USER} is:public"})),("Frappe PRs","https://github.com/pulls?"+urlencode({"q":f"is:pr author:{USER} org:frappe is:public"}))])+'</p>\n'
    result+='\n'+picture('snake','Animated Snake eating my actual GitHub contributions.',f'https://github.com/{USER}?tab=overview',False)
    return result


def main():
    if not os.environ.get("GITHUB_TOKEN"):
        raise SystemExit("GITHUB_TOKEN is required. Set it to a GitHub token with read access to public profile data.")
    try:
        data = collect()
    except (urllib.error.URLError, KeyError, RuntimeError) as error:
        raise SystemExit(f"Could not refresh profile data: {error}") from error
    render(data)


def render(data):
    OUT.mkdir(exist_ok=True)
    for mode,theme in THEMES.items():
        for mobile in [False,True]:
            suffix=mode+("-mobile" if mobile else "")
            (OUT/f"profile-{suffix}.svg").write_text(profile(data,theme,mobile),encoding="utf-8")
    (ROOT/"README.md").write_text(readme(data),encoding="utf-8")
    print("Rendered four profile variants and README.md.")


if __name__ == "__main__":
    main()
