"""
Paper search: Semantic Scholar as the authoritative source,
Gemini to generate relevance notes.
"""
import asyncio
import os
import re

import httpx
from google import genai
from google.genai import types

_SS_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"
_SS_FIELDS = "title,authors,year,abstract,venue,openAccessPdf,externalIds,url"
_HEADERS = {"User-Agent": "PaperAssistant/1.0"}
_TIMEOUT = 10.0

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def _best_url(paper: dict) -> str | None:
    oa = paper.get("openAccessPdf") or {}
    if oa.get("url"):
        return oa["url"]
    ext = paper.get("externalIds") or {}
    if ext.get("ArXiv"):
        return f"https://arxiv.org/pdf/{ext['ArXiv']}.pdf"
    if ext.get("DOI"):
        return f"https://doi.org/{ext['DOI']}"
    pid = paper.get("paperId")
    if pid:
        return f"https://www.semanticscholar.org/paper/{pid}"
    return paper.get("url")


async def _ss_search(query: str, limit: int = 8) -> list[dict]:
    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=_TIMEOUT) as client:
            r = await client.get(_SS_SEARCH, params={"query": query, "fields": _SS_FIELDS, "limit": limit})
            r.raise_for_status()
            return r.json().get("data") or []
    except Exception:
        return []


async def _gemini_relevance(query: str, papers: list[dict]) -> list[str]:
    """Return a one-sentence relevance note for each paper (parallel-safe)."""
    if not papers:
        return []

    listing = "\n".join(
        f"{i+1}. {p.get('title','')} ({p.get('year','')}) — {(p.get('abstract') or '')[:200]}"
        for i, p in enumerate(papers)
    )
    prompt = (
        f"A researcher asked: \"{query}\"\n\n"
        f"For each paper below, write ONE short sentence (max 20 words) explaining "
        f"why it is or isn't relevant to the question. "
        f"Return ONLY a JSON array of strings, one per paper, in the same order.\n\n"
        f"{listing}"
    )
    try:
        client = _get_client()
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1),
        )
        text = (response.text or "").strip()
        # Extract JSON array
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if m:
            import json
            notes = json.loads(m.group(0))
            if isinstance(notes, list):
                return [str(n) for n in notes]
    except Exception:
        pass
    return ["" for _ in papers]


def _format_authors(paper: dict) -> str:
    authors = paper.get("authors") or []
    names = [a.get("name", "") for a in authors]
    if len(names) > 3:
        return f"{names[0]} et al."
    return ", ".join(names)


async def search_papers(query: str) -> list[dict]:
    """Search Semantic Scholar for papers matching *query*, enriched with Gemini notes."""
    raw = await _ss_search(query)
    if not raw:
        return []

    notes = await _gemini_relevance(query, raw)

    results = []
    for i, paper in enumerate(raw):
        results.append({
            "title":      paper.get("title") or "",
            "authors":    _format_authors(paper),
            "year":       paper.get("year"),
            "venue":      paper.get("venue") or "",
            "abstract":   (paper.get("abstract") or "")[:400],
            "url":        _best_url(paper),
            "relevance":  notes[i] if i < len(notes) else "",
            "semantic_scholar_id": paper.get("paperId"),
        })

    return results
