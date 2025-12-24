#!/usr/bin/env python3
"""
Update data/publications.json by pulling from:
- INSPIRE-HEP (REST API, reliable)
- Google Scholar (best-effort HTML parsing; may be rate-limited/captcha'd)

Usage:
  python3 scripts/update_publications.py --out data/publications.json

Config is read from data/sources.json by default.
"""
from __future__ import annotations
import argparse, json, re, sys, time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; academic-homepage-bot/1.0)"}

@dataclass
class Pub:
    year: Optional[int]
    title: str
    authors: str = ""
    venue: str = ""
    links: Dict[str,str] = None
    note: str = ""

    def to_json(self) -> Dict[str, Any]:
        d = asdict(self)
        if d["links"] is None:
            d["links"] = {}
        # Remove empty fields for cleanliness
        return {k:v for k,v in d.items() if v not in ("", None, {}, [])}

def load_sources(path: str) -> Dict[str,str]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def inspire_literature(author_id: str=None, author_identifier: str=None, size: int=200) -> List[Pub]:
    # INSPIRE literature endpoint: https://inspirehep.net/api/literature
    # We'll query by author id (robust) when possible, else by identifier.
    q = None
    if author_id:
        # 'authors.id' is used by INSPIRE API for matching authors
        q = f"authors.id:{author_id}"
    elif author_identifier:
        q = f"a {author_identifier}"
    else:
        return []

    url = "https://inspirehep.net/api/literature"
    params = {
        "q": q,
        "size": size,
        "sort": "mostrecent"
    }
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    hits = data.get("hits", {}).get("hits", [])
    pubs: List[Pub] = []
    for h in hits:
        md = h.get("metadata", {})
        title = ""
        titles = md.get("titles") or []
        if titles:
            title = titles[0].get("title", "") or ""
        if not title:
            continue
        year = md.get("earliest_date")
        yr = None
        if year and len(year) >= 4 and year[:4].isdigit():
            yr = int(year[:4])
        # authors
        auths = md.get("authors") or []
        authors = "; ".join([a.get("full_name","") for a in auths if a.get("full_name")])
        # venue
        venue = ""
        pub_info = md.get("publication_info") or []
        if pub_info:
            jtitle = pub_info[0].get("journal_title") or ""
            volume = pub_info[0].get("journal_volume") or ""
            page = pub_info[0].get("page_start") or ""
            year2 = pub_info[0].get("year") or ""
            parts = [jtitle, volume, page, str(year2) if year2 else ""]
            venue = " ".join([p for p in parts if p])
        # links
        links: Dict[str,str] = {}
        arxiv = md.get("arxiv_eprints") or []
        if arxiv:
            avid = arxiv[0].get("value")
            if avid:
                links["arXiv"] = f"https://arxiv.org/abs/{avid}"
        dois = md.get("dois") or []
        if dois:
            dv = dois[0].get("value")
            if dv:
                links["DOI"] = f"https://doi.org/{dv}"
        # inspire record link
        links["INSPIRE"] = h.get("links", {}).get("self", "")
        pubs.append(Pub(year=yr, title=title, authors=authors, venue=venue, links=links))
    return pubs

def scholar_publications(user: str, pagesize: int=100) -> List[Pub]:
    # Best-effort scrape of the citations profile list.
    # This can fail if Scholar blocks automated requests.
    url = "https://scholar.google.com/citations"
    params = {"hl": "en", "user": user, "cstart": 0, "pagesize": pagesize}
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    rows = soup.select("tr.gsc_a_tr")
    pubs: List[Pub] = []
    for row in rows:
        title_el = row.select_one("a.gsc_a_at")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        authors = (row.select_one("div.gs_gray") or "").get_text(" ", strip=True) if row.select_one("div.gs_gray") else ""
        venue = ""
        gray = row.select("div.gs_gray")
        if len(gray) >= 2:
            venue = gray[1].get_text(" ", strip=True)
        year = None
        year_el = row.select_one("span.gsc_a_h.gsc_a_hc.gs_ibl")
        if year_el:
            ytxt = year_el.get_text(strip=True)
            if ytxt.isdigit():
                year = int(ytxt)
        # Link to the publication page on Scholar
        href = title_el.get("href", "")
        links = {"Scholar": "https://scholar.google.com" + href} if href else {}
        pubs.append(Pub(year=year, title=title, authors=authors, venue=venue, links=links))
    return pubs

def key_for_merge(p: Pub) -> str:
    # Prefer arXiv id / DOI if present; else title normalized
    links = p.links or {}
    for k in ("arXiv","DOI"):
        if k in links and links[k]:
            return f"{k}:{links[k]}".lower()
    return re.sub(r"\s+", " ", p.title.strip().lower())

def merge(pubs_a: List[Pub], pubs_b: List[Pub]) -> List[Pub]:
    # keep richer entry when same key appears
    out: Dict[str, Pub] = {}
    for p in pubs_a + pubs_b:
        k = key_for_merge(p)
        if k not in out:
            out[k] = p
        else:
            existing = out[k]
            # heuristic: prefer entry with more links/venue/authors
            score = lambda x: (len((x.links or {}).keys()), len(x.venue or ""), len(x.authors or ""))
            if score(p) > score(existing):
                out[k] = p
    # sort by year desc then title
    res = list(out.values())
    res.sort(key=lambda x: ((x.year or 0), x.title.lower()), reverse=True)
    return res

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default="data/sources.json")
    ap.add_argument("--out", default="data/publications.json")
    ap.add_argument("--no-scholar", action="store_true", help="Skip Google Scholar scraping")
    ap.add_argument("--no-inspire", action="store_true", help="Skip INSPIRE API")
    args = ap.parse_args()

    src = load_sources(args.sources)

    pubs: List[Pub] = []
    if not args.no_inspire:
        try:
            pubs += inspire_literature(author_id=src.get("inspire_author_id"), author_identifier=src.get("inspire_author_identifier"))
            print(f"[ok] INSPIRE pubs: {len(pubs)}")
        except Exception as e:
            print(f"[warn] INSPIRE fetch failed: {e}", file=sys.stderr)

    scholar_pubs: List[Pub] = []
    if not args.no_scholar and src.get("google_scholar_user"):
        try:
            scholar_pubs = scholar_publications(src["google_scholar_user"])
            print(f"[ok] Scholar pubs: {len(scholar_pubs)}")
        except Exception as e:
            print(f"[warn] Scholar fetch failed: {e}", file=sys.stderr)

    merged = merge(pubs, scholar_pubs)

    # If everything fails, do not overwrite output.
    if len(merged) == 0:
        print("[error] No publications fetched; keeping existing file.", file=sys.stderr)
        return 2

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump([p.to_json() for p in merged], f, ensure_ascii=False, indent=2)
    print(f"[ok] Wrote {len(merged)} entries to {args.out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
