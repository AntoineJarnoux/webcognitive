/* WebCognitive Engine — tableau de bord (étape 7)
 *
 * Les chiffres sont calculés côté serveur (src/webcognitive/analytics.py) ;
 * cette page ne fait que les dessiner avec Plotly.js, servi en local par l'API
 * (/vendor/plotly.min.js, aucune connexion Internet nécessaire).
 *   GET /stats            répartitions, segments, thématiques, termes
 *   GET /stats/map        carte 2D des segments
 *   GET /stats/questions  questions posées à l'assistant
 */
"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (n) => Number(n).toLocaleString("fr-FR");

  /* Couleurs : palette vérifiée (daltonisme, contraste). Une couleur suit toujours la même entité. */
  const FORMAT = { pdf: "#2a78d6", txt: "#eb6834", html: "#1baf7a", docx: "#eda100" };
  const FORMAT_LABEL = { pdf: "PDF", txt: "TXT", html: "HTML", docx: "DOCX" };
  const LANG = { fr: "#6250d6", en: "#008300" };
  const LANG_LABEL = { fr: "français", en: "anglais" };
  const SINGLE = "#2a56b8";                          // série unique (bleu de l'interface)
  const SEQ = [[0, "#f4f8fd"], [0.15, "#cde2fb"], [0.35, "#86b6ef"], [0.6, "#3987e5"], [0.8, "#1c5cab"], [1, "#0d366b"]];
  const INK = "#1d2838", MUTED = "#5d6878", GRID = "#e3e8e5";

  const baseLayout = (extra = {}) => ({
    font: { family: '"Segoe UI", "Inter", "DejaVu Sans", system-ui, sans-serif', size: 12, color: INK },
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    margin: { l: 48, r: 12, t: 8, b: 40 },
    hoverlabel: { bgcolor: "#ffffff", bordercolor: "#cfd8d2", font: { color: INK, size: 12 } },
    xaxis: { gridcolor: GRID, zeroline: false, tickfont: { color: MUTED }, automargin: true },
    yaxis: { gridcolor: GRID, zeroline: false, tickfont: { color: MUTED }, automargin: true },
    legend: { orientation: "h", y: -0.18, font: { color: INK } },
    bargap: 0.25,
    ...extra,
  });
  const CONFIG = { displaylogo: false, responsive: true,
    modeBarButtonsToRemove: ["select2d", "lasso2d", "autoScale2d", "toggleSpikelines"] };
  const draw = (id, data, layout) => Plotly.react($(id), data, baseLayout(layout), CONFIG);

  /* ---------------------------------------------------------------- chargement */
  let loaded = false;
  function loadPlotly() {
    return new Promise((resolve, reject) => {
      if (window.Plotly) return resolve();
      const s = document.createElement("script");
      s.src = "/vendor/plotly.min.js";
      s.onload = resolve;
      s.onerror = () => reject(new Error("Plotly n'a pas pu être chargé (pip install -r requirements.txt)"));
      document.head.appendChild(s);
    });
  }

  window.loadDashboard = async () => {
    if (loaded) { refreshQuestions(); return; }
    $("tiles").innerHTML = `<p class="hint">Calcul des indicateurs…</p>`;
    try {
      await loadPlotly();
      const stats = await (await fetch("/stats")).json();
      loaded = true;
      renderTiles(stats);
      renderFormats(stats);
      renderDecades(stats);
      renderChunks(stats);
      renderThemes(stats);
      renderTerms(stats, "fr");
      renderMap();
      refreshQuestions();
    } catch (err) {
      $("tiles").innerHTML = `<p class="hint">Impossible d'afficher le tableau de bord : ${esc(err.message)}</p>`;
    }
  };

  /* ---------------------------------------------------------------- chiffres clés */
  function renderTiles(s) {
    const t = s.totals;
    const tiles = [
      [fmt(t.documents), "documents", `${t.documents_indexed} indexés · 4 formats`],
      [fmt(t.chunks), "segments indexés", `taille médiane ${t.chunk_median} caractères`],
      [fmt(t.words), "mots", "après nettoyage"],
      [`${t.years[0]}–${t.years[1]}`, "période couverte", `${t.undated} documents non datés`],
      ["…", "questions posées", "", "tile-questions"],
    ];
    $("tiles").innerHTML = tiles.map(([value, label, sub, id]) => `
      <div class="tile"${id ? ` id="${id}"` : ""}><span class="tile-value">${esc(value)}</span>
        <span class="tile-label">${esc(label)}</span><span class="tile-sub">${esc(sub)}</span></div>`).join("");
  }

  /* ---------------------------------------------------------------- formats */
  function renderFormats(s) {
    const f = s.by_format;
    draw("ch-format", [{
      type: "pie", hole: 0.55, sort: false, direction: "clockwise",
      labels: f.map((d) => FORMAT_LABEL[d.format]), values: f.map((d) => d.documents),
      marker: { colors: f.map((d) => FORMAT[d.format]), line: { color: "#ffffff", width: 2 } },
      texttemplate: "%{label}<br>%{value}", textposition: "outside", textfont: { color: INK },
      customdata: f.map((d) => [d.words, d.chunks]),
      hovertemplate: "<b>%{label}</b> : %{value} documents (%{percent})<br>%{customdata[0]:,} mots · %{customdata[1]:,} segments<extra></extra>",
    }], { showlegend: false, margin: { l: 20, r: 20, t: 20, b: 20 },
      annotations: [{ text: `<b>${s.totals.documents}</b><br>documents`, showarrow: false, font: { size: 14, color: INK } }] });

    draw("ch-words", [{
      type: "bar", x: f.map((d) => FORMAT_LABEL[d.format]), y: f.map((d) => d.words),
      marker: { color: f.map((d) => FORMAT[d.format]), cornerradius: 4 },
      text: f.map((d) => fmt(d.words)), textposition: "outside", textfont: { color: INK }, cliponaxis: false,
      customdata: f.map((d) => [d.documents, Math.round(d.words / d.documents)]),
      hovertemplate: "<b>%{x}</b> : %{y:,} mots<br>%{customdata[0]} documents, %{customdata[1]:,} mots en moyenne<extra></extra>",
    }], { showlegend: false, separators: ", " });
  }

  /* ---------------------------------------------------------------- décennies */
  function renderDecades(s) {
    const d = s.by_decade;
    draw("ch-decade", ["fr", "en"].map((lang) => ({
      type: "bar", name: LANG_LABEL[lang], x: d.map((r) => r.decade.replace("s", "")), y: d.map((r) => r[lang]),
      marker: { color: LANG[lang], line: { color: "#ffffff", width: 2 } },
      hovertemplate: `%{x} : %{y} document(s) en ${LANG_LABEL[lang]}<extra></extra>`,
    })), { barmode: "stack", yaxis: { dtick: 2, gridcolor: GRID, tickfont: { color: MUTED } },
      legend: { orientation: "h", y: 1.12, x: 0 } });
  }

  /* ---------------------------------------------------------------- segments */
  function renderChunks(s) {
    const h = s.chunk_histogram.filter((b) => b.count > 0 || b.from >= 100);
    $("cap-chunks").textContent = `Nombre de segments par tranche de 25 caractères. Taille moyenne ${s.totals.chunk_mean}, médiane ${s.totals.chunk_median} (découpage visé : 500, coupé en fin de phrase).`;
    draw("ch-chunks", [{
      type: "bar", x: h.map((b) => b.from + 12.5), y: h.map((b) => b.count), width: 23,
      marker: { color: SINGLE, cornerradius: 3 },
      customdata: h.map((b) => `${b.from}–${b.to}`),
      hovertemplate: "%{customdata} caractères : %{y:,} segments<extra></extra>",
    }], { xaxis: { title: { text: "caractères par segment", font: { color: MUTED } }, gridcolor: GRID, tickfont: { color: MUTED }, dtick: 100 },
      showlegend: false });
  }

  /* ---------------------------------------------------------------- thématiques */
  function renderThemes(s) {
    const docs = s.themes_by_document;   // triés par date côté serveur : le plus ancien en haut
    const themes = s.themes;
    draw("ch-themes", [{
      type: "heatmap", x: themes, y: docs.map((d) => `${d.year || "s. d."} · ${d.label}`),
      z: docs.map((d) => themes.map((t) => d.per_10k[t])),
      customdata: docs.map((d) => themes.map((t) => [d.counts[t], d.title])),
      colorscale: SEQ, zmin: 0, zmax: 60, xgap: 2, ygap: 2,
      colorbar: { title: { text: "pour 10 000 mots", side: "right", font: { color: MUTED } }, thickness: 10, outlinewidth: 0, tickfont: { color: MUTED } },
      hovertemplate: "<b>%{customdata[1]}</b><br>%{x} : %{customdata[0]} mention(s), %{z} pour 10 000 mots<extra></extra>",
    }], { margin: { l: 10, r: 10, t: 90, b: 10 }, xaxis: { side: "top", tickangle: -30, tickfont: { color: INK } },
      yaxis: { autorange: "reversed", tickfont: { size: 11, color: INK }, automargin: true } });

    const dec = s.themes_by_decade;
    draw("ch-decade-themes", [{
      type: "heatmap", x: dec.map((d) => `${d.decade.replace("s", "")}<br><span style="font-size:10px">${d.documents} doc.</span>`),
      y: themes, z: themes.map((t) => dec.map((d) => d.per_10k[t])),
      colorscale: SEQ, zmin: 0, zmax: 60, xgap: 2, ygap: 2, showscale: false,
      hovertemplate: "%{y}, %{x} : %{z} pour 10 000 mots<extra></extra>",
    }], { margin: { l: 10, r: 10, t: 10, b: 50 }, yaxis: { autorange: "reversed", automargin: true, tickfont: { color: INK } } });
  }

  /* ---------------------------------------------------------------- termes */
  let statsCache = null;
  function renderTerms(s, lang) {
    statsCache = s;
    const terms = s.top_terms[lang].slice().reverse();
    draw("ch-terms", [{
      type: "bar", orientation: "h", y: terms.map((t) => t.term), x: terms.map((t) => t.count),
      marker: { color: LANG[lang], cornerradius: 3 },
      text: terms.map((t) => fmt(t.count)), textposition: "outside", cliponaxis: false, textfont: { color: MUTED, size: 11 },
      hovertemplate: "« %{y} » : %{x:,} occurrences<extra></extra>",
    }], { margin: { l: 10, r: 40, t: 4, b: 30 }, showlegend: false, yaxis: { automargin: true, tickfont: { color: INK } } });
  }
  document.querySelectorAll(".seg-toggle button").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll(".seg-toggle button").forEach((x) => x.setAttribute("aria-pressed", x === b));
    if (statsCache) renderTerms(statsCache, b.dataset.lang);
  }));

  /* ---------------------------------------------------------------- carte sémantique */
  let mapData = null;
  async function renderMap() {
    const r = await fetch("/stats/map");
    if (!r.ok) {
      $("ch-map").innerHTML = `<p class="hint">${esc((await r.json()).detail)}</p>`;
      return;
    }
    mapData = await r.json();
    const docs = [...new Set(mapData.doc)].sort();
    const titles = {};
    mapData.doc.forEach((d, i) => { titles[d] = mapData.title[i]; });
    $("map-doc").innerHTML += docs.map((d) => `<option value="${d}">${d} · ${esc(titles[d].slice(0, 60))}</option>`).join("");
    drawMap("");
  }
  function drawMap(highlight) {
    const traces = ["fr", "en"].map((lang) => {
      const idx = mapData.lang.map((l, i) => (l === lang ? i : -1)).filter((i) => i >= 0);
      return {
        type: "scattergl", mode: "markers", name: `passages en ${LANG_LABEL[lang]}`,
        x: idx.map((i) => mapData.x[i]), y: idx.map((i) => mapData.y[i]),
        text: idx.map((i) => `<b>${esc(mapData.title[i])}</b> · ${esc(mapData.loc[i] || "")}<br>${esc(mapData.text[i]).replace(/(.{1,80})(\s|$)/g, "$1<br>")}`),
        hovertemplate: "%{text}<extra></extra>",
        marker: {
          size: idx.map((i) => (highlight && mapData.doc[i] === highlight ? 9 : 5)),
          color: idx.map((i) => (!highlight || mapData.doc[i] === highlight ? LANG[lang] : "#c9d1cc")),
          opacity: idx.map((i) => (!highlight ? 0.65 : mapData.doc[i] === highlight ? 1 : 0.35)),
          line: { color: "#ffffff", width: idx.map((i) => (highlight && mapData.doc[i] === highlight ? 1 : 0)) },
        },
      };
    });
    draw("ch-map", traces, { margin: { l: 10, r: 10, t: 10, b: 10 }, dragmode: "pan", hovermode: "closest",
      xaxis: { visible: false }, yaxis: { visible: false }, showlegend: !highlight,
      legend: { orientation: "h", x: 0, y: 1.06 } });
  }
  $("map-doc").addEventListener("change", (e) => mapData && drawMap(e.target.value));

  /* ---------------------------------------------------------------- questions posées */
  async function refreshQuestions() {
    const q = await (await fetch("/stats/questions")).json();
    const tile = $("tile-questions");
    if (tile) {
      tile.querySelector(".tile-value").textContent = fmt(q.questions);
      tile.querySelector(".tile-sub").textContent = q.questions ? `${q.refused} refus · ${q.mean_seconds ?? "–"} s en moyenne` : "aucune pour l'instant";
    }
    if (!q.questions) {
      $("questions").innerHTML = `<p class="hint">Aucune question posée pour l'instant. Utilisez l'onglet Assistant : chaque question sera comptée ici.</p>`;
      return;
    }
    $("questions").innerHTML = `
      <div class="q-grid">
        <div><h3>Documents les plus cités dans les réponses</h3><div id="ch-cited" class="chart small"></div></div>
        <div><h3>Dernières questions</h3><ol class="recent">${q.recent.map((r) => `
          <li><span>${esc(r.question)}</span>${r.refused ? `<em class="tag-refused">refus</em>` : ""}
            <time>${new Date(r.at).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" })}</time></li>`).join("")}</ol></div>
      </div>`;
    const c = q.most_cited.slice().reverse();
    if (!c.length) { $("ch-cited").innerHTML = `<p class="hint">Aucune source citée pour l'instant.</p>`; return; }
    $("ch-cited").style.height = `${70 + 30 * c.length}px`;
    draw("ch-cited", [{
      type: "bar", orientation: "h", y: c.map((d) => `${d.id} · ${d.label}`), x: c.map((d) => d.count),
      marker: { color: SINGLE, cornerradius: 3 }, text: c.map((d) => d.count), textposition: "outside", cliponaxis: false,
      hovertemplate: "%{y} : cité dans %{x} réponse(s)<extra></extra>",
    }], { margin: { l: 10, r: 30, t: 4, b: 30 }, showlegend: false, xaxis: { dtick: 1, gridcolor: GRID, tickfont: { color: MUTED } },
      yaxis: { automargin: true, tickfont: { color: INK } } });
  }
})();
