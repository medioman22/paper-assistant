import { useState, useEffect, useRef } from "react";
import { PaperUpload } from "./components/PaperUpload";
import { PaperSummaryPanel } from "./components/PaperSummary";
import { IllustrationPanel } from "./components/IllustrationPanel";
import { ImageGallery } from "./components/ImageGallery";
import { ChatPanel } from "./components/ChatPanel";
import { RecentSessions, DuplicateBanner } from "./components/RecentSessions";
import { RelatedPapers } from "./components/RelatedPapers";
import { LiteratureMap } from "./components/LiteratureMap";
import { uploadPaper, fetchPresets, fetchSessions, resumeSession, deleteSession, generateIllustration } from "./hooks/useApi";
import { PaperSummary, Preset, IllustrationResult, AspectRatio, Resolution, SessionMeta } from "./types";
import "./App.css";

export default function App() {
  const [summary, setSummary] = useState<PaperSummary | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [illustrations, setIllustrations] = useState<IllustrationResult[]>([]);
  const [initialChatMessages, setInitialChatMessages] = useState<import("./types").ChatMessage[]>([]);
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>("1:1");
  const [resolution, setResolution] = useState<Resolution>("2048");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentSessions, setRecentSessions] = useState<SessionMeta[]>([]);
  const [duplicates, setDuplicates] = useState<SessionMeta[]>([]);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [showLitMap, setShowLitMap] = useState(false);
  const galleryRef = useRef<HTMLDivElement>(null);

  useEffect(() => { fetchPresets().then(setPresets).catch(() => {}); }, []);
  useEffect(() => { fetchSessions().then(setRecentSessions).catch(() => {}); }, []);

  async function handleUpload(file: File, force = false) {
    setUploading(true);
    setError(null);
    setDuplicates([]);
    try {
      const resp = await uploadPaper(file, force);
      if (resp.duplicate_sessions.length > 0 && !resp.is_new_session) {
        setDuplicates(resp.duplicate_sessions);
        setPendingFile(file);
      } else {
        openSession(resp.session_id, resp.summary);
        setRecentSessions(await fetchSessions());
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setUploading(false);
    }
  }

  function openSession(sid: string, s: PaperSummary, savedIllustrations: IllustrationResult[] = [], chatMsgs: import("./types").ChatMessage[] = []) {
    setSummary(s);
    setSessionId(sid);
    setIllustrations(savedIllustrations);
    setInitialChatMessages(chatMsgs);
    setDuplicates([]);
    setPendingFile(null);
    setShowLitMap(false);
  }

  async function handleResume(sid: string) {
    try {
      const resp = await resumeSession(sid);
      const chatMsgs: import("./types").ChatMessage[] = (resp.chat_history ?? []).flatMap((t) => [
        { role: "user" as const, text: t.question },
        { role: "assistant" as const, text: t.answer, sources: t.sources, context: t.answer },
      ]);
      openSession(resp.session_id, resp.summary, resp.illustrations ?? [], chatMsgs);
    } catch (err) {
      setError(String(err));
    }
  }

  async function handleStartFresh() {
    if (pendingFile) await handleUpload(pendingFile, true);
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
        <button className="lit-map-btn" onClick={() => setShowLitMap(true)}>
          ⬡ Literature Map
        </button>
      </header>

      {showLitMap && (
        <LiteratureMap
          onClose={() => setShowLitMap(false)}
          onOpenSession={(sid) => { setShowLitMap(false); handleResume(sid); }}
        />
      )}

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
              <button className="reset-btn" onClick={() => { setSummary(null); setSessionId(null); setIllustrations([]); setInitialChatMessages([]); setPendingFile(null); }}>
                ← Papers
              </button>
            </div>

            <div className="content-grid">
              <div className="main-column">
                <PaperSummaryPanel summary={summary} />
                {sessionId && <RelatedPapers sessionId={sessionId} onOpenSession={handleResume} />}
                {sessionId && (
                  <ChatPanel
                    sessionId={sessionId}
                    initialMessages={initialChatMessages}
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
