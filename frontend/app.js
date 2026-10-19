/* WebCognitive Engine — interface web (étape 6)
 *
 * Tout passe par l'API REST de l'étape 4 et 5, avec des requêtes asynchrones (fetch) :
 *   POST /ask  (stream: true)  la réponse arrive morceau par morceau (une ligne JSON par événement)
 *   GET  /chunks/{id}          contexte d'un extrait (segments voisins)
 *   GET  /search               onglet « Recherche dans le corpus »
 *   GET  /health               état de la base et du LLM (en haut à droite)
 */
"use strict";

const $ = (id) => document.getElementById(id);
const escapeHtml = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ------------------------------------------------------------------ état du serveur */
async function checkHealth() {
  const dot = $("status-dot"), text = $("status-text");
  try {
    const h = await (await fetch("/health")).json();
    const llm = h.llm || {};
    if (h.status !== "ok") {
      dot.className = "dot ko"; text.textContent = "Base vectorielle vide : lancez build_vectordb.py";
    } else if (!llm.ollama) {
      dot.className = "dot warn"; text.textContent = `${h.chunks} extraits · Ollama non lancé`;
    } else if (!llm.model_available) {
      dot.className = "dot warn"; text.textContent = `Modèle « ${llm.model} » absent : ollama pull ${llm.model}`;
    } else {
      dot.className = "dot ok"; text.textContent = `${h.documents_indexed} documents · ${h.chunks} extraits · LLM ${llm.model}`;
    }
  } catch {
    dot.className = "dot ko"; text.textContent = "API injoignable : lancez python scripts/serve_api.py";
  }
}

/* ------------------------------------------------------------------ onglets */
function showTab(name) {
  const chat = name === "chat";
  $("tab-chat").setAttribute("aria-selected", chat);
  $("tab-search").setAttribute("aria-selected", !chat);
  $("view-chat").hidden = !chat;
  $("view-search").hidden = chat;
  (chat ? $("question") : $("search-q")).focus();
}
$("tab-chat").onclick = () => showTab("chat");
$("tab-search").onclick = () => showTab("search");

/* ------------------------------------------------------------------ rendu de la réponse */
// Échappe le texte, met le gras **…** et transforme [1], [1, 3] en boutons cliquables
function renderAnswer(text) {
  let html = escapeHtml(text).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\[([\d,;\s]+|\d+(?:\s*et\s*\d+)*)\]/g, (match, group) => {
    const nums = group.match(/\d+/g) || [];
    return nums.map((n) => `<button type="button" class="cite" data-n="${n}" title="Voir l'extrait ${n}">${n}</button>`).join("");
  });
  return html.replace(/\n{2,}/g, "<br><br>").replace(/\n/g, "<br>");
}

function addMessage(cls, html) {
  $("empty")?.remove();
  const div = document.createElement("div");
  div.className = `msg ${cls}`;
  div.innerHTML = html;
  $("messages").appendChild(div);
  div.scrollIntoView({ block: "end" });
  return div;
}

/* ------------------------------------------------------------------ panneau des sources */
let currentSources = [];

function sourceCard(s) {
  const loc = s.location || "document entier";
  const by = [s.author, s.year].filter(Boolean).join(", ");
  return `
    <article class="source ${s.cited ? "cited" : "uncited"}" id="source-${s.number}">
      <div class="source-top"><span class="source-num">[${s.number}]</span><span class="source-file">${escapeHtml(s.filename)}</span></div>
      <span class="source-loc">${escapeHtml(loc)}</span>
      <div class="source-title">${escapeHtml(s.title || "")}${by ? ` (${escapeHtml(by)})` : ""}</div>
      <p class="source-text">${escapeHtml(s.text)}</p>
      <div class="source-actions">
        <button type="button" class="linkish" data-context="${escapeHtml(s.chunk_id)}">Voir le contexte</button>
        <span class="score">score ${Number(s.score).toFixed(2)}</span>
      </div>
      <div class="context" hidden></div>
    </article>`;
}

function renderSources(sources, final, refused = false) {
  currentSources = sources;
  const list = $("sources");
  if (!sources.length) {
    list.innerHTML = `<p class="hint">Aucun extrait trouvé pour cette question.</p>`;
    return;
  }
  if (!final) {                      // pendant la rédaction : tous les extraits envoyés au LLM
    list.innerHTML = `<p class="hint">${sources.length} extraits transmis au modèle…</p>` + sources.map(sourceCard).join("");
    return;
  }
  const cited = sources.filter((s) => s.cited), other = sources.filter((s) => !s.cited);
  let html = cited.length
    ? `<h3>Citées dans la réponse</h3>` + cited.map(sourceCard).join("")
    : `<p class="hint">${refused ? "Aucun des extraits trouvés ne contient la réponse : le moteur préfère ne rien inventer."
                                 : "La réponse ne cite aucun extrait."}</p>`;
  if (other.length) {
    html += `<details class="uncited-group" ${cited.length || refused ? "" : "open"}><summary>Extraits consultés mais non cités (${other.length})</summary>`
      + other.map(sourceCard).join("") + `</details>`;
  }
  list.innerHTML = html;
}

function focusSource(n) {
  const card = $(`source-${n}`);
  if (!card) return;
  card.closest("details")?.setAttribute("open", "");
  card.scrollIntoView({ behavior: "smooth", block: "nearest" });
  card.classList.remove("flash"); void card.offsetWidth; card.classList.add("flash");
}

