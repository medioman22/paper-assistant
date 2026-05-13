"""Tests for app.services.paper_resolver.

Unit tests mock httpx to avoid real network calls.
Integration tests (marked @pytest.mark.integration) hit the live
Semantic Scholar API and are skipped in CI unless explicitly selected.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio  # noqa: F401 — ensures the plugin is loaded

from app.services.paper_resolver import resolve_paper, resolve_papers

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(data: list[dict], status_code: int = 200) -> MagicMock:
    """Build a fake httpx.Response-like object."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {"data": data}
    if status_code >= 400:
        from httpx import HTTPStatusError, Request, Response
        mock_resp.raise_for_status.side_effect = HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(spec=Request),
            response=MagicMock(spec=Response),
        )
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


# Canned Semantic Scholar paper dicts
_ATTENTION_SS = {
    "paperId": "204e3073870fae3d05bcbc2f6a8e263d9b72e776",
    "title": "Attention Is All You Need",
    "authors": [{"name": "Ashish Vaswani"}, {"name": "Noam Shazeer"}],
    "year": 2017,
    "venue": "Neural Information Processing Systems",
    "externalIds": {"ArXiv": "1706.03762", "DOI": "10.48550/arXiv.1706.03762"},
    "openAccessPdf": {"url": "https://arxiv.org/pdf/1706.03762.pdf"},
    "url": "https://www.semanticscholar.org/paper/204e3073870fae3d05bcbc2f6a8e263d9b72e776",
    "abstract": "The dominant sequence transduction models ...",
}

_ALEXNET_SS = {
    "paperId": "abd1c342495432171beb7ca8fd9551ef13cbd0ff",
    "title": "ImageNet Classification with Deep Convolutional Neural Networks",
    "authors": [{"name": "Alex Krizhevsky"}, {"name": "Ilya Sutskever"}, {"name": "Geoffrey E. Hinton"}],
    "year": 2012,
    "venue": "Neural Information Processing Systems",
    "externalIds": {"DOI": "10.1145/3065386"},
    "openAccessPdf": None,
    "url": "https://www.semanticscholar.org/paper/abd1c342495432171beb7ca8fd9551ef13cbd0ff",
    "abstract": "We trained a large, deep convolutional neural network ...",
}


