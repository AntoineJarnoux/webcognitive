"""Étape 5 : pipeline RAG (Retrieval-Augmented Generation) avec un LLM local.

    question ──► recherche (étape 4) ──► k extraits numérotés [1]…[k]
                                              │
             consigne + extraits + question ──► LLM local (Ollama) ──► réponse avec [n]
                                                                          │
                                       [n] cités ──► sources affichées (fichier, page)

Trois idées pour éviter les inventions (« hallucinations ») :
1. **La consigne** (prompt système) oblige le LLM à répondre uniquement à partir des
   extraits, et à dire « Je ne sais pas » si la réponse n'y est pas.
2. **La citation** : chaque extrait porte un numéro, le LLM doit l'indiquer entre
   crochets. On sait ainsi d'où vient chaque information, et on peut la vérifier.
3. **Le garde-fou** : si même le meilleur extrait est très loin de la question
   (cosinus < 0,35, ex. « Quelle est la capitale de l'Australie ? »), on refuse
   sans appeler le LLM. Pour les questions proches du thème, c'est la consigne qui joue.

Ollama fait tourner le LLM sur la machine et l'expose sur http://127.0.0.1:11434 :
on lui envoie la conversation en JSON et il renvoie la réponse, mot par mot si on le demande.
"""
from __future__ import annotations

import json
import re
import time
from typing import Iterator

import requests

from . import config
from .search_engine import Filters, SearchEngine

REFUSAL = "Je ne sais pas : cette information n'est pas dans le corpus."

SYSTEM_PROMPT = f"""Tu es l'assistant documentaire de WebCognitive Engine, spécialisé dans l'histoire d'Internet.
Tu réponds à la question en t'appuyant UNIQUEMENT sur les extraits numérotés du CONTEXTE.

Règles :
1. N'utilise jamais tes connaissances personnelles : seulement le contenu des extraits.
2. Si les extraits ne contiennent pas la réponse, réponds exactement : « {REFUSAL} » et rien d'autre.
3. Réponds en français, de façon précise et concise (quelques phrases), même si les extraits sont en anglais.
4. Après chaque information, indique entre crochets le numéro de l'extrait qui la justifie, par exemple [2].
   N'invente jamais de numéro d'extrait."""


class LLMUnavailable(RuntimeError):
    """Ollama n'est pas lancé, ou le modèle n'est pas téléchargé."""


# --------------------------------------------------------------------------- #
# Client Ollama (API HTTP locale)
# --------------------------------------------------------------------------- #
class OllamaClient:
    def __init__(self, model: str = config.LLM_MODEL, url: str = config.OLLAMA_URL,
                 temperature: float = config.LLM_TEMPERATURE, num_ctx: int = config.LLM_NUM_CTX,
                 timeout: int = config.LLM_TIMEOUT):
        self.model, self.url = model, url.rstrip("/")
        self.options = {"temperature": temperature, "num_ctx": num_ctx}
        self.timeout = timeout

    def status(self) -> dict:
        """Ollama répond-il, et le modèle est-il téléchargé ?"""
        try:
            tags = requests.get(f"{self.url}/api/tags", timeout=3).json()
        except requests.RequestException:
            return {"model": self.model, "ollama": False, "model_available": False}
        names = {m.get("name", "") for m in tags.get("models", [])}
        available = any(n == self.model or n.split(":")[0] == self.model for n in names)
        return {"model": self.model, "ollama": True, "model_available": available}

    def chat(self, messages: list[dict]) -> Iterator[str]:
        """Envoie la conversation et renvoie la réponse morceau par morceau (streaming)."""
        try:
            response = requests.post(f"{self.url}/api/chat", stream=True, timeout=self.timeout, json={
                "model": self.model, "messages": messages, "stream": True, "options": self.options})
        except requests.RequestException as exc:
            raise LLMUnavailable(f"Ollama ne répond pas sur {self.url} : lancez Ollama "
                                 f"(https://ollama.com) puis « ollama pull {self.model} ».") from exc
        if response.status_code == 404:
            raise LLMUnavailable(f"Le modèle « {self.model} » n'est pas téléchargé : lancez « ollama pull {self.model} ».")
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            if data.get("error"):
                raise LLMUnavailable(data["error"])
            piece = data.get("message", {}).get("content", "")
            if piece:
                yield piece
            if data.get("done"):
                break


