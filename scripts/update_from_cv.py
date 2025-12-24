#!/usr/bin/env python3
"""
Best-effort update of talks + teaching from assets/cv.pdf.
This works well if your CV follows the same headings as the current PDF.

Usage:
  python3 scripts/update_from_cv.py --cv assets/cv.pdf
"""
from __future__ import annotations
import argparse, json, re
from typing import Dict, List
import pdfplumber

MONTHS = {
  "january":"01","february":"02","march":"03","april":"04","may":"05","june":"06",
  "july":"07","august":"08","september":"09","october":"10","november":"11","december":"12"
}

def month_to_iso(s: str) -> str:
  # "September 2025" -> "2025-09-01"
  s = s.strip()
  m = re.match(r"([A-Za-z]+)\s+(\d{4})", s)
  if not m: 
    return ""
  mm = MONTHS.get(m.group(1).lower(), "01")
  return f"{m.group(2)}-{mm}-01"

def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--cv", default="assets/cv.pdf")
  ap.add_argument("--talks_out", default="data/talks.json")
  ap.add_argument("--teach_out", default="data/teaching.json")
  args = ap.parse_args()

  with pdfplumber.open(args.cv) as pdf:
    text = "\n".join([p.extract_text() or "" for p in pdf.pages])

  # Talks: try to find lines like "• September 2025, CJQS seminar, Tianjin University, “Title”."
  talks: List[Dict] = []
  for line in text.splitlines():
    line = line.strip()
    if not line.startswith("• "):
      continue
    if "," not in line:
      continue
    # crude parse
    # "• September 2025, CJQS seminar, Tianjin University, “Generalized ...”."
    m = re.match(r"•\s+([A-Za-z]+\s+\d{4}),\s*(.*)", line)
    if not m:
      continue
    date = month_to_iso(m.group(1))
    rest = m.group(2)
    # Split title in quotes if present
    title = ""
    where = rest
    q = re.search(r"“([^”]+)”", rest) or re.search(r"\"([^\"]+)\"", rest)
    if q:
      title = q.group(1).strip()
      where = re.sub(r"[“\"].*[”\"]", "", rest).strip().strip(",")
    if title and date:
      talks.append({"date": date, "title": title, "where": where, "links": {}})

  # Teaching: find lines with "PHYS"
  past = []
  for line in text.splitlines():
    line = line.strip()
    m = re.match(r"–\s*(PHYS\s*\d+:\s*.*)\s+(Spring|Fall|Winter|Summer)\s+(\d{4})", line)
    if m:
      course = m.group(1).strip()
      term = f"{m.group(2)} {m.group(3)}"
      past.append({"term": term, "role": "Teaching Assistant", "course": course, "institution": ""})

  teaching = {"current": [], "past": past}

  if talks:
    talks.sort(key=lambda x: x["date"], reverse=True)
    with open(args.talks_out, "w", encoding="utf-8") as f:
      json.dump(talks, f, ensure_ascii=False, indent=2)

  if past:
    with open(args.teach_out, "w", encoding="utf-8") as f:
      json.dump(teaching, f, ensure_ascii=False, indent=2)

  print(f"[ok] talks={len(talks)} teaching_past={len(past)}")
  return 0

if __name__ == "__main__":
  raise SystemExit(main())
