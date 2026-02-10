# Rui Wen — Academic Homepage (static)

This is a lightweight, modern academic homepage designed for GitHub Pages (or any static hosting).

## What changed in this version
- Navigation bar is at the very top and sticky.
- Teaching is rendered from `data/teaching.json`.
- Publications can be auto-updated from **Google Scholar** and **INSPIRE-HEP** via GitHub Actions.
- Talks/Teaching can be re-generated from `assets/cv.pdf` (best-effort).

## Quick start (local preview)
Because the page loads JSON via `fetch`, preview with a local server:

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

## Update content (manual)
Edit:
- `data/site.json`
- `data/publications.json`
- `data/talks.json`
- `data/teaching.json`

Optional:
- Add portrait: `assets/photo.jpg`
- Replace CV: `assets/cv.pdf`

## Auto-update publications (recommended)
This repo includes a workflow: `.github/workflows/update_publications.yml`.

1) In GitHub repo settings:
- **Settings → Actions → General → Workflow permissions**
- Set to **Read and write permissions**.

2) Check/update your IDs in `data/sources.json`:
- `google_scholar_user`: from your Scholar profile URL `...user=XXXX`
- `inspire_author_id`: from your INSPIRE author page URL `.../authors/YYYY`

3) Run manually once:
- **Actions → Update publications and CV sections → Run workflow**

It will also run weekly (every Monday).

### Note on Google Scholar
Google Scholar has no official public API and sometimes blocks automation. If Scholar blocks the workflow, the script keeps going (INSPIRE still works) and you can re-run later.

## Regenerate talks/teaching from CV
If you update `assets/cv.pdf`, you can run locally:

```bash
pip install -r requirements.txt
python scripts/update_from_cv.py --cv assets/cv.pdf
```

Then commit and push the updated JSON files.


## Notes
Add notes in `data/notes.json` (a list). Each note can have:
- `date` (YYYY-MM-DD)
- `title`
- `summary` (optional)
- `tags` (optional list)
- `file` (optional local path like `assets/notes/my_note.pdf`)
- `links` (optional object of button-name → URL)

Example entry:

```json
{
  "date": "2026-02-10",
  "title": "My note title",
  "summary": "A short description.",
  "tags": ["TQFT", "symmetry"],
  "file": "assets/notes/my_note.pdf",
  "links": {"GitHub": "https://..."}
}
```
