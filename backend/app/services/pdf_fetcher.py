"""
Fetch a PDF from a paper URL.

Strategy (in order):
1. arXiv abs URL          → rewrite to /pdf/ download URL
2. Direct PDF URL         → download if content-type is application/pdf
3. DOI URL                → follow redirect, apply publisher patterns,
                            then Unpaywall, then HTML scrape
4. Gemini web search      → ask Gemini (with Google Search) for the PDF URL
                            given the paper title / DOI (last resort)
"""
import os
import re
import httpx
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

HEADERS = {"User-Agent": "PaperAssistant/1.0 (research tool; contact: paper-assistant@gmail.com)"}
TIMEOUT = 30.0
_CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "paper-assistant@gmail.com")

_genai_client: genai.Client | None = None


def _get_genai_client() -> genai.Client:
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _genai_client


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def _arxiv_pdf_url(url: str) -> str | None:
    m = re.search(r"arxiv\.org/abs/([^\s?#]+)", url)
    if m:
        return f"https://arxiv.org/pdf/{m.group(1)}.pdf"
    if re.search(r"arxiv\.org/pdf/", url):
        return url
    return None


def _doi_from_url(url: str) -> str | None:
    m = re.search(r"doi\.org/(.+)", url)
    return m.group(1).rstrip("/") if m else None


# ---------------------------------------------------------------------------
# Downloaders
# ---------------------------------------------------------------------------

async def _download(pdf_url: str) -> bytes:
    async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
        r = await client.get(pdf_url)
        r.raise_for_status()
        ct = r.headers.get("content-type", "")
        if "pdf" in ct or pdf_url.lower().endswith(".pdf"):
            return r.content
        raise ValueError(f"URL did not return a PDF (content-type: {ct})")


# ---------------------------------------------------------------------------
# Publisher-specific URL patterns
# ---------------------------------------------------------------------------

def _publisher_pdf_urls(publisher_url: str, doi: str) -> list[str]:
    candidates: list[str] = []
    u = publisher_url.lower()

    if "pnas.org" in u:
        candidates += [
            f"https://www.pnas.org/doi/pdfdirect/{doi}",
            f"https://www.pnas.org/doi/pdf/{doi}",
        ]
    elif "nature.com" in u:
        article_id = publisher_url.rstrip("/").split("/")[-1]
        candidates += [
            f"https://www.nature.com/articles/{article_id}.pdf",
            f"https://www.nature.com/articles/{article_id}/pdf",
        ]
    elif "science.org" in u or "sciencemag.org" in u:
        candidates.append(publisher_url.replace("/doi/", "/doi/pdf/"))
    elif "biorxiv.org" in u or "medrxiv.org" in u:
        candidates.append(publisher_url.rstrip("/") + ".full.pdf")
    elif "frontiersin.org" in u:
        candidates.append(publisher_url.rstrip("/") + "/pdf")
    elif "mdpi.com" in u:
        candidates.append(publisher_url.replace("/htm", "/pdf").replace("/html", "/pdf"))
    elif "ieeexplore.ieee.org" in u:
        m = re.search(r"/document/(\d+)", publisher_url)
        if m:
            candidates.append(f"https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber={m.group(1)}")
    elif "dl.acm.org" in u:
        candidates.append(publisher_url.replace("/doi/", "/doi/pdf/"))
    elif "cell.com" in u:
        candidates.append(publisher_url.rstrip("/") + "/pdf")
    elif "springer.com" in u or "link.springer.com" in u:
        candidates.append(re.sub(r"/article/", "/content/pdf/", publisher_url) + ".pdf")

    return candidates


async def _follow_doi(doi: str) -> tuple[str | None, list[str]]:
    """Follow DOI redirect; return (publisher_url, pdf_candidate_list)."""
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=15.0, follow_redirects=True) as client:
            r = await client.head(f"https://doi.org/{doi}")
            publisher_url = str(r.url)
        return publisher_url, _publisher_pdf_urls(publisher_url, doi)
    except Exception:
        return None, []


async def _unpaywall_pdf_url(doi: str) -> str | None:
    api_url = f"https://api.unpaywall.org/v2/{doi}?email={_CONTACT_EMAIL}"
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


