"""
Persistent literature graph.
Nodes = papers (local sessions or external references).
Edges = directional relationships between papers.
"""
import json
import hashlib
import re
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"
_GRAPH_FILE = _DATA_DIR / "literature_graph.json"
_DATA_DIR.mkdir(exist_ok=True)

_nodes: dict[str, dict] = {}
_edges: list[dict] = []

_VALID_RELS = {"cited", "foundational", "parallel", "subsequent", "related"}

_REL_KEYWORDS = {
    "cited":       ["cited", "citation", "directly"],
    "foundational":["foundational", "seminal", "foundation", "basis", "classic"],
    "parallel":    ["parallel", "contemporary", "simultaneous", "concurrent"],
    "subsequent":  ["subsequent", "building", "follow", "follow-up", "extension"],
}


def _normalize_rel(raw: str) -> str:
    """Map arbitrary Gemini relationship strings to one of the 5 canonical values."""
    s = raw.lower().strip()
    if s in _VALID_RELS:
        return s
    for rel, keywords in _REL_KEYWORDS.items():
        if any(k in s for k in keywords):
            return rel
    return "related"


def _load() -> None:
    if _GRAPH_FILE.exists():
        data = json.loads(_GRAPH_FILE.read_text())
        for n in data.get("nodes", []):
            _nodes[n["id"]] = n
        for e in data.get("edges", []):
            e["relationship"] = _normalize_rel(e.get("relationship", "related"))
            _edges.append(e)


def _save() -> None:
    _GRAPH_FILE.write_text(json.dumps({"nodes": list(_nodes.values()), "edges": _edges}, indent=2))


_load()


def _paper_id(title: str, authors: str = "", year: str = "") -> str:
    key = f"{title.lower().strip()}{authors.lower()}{year}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def _title_matches(a: str, b: str) -> bool:
    def norm(s: str) -> str:
        return re.sub(r"\W+", " ", s.lower()).strip()
    return norm(a) == norm(b)


def _two_sentences(text: str) -> str:
    if not text:
        return ""
    sentences: list[str] = []
    for chunk in re.split(r"(?<=[.!?])\s+", text.strip()):
        chunk = chunk.strip()
        if chunk:
            sentences.append(chunk if chunk[-1] in ".!?" else chunk + ".")
        if len(sentences) == 2:
            break
    return " ".join(sentences)


def _repoint_edges(old_id: str, new_id: str) -> None:
    for e in _edges:
        if e["source"] == old_id:
            e["source"] = new_id
        if e["target"] == old_id:
            e["target"] = new_id
        e["id"] = f"{e['source']}->{e['target']}"


def upsert_local_paper(session_id: str, title: str, abstract: str = "", takeaway: str = "") -> str:
    """Add or refresh a local (uploaded) paper node, merging any matching external node."""
    # Merge any existing external node with matching title
    for old_id, n in list(_nodes.items()):
        if old_id != session_id and not n.get("session_id") and _title_matches(n.get("title", ""), title):
            _repoint_edges(old_id, session_id)
            del _nodes[old_id]
            break

    existing = _nodes.get(session_id, {})
    _nodes[session_id] = {
        **existing,
        "id": session_id,
        "title": title,
        "abstract": _two_sentences(abstract),
        "takeaway": takeaway,
        "session_id": session_id,
    }
    _save()
    return session_id


def upsert_external_paper(title: str, authors: str, year: str, venue: str,
                           takeaway: str, url: str) -> str:
    """Add or refresh an external (recommended) paper node, deduplicating by title."""
    # Check ALL existing nodes (local and external) for title match
    for n in _nodes.values():
        if _title_matches(n.get("title", ""), title):
            # Update URL and takeaway if we have better data
            if url and not n.get("url"):
                n["url"] = url
            if takeaway and not n.get("takeaway"):
                n["takeaway"] = takeaway
            _save()
            return n["id"]

    node_id = _paper_id(title, authors, str(year))
    existing = _nodes.get(node_id, {})
    _nodes[node_id] = {
        **existing,
        "id": node_id,
        "title": title,
        "authors": authors,
        "year": str(year),
        "venue": venue,
        "abstract": existing.get("abstract", ""),
        "takeaway": takeaway,
        "url": url,
        "session_id": existing.get("session_id"),
    }
    _save()
    return node_id


def add_edge(source: str, target: str, relationship: str) -> None:
    rel = _normalize_rel(relationship)
    for e in _edges:
        if e["source"] == source and e["target"] == target:
            e["relationship"] = rel
            _save()
            return
    # Skip self-loops
    if source == target:
        return
    _edges.append({"id": f"{source}->{target}", "source": source, "target": target, "relationship": rel})
    _save()


def get_recommendations_for(session_id: str) -> list[dict]:
    result = []
    for e in _edges:
        if e["source"] == session_id and e["target"] in _nodes:
            node = dict(_nodes[e["target"]])
            node["relationship"] = e["relationship"]
            result.append(node)
    return result


def get_graph() -> dict:
    return {"nodes": list(_nodes.values()), "edges": list(_edges)}
