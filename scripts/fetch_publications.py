#!/usr/bin/env python3
"""Fetch/refresh publications.json from Google Scholar and INSPIRE-HEP.

This script is designed for a static site workflow:
- It *writes* data/publications.json.
- The website only reads the JSON (no runtime scraping).

Usage (from repo root):
  python3 scripts/fetch_publications.py --scholar-user 1CoCLEoAAAAJ --inspire-author-id 1718074

Notes
- Google Scholar has no official API and sometimes blocks automated requests.
  If Scholar fetching fails, the script continues with INSPIRE-HEP only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup


def _norm_title(t: str) -> str:
    t = t.lower().strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^a-z0-9 ]+", "", t)
    return t


def _safe_get(d: Dict[str, Any], path: List[str], default=None):
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def fetch_google_scholar(user: str, pagesize: int = 100) -> List[Dict[str, Any]]:
    """Best-effort HTML scraping for a Scholar profile page."""

    # Try en first, then zh-CN as a fallback (sometimes served differently).
    urls = [
        f"https://scholar.google.com/citations?hl=en&user={user}&cstart=0&pagesize={pagesize}",
        f"https://scholar.google.com/citations?hl=zh-CN&user={user}&cstart=0&pagesize={pagesize}",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    last_err: Optional[Exception] = None
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
            html = r.text

            soup = BeautifulSoup(html, "html.parser")
            rows = soup.select("tr.gsc_a_tr")
            if not rows:
                raise RuntimeError("No publication rows found (page structure changed or blocked).")

            out: List[Dict[str, Any]] = []
            for row in rows:
                title_el = row.select_one("a.gsc_a_at")
                year_el = row.select_one("td.gsc_a_y span")
                meta_els = row.select("td.gsc_a_t .gs_gray")

                title = title_el.get_text(strip=True) if title_el else ""
                year_s = year_el.get_text(strip=True) if year_el else ""
                authors = meta_els[0].get_text(strip=True) if len(meta_els) >= 1 else ""
                venue = meta_els[1].get_text(strip=True) if len(meta_els) >= 2 else ""

                year = None
                if year_s.isdigit():
                    year = int(year_s)

                if not title:
                    continue

                out.append(
                    {
                        "year": year,
                        "title": title,
                        "authors": authors,
                        "venue": venue,
                        "links": {
                            "Google Scholar": f"https://scholar.google.com/citations?hl=en&user={user}",
                        },
                        "source": "scholar",
                    }
                )

            return out
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"Google Scholar fetch failed. Last error: {last_err}")


def _parse_inspire_record(hit: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    md = hit.get("metadata", {})

    titles = md.get("titles") or []
    title = ""
    if titles and isinstance(titles, list) and isinstance(titles[0], dict):
        title = titles[0].get("title", "")
    if not title:
        return None

    # Authors
    authors_list = md.get("authors") or []
    names: List[str] = []
    for a in authors_list:
        if not isinstance(a, dict):
            continue
        name = a.get("full_name") or a.get("name") or ""
        if name:
            names.append(name)
    authors = ", ".join(names[:20])

    # Year
    year = None
    for key in ["publication_info", "preprint_date", "earliest_date"]:
        if key == "publication_info":
            infos = md.get("publication_info") or []
            if infos and isinstance(infos, list) and isinstance(infos[0], dict):
                y = infos[0].get("year")
                if isinstance(y, int):
                    year = y
                    break
                if isinstance(y, str) and y.isdigit():
                    year = int(y)
                    break
        else:
            ds = md.get(key)
            if isinstance(ds, str) and len(ds) >= 4 and ds[:4].isdigit():
                year = int(ds[:4])
                break

    # Venue
    venue = ""
    infos = md.get("publication_info") or []
    if infos and isinstance(infos, list) and isinstance(infos[0], dict):
        pi = infos[0]
        journal = pi.get("journal_title") or ""
        vol = pi.get("journal_volume") or ""
        page = pi.get("page_start") or pi.get("artid") or ""
        if journal:
            venue = journal
            if vol:
                venue += f" {vol}"
            if page:
                venue += f", {page}"
            if year:
                venue += f" ({year})"

    # IDs / links
    links: Dict[str, str] = {}
    dois = md.get("dois") or []
    if dois and isinstance(dois, list) and isinstance(dois[0], dict):
        doi = dois[0].get("value")
        if doi:
            links["DOI"] = f"https://doi.org/{doi}"

    arx = md.get("arxiv_eprints") or []
    if arx and isinstance(arx, list) and isinstance(arx[0], dict):
        arxiv = arx[0].get("value")
        if arxiv:
            links["arXiv"] = f"https://arxiv.org/abs/{arxiv}"

    self_url = _safe_get(hit, ["links", "self"], "")
    if self_url:
        links["INSPIRE"] = self_url.replace("/api/", "/")

    return {
        "year": year,
        "title": title,
        "authors": authors,
        "venue": venue or (f"arXiv:{arx[0].get('value')}" if links.get("arXiv") else ""),
        "links": links,
        "source": "inspire",
    }


def fetch_inspire(author_id: str, max_pages: int = 10, page_size: int = 100) -> List[Dict[str, Any]]:
    """Fetch literature via INSPIRE author record.

    We first read the author record to discover the 'publications' link.
    """

    author_url = f"https://inspirehep.net/api/authors/{author_id}"
    r = requests.get(author_url, timeout=20)
    r.raise_for_status()
    author = r.json()

    pubs_url = _safe_get(author, ["links", "publications"], "")
    if not pubs_url:
        # Fallback: try a simple query by the author identifier string, if present.
        ids = _safe_get(author, ["metadata", "ids"], []) or []
        inspire_id = None
        for it in ids:
            if isinstance(it, dict) and it.get("schema") == "INSPIRE BAI":
                inspire_id = it.get("value")
                break
        if inspire_id:
            pubs_url = f"https://inspirehep.net/api/literature?sort=mostrecent&size={page_size}&q=a%20{inspire_id}"

    if not pubs_url:
        raise RuntimeError("Could not find an INSPIRE publications endpoint for this author.")

    # Force bigger pagesize if possible
    pubs_url = re.sub(r"([?&])size=\d+", rf"\1size={page_size}", pubs_url)
    if "size=" not in pubs_url:
        sep = "&" if "?" in pubs_url else "?"
        pubs_url = f"{pubs_url}{sep}size={page_size}"

    out: List[Dict[str, Any]] = []
    url = pubs_url
    pages = 0
    while url and pages < max_pages:
        rr = requests.get(url, timeout=20)
        rr.raise_for_status()
        payload = rr.json()
        hits = payload.get("hits", {}).get("hits", []) or []
        for hit in hits:
            rec = _parse_inspire_record(hit)
            if rec:
                out.append(rec)
        url = _safe_get(payload, ["links", "next"], "")
        pages += 1

    return out


def merge_records(inspire: List[Dict[str, Any]], scholar: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_title: Dict[str, Dict[str, Any]] = {}

    for it in inspire:
        key = _norm_title(it.get("title", ""))
        if not key:
            continue
        by_title[key] = it

    for it in scholar:
        key = _norm_title(it.get("title", ""))
        if not key:
            continue
        if key in by_title:
            # Merge: keep inspire record but preserve missing fields from scholar.
            base = by_title[key]
            if not base.get("year") and it.get("year"):
                base["year"] = it["year"]
            if not base.get("venue") and it.get("venue"):
                base["venue"] = it["venue"]
            # Add scholar link
            base.setdefault("links", {})
            base["links"].setdefault("Google Scholar", it.get("links", {}).get("Google Scholar", ""))
        else:
            by_title[key] = it

    # sort by year desc, then title
    items = list(by_title.values())
    items.sort(key=lambda x: (x.get("year") or 0, x.get("title") or ""), reverse=True)
    # drop internal source field if desired; keep for debugging
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scholar-user", default=os.getenv("SCHOLAR_USER", ""), help="Google Scholar user id")
    ap.add_argument("--inspire-author-id", default=os.getenv("INSPIRE_AUTHOR_ID", ""), help="INSPIRE author numeric id")
    ap.add_argument("--out", default="data/publications.json", help="Output JSON path")
    args = ap.parse_args()

    inspire_records: List[Dict[str, Any]] = []
    scholar_records: List[Dict[str, Any]] = []

    if args.inspire_author_id:
        try:
            inspire_records = fetch_inspire(args.inspire_author_id)
            print(f"INSPIRE: {len(inspire_records)} records")
        except Exception as e:
            print(f"INSPIRE fetch failed: {e}", file=sys.stderr)

    if args.scholar_user:
        try:
            scholar_records = fetch_google_scholar(args.scholar_user)
            print(f"Scholar: {len(scholar_records)} records")
        except Exception as e:
            print(f"Google Scholar fetch failed: {e}", file=sys.stderr)

    if not inspire_records and not scholar_records:
        raise SystemExit("No records fetched. Provide --inspire-author-id and/or --scholar-user.")

    merged = merge_records(inspire_records, scholar_records)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(merged)} items -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
