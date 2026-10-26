#!/usr/bin/env python3
"""Job scout: collect roles broadly, let JEV score each one against your profile, report the best new matches.

Commands:
  collect            Fetch every seeded company job board (Greenhouse, Lever, Ashby, SmartRecruiters).
  add-web FILE       Ingest roles found by web search (JSON list) and auto-add any new company boards.
  assess [--dry-run] Send new or changed roles to JEV.
  report             Write the shortlist (Markdown + CSV) to reports/ and print it.
  run [--web FILE]   collect -> add-web -> assess -> report.
  discover NAMES...  Find job boards for employers (nine job systems, plus --careers-url pages) and add them.
  dismiss IDS...     Leave roles out of future New matches (filled, closed or ineligible).
  check              Check the JEV key and job-board access work, in plain words.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import re
import sqlite3
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "jobs.sqlite"
REPORTS = ROOT / "reports"
JEV_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
UA = {"User-Agent": "job-scout/1.0 (personal job search)"}
CA_FILE = os.getenv("SSL_CERT_FILE") or ("/etc/ssl/cert.pem" if Path("/etc/ssl/cert.pem").is_file() else None)
TLS = ssl.create_default_context(cafile=CA_FILE)

AU_TERMS = ("australia", "sydney", "nsw", "new south wales", "victoria", "queensland", "tasmania", "parramatta",
            "north sydney", "macquarie park", "gold coast", "newcastle", "wollongong", "geelong", "hobart", "darwin", "melbourne", "brisbane", "perth", "adelaide", "canberra", "anz",
            "apac", "asia pacific", "asia-pacific", ", au", "(au)", " au ")
ANYWHERE_TERMS = ("remote", "anywhere", "global", "worldwide", "distributed")

# ---------------------------------------------------------------- JEV questions
# Everything person-specific comes from profile.json. JEV is asked every dimension that has a weight in
# config.json, plus every hard exclusion. AGENTS.md explains each one to the person in plain words.
DIMENSIONS = {
    "experience_match": ("How well do the person's `experience` and `skills` in `candidate` match what `job` requires day to day? "
                         "Judge against the actual responsibilities and requirements, not the title.",
                         ["No meaningful match", "Weak, mostly transferable", "Partial match with clear gaps",
                          "Strong match with minor gaps", "Excellent, direct match"]),
    "target_fit": ("How closely does `job` match the kinds of roles described in `candidate.target_roles`?",
                   ["Unrelated", "Loosely related", "Adjacent role", "Close match", "Exactly the role they want"]),
    "enjoyment": ("Based on `candidate.enjoys`, how much would the candidate enjoy the actual day-to-day work in `job`?",
                  ["Work they would dislike", "Little they enjoy", "Some enjoyable elements",
                   "Mostly work they enjoy", "Exactly the work they enjoy"]),
    "wants_match": ("How well do `job` and its employer offer what `candidate.wants` describes?",
                    ["Nothing they want", "Little of what they want", "Some of what they want",
                     "Most of what they want", "Everything they want"]),
    "practicality": ("How practical is `job` for the candidate given `candidate.location` and `candidate.seniority`?",
                     ["Impractical location or level", "Major location or level mismatch",
                      "Workable with notable compromises", "Practical with minor compromises", "Ideal location and level"]),
    "career_growth": ("How much would `job` move the candidate towards the career and life goals described in "
                      "`candidate.target_roles`, `candidate.wants` and `candidate.life_goals`?",
                      ["Step backwards", "Sideways move", "Some growth", "Clear step up", "Major career accelerator"]),
    "community_impact": ("How much real-world good do the employer in `job` and the role itself do, as `candidate.purpose` "
                         "describes? Judge what the organisation actually changes for people and communities, not whether it "
                         "is a charity. Ordinary commercial products with little benefit beyond profit score low, and so do "
                         "harmful businesses.",
                         ["No meaningful benefit, or net harmful", "Ordinary commercial product, marginal benefit",
                          "Useful product with some indirect benefit to communities",
                          "Tackles a real societal problem with clear benefit at scale",
                          "Moves the needle on a major societal challenge, and the role drives it"]),
}
CONSTRAINTS = {
    "is_not_a_real_job": "Is `job` something other than a specific open job vacancy (e.g. a general talent pool, careers landing page, event or article)?",
    "location_ruled_out": "Does `job` require living or working somewhere `candidate.location` rules out, such as overseas?",
    "matches_avoid": "Is `job` the kind of role `candidate.avoid` says the candidate does not want?",
    "wrong_level": "Is `job` clearly far more junior or far more senior than `candidate.seniority`?",
    "needs_credential": "Does `job` require a professional licence, registration or qualification that `candidate` "
                        "does not show they hold?",
}


def jev_questions(cfg) -> dict:
    q = {k: {"type": "score", "instructions": DIMENSIONS[k][0], "criteria": DIMENSIONS[k][1]} for k in cfg["weights"]}
    q.update({k: {"type": "noul", "instructions": ins} for k, ins in CONSTRAINTS.items()})
    return q


# ---------------------------------------------------------------- helpers
def load(name: str):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def http_json(url: str, data: dict | None = None, headers: dict | None = None, timeout: int = 30):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers={**UA, **(headers or {}),
                                 **({"Content-Type": "application/json"} if body else {})})
    with urllib.request.urlopen(req, context=TLS, timeout=timeout) as r:
        return json.load(r)


def strip_html(s: str | None) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</(p|li|h\d|div)>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", s)).strip()


def location_ok(loc: str) -> bool:
    l = f" {(loc or '').lower()} "
    if any(t in l for t in AU_TERMS):
        return True
    rest = re.sub(r"[^a-z]+", " ", l)
    for t in ANYWHERE_TERMS:
        rest = rest.replace(t, " ")
    return any(t in l for t in ANYWHERE_TERMS) and not rest.strip()   # e.g. "Remote", "Anywhere"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.executescript("""
    create table if not exists jobs(
      id text primary key, company text, title text, location text, url text, description text,
      source text, hash text, first_seen text, last_seen text, open integer default 1);
    create table if not exists assessments(
      job_id text, hash text, assessed text, model text, score real, confidence real, excluded text, detail text,
      primary key(job_id, hash));
    create table if not exists reported(job_id text, hash text, reported text, primary key(job_id, hash));
    create table if not exists runs(id integer primary key, started text, collected integer, assessed integer, notes text);
    """)
    return c


def excluded_employer(company: str) -> bool:
    terms = load("config.json").get("exclude_employers", [])
    return any(t.lower() in (company or "").lower() for t in terms)


def upsert(c: sqlite3.Connection, job: dict, seen: str) -> None:
    if excluded_employer(job.get("company", "")):
        return
    desc = job.get("description", "")[:12000]
    norm = re.sub(r'\s+', ' ', desc)
    h = hashlib.sha256(f"{job['title']}|{job['location']}|{norm}".encode()).hexdigest()[:16]
    c.execute("""insert into jobs(id,company,title,location,url,description,source,hash,first_seen,last_seen,open)
                 values(?,?,?,?,?,?,?,?,?,?,1)
                 on conflict(id) do update set title=excluded.title, location=excluded.location, url=excluded.url,
                   description=excluded.description, hash=excluded.hash, last_seen=excluded.last_seen, open=1""",
              (job["id"], job["company"], job["title"], job["location"], job["url"], desc, job["source"], h, seen, seen))


# ---------------------------------------------------------------- collectors
def fetch_greenhouse(src):
    d = http_json(f"https://boards-api.greenhouse.io/v1/boards/{src['token']}/jobs?content=true", timeout=60)
    for j in d.get("jobs", []):
        yield {"id": f"gh:{src['token']}:{j['id']}", "title": j["title"], "location": (j.get("location") or {}).get("name", ""),
               "url": j["absolute_url"], "description": strip_html(j.get("content"))}


def fetch_lever(src):
    for j in http_json(f"https://api.lever.co/v0/postings/{src['token']}?mode=json", timeout=60):
        cats = j.get("categories") or {}
        loc = ", ".join(filter(None, [cats.get("location"), *(cats.get("allLocations") or []), j.get("workplaceType")]))
        lists = "\n".join(f"{l.get('text')}\n{strip_html(l.get('content'))}" for l in j.get("lists") or [])
        yield {"id": f"lever:{src['token']}:{j['id']}", "title": j["text"], "location": loc, "url": j["hostedUrl"],
               "description": "\n".join(filter(None, [j.get("descriptionPlain"), lists, j.get("additionalPlain")]))}


def fetch_ashby(src):
    d = http_json(f"https://api.ashbyhq.com/posting-api/job-board/{src['token']}?includeCompensation=true", timeout=60)
    for j in d.get("jobs", []):
        locs = [j.get("location") or ""] + [s.get("location", "") for s in j.get("secondaryLocations") or []]
        if j.get("isRemote"):
            locs.append("Remote")
        comp = (j.get("compensation") or {}).get("compensationTierSummary") or ""
        yield {"id": f"ashby:{src['token']}:{j['id']}", "title": j["title"], "location": ", ".join(filter(None, locs)),
               "url": j.get("jobUrl"), "description": "\n".join(filter(None, [j.get("descriptionPlain"), comp]))}


def fetch_smartrecruiters(src):
    offset = 0
    while True:
        d = http_json(f"https://api.smartrecruiters.com/v1/companies/{src['token']}/postings?country=au&limit=100&offset={offset}")
        for p in d.get("content", []):
            loc = p.get("location") or {}
            try:
                full = http_json(f"https://api.smartrecruiters.com/v1/companies/{src['token']}/postings/{p['id']}")
                sections = (full.get("jobAd") or {}).get("sections") or {}
                desc = "\n".join(strip_html((sections.get(k) or {}).get("text")) for k in
                                 ("companyDescription", "jobDescription", "qualifications", "additionalInformation"))
                url = full.get("postingUrl") or full.get("applyUrl")
            except Exception:
                desc, url = "", None
            yield {"id": f"sr:{src['token']}:{p['id']}", "title": p["name"],
                   "location": ", ".join(filter(None, [loc.get("city"), loc.get("region"), loc.get("country"),
                                                        "Remote" if loc.get("remote") else ""])),
                   "url": url or f"https://jobs.smartrecruiters.com/{src['token']}/{p['id']}", "description": desc}
        offset += 100
        if offset >= d.get("totalFound", 0):
            break


def fetch_workable(src):
    d = http_json(f"https://apply.workable.com/api/v1/widget/accounts/{src['token']}?details=true", timeout=60)
    for j in d.get("jobs", []):
        loc = ", ".join(filter(None, [j.get("city"), j.get("state"), j.get("country"), "Remote" if j.get("telecommuting") else ""]))
        yield {"id": f"workable:{src['token']}:{j.get('shortcode')}", "title": j["title"], "location": loc,
               "url": j.get("url") or j.get("application_url"), "description": strip_html(j.get("description"))}


def fetch_recruitee(src):
    for o in http_json(f"https://{src['token']}.recruitee.com/api/offers/").get("offers", []):
        yield {"id": f"recruitee:{src['token']}:{o['id']}", "title": o["title"],
               "location": ", ".join(filter(None, [o.get("location"), o.get("country"), "Remote" if o.get("remote") else ""])),
               "url": o.get("careers_url"), "description": strip_html((o.get("description") or "") + (o.get("requirements") or ""))}


def fetch_bamboohr(src):
    for j in http_json(f"https://{src['token']}.bamboohr.com/careers/list").get("result", []):
        loc = {k: v for d in (j.get("location") or {}, j.get("atsLocation") or {}) for k, v in d.items() if v}
        loc = ", ".join(filter(None, [loc.get("city"), loc.get("state"), loc.get("province"), loc.get("country"),
                                      "Remote" if j.get("isRemote") else ""]))
        url = f"https://{src['token']}.bamboohr.com/careers/{j['id']}"
        try:
            desc = strip_html(((http_json(url + "/detail").get("result") or {}).get("jobOpening") or {}).get("description"))
        except Exception:
            desc = ""
        yield {"id": f"bamboohr:{src['token']}:{j['id']}", "title": j.get("jobOpeningName", ""), "location": loc, "url": url,
               "description": desc}


def fetch_breezy(src):
    for j in http_json(f"https://{src['token']}.breezy.hr/json"):
        loc = j.get("location") or {}
        loc = ", ".join(filter(None, [loc.get("name"), (loc.get("country") or {}).get("name"),
                                      "Remote" if loc.get("is_remote") else ""]))
        yield {"id": f"breezy:{src['token']}:{j['id']}", "title": j["name"], "location": loc, "url": j.get("url"),
               "description": strip_html(j.get("description"))}


def fetch_personio(src):
    import xml.etree.ElementTree as ET
    req = urllib.request.Request(f"https://{src['token']}.jobs.personio.com/xml", headers=UA)
    with urllib.request.urlopen(req, context=TLS, timeout=30) as r:
        root = ET.fromstring(r.read())
    for p in root.findall("position"):
        desc = "\n".join(f"{d.findtext('name')}\n{strip_html(d.findtext('value'))}" for d in p.iter("jobDescription"))
        jid = p.findtext("id")
        yield {"id": f"personio:{src['token']}:{jid}", "title": p.findtext("name") or "", "location": p.findtext("office") or "",
               "url": f"https://{src['token']}.jobs.personio.com/job/{jid}", "description": desc}


def fetch_workday(src):
    base = f"https://{src['host']}/wday/cxs/{src['tenant']}/{src['site']}"
    offset, total = 0, 1
    while offset < total and offset < 2000:
        d = http_json(f"{base}/jobs", {"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": ""})
        total = d.get("total", 0) if offset == 0 else total
        for j in d.get("jobPostings", []):
            loc = j.get("locationsText") or "; ".join(j.get("bulletFields") or [])
            if loc and not location_ok(loc) and not re.match(r"\d+ Locations", loc):
                continue  # skip obviously overseas roles before fetching detail
            try:
                info = http_json(base + j["externalPath"]).get("jobPostingInfo") or {}
            except Exception:
                continue
            locs = ", ".join(filter(None, [info.get("location"), *(info.get("additionalLocations") or []), info.get("country", {}).get("descriptor") if isinstance(info.get("country"), dict) else None]))
            yield {"id": f"workday:{src['tenant']}:{info.get('jobReqId') or j['externalPath']}", "title": info.get("title") or j.get("title"),
                   "location": locs or loc, "url": info.get("externalUrl") or f"https://{src['host']}/{src['site']}{j['externalPath']}",
                   "description": strip_html(info.get("jobDescription"))}
        offset += 20


def fetch_oracle(src):
    api = f"https://{src['host']}/hcmRestApi/resources/latest"
    offset = 0
    while True:
        d = http_json(f"{api}/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList.secondaryLocations"
                      f"&finder=findReqs;siteNumber={src['site']},limit=100,offset={offset},sortBy=POSTING_DATES_DESC")
        item = (d.get("items") or [{}])[0]
        reqs = item.get("requisitionList") or []
        for j in reqs:
            loc = ", ".join(filter(None, [j.get("PrimaryLocation"), *[x.get("Name") for x in j.get("secondaryLocations") or []]]))
            if not location_ok(loc):
                continue
            try:
                det = http_json(f"{api}/recruitingCEJobRequisitionDetails?onlyData=true&expand=all"
                                f"&finder=ById;Id=%22{j['Id']}%22,siteNumber={src['site']}")["items"][0]
                desc = strip_html("\n".join(filter(None, [det.get("ExternalDescriptionStr"), det.get("ExternalResponsibilitiesStr"),
                                                          det.get("ExternalQualificationsStr")])))
            except Exception:
                desc = j.get("ShortDescriptionStr") or ""
            yield {"id": f"oracle:{src['host'].split('.')[0]}:{j['Id']}", "title": j.get("Title", ""), "location": loc,
                   "url": f"https://{src['host']}/hcmUI/CandidateExperience/en/sites/{src['site']}/job/{j['Id']}", "description": desc}
        offset += 100
        if not item.get("hasMore") and offset >= (item.get("TotalJobsCount") or 0):
            break


def fetch_atlassian(src):
    for j in http_json("https://www.atlassian.com/endpoint/careers/listings", timeout=60):
        yield {"id": f"atlassian:atlassian:{j.get('id')}", "title": j.get("title", ""), "location": ", ".join(j.get("locations") or []),
               "url": j.get("applyUrl") or f"https://www.atlassian.com/company/careers/details/{j.get('id')}",
               "description": strip_html("\n".join(filter(None, [j.get("overview"), j.get("responsibilities"), j.get("qualifications")])))}


def _page_job(url: str) -> dict | None:
    """Read one job page: schema.org JobPosting JSON-LD first, then SuccessFactors-style microdata."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible) job-scout"})
    with urllib.request.urlopen(req, context=TLS, timeout=30) as r:
        h = r.read(1500000).decode("utf-8", "replace")
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', h, re.S):
        try:
            data = json.loads(block)
        except Exception:
            continue
        for d in data if isinstance(data, list) else data.get("@graph", [data]):
            if isinstance(d, dict) and d.get("@type") == "JobPosting":
                locs = d.get("jobLocation") or []
                locs = locs if isinstance(locs, list) else [locs]
                parts = []
                for l in locs:
                    addr = (l.get("address") or {}) if isinstance(l, dict) else {}
                    if isinstance(addr, dict):
                        country = addr.get("addressCountry")
                        country = country.get("name") if isinstance(country, dict) else country
                        parts.append(", ".join(filter(None, [addr.get("addressLocality"), addr.get("addressRegion"), country])))
                place = "; ".join(filter(None, parts))
                if d.get("jobLocationType") == "TELECOMMUTE":
                    place += ", Remote"
                org = d.get("hiringOrganization")
                return {"title": html.unescape(d.get("title", "")), "location": place,
                        "description": strip_html(d.get("description")),
                        "company": org.get("name") if isinstance(org, dict) else None}
    title = re.search(r'itemprop="title"[^>]*>([^<]+)<', h) or re.search(r"<title>([^<|]+)", h)
    loc = (re.search(r'class="jobGeoLocation"[^>]*>([^<]+)<', h) or re.search(r'itemprop="streetAddress" content="([^"]+)"', h)
           or re.search(r'data-careersite-propertyid="city"[^>]*>([^<]+)<', h))
    desc = re.search(r'itemprop="description"[^>]*>(.*?)(?:<div[^>]+class="[^"]*(?:applylink|social)|</article>|$)', h, re.S)
    if not title:
        return None
    return {"title": html.unescape(title.group(1)).strip(), "location": strip_html(loc.group(1)) if loc else "",
            "description": strip_html(desc.group(1)) if desc else "", "company": None}