// Clic sur [n] dans une réponse, ou sur « Voir le contexte » dans une fiche
document.addEventListener("click", async (e) => {
  const cite = e.target.closest(".cite");
  if (cite) {
    const answer = cite.closest(".msg");
    if (answer && answer.sources) renderSources(answer.sources, true, answer.refused);   // revenir aux sources de cette réponse
    focusSource(cite.dataset.n);
    return;
  }
  const ctx = e.target.closest("[data-context]");
  if (ctx) showContext(ctx);
});

async function showContext(button) {
  const box = button.closest(".source, li").querySelector(".context");
  if (!box.hidden) { box.hidden = true; button.textContent = "Voir le contexte"; return; }
  const id = button.dataset.context;
  const chunk = await (await fetch(`/chunks/${encodeURIComponent(id)}`)).json();
  const parts = [];
  if (chunk.previous) parts.push(escapeHtml((await (await fetch(`/chunks/${chunk.previous}`)).json()).text));
  parts.push(`<mark>${escapeHtml(chunk.text)}</mark>`);
  if (chunk.next) parts.push(escapeHtml((await (await fetch(`/chunks/${chunk.next}`)).json()).text));
  box.innerHTML = parts.join(" … ");
  box.hidden = false; button.textContent = "Masquer le contexte";
}

/* ------------------------------------------------------------------ envoi d'une question (streaming) */
async function ask(question) {
  addMessage("user", escapeHtml(question));
  const bot = addMessage("bot", `<div class="answer"><span class="thinking">Recherche des extraits…</span></div><div class="meta"></div>`);
  const answerEl = bot.querySelector(".answer"), metaEl = bot.querySelector(".meta");
  $("send").disabled = true;

  const body = { question, stream: true, mode: $("opt-mode").value, k: Number($("opt-k").value) };
  if ($("opt-lang").value) body.lang = $("opt-lang").value;

  let text = "";
  try {
    const response = await fetch("/ask", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error((await response.json()).detail || `erreur ${response.status}`);

    // Lecture du flux : chaque ligne est un événement JSON (sources, token, done ou error)
    const reader = response.body.getReader(), decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const line of lines.filter(Boolean)) {
        const ev = JSON.parse(line);
        if (ev.type === "sources") {
          renderSources(ev.sources, false);
          answerEl.innerHTML = `<span class="thinking">Rédaction de la réponse…</span>`;
        } else if (ev.type === "token") {
          text += ev.text;
          answerEl.innerHTML = renderAnswer(text);
          answerEl.classList.add("cursor");
          bot.scrollIntoView({ block: "end" });
        } else if (ev.type === "done") {
          answerEl.classList.remove("cursor");
          answerEl.innerHTML = renderAnswer(ev.answer);
          answerEl.classList.toggle("refused", ev.refused);
          bot.sources = ev.sources; bot.refused = ev.refused;
          renderSources(ev.sources, true, ev.refused);
          const who = ev.guard ? "question hors du corpus (garde-fou)" : `${ev.model}`;
          metaEl.textContent = `${who} · ${ev.cited.length} source(s) citée(s) · ${(ev.total_ms / 1000).toFixed(1)} s`;
        } else if (ev.type === "error") {
          throw new Error(ev.message);
        }
      }
    }
  } catch (err) {
    answerEl.classList.remove("cursor");
    answerEl.classList.add("error");
    answerEl.textContent = `Impossible d'obtenir une réponse : ${err.message}`;
  } finally {
    $("send").disabled = false;
    checkHealth();
  }
}

$("ask-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const q = $("question").value.trim();
  if (!q || $("send").disabled) return;
  $("question").value = "";
  ask(q);
});
// Entrée envoie, Maj + Entrée passe à la ligne
$("question").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("ask-form").requestSubmit(); }
});
$("examples").addEventListener("click", (e) => {
  if (e.target.tagName === "BUTTON") ask(e.target.textContent);
});

/* ------------------------------------------------------------------ onglet Recherche */
$("search-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = $("search-q").value.trim();
  const params = new URLSearchParams({ q, k: 10, mode: $("search-mode").value });
  $("search-meta").textContent = "Recherche…";
  try {
    const r = await fetch(`/search?${params}`);
    if (!r.ok) throw new Error((await r.json()).detail);
    const data = await r.json();
    $("search-meta").textContent = `${data.count} résultats en ${data.took_ms} ms`;
    $("search-results").innerHTML = data.results.map((h) => `
      <li>
        <div class="source-top"><span class="source-num">${h.rank}.</span><span class="source-file">${escapeHtml(h.filename)}</span>
          <span class="score">score ${h.score.toFixed(3)}</span></div>
        <span class="source-loc">${escapeHtml(h.location || "document entier")}</span>
        <div class="source-title">${escapeHtml(h.title || "")}</div>
        <p class="source-text">${escapeHtml(h.text)}</p>
        <div class="source-actions"><button type="button" class="linkish" data-context="${escapeHtml(h.chunk_id)}">Voir le contexte</button></div>
        <div class="context" hidden></div>
      </li>`).join("");
  } catch (err) {
    $("search-meta").textContent = `Erreur : ${err.message}`;
  }
});

checkHealth();
