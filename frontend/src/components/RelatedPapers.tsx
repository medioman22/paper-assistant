import { useState, useEffect } from "react";
import { PaperRecommendation, RelationshipType } from "../types";
import { fetchRecommendations, generateRecommendations } from "../hooks/useApi";

const REL_LABELS: Record<RelationshipType, string> = {
  cited: "Cited",
  foundational: "Foundational",
  parallel: "Parallel",
  subsequent: "Subsequent",
  related: "Related",
};

interface Props {
  sessionId: string;
  onOpenSession?: (sessionId: string) => void;
}

export function RelatedPapers({ sessionId, onOpenSession }: Props) {
  const [recs, setRecs] = useState<PaperRecommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    fetchRecommendations(sessionId)
      .then((r) => { if (r.recommendations.length > 0) setRecs(r.recommendations); })
      .catch(() => {})
      .finally(() => setChecked(true));
  }, [sessionId]);

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    try {
      const r = await generateRecommendations(sessionId);
      setRecs(r.recommendations);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="related-papers">
      <div className="related-header">
        <h3>Related Papers</h3>
        <button className="btn-ghost small" onClick={handleGenerate} disabled={loading}>
          {loading ? "Finding…" : recs.length > 0 ? "↺ Refresh" : "Find related papers"}
        </button>
      </div>

      {error && <p className="related-error">{error}</p>}

      {checked && recs.length === 0 && !loading && (
        <p className="related-empty">Click "Find related papers" to discover foundational and related work.</p>
      )}

      <div className="related-list">
        {recs.map((r, i) => (
          <div key={i} className="related-card">
            <div className="related-card-top">
              <span className={`rel-badge rel-${r.relationship}`}>{REL_LABELS[r.relationship] ?? r.relationship}</span>
              <span className="related-year">{r.year}{r.venue ? ` · ${r.venue}` : ""}</span>
            </div>
            <p className="related-title">
              {r.url
                ? <a href={r.url} target="_blank" rel="noreferrer">{r.title}</a>
                : r.title}
            </p>
            <p className="related-authors">{r.authors}</p>
            <p className="related-takeaway">{r.takeaway}</p>
            {r.session_id && onOpenSession && (
              <button className="btn-ghost small" onClick={() => onOpenSession(r.session_id!)}>
                Open session →
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
