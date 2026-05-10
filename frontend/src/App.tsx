import { useState, useEffect, useRef } from "react";
import { PaperUpload } from "./components/PaperUpload";
import { PaperSummaryPanel } from "./components/PaperSummary";
import { IllustrationPanel } from "./components/IllustrationPanel";
import { ImageGallery } from "./components/ImageGallery";
import { ChatPanel } from "./components/ChatPanel";
import { RecentSessions, DuplicateBanner } from "./components/RecentSessions";
import { uploadPaper, fetchPresets, fetchSessions, resumeSession, generateIllustration } from "./hooks/useApi";
import { PaperSummary, Preset, IllustrationResult, AspectRatio, Resolution, SessionMeta } from "./types";
import "./App.css";

export default function App() {
  const [summary, setSummary] = useState<PaperSummary | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [illustrations, setIllustrations] = useState<IllustrationResult[]>([]);
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>("1:1");
  const [resolution, setResolution] = useState<Resolution>("2048");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentSessions, setRecentSessions] = useState<SessionMeta[]>([]);
  const [duplicates, setDuplicates] = useState<SessionMeta[]>([]);
  const [pendingSummary, setPendingSummary] = useState<{ sessionId: string; summary: PaperSummary } | null>(null);
  const galleryRef = useRef<HTMLDivElement>(null);

  useEffect(() => { fetchPresets().then(setPresets).catch(() => {}); }, []);
  useEffect(() => { fetchSessions().then(setRecentSessions).catch(() => {}); }, []);

  async function handleUpload(file: File) {
    setUploading(true);
    setError(null);
    setDuplicates([]);
    setPendingSummary(null);
    try {
      const resp = await uploadPaper(file);
      if (resp.duplicate_sessions.length > 0) {
        // Hold off opening — let user choose to resume or start fresh
        setDuplicates(resp.duplicate_sessions);
        setPendingSummary({ sessionId: resp.session_id, summary: resp.summary });
      } else {
        openSession(resp.session_id, resp.summary);
      }
      setRecentSessions(await fetchSessions());
    } catch (err) {
      setError(String(err));
    } finally {
      setUploading(false);
    }
  }

  function openSession(sid: string, s: PaperSummary, savedIllustrations: IllustrationResult[] = []) {
    setSummary(s);
    setSessionId(sid);
    setIllustrations(savedIllustrations);
    setDuplicates([]);
    setPendingSummary(null);
  }

  async function handleResume(sid: string) {
    try {
      const resp = await resumeSession(sid);
      openSession(resp.session_id, resp.summary, resp.illustrations ?? []);
    } catch (err) {
      setError(String(err));
    }
  }

  function handleStartFresh() {
    if (pendingSummary) openSession(pendingSummary.sessionId, pendingSummary.summary);
  }

  function paperContext(): string {
    if (!summary) return "";
    const points = summary.key_points.join("; ");
    return `Title: ${summary.title}. Abstract: ${summary.abstract}. Key points: ${points}. Methodology: ${summary.methodology}. Findings: ${summary.findings}`;
  }

  function handleNewResult(result: IllustrationResult) {
    setIllustrations((prev) => [...prev, result]);
    setTimeout(() => galleryRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  }

  const SCHEME_TEMPLATE =
    "Create a clear technical scheme or diagram that visually explains the following concept from a research paper. " +
    "Style: clean line diagram, labeled components, minimal color, white background, schematic/blueprint aesthetic. " +
    "Concept to illustrate:\n{context}";

  async function handleChatIllustrate(context: string): Promise<void> {
    const preset = "key_concept";
    const existing = illustrations.filter((r) => r.preset === preset);
    const iteration = existing.length === 0 ? 1 : Math.max(...existing.map((r) => r.iteration)) + 1;
    try {
      const result = await generateIllustration({
        preset, paper_context: context,
        aspect_ratio: aspectRatio, resolution, iteration,
        custom_template: SCHEME_TEMPLATE,
        session_id: sessionId ?? undefined,
      });
      handleNewResult(result);
    } catch { /* swallow */ }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <h1>Paper Assistant</h1>
          <p>Upload a research paper — get a summary, chat, and AI-generated illustrations</p>
        </div>
      </header>

      <main className="app-main">
        {!summary ? (
          <div className="upload-wrapper">
            <PaperUpload onUpload={handleUpload} loading={uploading} />
            {error && <div className="error-banner">{error}</div>}
            {duplicates.length > 0 && (
              <DuplicateBanner
                duplicates={duplicates}
                onResume={handleResume}
                onDismiss={handleStartFresh}
              />
            )}
            <RecentSessions
              sessions={recentSessions}
              onResume={handleResume}
              onDeleted={(id) => setRecentSessions((s) => s.filter((x) => x.session_id !== id))}
            />
          </div>
        ) : (
          <>
            <div className="top-bar">
              <button className="reset-btn" onClick={() => { setSummary(null); setSessionId(null); setIllustrations([]); }}>
                ← Papers
              </button>
            </div>

            <div className="content-grid">
              <div className="main-column">
                <PaperSummaryPanel summary={summary} />
                {sessionId && (
                  <ChatPanel
                    sessionId={sessionId}
                    onIllustrate={handleChatIllustrate}
                  />
                )}
              </div>

              <aside className="side-panel">
                <IllustrationPanel
                  presets={presets}
                  paperContext={paperContext()}
                  illustrations={illustrations}
                  aspectRatio={aspectRatio}
                  resolution={resolution}
                  sessionId={sessionId ?? undefined}
                  onAspectRatioChange={setAspectRatio}
                  onResolutionChange={setResolution}
                  onNewResult={handleNewResult}
                />
              </aside>
            </div>

            <div ref={galleryRef}>
              <ImageGallery results={illustrations} />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
