# Rui Wen — Academic Homepage (static)

This is a lightweight, modern academic homepage designed for GitHub Pages (or any static hosting).

## Quick start (local preview)
Because the page loads JSON via `fetch`, you should preview with a local server (not by double-clicking the HTML file).

```bash
cd rui-wen-academic-homepage
python3 -m http.server 8000
# open http://localhost:8000
```

## Update content
Edit these files:

- `data/site.json` — name, affiliation, email, links, keywords, about text
- `data/publications.json` — your publication list
- `data/talks.json` — talks list

Optional:
- Add a portrait at `assets/photo.jpg` (or set `portrait` in `data/site.json`)
- Add your CV PDF at `assets/cv.pdf`

## Deploy on GitHub Pages
1. Create a GitHub repository (e.g. `ruiwen` or `homepage`).
2. Upload all files in this folder to the repo root.
3. In GitHub: **Settings → Pages**
   - Source: `Deploy from a branch`
   - Branch: `main` / `(root)`
4. Your site will be at `https://<username>.github.io/<repo>/` (or `https://<username>.github.io/` if the repo is named `<username>.github.io`).

## Custom domain (optional)
In **Settings → Pages**, set a custom domain and follow the DNS instructions GitHub provides.
