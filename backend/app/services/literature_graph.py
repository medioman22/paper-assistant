"""
Persistent literature graph.
Nodes = papers (local sessions or external references).
Edges = directional relationships between papers.
"""
import json
import hashlib
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"
_GRAPH_FILE = _DATA_DIR / "literature_graph.json"
_DATA_DIR.mkdir(exist_ok=True)

# {node_id: {id, title, authors, year, venue, abstract, takeaway, url, session_id|None}}
_nodes: dict[str, dict] = {}
# [{id, source, target, relationship}]
_edges: list[dict] = []


def _load() -> None:
    if _GRAPH_FILE.exists():
        data = json.loads(_GRAPH_FILE.read_text())
        for n in data.get("nodes", []):
            _nodes[n["id"]] = n
        _edges.extend(data.get("edges", []))


def _save() -> None:
    _GRAPH_FILE.write_text(json.dumps({"nodes": list(_nodes.values()), "edges": _edges}, indent=2))


_load()


def _paper_id(title: str, authors: str = "", year: str = "") -> str:
    key = f"{title.lower().strip()}{authors.lower()}{year}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def _two_sentences(text: str) -> str:
    """Return at most the first two sentences of text."""
    if not text:
        return ""
    parts = []
    for sep in (".", "!", "?"):
        text = text.replace(sep + " ", sep + "\n")
    sentences = [s.strip().rstrip("\n") for s in text.replace("\n", " ").split("\n") if s.strip()]
    for s in sentences[:2]:
        parts.append(s if s.endswith((".", "!", "?")) else s + ".")
    return " ".join(parts)


def upsert_local_paper(session_id: str, title: str, abstract: str = "", takeaway: str = "") -> str:
    """Add or refresh a local (uploaded) paper node. Returns node_id."""
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
    """Add or refresh an external (recommended) paper node. Returns node_id."""
    node_id = _paper_id(title, authors, str(year))
    # Prefer an existing local session with the same title
    for n in _nodes.values():
        if n.get("session_id") and n.get("title", "").lower().strip() == title.lower().strip():
            return n["id"]
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
    for e in _edges:
        if e["source"] == source and e["target"] == target:
            e["relationship"] = relationship
            _save()
            return
    _edges.append({"id": f"{source}->{target}", "source": source, "target": target, "relationship": relationship})
    _save()


def get_recommendations_for(session_id: str) -> list[dict]:
    """Return external nodes linked from this session, with their relationship included."""
    result = []
    for e in _edges:
        if e["source"] == session_id and e["target"] in _nodes:
            node = dict(_nodes[e["target"]])
            node["relationship"] = e["relationship"]
            result.append(node)
    return result


def get_graph() -> dict:
    return {"nodes": list(_nodes.values()), "edges": list(_edges)}
