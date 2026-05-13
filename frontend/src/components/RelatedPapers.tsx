import { useState, useEffect } from "react";
import { PaperRecommendation, RelationshipType, UploadResponse } from "../types";
import { fetchRecommendations, generateRecommendations, fetchAndAnalyzePaper } from "../hooks/useApi";

const REL_LABELS: Record<RelationshipType, string> = {
  cited: "Cited",
  foundational: "Foundational",
  parallel: "Parallel",
  subsequent: "Subsequent",
  related: "Related",
};

interface Props {
  sessionId: string;
  onOpenSession: (sessionId: string) => void;
  onDuplicates: (resp: UploadResponse, url: string, title?: string) => void;
}

export function RelatedPapers({ sessionId, onOpenSession, onDuplicates }: Props) {
  const [recs, setRecs] = useState<PaperRecommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetchingUrls, setFetchingUrls] = useState<Set<string>>(new Set());
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    fetchRecommendations(sessionId)
      .then((r) => { if (r.recommendations.length > 0) setRecs(r.recommendations); })
      .catch(() => {})
      .finally(() => setChecked(true));
  }, [sessionId]);

  async function handleGenerate() {
    setLoading(true);
    setErrors({});
    try {
      const r = await generateRecommendations(sessionId);
      setRecs(r.recommendations);
    } catch (e) {
      setErrors({ _global: String(e) });
    } finally {
      setLoading(false);
    }
  }

  async function handleFetch(url: string, force = false, title?: string) {
    setFetchingUrls((prev) => new Set(prev).add(url));
    setErrors((e) => ({ ...e, [url]: "" }));
    try {
      const resp = await fetchAndAnalyzePaper(url, force, title);
      if (!resp.is_new_session && resp.duplicate_sessions.length > 0) {
        onDuplicates(resp, url, title);
      } else {
        onOpenSession(resp.session_id);
      }
    } catch (e) {
      setErrors((prev) => ({ ...prev, [url]: String(e) }));
    } finally {
      setFetchingUrls((prev) => { const s = new Set(prev); s.delete(url); return s; });
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

      {errors._global && <p className="related-error">{errors._global}</p>}

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
            {errors[r.url] && <p className="related-error">{errors[r.url]}</p>}
            <div className="related-card-actions">
              {r.session_id
                ? <button className="btn-ghost small" onClick={() => onOpenSession(r.session_id!)}>Open session →</button>
                : r.url && (
                  <button
                    className="btn-ghost small fetch-btn"
                    disabled={fetchingUrls.has(r.url)}
                    onClick={() => handleFetch(r.url, false, r.title)}
                  >
                    {fetchingUrls.has(r.url) ? "Downloading…" : "⬇ Fetch & Analyze"}
                  </button>
                )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
