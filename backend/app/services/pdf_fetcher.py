"""
Fetch a PDF from a paper URL.

Strategy (in order):
1. arXiv abs URL  → rewrite to /pdf/ download URL
2. Direct PDF URL (ends with .pdf or content-type is application/pdf)
3. DOI URL        → query Unpaywall for an open-access PDF link
4. Semantic Scholar URL → extract DOI/arXiv ID and retry
"""
import re
import httpx

HEADERS = {"User-Agent": "PaperAssistant/1.0 (research tool; contact: paper-assistant)"}
TIMEOUT = 30.0


def _arxiv_pdf_url(url: str) -> str | None:
    """Return the PDF download URL for an arXiv abstract URL, or None."""
    m = re.search(r"arxiv\.org/abs/([^\s?#]+)", url)
    if m:
        return f"https://arxiv.org/pdf/{m.group(1)}.pdf"
    m = re.search(r"arxiv\.org/pdf/([^\s?#]+)", url)
    if m:
        return url  # already a PDF URL
    return None


def _doi_from_url(url: str) -> str | None:
    m = re.search(r"doi\.org/(.+)", url)
    return m.group(1) if m else None


async def _download(pdf_url: str) -> bytes:
    async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
        r = await client.get(pdf_url)
        r.raise_for_status()
        ct = r.headers.get("content-type", "")
        if "pdf" not in ct and not pdf_url.endswith(".pdf"):
            raise ValueError(f"URL did not return a PDF (content-type: {ct})")
        return r.content


async def _unpaywall_pdf_url(doi: str) -> str | None:
    email = "paper-assistant@example.com"
    api_url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
            r = await client.get(api_url)
            if r.status_code != 200:
                return None
            data = r.json()
            loc = data.get("best_oa_location") or {}
            return loc.get("url_for_pdf") or loc.get("url")
    except Exception:
        return None


async def fetch_pdf(url: str) -> bytes:
    """Download and return PDF bytes from a paper URL.

    Raises ValueError if no PDF could be retrieved.
    """
    errors: list[str] = []

    # 1. arXiv
    arxiv_url = _arxiv_pdf_url(url)
    if arxiv_url:
        try:
            return await _download(arxiv_url)
        except Exception as e:
            errors.append(f"arXiv: {e}")

    # 2. Direct download (works for many open-access publishers)
    try:
        return await _download(url)
    except Exception as e:
        errors.append(f"direct: {e}")

    # 3. DOI → Unpaywall
    doi = _doi_from_url(url)
    if doi:
        oa_url = await _unpaywall_pdf_url(doi)
        if oa_url:
            try:
                return await _download(oa_url)
            except Exception as e:
                errors.append(f"unpaywall ({oa_url}): {e}")
        else:
            errors.append("unpaywall: no open-access PDF found")

    raise ValueError(f"Could not retrieve PDF from {url}. Attempts: {'; '.join(errors)}")
