#!/usr/bin/env python3
"""
Carte 2D des vecteurs : chaque point est un segment du corpus.

Les vecteurs ont 384 dimensions ; on ne peut pas les dessiner tels quels. t-SNE
les projette en 2 dimensions en essayant de garder les voisins proches ensemble :
deux segments de sens proche restent deux points proches sur la carte.
(Les distances entre groupes éloignés, elles, ne sont pas fiables.)

Sortie : docs/carte_vecteurs.html (page interactive, à ouvrir dans un navigateur).
La bibliothèque de graphiques Plotly est incluse dans la page : elle s'ouvre sans connexion.

Usage :
    python scripts/carte_vecteurs.py          # ~1 min sur CPU
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np  # noqa: E402
from plotly.offline import get_plotlyjs  # noqa: E402
from sklearn.manifold import TSNE  # noqa: E402

from webcognitive import config  # noqa: E402
from webcognitive.embeddings import load_index  # noqa: E402
from webcognitive.search_engine import location  # noqa: E402

OUTPUT = config.ROOT / "docs" / "carte_vecteurs.html"


def main() -> int:
    chunks, vectors, manifest = load_index(config.EMBEDDINGS_DIR)
    print(f"{len(chunks)} segments, {vectors.shape[1]} dimensions -> projection t-SNE en 2D…")
    start = time.perf_counter()
    xy = TSNE(n_components=2, metric="cosine", init="pca", perplexity=30, random_state=0).fit_transform(vectors)
    print(f"t-SNE : {time.perf_counter() - start:.0f} s")

    data = {
        "x": np.round(xy[:, 0], 2).tolist(),
        "y": np.round(xy[:, 1], 2).tolist(),
        "id": [c["chunk_id"] for c in chunks],
        "doc": [c["doc_id"] for c in chunks],
        "title": [c["title"] or c["filename"] for c in chunks],
        "format": [c["format"] for c in chunks],
        "lang": [c["lang"] for c in chunks],
        "year": [c["year"] for c in chunks],
        "loc": [location(c) for c in chunks],
        "text": [c["text"] for c in chunks],
    }
    html = TEMPLATE.replace("__PLOTLY__", get_plotlyjs()).replace("__DATA__", json.dumps(data, ensure_ascii=False)) \
                   .replace("__MODEL__", manifest["model"].split("/")[-1]) \
                   .replace("__COUNT__", f"{len(chunks):,}".replace(",", " "))
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Carte écrite : {OUTPUT.relative_to(config.ROOT)}")
    return 0


TEMPLATE = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Carte des vecteurs</title>
<script>__PLOTLY__</script>
<style>
  :root { --bg:#0b1020; --panel:#121a30; --line:#24304f; --text:#e6ebf5; --muted:#8d99b5; --accent:#5aa9ff; }
  * { box-sizing:border-box; }
  body { margin:0; background:radial-gradient(1200px 700px at 70% -10%, #1a2550 0%, var(--bg) 60%); color:var(--text);
         font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; min-height:100vh; }
  header { padding:22px 28px 8px; }
  h1 { margin:0; font-size:22px; letter-spacing:.2px; }
  .sub { color:var(--muted); font-size:13px; margin-top:4px; }
  .bar { display:flex; flex-wrap:wrap; gap:10px; align-items:center; padding:10px 28px; }
  .seg { display:flex; background:var(--panel); border:1px solid var(--line); border-radius:10px; overflow:hidden; }
  .seg button { background:none; border:0; color:var(--muted); padding:8px 14px; font-size:13px; cursor:pointer; }
  .seg button.on { background:var(--accent); color:#06101f; font-weight:600; }
  input { background:var(--panel); border:1px solid var(--line); color:var(--text); border-radius:10px; padding:8px 12px;
          font-size:13px; width:280px; outline:none; }
  input:focus { border-color:var(--accent); }
  #count { color:var(--muted); font-size:13px; }
  main { display:grid; grid-template-columns:1fr 340px; gap:14px; padding:6px 28px 24px; }
  #plot { height:calc(100vh - 150px); min-height:480px; background:rgba(18,26,48,.6); border:1px solid var(--line); border-radius:14px; }
  aside { background:rgba(18,26,48,.85); border:1px solid var(--line); border-radius:14px; padding:16px; overflow:auto;
          height:calc(100vh - 150px); min-height:480px; font-size:13px; line-height:1.5; }
  aside h2 { font-size:14px; margin:0 0 8px; color:var(--accent); }
  .meta { color:var(--muted); font-size:12px; margin-bottom:10px; }
  .hint { color:var(--muted); }
  code { color:#9fd0ff; }
  @media (max-width: 900px) { main { grid-template-columns:1fr; } aside { height:auto; } }
</style>
</head>
<body>
<header>
  <h1>Carte des vecteurs du corpus</h1>
  <div class="sub">__COUNT__ segments · 384 dimensions projetées en 2D (t-SNE) · modèle __MODEL__ · deux points proches = deux passages de sens proche</div>
</header>
<div class="bar">
  <div class="seg" id="modes">
    <button data-k="title" class="on">Document</button><button data-k="format">Format</button>
    <button data-k="lang">Langue</button><button data-k="decade">Décennie</button>
  </div>
  <input id="q" placeholder="Surligner un mot (ex. DNS, Pouzin, 1983)…" autocomplete="off">
  <span id="count"></span>
</div>
<main>
  <div id="plot"></div>
  <aside id="side">
    <h2>Mode d'emploi</h2>
    <p class="hint">Survolez un point pour voir son passage, cliquez pour l'afficher ici. Molette : zoom. Double-clic : vue d'ensemble.
    Cliquez une légende pour masquer un groupe, double-cliquez pour l'isoler.</p>
    <p class="hint">Les passages qui parlent du même sujet forment des îlots, même s'ils viennent de documents
    différents, ou de langues différentes : c'est ce que la recherche sémantique exploite.</p>
  </aside>
</main>
<script>
const D = __DATA__;
const N = D.x.length;
D.decade = D.year.map(y => y ? (Math.floor(y / 10) * 10) + "s" : "inconnue");
const PALETTE = ["#5aa9ff","#ff7a90","#ffd166","#06d6a0","#c792ea","#ff9f43","#4dd0e1","#f78fb3","#a3e635","#f472b6",
  "#60a5fa","#fbbf24","#34d399","#a78bfa","#fb7185","#22d3ee","#facc15","#4ade80","#e879f9","#38bdf8"];
let mode = "title", query = "";
const short = s => s.length > 150 ? s.slice(0, 150) + "…" : s;
const wrap = s => s.replace(/(.{1,70})(\s|$)/g, "$1<br>");

function traces() {
  const keys = [...new Set(D[mode])].sort();
  const q = query.trim().toLowerCase();
  let hits = 0;
  const out = keys.map((k, i) => {
    const idx = []; for (let j = 0; j < N; j++) if (D[mode][j] === k) idx.push(j);
    const match = idx.map(j => !q || D.text[j].toLowerCase().includes(q));
    hits += match.filter(Boolean).length;
    return {
      type: "scattergl", mode: "markers", name: String(k).slice(0, 48),
      x: idx.map(j => D.x[j]), y: idx.map(j => D.y[j]), customdata: idx,
      text: idx.map(j => `<b>${D.title[j]}</b> · ${D.loc[j] || ""}<br>${wrap(short(D.text[j]))}`),
      hovertemplate: "%{text}<extra></extra>",
      marker: { size: idx.map((_, n) => q && match[n] ? 9 : 5), color: PALETTE[i % PALETTE.length],
                opacity: idx.map((_, n) => !q ? 0.8 : (match[n] ? 1 : 0.07)),
                line: { width: idx.map((_, n) => q && match[n] ? 1 : 0), color: "#ffffff" } }
    };
  });
  document.getElementById("count").textContent = q ? `${hits} segment(s) contiennent « ${query.trim()} »` : `${N} segments`;
  return out;
}
const layout = {
  paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", margin: { l: 10, r: 10, t: 10, b: 10 },
  xaxis: { visible: false }, yaxis: { visible: false }, dragmode: "pan", hovermode: "closest",
  hoverlabel: { bgcolor: "#0b1020", bordercolor: "#5aa9ff", font: { color: "#e6ebf5", size: 12 } },
  legend: { font: { color: "#c9d3ea", size: 11 }, bgcolor: "rgba(11,16,32,.7)", itemsizing: "constant" }
};
const plot = document.getElementById("plot");
function draw() { Plotly.react(plot, traces(), layout, { responsive: true, scrollZoom: true, displaylogo: false }); }
draw();
document.querySelectorAll("#modes button").forEach(b => b.onclick = () => {
  document.querySelectorAll("#modes button").forEach(x => x.classList.remove("on"));
  b.classList.add("on"); mode = b.dataset.k; draw();
});
let t; document.getElementById("q").oninput = e => { clearTimeout(t); t = setTimeout(() => { query = e.target.value; draw(); }, 200); };
plot.on("plotly_click", ev => {
  const j = ev.points[0].customdata;
  const esc = s => s.replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  document.getElementById("side").innerHTML =
    `<h2>${esc(D.title[j])}</h2><div class="meta"><code>${D.id[j]}</code> · ${D.loc[j] || ""} · ${D.format[j]} · ${D.lang[j]} · ${D.year[j] || ""}</div>` +
    `<p>${esc(D.text[j])}</p>`;
});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    sys.exit(main())