async def _scrape_pdf_from_html(page_url: str) -> str | None:
    """Try to extract a PDF or arXiv link from an HTML landing page."""
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=15.0, follow_redirects=True) as client:
            r = await client.get(page_url)
            if "html" not in r.headers.get("content-type", ""):
                return None
            soup = BeautifulSoup(r.text, "html.parser")

        base_origin = re.match(r"(https?://[^/]+)", page_url)
        origin = base_origin.group(1) if base_origin else ""

        for tag in soup.find_all("a", href=True):
            href: str = tag["href"]
            lower = href.lower()
            if ".pdf" in lower or "/pdf" in lower or "download" in lower:
                if href.startswith("http"):
                    return href
                if href.startswith("/") and origin:
                    return origin + href

        # arXiv ID anywhere on page
        m = re.search(r"arxiv\.org/(abs|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?)", r.text)
        if m:
            return f"https://arxiv.org/pdf/{m.group(2)}.pdf"

        return None
    except Exception:
        return None


async def _gemini_pdf_url(title: str | None, doi: str | None) -> str | None:
    """Ask Gemini (with Google Search) to find the PDF URL for a paper."""
    if not title and not doi:
        return None

    query_parts = []
    if title:
        query_parts.append(f'"{title}"')
    if doi:
        query_parts.append(f"DOI:{doi}")
    query_parts.append("PDF OR arXiv OR open access")

    prompt = (
        "Find the direct PDF download URL or arXiv URL for this academic paper:\n"
        + " ".join(query_parts)
        + "\n\nReturn ONLY the URL, nothing else. "
        "Prefer: arXiv PDF, institutional repository PDF, or open-access publisher PDF. "
        "Return null if you cannot find a verified open-access PDF."
    )
    try:
        client = _get_genai_client()
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        text = (response.text or "").strip()
        # Extract first URL-like string
        m = re.search(r"https?://\S+", text)
        if m:
            url = m.group(0).rstrip(".,;)")
            return url
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def fetch_pdf(url: str, title: str | None = None) -> bytes:
    """Download and return PDF bytes from a paper URL.

    Parameters
    ----------
    url:   Paper URL (DOI, arXiv, direct PDF, or any publisher link).
    title: Optional paper title used as a hint for Gemini web search fallback.

    Raises ValueError if no PDF could be retrieved.
    """
    errors: list[str] = []
    doi = _doi_from_url(url)
    publisher_url: str | None = None
    pdf_candidates: list[str] = []

    # 1. arXiv rewrite
    arxiv_url = _arxiv_pdf_url(url)
    if arxiv_url:
        try:
            return await _download(arxiv_url)
        except Exception as e:
            errors.append(f"arXiv: {e}")

    # 2. Direct download
    try:
        return await _download(url)
    except Exception as e:
        errors.append(f"direct: {e}")

    # 3. Publisher-specific patterns (DOI redirect)
    if doi:
        publisher_url, pdf_candidates = await _follow_doi(doi)
        for candidate in pdf_candidates:
            try:
                return await _download(candidate)
            except Exception as e:
                errors.append(f"publisher ({candidate}): {e}")

    # 4. Unpaywall
    if doi:
        oa_url = await _unpaywall_pdf_url(doi)
        if oa_url and oa_url not in (url, *pdf_candidates):
            try:
                return await _download(oa_url)
            except Exception as e:
                errors.append(f"unpaywall ({oa_url}): {e}")
        else:
            errors.append("unpaywall: no open-access PDF found")

    # 5. Scrape HTML landing page
    scrape_target = publisher_url or url
    scraped_url = await _scrape_pdf_from_html(scrape_target)
    if scraped_url and scraped_url not in (url, *pdf_candidates):
        try:
            return await _download(scraped_url)
        except Exception as e:
            errors.append(f"scrape ({scraped_url}): {e}")

    # 6. Gemini web search (last resort)
    gemini_url = await _gemini_pdf_url(title, doi)
    if gemini_url and gemini_url not in (url, *pdf_candidates):
        try:
            return await _download(gemini_url)
        except Exception as e:
            errors.append(f"gemini ({gemini_url}): {e}")

    raise ValueError(f"Could not retrieve PDF from {url}. Attempts: {'; '.join(errors)}")
