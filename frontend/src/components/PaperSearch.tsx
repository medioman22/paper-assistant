import { useState, useRef } from "react";
import { PaperSearchResult, UploadResponse } from "../types";
import { searchPapers, fetchAndAnalyzePaper } from "../hooks/useApi";

interface Props {
  onOpenSession: (sessionId: string) => void;
  onDuplicates: (resp: UploadResponse, url: string, title?: string) => void;
}

export function PaperSearch({ onOpenSession, onDuplicates }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PaperSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchingUrl, setFetchingUrl] = useState<Set<string>>(new Set());
  const [fetchErrors, setFetchErrors] = useState<Record<string, string>>({});
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResults([]);
    try {
      const res = await searchPapers(query.trim());
      setResults(res.results);
      if (res.results.length === 0) setError("No papers found. Try a different query.");
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleFetch(url: string, title: string) {
    setFetchingUrl(prev => new Set(prev).add(url));
    setFetchErrors(prev => ({ ...prev, [url]: "" }));
    try {
      const resp = await fetchAndAnalyzePaper(url, false, title);
      if (!resp.is_new_session && resp.duplicate_sessions.length > 0) {
        onDuplicates(resp, url, title);
      } else {
        onOpenSession(resp.session_id);
      }
    } catch (err) {
      setFetchErrors(prev => ({ ...prev, [url]: String(err) }));
    } finally {
      setFetchingUrl(prev => { const s = new Set(prev); s.delete(url); return s; });
    }
  }

  return (
    <div className="paper-search">
      <div className="paper-search-header">
        <h3>Search Papers</h3>
        <span className="paper-search-badge">via Semantic Scholar</span>
      </div>

      <form className="paper-search-form" onSubmit={handleSearch}>
        <input
          ref={inputRef}
          className="paper-search-input"
          type="text"
          placeholder="Ask a research question or describe a topic…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          disabled={loading}
        />
        <button className="btn-primary small" type="submit" disabled={loading || !query.trim()}>
          {loading ? "Searching…" : "Search"}
        </button>
      </form>

      {error && <p className="related-error">{error}</p>}

      {results.length > 0 && (
        <div className="related-list">
          {results.map((r, i) => (
            <div key={i} className="related-card">
              <div className="related-card-top">
                <span className="rel-badge rel-related">Scholar</span>
                <span className="related-year">
                  {r.year ?? ""}
                  {r.venue ? ` · ${r.venue}` : ""}
                </span>
              </div>
              <p className="related-title">
                {r.url
                  ? <a href={r.url} target="_blank" rel="noreferrer">{r.title}</a>
                  : r.title}
              </p>
              <p className="related-authors">{r.authors}</p>
              {r.relevance && <p className="related-takeaway">{r.relevance}</p>}
              {r.abstract && (
                <p className="paper-search-abstract">{r.abstract}</p>
              )}
              {fetchErrors[r.url ?? ""] && (
                <p className="related-error">{fetchErrors[r.url ?? ""]}</p>
              )}
              {r.url && (
                <div className="related-card-actions">
                  <button
                    className="btn-ghost small fetch-btn"
                    disabled={fetchingUrl.has(r.url)}
                    onClick={() => handleFetch(r.url!, r.title)}
                  >
                    {fetchingUrl.has(r.url) ? "Downloading…" : "⬇ Fetch & Analyze"}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
