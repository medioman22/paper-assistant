from fastapi import APIRouter, HTTPException
from ..services import session_store, literature_graph, recommendations_service

router = APIRouter(prefix="/literature", tags=["literature"])


@router.get("/graph")
async def get_graph():
    return literature_graph.get_graph()


@router.get("/recommendations/{session_id}")
async def get_cached_recommendations(session_id: str):
    s = session_store.get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"recommendations": literature_graph.get_recommendations_for(session_id), "cached": True}


@router.post("/recommendations/{session_id}")
async def generate_recommendations(session_id: str):
    s = session_store.get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")

    literature_graph.upsert_local_paper(
        session_id=session_id,
        title=s["title"],
        abstract=s.get("abstract", ""),
        takeaway=s.get("findings", ""),
    )

    try:
        recs = await recommendations_service.get_recommendations(
            title=s["title"],
            abstract=s["abstract"],
            key_points=s.get("key_points", []),
            methodology=s.get("methodology", ""),
            findings=s.get("findings", ""),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Recommendation failed: {exc}") from exc

    result = []
    for r in recs:
        node_id = literature_graph.upsert_external_paper(
            title=r.get("title", ""),
            authors=r.get("authors", ""),
            year=str(r.get("year", "")),
            venue=r.get("venue", ""),
            takeaway=r.get("takeaway", ""),
            url=r.get("url", ""),
        )
        literature_graph.add_edge(session_id, node_id, r.get("relationship", "related"))
        result.append({**r, "node_id": node_id})

    return {"recommendations": result, "cached": False}