# ---------------------------------------------------------------------------
# Unit tests (mocked)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_exact_title_match_found():
    """Exact title match returns found=True with correct metadata."""
    mock_resp = _make_response([_ATTENTION_SS])

    with patch("httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.get = AsyncMock(return_value=mock_resp)

        result = await resolve_paper("Attention Is All You Need", year=2017)

    assert result["found"] is True
    assert result["title"] == "Attention Is All You Need"
    assert result["year"] == 2017
    assert result["semantic_scholar_id"] == "204e3073870fae3d05bcbc2f6a8e263d9b72e776"
    # openAccessPdf is present, so pdf_url should use it
    assert result["pdf_url"] == "https://arxiv.org/pdf/1706.03762.pdf"
    assert "Vaswani" in result["authors"]


@pytest.mark.asyncio
async def test_year_within_tolerance_still_matches():
    """A candidate whose year is within ±2 of the hint is still returned."""
    # Shift the year by 1 to simulate a near-match
    shifted = dict(_ATTENTION_SS, year=2016)
    mock_resp = _make_response([shifted])

    with patch("httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.get = AsyncMock(return_value=mock_resp)

        result = await resolve_paper("Attention Is All You Need", year=2017)

    assert result["found"] is True
    assert result["year"] == 2016


@pytest.mark.asyncio
async def test_year_mismatch_outside_tolerance_falls_back():
    """A large year discrepancy lowers score; only a poor title sim makes it fail."""
    # Craft a candidate with same title but a year far outside tolerance
    far_year = dict(_ATTENTION_SS, year=2000)
    mock_resp = _make_response([far_year])

    with patch("httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.get = AsyncMock(return_value=mock_resp)

        # Title similarity is still high (1.0), so it is returned even without
        # the year bonus — the result is found but year reflects SS data.
        result = await resolve_paper("Attention Is All You Need", year=2017)

    # Title sim alone is enough to pass the 0.40 threshold
    assert result["found"] is True
    assert result["year"] == 2000


@pytest.mark.asyncio
async def test_no_results_returns_found_false():
    """Empty data array returns found=False."""
    mock_resp = _make_response([])

    with patch("httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.get = AsyncMock(return_value=mock_resp)

        result = await resolve_paper("A paper that does not exist at all", year=2020)

    assert result["found"] is False
    assert result["title"] == "A paper that does not exist at all"
    assert result["url"] is None
    assert result["pdf_url"] is None


@pytest.mark.asyncio
async def test_api_error_returns_found_false():
    """Network/HTTP error returns found=False gracefully."""
    import httpx as _httpx

    with patch("httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.get = AsyncMock(side_effect=_httpx.ConnectError("timeout"))

        result = await resolve_paper("Attention Is All You Need", year=2017)

    assert result["found"] is False
    assert result["semantic_scholar_id"] is None


@pytest.mark.asyncio
async def test_poor_title_similarity_returns_found_false():
    """If the best candidate title is totally different, return found=False."""
    unrelated = dict(_ATTENTION_SS, title="Quantum Computing in Biochemistry")
    mock_resp = _make_response([unrelated])

    with patch("httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.get = AsyncMock(return_value=mock_resp)

        result = await resolve_paper("Attention Is All You Need", year=2017)

    assert result["found"] is False


@pytest.mark.asyncio
async def test_pdf_url_fallback_arxiv():
    """When openAccessPdf is absent, ArXiv ID is used for pdf_url."""
    no_oa = dict(_ATTENTION_SS, openAccessPdf=None)
    mock_resp = _make_response([no_oa])

    with patch("httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.get = AsyncMock(return_value=mock_resp)

        result = await resolve_paper("Attention Is All You Need", year=2017)

    assert result["found"] is True
    assert result["pdf_url"] == "https://arxiv.org/pdf/1706.03762.pdf"


@pytest.mark.asyncio
async def test_pdf_url_fallback_doi():
    """When neither openAccessPdf nor ArXiv present, DOI is used."""
    no_oa_no_arxiv = dict(
        _ALEXNET_SS,
        openAccessPdf=None,
        externalIds={"DOI": "10.1145/3065386"},
    )
    mock_resp = _make_response([no_oa_no_arxiv])

    with patch("httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.get = AsyncMock(return_value=mock_resp)

        result = await resolve_paper(
            "ImageNet Classification with Deep Convolutional Neural Networks",
            year=2012,
        )

    assert result["found"] is True
    assert result["pdf_url"] == "https://doi.org/10.1145/3065386"


@pytest.mark.asyncio
async def test_pdf_url_fallback_semanticscholar():
    """When no PDF source is available, fallback to Semantic Scholar page URL."""
    bare = dict(
        _ALEXNET_SS,
        openAccessPdf=None,
        externalIds={},
    )
    mock_resp = _make_response([bare])

    with patch("httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.get = AsyncMock(return_value=mock_resp)

        result = await resolve_paper(
            "ImageNet Classification with Deep Convolutional Neural Networks",
            year=2012,
        )

    assert result["found"] is True
    assert result["pdf_url"].startswith("https://www.semanticscholar.org/paper/")


@pytest.mark.asyncio
async def test_resolve_papers_concurrency():
    """resolve_papers resolves a list and returns one result per input."""
    mock_resp_attention = _make_response([_ATTENTION_SS])
    mock_resp_alexnet = _make_response([_ALEXNET_SS])

    call_count = 0

    async def fake_get(url, params=None, **kwargs):
        nonlocal call_count
        q = (params or {}).get("query", "")
        call_count += 1
        if "Attention" in q:
            return mock_resp_attention
        return mock_resp_alexnet

    with patch("httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.get = fake_get

        results = await resolve_papers([
            {"title": "Attention Is All You Need", "year": 2017},
            {"title": "ImageNet Classification with Deep Convolutional Neural Networks", "year": 2012},
        ])

    assert len(results) == 2
    assert results[0]["found"] is True
    assert results[1]["found"] is True


# ---------------------------------------------------------------------------
# Integration tests — hit the real Semantic Scholar API
# ---------------------------------------------------------------------------

async def _resolve_with_test_retry(title: str, year: int, max_attempts: int = 5) -> dict:
    """Retry resolve_paper at the test level to handle transient 429 errors.

    Each attempt waits progressively longer before trying again.
    This is separate from the library-level retry so the library's back-off
    remains lightweight for production use.
    """
    import asyncio
    wait = 15
    for attempt in range(max_attempts):
        result = await resolve_paper(title, year=year)
        if result["found"]:
            return result
        # If not found but no error (genuine no-match), bail early
        # We detect rate-limiting by checking whether the SS id is absent despite
        # the title being well-known — just retry up to max_attempts.
        if attempt < max_attempts - 1:
            await asyncio.sleep(wait)
            wait = min(wait * 2, 60)  # cap at 60s per wait
    return result


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_attention_is_all_you_need():
    """Live API: 'Attention Is All You Need' (2017) resolves correctly.

    The unauthenticated Semantic Scholar API is rate-limited (~1 req/s from
    a given IP).  _resolve_with_test_retry() retries up to 5 times with
    back-off, so this test tolerates transient 429s.
    """
    result = await _resolve_with_test_retry("Attention Is All You Need", year=2017)
    if not result["found"]:
        pytest.skip("Semantic Scholar API unavailable (rate limit / network) — skipping integration check")
    assert "attention" in result["title"].lower() or "transformer" in result["title"].lower()
    assert result["year"] in range(2015, 2020)
    assert result["semantic_scholar_id"] is not None
    assert result["pdf_url"] is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_alexnet():
    """Live API: AlexNet paper (2012) resolves correctly.

    See note on rate limiting in test_integration_attention_is_all_you_need.
    """
    result = await _resolve_with_test_retry(
        "ImageNet Classification with Deep Convolutional Neural Networks",
        year=2012,
    )
    if not result["found"]:
        pytest.skip("Semantic Scholar API unavailable (rate limit / network) — skipping integration check")
    assert "imagenet" in result["title"].lower() or "convolutional" in result["title"].lower()
    assert result["year"] in range(2010, 2015)
    assert result["semantic_scholar_id"] is not None
    assert result["pdf_url"] is not None
