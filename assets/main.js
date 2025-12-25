/* Data-driven rendering for easy maintenance */
const $ = (sel) => document.querySelector(sel);

async function loadJSON(path){
  const res = await fetch(path, { cache: "no-store" });
  if(!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
  return res.json();
}

function normalize(s){ return (s ?? "").toString().toLowerCase(); }

function buildLink(name, href){
  const a = document.createElement("a");
  a.className = "btn";
  a.href = href;
  a.target = "_blank";
  a.rel = "noreferrer";
  a.textContent = name;
  return a;
}

function buildPill(name, href){
  const a = document.createElement("a");
  a.className = "pill";
  a.href = href;
  a.target = "_blank";
  a.rel = "noreferrer";
  a.textContent = name;
  return a;
}

function setText(id, text){
  const el = $(id);
  if(el) el.textContent = text;
}

function renderSite(site){
  const nameValue = site.name ?? "Name";
  const nameEl = $("#site-name");
  if(nameEl){ nameEl.textContent = nameValue; nameEl.setAttribute("data-text", nameValue); }
  setText("#name-inline", site.name ?? "Name");
  setText("#year", new Date().getFullYear());

  const titleParts = [site.title, site.affiliation].filter(Boolean);
  setText("#site-title", titleParts.join(" · "));
  setText("#site-location", site.location ?? "");

  // Keywords
  const chips = $("#keyword-chips");
  chips.innerHTML = "";
  (site.keywords ?? []).forEach(k => {
    const span = document.createElement("span");
    span.className = "chip";
    span.textContent = k;
    chips.appendChild(span);
  });

  // About text
  const about = $("#about-text");
  about.innerHTML = "";
  (site.about ?? []).forEach(p => {
    const para = document.createElement("p");
    para.className = "prose";
    para.textContent = p;
    about.appendChild(para);
  });

  // Interests list mirrors keywords (editable independently if you want)
  const interests = $("#interests-list");
  interests.innerHTML = "";
  (site.keywords ?? []).forEach(k => {
    const li = document.createElement("li");
    li.textContent = k;
    interests.appendChild(li);
  });

  // Primary links (top buttons)
  const links = $("#primary-links");
  links.innerHTML = "";

  // Email button (obfuscated)
  if(site.email && site.email.includes("@")){
    const btn = document.createElement("button");
    btn.className = "btn";
    btn.type = "button";
    btn.innerHTML = `Email <span class="mono">${site.email.replace("@"," [at] ")}</span>`;
    btn.addEventListener("click", () => {
      window.location.href = `mailto:${site.email}`;
    });
    links.appendChild(btn);
  }

  // Other links
  const linkMap = site.links ?? {};
  Object.entries(linkMap).forEach(([name, href]) => {
    if(!href) return;
    links.appendChild(buildLink(name, href));
  });

  // Footer links
  const footer = $("#footer-links");
  footer.innerHTML = "";
  Object.entries(linkMap).forEach(([name, href]) => {
    if(!href) return;
    footer.appendChild(buildLink(name, href));
  });

  // Contact email line
  const emailLine = $("#email-line");
  if(site.email){
    emailLine.textContent = `Email: ${site.email.replace("@"," [at] ")}`;
  }else{
    emailLine.textContent = "Email: (add in data/site.json)";
  }

  setText("#site-notice", site.notice ?? "");
}

function renderPublications(pubs){
  pubs.sort((a,b) => (b.year ?? 0) - (a.year ?? 0));

  const years = [...new Set(pubs.map(p => p.year).filter(Boolean))];
  const yearSel = $("#pub-year");
  years.forEach(y => {
    const opt = document.createElement("option");
    opt.value = String(y);
    opt.textContent = String(y);
    yearSel.appendChild(opt);
  });

  const list = $("#pub-list");
  const search = $("#pub-search");

  function matches(p, q, y){
    const hay = [p.title, p.authors, p.venue, p.note, p.year].map(x => normalize(x)).join(" ");
    const okQ = !q || hay.includes(q);
    const okY = !y || String(p.year ?? "") === y;
    return okQ && okY;
  }

  function render(){
    const q = normalize(search.value);
    const y = yearSel.value;
    list.innerHTML = "";

    const filtered = pubs.filter(p => matches(p, q, y));
    if(filtered.length === 0){
      const empty = document.createElement("p");
      empty.className = "prose";
      empty.textContent = "No matches.";
      list.appendChild(empty);
      return;
    }

    filtered.forEach(p => {
      const item = document.createElement("article");
      item.className = "item";

      const h = document.createElement("h3");
      h.className = "item-title";
      h.textContent = p.title ?? "(untitled)";
      item.appendChild(h);

      const meta = document.createElement("p");
      meta.className = "item-meta";
      const parts = [
        p.authors,
        p.venue,
        p.year ? String(p.year) : null
      ].filter(Boolean);
      meta.textContent = parts.join(" · ");
      item.appendChild(meta);

      if(p.note){
        const note = document.createElement("p");
        note.className = "item-meta";
        note.textContent = p.note;
        item.appendChild(note);
      }

      const links = document.createElement("div");
      links.className = "item-links";
      const lm = p.links ?? {};
      Object.entries(lm).forEach(([name, href]) => {
        if(!href) return;
        links.appendChild(buildPill(name, href));
      });
      if(links.childElementCount) item.appendChild(links);

      list.appendChild(item);
    });
  }

  search.addEventListener("input", render);
  yearSel.addEventListener("change", render);
  render();
}

function renderTalks(talks){
  talks.sort((a,b) => normalize(b.date).localeCompare(normalize(a.date)));

  const list = $("#talk-list");
  const search = $("#talk-search");

  function matches(t, q){
    const hay = [t.title, t.where, t.date].map(x => normalize(x)).join(" ");
    return !q || hay.includes(q);
  }

  function render(){
    const q = normalize(search.value);
    list.innerHTML = "";

    const filtered = talks.filter(t => matches(t, q));
    if(filtered.length === 0){
      const empty = document.createElement("p");
      empty.className = "prose";
      empty.textContent = "No matches.";
      list.appendChild(empty);
      return;
    }

    filtered.forEach(t => {
      const item = document.createElement("article");
      item.className = "item";

      const h = document.createElement("h3");
      h.className = "item-title";
      h.textContent = t.title ?? "(untitled)";
      item.appendChild(h);

      const meta = document.createElement("p");
      meta.className = "item-meta";
      const parts = [t.date, t.where].filter(Boolean);
      meta.textContent = parts.join(" · ");
      item.appendChild(meta);

      const links = document.createElement("div");
      links.className = "item-links";
      const lm = t.links ?? {};
      Object.entries(lm).forEach(([name, href]) => {
        if(!href) return;
        links.appendChild(buildPill(name, href));
      });
      if(links.childElementCount) item.appendChild(links);

      list.appendChild(item);
    });
  }

  search.addEventListener("input", render);
  render();
}

function renderTeaching(teach){
  const cur = $("#teach-current");
  const past = $("#teach-past");
  cur.innerHTML = "";
  past.innerHTML = "";

  const curItems = teach.current ?? [];
  const pastItems = teach.past ?? [];

  if(curItems.length === 0){
    const li = document.createElement("li");
    li.textContent = "—";
    cur.appendChild(li);
  }else{
    curItems.forEach(t => {
      const li = document.createElement("li");
      const parts = [t.course, t.term, t.institution].filter(Boolean);
      li.textContent = parts.join(" · ");
      cur.appendChild(li);
    });
  }

  if(pastItems.length === 0){
    const li = document.createElement("li");
    li.textContent = "—";
    past.appendChild(li);
  }else{
    pastItems.forEach(t => {
      const li = document.createElement("li");
      const parts = [t.course, t.term, t.institution].filter(Boolean);
      li.textContent = parts.join(" · ");
      past.appendChild(li);
    });
  }
}

async function main(){
  try{
    const site = await loadJSON("data/site.json");
    renderSite(site);

    const pubs = await loadJSON("data/publications.json");
    renderPublications(pubs);

    const talks = await loadJSON("data/talks.json");
    renderTalks(talks);

    const teaching = await loadJSON("data/teaching.json");
    renderTeaching(teaching);

    // Portrait
    const imgPath = site.portrait ?? "assets/photo.jpg";
    const portrait = document.querySelector(".portrait");
    const img = new Image();
    img.onload = () => {
      portrait.innerHTML = "";
      portrait.appendChild(img);
    };
    img.onerror = () => { /* keep placeholder */ };
    img.alt = `${site.name ?? "Portrait"} photo`;
    img.src = imgPath;

  }catch(err){
    console.error(err);
    const main = document.querySelector("main");
    const p = document.createElement("p");
    p.className = "prose";
    p.textContent = "Site data failed to load. If you're previewing locally, run a local server (see README).";
    main.prepend(p);
  }
}

document.addEventListener("DOMContentLoaded", main);