def fetch_sitemap(src, known_urls: set):
    """Any careers site with a sitemap. Only pages not already in the database are downloaded."""
    def locs(u):
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (compatible) job-scout"})
        with urllib.request.urlopen(req, context=TLS, timeout=30) as r:
            return [html.unescape(x) for x in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.read().decode("utf-8", "replace"))]
    urls = locs(src["sitemap"])
    for sub in [u for u in urls if u.endswith(".xml")][:20]:
        try:
            urls += locs(sub)
        except Exception:
            pass
    pattern = re.compile(src.get("job_pattern", r"/jobs?/"), re.I)
    key = urllib.parse.urlparse(src["sitemap"]).hostname
    new = [u for u in dict.fromkeys(urls) if pattern.search(u) and u not in known_urls]
    for u in [u for u in dict.fromkeys(urls) if pattern.search(u) and u in known_urls]:
        yield {"id": f"sitemap:{key}:{hashlib.sha256(u.encode()).hexdigest()[:16]}", "url": u, "_seen_only": True}

    def one(u):
        try:
            return u, _page_job(u)
        except Exception:
            return u, None
    with ThreadPoolExecutor(4) as pool:
        for u, job in pool.map(one, new):
            if job:
                yield {"id": f"sitemap:{key}:{hashlib.sha256(u.encode()).hexdigest()[:16]}", "url": u, **job,
                       "company": job.get("company") or src["company"]}