# --------------------------------------------------------------------------- #
# Pipeline RAG
# --------------------------------------------------------------------------- #
def format_context(hits: list[dict]) -> str:
    """Les extraits numérotés, chacun avec sa source, tels que le LLM les lit."""
    blocks = []
    for n, h in enumerate(hits, start=1):
        meta = ", ".join(str(v) for v in (h.get("author"), h.get("year")) if v)
        title = f"{h.get('title') or h['filename']}" + (f" ({meta})" if meta else "")
        blocks.append(f"[{n}] Source : {h['citation']} — {title}\n{h['text']}")
    return "\n\n".join(blocks)


def build_messages(question: str, hits: list[dict]) -> list[dict]:
    user = (f"CONTEXTE :\n\n{format_context(hits)}\n\n"
            f"QUESTION : {question}\n\n"
            "RÉPONSE (en français, avec le numéro des extraits entre crochets) :")
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def cited_numbers(answer: str, count: int) -> list[int]:
    """Numéros d'extraits cités dans la réponse : [2], [1, 3] ou [1][4]. Les numéros inventés sont ignorés."""
    found = []
    for group in re.findall(r"\[([\d,\s;et]+)\]", answer):
        for n in re.findall(r"\d+", group):
            n = int(n)
            if 1 <= n <= count and n not in found:
                found.append(n)
    return sorted(found)


def is_refusal(answer: str) -> bool:
    return "je ne sais pas" in answer.lower()


def source_view(n: int, hit: dict, cited: list[int]) -> dict:
    """Ce que l'interface affiche pour une source."""
    keys = ("chunk_id", "doc_id", "filename", "format", "title", "author", "year", "lang", "page", "page_end",
            "section", "location", "citation", "text", "score")
    return {"number": n, "cited": n in cited, **{k: hit.get(k) for k in keys}}


class RagPipeline:
    def __init__(self, engine: SearchEngine, llm: OllamaClient | None = None,
                 min_score: float = config.RAG_MIN_SCORE):
        self.engine = engine
        self.llm = llm or OllamaClient()
        self.min_score = min_score

    def retrieve(self, question: str, k: int, mode: str, filters: Filters | None) -> list[dict]:
        return self.engine.search(question, k, mode, filters)

    def off_topic(self, hits: list[dict]) -> bool:
        """Garde-fou : aucun extrait, ou meilleur cosinus trop faible (question sans rapport avec le corpus)."""
        if not hits:
            return True
        best = max((h.get("semantic_score") for h in hits if h.get("semantic_score") is not None), default=None)
        return best is not None and best < self.min_score

    def stream(self, question: str, k: int = config.RAG_K, mode: str = config.RAG_MODE,
               filters: Filters | None = None) -> Iterator[dict]:
        """Déroulé complet sous forme d'événements, pour l'affichage en direct :
        {"type": "sources"}, puis des {"type": "token"}, puis {"type": "done"} (ou {"type": "error"})."""
        start = time.perf_counter()
        hits = self.retrieve(question, k, mode, filters)
        retrieval_ms = (time.perf_counter() - start) * 1000
        yield {"type": "sources", "sources": [source_view(n, h, []) for n, h in enumerate(hits, start=1)],
               "retrieval_ms": round(retrieval_ms)}

        if self.off_topic(hits):
            yield {"type": "token", "text": REFUSAL}
            yield self._done(REFUSAL, hits, retrieval_ms, start, guard=True)
            return

        answer = ""
        try:
            for piece in self.llm.chat(build_messages(question, hits)):
                answer += piece
                yield {"type": "token", "text": piece}
        except LLMUnavailable as exc:
            yield {"type": "error", "message": str(exc)}
            return
        yield self._done(answer.strip(), hits, retrieval_ms, start, guard=False)

    def _done(self, answer: str, hits: list[dict], retrieval_ms: float, start: float, guard: bool) -> dict:
        refused = is_refusal(answer)
        cited = [] if refused else cited_numbers(answer, len(hits))
        return {
            "type": "done", "answer": answer, "refused": refused, "guard": guard, "cited": cited,
            "sources": [source_view(n, h, cited) for n, h in enumerate(hits, start=1)],
            "model": None if guard else self.llm.model,
            "retrieval_ms": round(retrieval_ms), "total_ms": round((time.perf_counter() - start) * 1000),
        }

    def ask(self, question: str, k: int = config.RAG_K, mode: str = config.RAG_MODE,
            filters: Filters | None = None) -> dict:
        """Version sans streaming : renvoie directement la réponse complète et ses sources."""
        for event in self.stream(question, k, mode, filters):
            if event["type"] == "error":
                raise LLMUnavailable(event["message"])
            if event["type"] == "done":
                return event
        raise RuntimeError("le pipeline s'est arrêté sans réponse")
