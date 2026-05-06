#!/usr/bin/env python3
"""System 4 layer 1: Score every blog post on age + indexing status.

For each URL in the site's sitemap (filtered to blog posts), we determine:
  - publication / last-modified date (from JSON-LD, article meta tags, or <time>)
  - GSC indexing status via urlInspection.index.inspect
  - last crawl time

We flag:
  not_indexed: GSC reports the URL is not indexed
  index_warning: GSC reports a partial issue (canonical mismatch, soft 404, etc.)
  stale_12mo:   age >= 365 days
  aging:        305 <= age < 365 days

Output: state/refresh-candidates.json (consumed by the layer-2 Claude prompt
that adds per-URL action recommendations and produces refresh-queue.json).

Auth reuses the helpers from SEO-Access/mcp-gsc/gsc_server.py.

Usage:
  refresh-scorer.py [--site https://www.your-site.com/] [--include /blog/] [--max-urls 60]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import ssl
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()

ROOT = Path(__file__).resolve().parent.parent
GSC_PATH = Path("/path/to/the-four-systems/SEO-Access/mcp-gsc")
sys.path.insert(0, str(GSC_PATH))

try:
    from gsc_server import get_gsc_service  # type: ignore
except Exception as e:
    print(f"ERROR: cannot import gsc_server auth helpers: {e}", file=sys.stderr)
    sys.exit(1)

UA = "Mozilla/5.0 (compatible; the-four-systems/refresh-scorer)"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


# ---------- sitemap helpers --------------------------------------------------

def fetch_text(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
        return r.read().decode("utf-8", errors="replace")


def discover_sitemaps(site: str) -> list[str]:
    """Find sitemap URL(s) via /robots.txt and common fallbacks."""
    site = site.rstrip("/")
    found: list[str] = []
    try:
        robots = fetch_text(f"{site}/robots.txt")
        for line in robots.splitlines():
            if line.lower().startswith("sitemap:"):
                found.append(line.split(":", 1)[1].strip())
    except Exception:
        pass
    if found:
        return found
    # fallbacks
    for path in ["/sitemap.xml", "/sitemap-index.xml", "/sitemap-0.xml"]:
        try:
            fetch_text(f"{site}{path}")
            return [f"{site}{path}"]
        except Exception:
            continue
    return []


def expand_sitemap(url: str, depth: int = 0) -> list[dict]:
    """Return list of dicts: {loc, lastmod (or None)}. Follows index files."""
    if depth > 3:
        return []
    try:
        body = fetch_text(url)
    except Exception as e:
        print(f"WARN: failed to fetch {url}: {e}", file=sys.stderr)
        return []
    body = re.sub(r"<\?xml[^>]+\?>", "", body)
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        print(f"WARN: sitemap parse error {url}: {e}", file=sys.stderr)
        return []
    tag = root.tag.split("}")[-1]
    if tag == "sitemapindex":
        out: list[dict] = []
        for sm in root.findall("sm:sitemap", SITEMAP_NS):
            loc = sm.findtext("sm:loc", default="", namespaces=SITEMAP_NS).strip()
            if loc:
                out.extend(expand_sitemap(loc, depth + 1))
        return out
    elif tag == "urlset":
        out = []
        for u in root.findall("sm:url", SITEMAP_NS):
            loc = u.findtext("sm:loc", default="", namespaces=SITEMAP_NS).strip()
            lastmod = u.findtext("sm:lastmod", default="", namespaces=SITEMAP_NS).strip() or None
            if loc:
                out.append({"loc": loc, "lastmod": lastmod})
        return out
    return []


# ---------- date extraction --------------------------------------------------

DATE_PATTERNS = [
    # JSON-LD (preferred): catches both datePublished and dateModified
    (re.compile(r'"datePublished"\s*:\s*"([^"]+)"'), "json_ld_published"),
    (re.compile(r'"dateModified"\s*:\s*"([^"]+)"'), "json_ld_modified"),
    # OpenGraph / article meta
    (re.compile(r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)', re.I), "og_published"),
    (re.compile(r'<meta[^>]+property=["\']article:modified_time["\'][^>]+content=["\']([^"\']+)', re.I), "og_modified"),
    (re.compile(r'<meta[^>]+name=["\']pubdate["\'][^>]+content=["\']([^"\']+)', re.I), "meta_pubdate"),
    # <time datetime="...">
    (re.compile(r'<time[^>]+datetime=["\']([^"\']+)["\'][^>]*>', re.I), "time_datetime"),
]


def parse_iso_date(s: str) -> dt.date | None:
    s = s.strip()
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        return dt.datetime.fromisoformat(s).date()
    except ValueError:
        pass
    # Try date-only patterns
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d %b %Y", "%B %d, %Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def extract_dates(html: str) -> dict:
    """Return dict with published, modified, and source labels."""
    out: dict = {"published": None, "modified": None, "source": None}
    for pat, label in DATE_PATTERNS:
        for m in pat.finditer(html):
            d = parse_iso_date(m.group(1))
            if d is None:
                continue
            if "modified" in label and out["modified"] is None:
                out["modified"] = d.isoformat()
                out["source"] = out["source"] or label
            elif "published" in label and out["published"] is None:
                out["published"] = d.isoformat()
                out["source"] = out["source"] or label
            elif label == "time_datetime" and out["published"] is None:
                out["published"] = d.isoformat()
                out["source"] = out["source"] or label
    return out


# ---------- GSC URL inspection -----------------------------------------------

def inspect_url(svc, site: str, url: str) -> dict:
    """Call urlInspection.index.inspect. Returns the inspectionResult dict or {}."""
    try:
        body = {"inspectionUrl": url, "siteUrl": site}
        resp = svc.urlInspection().index().inspect(body=body).execute()
        return resp.get("inspectionResult", {})
    except Exception as e:
        return {"_error": str(e)[:200]}


def summarise_inspection(insp: dict) -> dict:
    """Compress the verbose inspection response into the fields we score on."""
    if not insp or "_error" in insp:
        return {
            "verdict": None,
            "coverage_state": None,
            "indexing_state": None,
            "last_crawl_time": None,
            "google_canonical": None,
            "user_canonical": None,
            "error": insp.get("_error") if insp else None,
        }
    idx = insp.get("indexStatusResult", {}) or {}
    return {
        "verdict": idx.get("verdict"),
        "coverage_state": idx.get("coverageState"),
        "indexing_state": idx.get("indexingState"),
        "last_crawl_time": idx.get("lastCrawlTime"),
        "google_canonical": idx.get("googleCanonical"),
        "user_canonical": idx.get("userCanonical"),
        "error": None,
    }


# ---------- main flow --------------------------------------------------------

def score(candidate: dict, today: dt.date) -> dict:
    flags: list[str] = []

    # Pick the best date we have: modified > published > sitemap lastmod
    date_str = (candidate["dates"].get("modified")
                or candidate["dates"].get("published")
                or candidate.get("sitemap_lastmod"))
    age_days = None
    if date_str:
        try:
            d = dt.date.fromisoformat(date_str[:10])
            age_days = (today - d).days
        except ValueError:
            pass

    if age_days is not None:
        if age_days >= 365:
            flags.append("stale_12mo")
        elif 305 <= age_days < 365:
            flags.append("aging")

    insp = candidate["indexing"]
    cov = (insp.get("coverage_state") or "").lower()
    verdict = (insp.get("verdict") or "").lower()
    if verdict == "fail" or "not in index" in cov or "discovered" in cov or "crawled" in cov and "not indexed" in cov:
        flags.append("not_indexed")
    elif verdict == "neutral" or any(k in cov for k in ["alternate", "duplicate", "soft 404", "redirect"]):
        flags.append("index_warning")

    # Priority: not_indexed > stale > aging > index_warning
    priority = 9
    if "not_indexed" in flags:
        priority = 1
    elif "stale_12mo" in flags:
        priority = 2
    elif "aging" in flags:
        priority = 3
    elif "index_warning" in flags:
        priority = 3

    return {"flags": flags, "age_days": age_days, "priority": priority}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--site", default=os.environ.get("REFRESH_SITE", "https://www.your-site.com/"))
    p.add_argument("--include", default=os.environ.get("REFRESH_INCLUDE", "/blog/"),
                   help="Substring URLs must contain to be considered (e.g. /blog/)")
    p.add_argument("--max-urls", type=int, default=int(os.environ.get("REFRESH_MAX_URLS", "60")))
    args = p.parse_args()

    site = args.site
    print(f"Site: {site}")
    print(f"Include filter: {args.include!r}")
    print(f"Max URLs: {args.max_urls}")

    sitemaps = discover_sitemaps(site)
    if not sitemaps:
        print(f"ERROR: could not find a sitemap for {site}", file=sys.stderr)
        return 1
    print(f"Sitemaps: {sitemaps}")

    all_urls: list[dict] = []
    for sm in sitemaps:
        all_urls.extend(expand_sitemap(sm))
    print(f"Sitemap URLs total: {len(all_urls)}")

    # Filter
    filtered = [u for u in all_urls if args.include in u["loc"]]
    print(f"After include filter: {len(filtered)}")
    filtered = filtered[: args.max_urls]
    print(f"After max-urls cap: {len(filtered)}")

    # GSC client
    print("Authenticating GSC...")
    try:
        svc = get_gsc_service()
    except Exception as e:
        print(f"ERROR: GSC auth failed: {e}", file=sys.stderr)
        return 1

    today = dt.date.today()
    candidates: list[dict] = []
    for i, u in enumerate(filtered, 1):
        loc = u["loc"]
        print(f"[{i:3d}/{len(filtered)}] {loc}")
        # Date extraction
        dates = {"published": None, "modified": None, "source": None}
        try:
            html = fetch_text(loc)
            dates = extract_dates(html)
        except Exception as e:
            print(f"  fetch failed: {e}")
        # GSC inspection
        insp = summarise_inspection(inspect_url(svc, site, loc))
        c = {
            "url": loc,
            "sitemap_lastmod": u.get("lastmod"),
            "dates": dates,
            "indexing": insp,
        }
        c.update(score(c, today))
        candidates.append(c)

    # Sort: priority asc, then oldest first
    candidates.sort(key=lambda c: (c.get("priority", 9), -(c.get("age_days") or 0)))

    flagged = [c for c in candidates if c.get("flags")]
    out = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "site": site,
        "include_filter": args.include,
        "totals": {
            "urls_evaluated": len(candidates),
            "urls_flagged": len(flagged),
            "by_flag": {
                "not_indexed":   sum(1 for c in candidates if "not_indexed" in c["flags"]),
                "index_warning": sum(1 for c in candidates if "index_warning" in c["flags"]),
                "stale_12mo":    sum(1 for c in candidates if "stale_12mo" in c["flags"]),
                "aging":         sum(1 for c in candidates if "aging" in c["flags"]),
            },
        },
        "candidates": candidates,
    }

    out_path = ROOT / "state" / "refresh-candidates.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {out_path} ({len(candidates)} candidates, {len(flagged)} flagged)")

    # Raw markdown report (b-roll)
    raw = ROOT / "reports" / f"{today}-refresh-raw.md"
    lines = [
        f"# Refresh raw scan, {site}, {today}",
        "",
        f"- URLs evaluated: {len(candidates)}",
        f"- Flagged: {len(flagged)}",
        "",
        "## Counts by flag",
    ]
    for f, n in out["totals"]["by_flag"].items():
        lines.append(f"- {f}: {n}")
    lines += ["", "## Top 30 flagged URLs", "",
              "| URL | Flags | Age (d) | Coverage |",
              "| --- | --- | ---: | --- |"]
    for c in flagged[:30]:
        cov = c["indexing"].get("coverage_state") or "-"
        lines.append(
            f"| `{c['url']}` | {', '.join(c['flags'])} | {c.get('age_days') if c.get('age_days') is not None else '-'} | {cov} |"
        )
    raw.write_text("\n".join(lines) + "\n")
    print(f"Wrote {raw}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