FETCHERS = {"greenhouse": fetch_greenhouse, "lever": fetch_lever, "ashby": fetch_ashby, "smartrecruiters": fetch_smartrecruiters,
            "workable": fetch_workable, "recruitee": fetch_recruitee, "bamboohr": fetch_bamboohr, "breezy": fetch_breezy,
            "personio": fetch_personio, "workday": fetch_workday, "oracle": fetch_oracle, "atlassian": fetch_atlassian,
            "sitemap": fetch_sitemap}
ATS_PATTERNS = [
    ("greenhouse", r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([\w-]+)"),
    ("lever", r"jobs\.lever\.co/([\w-]+)"),
    ("ashby", r"jobs\.ashbyhq\.com/([\w.-]+)"),
    ("smartrecruiters", r"(?:jobs|careers)\.smartrecruiters\.com/([\w-]+)"),
    ("workable", r"apply\.workable\.com/([\w-]+)"),
    ("recruitee", r"([\w-]+)\.recruitee\.com"),
    ("bamboohr", r"([\w-]+)\.bamboohr\.com"),
    ("breezy", r"([\w-]+)\.breezy\.hr"),
    ("personio", r"([\w-]+)\.jobs\.personio\.(?:com|de)"),
]
WORKDAY_URL = re.compile(r"https://(([\w-]+)\.wd\d+\.myworkdayjobs\.com)/(?:[a-z]{2}-[A-Z]{2}/)?([\w-]+)")


def detect_ats(url: str):
    m = WORKDAY_URL.search(url or "")
    if m and m.group(3) not in ("wday", "job"):
        return "workday", m.group(2), {"host": m.group(1), "tenant": m.group(2), "site": m.group(3)}
    for ats, pat in ATS_PATTERNS:
        m = re.search(pat, url or "", re.I)
        if m and m.group(1).lower() not in ("www", "api", "jobs", "app"):
            return ats, m.group(1), {"token": m.group(1)}
    return None


def collect(c: sqlite3.Connection) -> int:
    sources, seen, total = load("sources.json"), now(), 0
    errors = []

    known_urls = {r[0] for r in c.execute("select url from jobs where source='sitemap' and open=1")}

    def run_source(src):
        fetch = FETCHERS[src["ats"]]
        return src, list(fetch(src, known_urls) if src["ats"] == "sitemap" else fetch(src))

    with ThreadPoolExecutor(10) as pool:
        futures = {pool.submit(run_source, s): s for s in sources}
        for f in as_completed(futures):
            try:
                src, jobs = f.result()
            except Exception as e:  # one broken board should not stop the run
                errors.append(f"{futures[f]['company']}: {str(e)[:80]}"); continue
            ids = []
            for j in [j for j in jobs if j.get("_seen_only")]:
                c.execute("update jobs set last_seen=?, open=1 where id=?", (seen, j["id"]))
                ids.append(j["id"])
            fresh = [j for j in jobs if not j.get("_seen_only")]
            kept = [j for j in fresh if location_ok(j["location"])]
            for j in kept:
                upsert(c, {**j, "company": j.get("company") or src["company"], "source": src["ats"]}, seen)
                ids.append(j["id"])
            prefix = jobs[0]["id"].split(":")[0] + ":" + jobs[0]["id"].split(":")[1] + ":" if jobs else None
            if prefix:  # anything from this board not seen now has closed
                marks = ','.join('?' * len(ids)) or "''"
                c.execute(f"update jobs set open=0 where id like ? and id not in ({marks})",
                          [prefix + "%", *ids])
            total += len(ids)
            print(f"  {src['company'][:28]:<28} {len(jobs):>4} roles, {len(ids):>3} in Australia/remote")
    c.commit()
    if errors:
        print(f"  {len(errors)} board(s) failed: {errors}", file=sys.stderr)
    return total


def add_web(c: sqlite3.Connection, path: Path) -> int:
    items = json.loads(path.read_text(encoding="utf-8"))
    sources = load("sources.json")
    known = {(s["ats"], (s.get("token") or s.get("tenant") or s.get("sitemap") or "").lower()) for s in sources}
    seen, n, added = now(), 0, []
    norm_url = lambda u: re.sub(r"[?#].*$", "", u or "").rstrip("/").lower()
    have = {}  # roles already open (usually from a company board), so web copies don't get a second ID
    for r in c.execute("select id, company, title, url from jobs where open=1 order by source='web' desc"):
        have[norm_url(r["url"])] = r["id"]
        have[((r["company"] or "").lower().strip(), (r["title"] or "").lower().strip())] = r["id"]
    for it in items:
        if not it.get("url") or not it.get("title"):
            continue
        ats = detect_ats(it["url"])
        if ats and (ats[0], ats[1].lower()) not in known:
            sources.append({"company": it.get("company") or ats[1], "ats": ats[0], **ats[2]})
            known.add((ats[0], ats[1].lower())); added.append(f"{it.get('company')} ({ats[0]})")
        jid = "web:" + hashlib.sha256(re.sub(r"[?#].*$", "", it["url"]).encode()).hexdigest()[:20]
        dup = have.get(norm_url(it["url"])) or have.get(((it.get("company") or "").lower().strip(), it["title"].lower().strip()))
        if dup and dup != jid:
            continue
        upsert(c, {"id": jid, "company": it.get("company", ""), "title": it["title"], "location": it.get("location", ""),
                   "url": it["url"], "description": it.get("description", ""), "source": "web"}, seen)
        n += 1
    # web finds have no board to confirm closure; let them age out after three weeks
    c.execute("update jobs set open=0 where source='web' and last_seen < ?",
              ((datetime.now(timezone.utc) - timedelta(days=21)).isoformat(),))
    c.commit()
    if added:
        (ROOT / "sources.json").write_text(json.dumps(sources, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  Added {len(added)} new company board(s) to sources.json: {', '.join(added)}")
    return n


# ---------------------------------------------------------------- discovery
def _slugs(name: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", name.lower().replace("&", "and"))
    if not words:
        return []
    stop = {"bank", "group", "financial", "australia", "the", "and", "of", "limited", "ltd", "pty", "technologies", "global", "com", "au"}
    core = [w for w in words if w not in stop] or words
    c = "".join(core)
    out = {"".join(words), "-".join(words), c, words[0], c + "australia", c + "au", c + "-au", c + "-australia"}
    return [x for x in out if len(x) > 2]


def _probe(ats: str, slug: str) -> int:
    """Number of Australian/remote roles on this board, or 0 if it doesn't exist."""
    try:
        return sum(location_ok(j["location"]) for j in FETCHERS[ats]({"token": slug, "company": slug}))
    except Exception:
        return 0


def _careers_links(url: str) -> list:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible) job-scout"})
        with urllib.request.urlopen(req, context=TLS, timeout=20) as r:
            text = r.geturl() + " " + r.read(1500000).decode("utf-8", "replace")
    except Exception:
        return []
    found = []
    for u in set(re.findall(r"https?://[^\s\"'<>\\]+", html.unescape(text))):
        hit = detect_ats(u)
        if hit:
            found.append(hit)
        m = re.match(r"https://([\w.-]+\.oraclecloud\.com)/hcmUI/CandidateExperience/[a-z]{2}/sites/([\w-]+)", u)
        if m:
            found.append(("oracle", m.group(1), {"host": m.group(1), "site": m.group(2)}))
    return found


def discover(names: list[str], careers_urls: list[str]) -> int:
    """Find job boards for employer names (probing nine systems) and careers pages (reading their links)."""
    sources = load("sources.json")
    def key(s):
        return (s["ats"], (s.get("token") or s.get("tenant") or s.get("host") or s.get("sitemap") or "").lower())
    known = {key(s) for s in sources}
    probe_ats = ["greenhouse", "lever", "ashby", "smartrecruiters", "workable", "recruitee", "bamboohr", "breezy", "personio"]
    tasks = [(n, a, sl) for n in names for sl in _slugs(n) for a in probe_ats if (a, sl) not in known]
    added = []
    with ThreadPoolExecutor(24) as pool:
        for (name, ats, slug), n in zip(tasks, pool.map(lambda t: _probe(t[1], t[2]), tasks)):
            if n and (ats, slug) not in known:
                sources.append({"company": name, "ats": ats, "token": slug}); known.add((ats, slug))
                added.append(f"{name} ({ats}/{slug}, {n} AU roles)")
    for url in careers_urls:
        for ats, ident, extra in _careers_links(url):
            src = {"company": urllib.parse.urlparse(url).hostname.replace("www.", ""), "ats": ats, **extra}
            if key(src) in known:
                continue
            try:
                n = sum(location_ok(j["location"]) for j in FETCHERS[ats](src))
            except Exception:
                n = 0
            if n:
                sources.append(src); known.add(key(src)); added.append(f"{src['company']} ({ats}, {n} AU roles)")
    if added:
        (ROOT / "sources.json").write_text(json.dumps(sources, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Discovery: {len(added)} new board(s) added" + ("".join(f"\n  + {a}" for a in added)))
    return len(added)


# ---------------------------------------------------------------- JEV
KEY_FILE = ROOT / "jev_key.txt"  # the on-your-computer route keeps the key here; .gitignore keeps it out of git


def api_key(cfg) -> str:
    """The JEV key from JEV_API_KEY or jev_key.txt, or "" when Claude's cloud adds it to requests itself."""
    key = os.getenv("JEV_API_KEY") or os.getenv("TYPESAFE_API_KEY")
    if not key and KEY_FILE.is_file():
        key = KEY_FILE.read_text(encoding="utf-8-sig").strip()
    return key or ""


# Personal details never go to JEV: only what it needs to judge fit. Fields that identify someone are dropped,
# and contact details that slip into free text (an email, phone number or profile link from a pasted resume) are
# blanked out.
PERSONAL_FIELDS = {"name", "first_name", "last_name", "full_name", "email", "phone", "mobile", "address",
                   "linkedin", "website", "url", "date_of_birth", "dob", "age", "gender", "referees", "references"}
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
_URL = re.compile(r"(https?://|www\.)\S+|\b(linkedin|github)\.com/\S*", re.I)
_PHONE = re.compile(r"(?<![\w$.])(\+\d[\d ()-]{7,}\d|\(?0\d[\d ()-]{6,}\d)(?![\w.])")  # +61 4.. or 04.., not years


def scrub(text: str) -> str:
    text = _EMAIL.sub("[email removed]", text)
    text = _URL.sub("[link removed]", text)
    return _PHONE.sub(lambda m: "[phone removed]" if 9 <= sum(ch.isdigit() for ch in m[1]) <= 15 else m[1], text)


def jev_candidate(profile: dict) -> dict:
    def clean(v):
        if isinstance(v, str):
            return scrub(v)
        if isinstance(v, list):
            return [clean(x) for x in v]
        if isinstance(v, dict):
            return {k: clean(x) for k, x in v.items() if k.lower() not in PERSONAL_FIELDS}
        return v
    return clean({k: v for k, v in profile.items() if k.lower() not in PERSONAL_FIELDS})


def payload(profile: dict, job: sqlite3.Row, cfg) -> dict:
    return {"model": cfg["jev_model"],
            "state": {"candidate": jev_candidate(profile),
                      "job": {"company": job["company"], "title": job["title"], "location": job["location"],
                              "description": (job["description"] or "")[:6000]}},
            "questions": jev_questions(cfg)}


def call_jev(body: dict, key: str) -> dict:
    headers = {"Content-Type": "application/json", **({"Authorization": f"Bearer {key}"} if key else {})}
    req = urllib.request.Request(JEV_ENDPOINT, data=json.dumps(body, ensure_ascii=False).encode(), headers=headers, method="POST")
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, context=TLS, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 529) or attempt == 4:
                raise RuntimeError(f"JEV HTTP {e.code}: {e.read().decode(errors='replace')[:200]}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 4:
                raise RuntimeError(f"JEV connection failed: {e}") from e
        time.sleep(min(30, 2 ** attempt))
    raise RuntimeError("unreachable")


def combine(answers: dict, cfg) -> tuple[float, float, list[str], dict]:
    """Weighted score (0-100) from JEV's dimension scores; JEV makes every judgement, Python only weights."""
    detail, total, conf = {}, 0.0, 0.0
    for k, w in cfg["weights"].items():
        a = answers.get(k) or {}
        if a.get("type") != "score" or not isinstance(a.get("score"), (int, float)):
            raise ValueError(f"JEV returned no score for {k}")
        detail[k] = round(a["score"] * 25)
        total += w * a["score"] * 25
        conf += w * float(a.get("confidence") or 0)
    wsum = sum(cfg["weights"].values())
    excluded = []
    for k in CONSTRAINTS:
        p = (answers.get(k) or {}).get("noul")
        detail[k] = p
        if isinstance(p, (int, float)) and p >= cfg["constraint_cutoff"]:
            excluded.append(k)
    return round(total / wsum, 1), round(100 * conf / wsum), excluded, detail


def assess(c: sqlite3.Connection, dry_run: bool = False, limit: int | None = None) -> int:
    cfg, profile = load("config.json"), load("profile.json")
    todo = c.execute("""select j.* from jobs j left join assessments a on a.job_id=j.id and a.hash=j.hash
                        where j.open=1 and a.job_id is null order by j.first_seen desc limit ?""",
                     (min(limit or cfg["max_jobs_per_run"], cfg["max_jobs_per_run"]),)).fetchall()
    print(f"  {len(todo)} new or changed roles to send to JEV")
    topup = top_up_candidates(c, cfg)
    if topup:
        print(f"  {len(topup)} assessed roles that could reach {cfg['shortlist_threshold']}% need newly added questions")
    if dry_run or not (todo or topup):
        if todo:
            print(json.dumps(payload(profile, todo[0], cfg), indent=2, ensure_ascii=False)[:4000])
        return 0
    key = api_key(cfg)
    n = assess_new(c, cfg, profile, todo, key) if todo else 0
    if topup:
        top_up(c, cfg, profile, topup, key)
    return n


def assess_new(c: sqlite3.Connection, cfg, profile, todo, key) -> int:
    done, failed = 0, []

    def one(job):
        data = call_jev(payload(profile, job, cfg), key)
        return job, data, combine(data.get("answers") or {}, cfg)

    first, rest = todo[0], todo[1:]
    try:  # preflight so a bad key or network fails fast
        results = [one(first)]
    except Exception as e:
        hint = "" if key else " (no key sent: check the JEV key is saved as SETUP.md describes for your route)"
        sys.exit(f"JEV preflight failed: {e}{hint}")
    with ThreadPoolExecutor(cfg["jev_workers"]) as pool:
        futures = {pool.submit(one, j): j for j in rest}
        for f in as_completed(futures):
            try:
                results.append(f.result())
            except Exception as e:
                failed.append((futures[f]["title"], str(e)[:120]))
            if len(results) % 25 == 0:
                print(f"  {len(results)}/{len(todo)} assessed", flush=True)
            for job, data, (score, conf, excl, detail) in results[done:]:
                c.execute("insert or replace into assessments values(?,?,?,?,?,?,?,?)",
                          (job["id"], job["hash"], now(), data.get("model"), score, conf, ",".join(excl), json.dumps(detail)))
            done = len(results)
            c.commit()
    for job, data, (score, conf, excl, detail) in results[done:]:
        c.execute("insert or replace into assessments values(?,?,?,?,?,?,?,?)",
                  (job["id"], job["hash"], now(), data.get("model"), score, conf, ",".join(excl), json.dumps(detail)))
    c.commit()
    print(f"  JEV assessed {len(results)}; {len(failed)} failed")
    for t, e in failed[:10]:
        print(f"    failed: {t}: {e}", file=sys.stderr)
    return len(results)


def missing_dims(detail: dict, cfg) -> list[str]:
    return [k for k in cfg["weights"] if not isinstance(detail.get(k), (int, float))]


def rescore(detail: dict, cfg) -> float:
    """Weighted score from the 0-100 dimension scores stored in an assessment's detail."""
    return round(sum(w * detail[k] for k, w in cfg["weights"].items()) / sum(cfg["weights"].values()), 1)


def top_up_candidates(c: sqlite3.Connection, cfg) -> list:
    """Unchanged roles assessed before a dimension was added to the weights. Only roles that could still reach the
    threshold (missing dimensions scored 100) are asked, so adding a question doesn't re-send every role."""
    rows = c.execute("""select j.*, a.detail, a.confidence from jobs j join assessments a on a.job_id=j.id and a.hash=j.hash
                        where j.open=1 and a.excluded=''""").fetchall()
    out = []
    for r in rows:
        d = json.loads(r["detail"])
        miss = missing_dims(d, cfg)
        if miss and rescore({**d, **{k: 100 for k in miss}}, cfg) >= cfg["shortlist_threshold"]:
            out.append((r, miss))
    return out


def top_up(c: sqlite3.Connection, cfg, profile, rows, key) -> int:
    """Ask JEV only the missing questions and merge the answers into the existing assessment, so the other
    dimensions keep their earlier scores. Works without a stored description: company and title are sent."""
    def one(item):
        r, miss = item
        body = payload(profile, r, cfg)
        body["questions"] = {k: body["questions"][k] for k in miss}
        return r, miss, call_jev(body, key)

    wsum, done, failed = sum(cfg["weights"].values()), 0, []
    with ThreadPoolExecutor(cfg["jev_workers"]) as pool:
        for f in as_completed([pool.submit(one, item) for item in rows]):
            try:
                r, miss, data = f.result()
                answers, d = data.get("answers") or {}, json.loads(r["detail"])
                conf = (r["confidence"] or 0) * sum(w for k, w in cfg["weights"].items() if k not in miss)
                for k in miss:
                    a = answers.get(k) or {}
                    if a.get("type") != "score" or not isinstance(a.get("score"), (int, float)):
                        raise ValueError(f"JEV returned no score for {k}")
                    d[k] = round(a["score"] * 25)
                    conf += cfg["weights"][k] * 100 * float(a.get("confidence") or 0)
                c.execute("update assessments set score=?, confidence=?, detail=? where job_id=? and hash=?",
                          (rescore(d, cfg), round(conf / wsum), json.dumps(d), r["id"], r["hash"]))
                done += 1
                if done % 25 == 0:
                    c.commit(); print(f"  {done}/{len(rows)} topped up", flush=True)
            except Exception as e:
                failed.append(str(e)[:120])
    c.commit()
    print(f"  JEV topped up {done}; {len(failed)} failed")
    for e in failed[:5]:
        print(f"    failed: {e}", file=sys.stderr)
    return done


# ---------------------------------------------------------------- report
LABELS = {"experience_match": "experience", "target_fit": "target fit", "enjoyment": "enjoyment", "wants_match": "wants",
          "practicality": "practicality", "career_growth": "growth", "community_impact": "impact"}


ACTIVE = ("applied", "interviewing", "offer")
RECENT_REJECTION_DAYS = 30


def applications() -> list[dict]:
    """Roles already applied for, if the person keeps applications.json."""
    f = ROOT / "applications.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else []


NOISE = {"pty", "ltd", "limited", "inc", "group", "australia", "au"}


def _norm(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", " ", (s or "").lower().replace("&", " and "))
    return " ".join(w for w in s.split() if w not in NOISE)


def same_role(company: str, title: str, other_company: str, other_title: str) -> bool:
    """Same title at the same employer, allowing for brand variants: "Optus" matches "Optus (Singtel Group)", and
    "Premier's Department NSW (Investment NSW)" matches either name."""
    t = set(_norm(title).split())
    if not t or set(_norm(other_title).split()) != t:
        return False
    names = lambda co: {_norm(n) for n in re.split(r"[()]", co or "")} - {""}
    return any(f" {a} " in f" {b} " or f" {b} " in f" {a} " for a in names(company) for b in names(other_company))


def applied_to(job, apps: list[dict]) -> dict | None:
    """The application matching a job: by job ID, by listing URL, or by company and title."""
    url = lambda u: (u or "").rstrip("/").lower()
    for a in apps:
        if a.get("job_id") == job["id"] or (a.get("url") and url(a["url"]) == url(job["url"])):
            return a
        if same_role(job["company"], job["title"], a.get("company", ""), a.get("title", "")):
            return a
    return None


def applications_section(apps: list[dict], today: datetime) -> list[str]:
    day = lambda s: datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=today.tzinfo)
    cutoff = today - timedelta(days=RECENT_REJECTION_DAYS)
    active = [a for a in apps if a.get("status") in ACTIVE]
    rejected = [a for a in apps if a.get("status") == "rejected" and a.get("updated") and day(a["updated"]) >= cutoff]
    if not (active or rejected):
        return []
    line = lambda a, what: (f"- **{a['company']}**, {a['title']}: {what}" + (f". {a['note']}" if a.get("note") else ""))
    L = ["## Your applications", ""]
    for a in sorted(active, key=lambda a: a.get("updated", ""), reverse=True):
        waited = (today - day(a["updated"])).days if a.get("updated") else None
        what = {"applied": "applied", "interviewing": "interviewing", "offer": "offer"}[a["status"]]
        what += f" {day(a['applied']):%-d %b}" if a["status"] == "applied" and a.get("applied") else ""
        ago = {0: "today", 1: "yesterday"}.get(waited, f"{waited} days ago")
        what += f", last update {day(a['updated']):%-d %b} ({ago})" if waited is not None else ""
        L.append(line(a, what))
    if rejected:
        L += ["", f"Rejected in the last {RECENT_REJECTION_DAYS} days:", ""]
        for a in sorted(rejected, key=lambda a: a["updated"], reverse=True):
            L.append(line(a, f"rejected {day(a['updated']):%-d %b}"
                             + (f" (applied {day(a['applied']):%-d %b})" if a.get("applied") else "")))
    return L + [""]


def current_score(r: sqlite3.Row, cfg) -> dict:
    """The role with its score worked out from the current weights, when JEV has answered every weighted question."""
    r, d = dict(r), json.loads(r["detail"])
    if not missing_dims(d, cfg):
        r["score"] = rescore(d, cfg)
    return r


def report(c: sqlite3.Connection) -> Path:
    cfg = load("config.json")
    rows = c.execute("""select j.*, a.score, a.confidence, a.excluded, a.detail, a.model,
                          exists(select 1 from reported r where r.job_id=j.id and r.hash=j.hash) as already
                        from jobs j join assessments a on a.job_id=j.id and a.hash=j.hash
                        where j.open=1 order by a.score desc""").fetchall()
    rows = [r for r in rows if not excluded_employer(r["company"])]
    rows = [current_score(r, cfg) for r in rows]
    rows.sort(key=lambda r: r["score"], reverse=True)
    apps = applications()
    applied = [r for r in rows if applied_to(r, apps)]
    rows = [r for r in rows if not applied_to(r, apps)]
    eligible = [r for r in rows if not r["excluded"] and r["score"] >= cfg["shortlist_threshold"]]
    # A role found again at a new URL or under another brand name gets a new ID, so also match earlier reports by role.
    # Two roles with the same title on one company board are separate vacancies, so that pair doesn't count.
    sent = c.execute("select distinct j.id, j.company, j.title, j.source from jobs j join reported r on r.job_id=j.id").fetchall()
    by_title = {}
    for s in sent:
        by_title.setdefault(_norm(s["title"]), []).append(s)
    copy = lambda r, s: s["id"] != r["id"] and ("web" in (r["source"], s["source"]) or r["source"] != s["source"]) \
        and same_role(r["company"], r["title"], s["company"], s["title"])
    seen = lambda r: r["already"] or any(copy(r, s) for s in by_title.get(_norm(r["title"]), []))
    new = [r for r in eligible if not seen(r)][: cfg["shortlist_size"]]
    still_open = [r for r in eligible if r["already"]]
    today = datetime.now(ZoneInfo("Australia/Sydney"))
    stamp = today.strftime("%Y-%m-%d")
    REPORTS.mkdir(exist_ok=True)

    L = [f"# Job scout — {today:%-d %B %Y}", "", *applications_section(apps, today)]
    if new:
        L += ["## New matches", ""]
        for i, r in enumerate(new, 1):
            d = json.loads(r["detail"])
            dims = ", ".join(f"{LABELS[k]} {d[k]}" for k in cfg["weights"])
            L += [f"### {i}. [{r['title']} — {r['company']}]({r['url']}) — {r['score']:.0f}%", "",
                  f"- Location: {r['location']}  ·  JEV confidence {r['confidence']}%",
                  f"- JEV dimensions: {dims}", f"- Job ID: `{r['id']}`", ""]
    else:
        L += ["## New matches", "", f"No new roles cleared {cfg['shortlist_threshold']}% this run.", ""]
    if still_open:
        L += ["## Still open from earlier reports", ""]
        L += [f"- [{r['title']} — {r['company']}]({r['url']}) — {r['score']:.0f}%" for r in still_open[:20]]
        L.append("")
    excluded = sum(1 for r in rows if r["excluded"])
    L += ["---", f"{len(rows)} open roles assessed by JEV in total; {excluded} excluded by hard constraints; "
          f"{len(eligible)} at or above {cfg['shortlist_threshold']}%"
          + (f"; {len(applied)} you've applied for left out." if applied else ".")]
    md = REPORTS / f"{stamp}.md"
    md.write_text("\n".join(L) + "\n", encoding="utf-8")

    fields = ["score", "confidence", "excluded", "company", "title", "location", "url", *cfg["weights"], *CONSTRAINTS, "id", "model"]
    with (REPORTS / f"{stamp}-all-assessed.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({**dict(r), **json.loads(r["detail"])})
    for r in new:
        c.execute("insert or ignore into reported values(?,?,?)", (r["id"], r["hash"], now()))
    c.commit()
    print("\n".join(L))
    return md


def dismiss(c: sqlite3.Connection, ids: list[str]) -> int:
    """Mark roles as reported so they never appear under New matches, e.g. ones found filled or ineligible on review.
    A role whose listing later changes is assessed and reported afresh."""
    n = 0
    for i in ids:
        row = c.execute("select hash from jobs where id=?", (i,)).fetchone()
        if row is None:
            print(f"  unknown job ID: {i}", file=sys.stderr); continue
        n += c.execute("insert or ignore into reported values(?,?,?)", (i, row["hash"], now())).rowcount
    c.commit()
    print(f"  dismissed {n} role(s)")
    return n


def check() -> int:
    """Plain-words check that the JEV key and the job boards can be reached, for setup."""
    cfg, ok = load("config.json"), True
    sample = {"company": "Example Pty Ltd", "title": "Operations Manager", "location": "Sydney",
              "description": "Example listing used to check the connection to JEV."}
    body = {"model": cfg["jev_model"], "state": {"candidate": {"summary": "Connection check"}, "job": sample},
            "questions": {"is_not_a_real_job": {"type": "noul", "instructions": CONSTRAINTS["is_not_a_real_job"]}}}
    try:
        call_jev(body, api_key(cfg))
        print("JEV: working. The scoring service accepted the key.")
    except Exception as e:
        ok = False
        print(f"JEV: not working ({str(e)[:160]}).")
        if "connection failed" in str(e):
            print("  This session can't reach JEV at all, so its internet access needs changing. "
                  "See the API key steps for your route in SETUP.md.")
        else:
            print("  Most likely the API key isn't saved yet, or was pasted with a typo. See the API key steps for your route in SETUP.md.")
    try:
        n = len(list(fetch_greenhouse({"token": "airwallex", "company": "Airwallex"})))
        print(f"Job boards: working (a test board returned {n} roles).")
    except Exception as e:
        ok = False
        print(f"Job boards: not reachable ({str(e)[:160]}).")
        print("  Internet access needs switching on fully. See the API key steps for your route in SETUP.md.")
    return 0 if ok else 1


def compact(c: sqlite3.Connection) -> None:
    """Drop descriptions JEV has already assessed (the hash still detects changes) so the database stays small."""
    c.execute("""update jobs set description='' where description!='' and exists
                 (select 1 from assessments a where a.job_id=jobs.id and a.hash=jobs.hash)""")
    c.execute("delete from jobs where open=0 and last_seen < ?", ((datetime.now(timezone.utc) - timedelta(days=120)).isoformat(),))
    c.commit()
    c.execute("vacuum")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("collect")
    w = sub.add_parser("add-web"); w.add_argument("file", type=Path)
    a = sub.add_parser("assess"); a.add_argument("--dry-run", action="store_true"); a.add_argument("--limit", type=int)
    sub.add_parser("report")
    dsc = sub.add_parser("discover", help="find job boards for employer names and careers pages")
    dsc.add_argument("names", nargs="*", help="employer names")
    dsc.add_argument("--file", type=Path, help="JSON list of names, or of web finds (their company field is used)")
    dsc.add_argument("--careers-url", action="append", default=[], help="careers page to read for job-board links")
    r = sub.add_parser("run"); r.add_argument("--web", type=Path); r.add_argument("--dry-run", action="store_true")
    dm = sub.add_parser("dismiss", help="leave roles out of future New matches (filled, closed or ineligible)")
    dm.add_argument("ids", nargs="+", help="job IDs from the report or the all-assessed CSV")
    sub.add_parser("check", help="check the JEV key and job-board access")
    args = p.parse_args()
    if args.cmd == "check":
        return check()
    if args.cmd == "discover":
        names = list(args.names)
        if args.file:
            items = json.loads(args.file.read_text(encoding="utf-8"))
            names += [i if isinstance(i, str) else i.get("company", "") for i in items]
        discover(sorted({n.strip() for n in names if n and n.strip()}), args.careers_url)
        return 0
    c = db()
    if args.cmd == "dismiss":
        dismiss(c, args.ids)
        return 0
    if args.cmd in ("collect", "run"):
        print("Collecting company job boards…"); n = collect(c); print(f"  {n} Australian/remote roles on boards")
    if args.cmd == "add-web" or (args.cmd == "run" and args.web):
        print(f"Web finds: {add_web(c, args.web if args.cmd == 'run' else args.file)} roles ingested")
    if args.cmd in ("assess", "run"):
        print("Assessing with JEV…"); assess(c, dry_run=args.dry_run, limit=getattr(args, "limit", None))
    if args.cmd == "report" or (args.cmd == "run" and not args.dry_run):
        report(c)
        compact(c)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
