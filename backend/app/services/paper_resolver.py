"""Resolve paper metadata via the Semantic Scholar Search API.

Given a title (+ optional authors / year hint from Gemini), this module
queries Semantic Scholar, picks the best-matching result, and returns a
normalised dict with verified URLs.

URL priority
------------
1. openAccessPdf.url  (direct PDF)
2. https://arxiv.org/pdf/{ArXiv}.pdf
3. https://doi.org/{DOI}
4. https://www.semanticscholar.org/paper/{paperId}
"""

from __future__ import annotations

import asyncio
import logging
from difflib import SequenceMatcher
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_SS_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS = "title,authors,year,venue,externalIds,openAccessPdf,url,abstract"
_YEAR_TOLERANCE = 2
_REQUEST_TIMEOUT = 10.0  # seconds


def _title_similarity(a: str, b: str) -> float:
    """Case-insensitive ratio between two title strings."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _best_url(paper: dict[str, Any]) -> str:
    """Return the most useful URL for *paper* using the priority rules."""
    oa = paper.get("openAccessPdf") or {}
    if oa.get("url"):
        return oa["url"]

    ext = paper.get("externalIds") or {}
    arxiv = ext.get("ArXiv")
    if arxiv:
        return f"https://arxiv.org/pdf/{arxiv}.pdf"

    doi = ext.get("DOI")
    if doi:
        return f"https://doi.org/{doi}"

    return f"https://www.semanticscholar.org/paper/{paper['paperId']}"


def _pick_best(candidates: list[dict], title: str, year: int | None) -> dict | None:
    """Return the best-matching candidate or *None* if nothing is good enough."""
    if not candidates:
        return None

    scored: list[tuple[float, dict]] = []
    for c in candidates:
        sim = _title_similarity(title, c.get("title") or "")
        # Year bonus: exact match +0.10, within tolerance +0.05
        y = c.get("year")
        if year is not None and y is not None:
            diff = abs(int(y) - int(year))
            if diff == 0:
                sim += 0.10
            elif diff <= _YEAR_TOLERANCE:
                sim += 0.05
        scored.append((sim, c))

    scored.sort(key=lambda t: t[0], reverse=True)
    best_score, best = scored[0]

    # Require at least a decent title similarity
    if best_score < 0.40:
        return None
    return best


async def resolve_paper(
    title: str,
    authors: str = "",
    year: int | None = None,
) -> dict:
    """Query Semantic Scholar and return verified paper metadata.

    Parameters
    ----------
    title:   Paper title as suggested by Gemini.
    authors: Author string (hint only, not used for filtering).
    year:    Publication year hint; used to break ties (±2 tolerance).

    Returns
    -------
    dict with keys:
        title, authors, year, venue, url, pdf_url,
        semantic_scholar_id, found (bool)
    """
    _empty = {
        "title": title,
        "authors": authors,
        "year": year,
        "venue": None,
        "url": None,
        "pdf_url": None,
        "semantic_scholar_id": None,
        "found": False,
    }

    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            params = {"query": title, "fields": _FIELDS, "limit": 3}
            resp = await client.get(_SS_SEARCH, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("Semantic Scholar request failed for %r: %s", title, exc)
        return _empty

    candidates = data.get("data") or []
    best = _pick_best(candidates, title, year)

    if best is None:
        logger.info("No good Semantic Scholar match for %r (year=%s)", title, year)
        return _empty

    # Build author string from structured data if richer than the hint
    ss_authors = ", ".join(
        a.get("name", "") for a in (best.get("authors") or [])
    )
    resolved_authors = ss_authors if ss_authors else authors

    pdf_url = _best_url(best)
    # The `url` field from SS points to the paper page
    ss_page_url = best.get("url") or f"https://www.semanticscholar.org/paper/{best['paperId']}"

    return {
        "title": best.get("title") or title,
        "authors": resolved_authors,
        "year": best.get("year") or year,
        "venue": best.get("venue") or None,
        "url": ss_page_url,
        "pdf_url": pdf_url,
        "semantic_scholar_id": best.get("paperId"),
        "found": True,
    }


async def resolve_papers(papers: list[dict]) -> list[dict]:
    """Concurrently resolve a list of Gemini-suggested paper dicts.

    Each input dict must have at least a ``title`` key; ``authors`` and
    ``year`` are used as hints when present.
    """
    tasks = [
        resolve_paper(
            title=p.get("title", ""),
            authors=p.get("authors", ""),
            year=p.get("year"),
        )
        for p in papers
    ]
    return list(await asyncio.gather(*tasks))
