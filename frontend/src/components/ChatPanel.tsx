import { useState, useRef, useEffect } from "react";
import { ChatMessage, ChatSource } from "../types";
import { askQuestion } from "../hooks/useApi";

interface Props {
  sessionId: string;
  initialMessages?: ChatMessage[];
  onIllustrate: (context: string) => Promise<void>;
}

function SourceList({ sources }: { sources: ChatSource[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="source-wrap">
      <button className="chat-action-btn source-btn" onClick={() => setOpen((o) => !o)}>
        ¶ Sources ({sources.length}) {open ? "▲" : "▼"}
      </button>
      {open && (
        <div className="source-list">
          {sources.map((s, i) => (
            <div key={i} className="source-item">
              <span className={`source-tag ${s.type}`}>{s.type === "paper" ? "Paper" : "Web"}</span>
              {s.url
                ? <a href={s.url} target="_blank" rel="noreferrer">{s.quote}</a>
                : <p>"{s.quote}"</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ChatPanel({ sessionId, initialMessages, onIllustrate }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages ?? []);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [illustratingIdx, setIllustratingIdx] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setLoading(true);
    try {
      const resp = await askQuestion(sessionId, q);
      setMessages((m) => [...m, { role: "assistant", text: resp.answer, sources: resp.sources, context: resp.answer }]);
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", text: `Error: ${err}` }]);
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }

  return (
    <div className="chat-panel">
      <h2>Ask about the paper</h2>
      <div className="chat-messages">
        {messages.length === 0 && (
          <p className="chat-empty">Ask anything about the paper — methodology, findings, definitions…</p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`chat-bubble ${msg.role}`}>
            <p>{msg.text}</p>
            {msg.role === "assistant" && (
              <div className="chat-actions">
                {msg.sources && msg.sources.length > 0 && <SourceList sources={msg.sources} />}
                {msg.context && (
                  <button
                    className={`chat-action-btn illustrate-btn${illustratingIdx === i ? " loading" : ""}`}
                    disabled={illustratingIdx !== null}
                    onClick={async () => {
                      setIllustratingIdx(i);
                      try { await onIllustrate(msg.context!); } finally { setIllustratingIdx(null); }
                    }}
                  >
                    {illustratingIdx === i ? <span className="chat-dots"><span /><span /><span /></span> : "✦ Illustrate"}
                  </button>
                )}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="chat-bubble assistant loading">
            <span className="chat-dots"><span /><span /><span /></span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="chat-input-row">
        <textarea
          className="chat-input"
          placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          rows={2}
          disabled={loading}
        />
        <button className="chat-send-btn" onClick={handleSend} disabled={loading || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
