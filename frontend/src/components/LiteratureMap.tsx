import { useEffect, useCallback } from "react";
import {
  ReactFlow, Background, Controls, MiniMap,
  Node, Edge, NodeProps, Handle, Position,
  useNodesState, useEdgesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { LiteratureGraph, RelationshipType } from "../types";
import { fetchLiteratureGraph } from "../hooks/useApi";

const REL_COLORS: Record<string, string> = {
  cited: "#6c8ebf",
  foundational: "#d79b00",
  parallel: "#82b366",
  subsequent: "#9673a6",
  related: "#666",
};

function PaperNodeComponent({ data }: NodeProps) {
  const d = data as Record<string, unknown>;
  const sessionId = d.session_id as string | null | undefined;
  const onOpen = d.onOpen as (() => void) | undefined;
  const url = d.url as string | undefined;

  return (
    <div className={`flow-node ${sessionId ? "flow-node-local" : ""}`}>
      <Handle type="target" position={Position.Top} />
      <div className="flow-node-title">{d.title as string}</div>
      {!!d.authors && <div className="flow-node-meta">{String(d.authors)}{d.year ? ` · ${String(d.year)}` : ""}</div>}
      {!!d.takeaway && <div className="flow-node-takeaway">{String(d.takeaway)}</div>}
      <div className="flow-node-actions">
        {sessionId && onOpen && <button className="flow-node-btn" onClick={onOpen}>Open →</button>}
        {!sessionId && url && (
          <>
            <a className="flow-node-btn" href={url} target="_blank" rel="noreferrer">↗ Link</a>
            {" · "}
            <button className="flow-node-btn" onClick={() => (d.onFetch as () => void)?.()}>⬇ Fetch</button>
          </>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

const nodeTypes = { paper: PaperNodeComponent };

function buildLayout(graphData: LiteratureGraph, onOpenSession: (id: string) => void, onFetchPaper: (url: string) => void): { nodes: Node[]; edges: Edge[] } {
  const HGAP = 340;
  const VGAP = 240;
  const localNodes = graphData.nodes.filter((n) => n.session_id);
  const externalNodes = graphData.nodes.filter((n) => !n.session_id);
  const positioned: Record<string, { x: number; y: number }> = {};

  localNodes.forEach((n, i) => { positioned[n.id] = { x: i * HGAP, y: 0 }; });

  externalNodes.forEach((n) => {
    const parentEdge = graphData.edges.find((e) => e.target === n.id);
    const parentPos = parentEdge ? positioned[parentEdge.source] : null;
    const base = parentPos ?? { x: Object.keys(positioned).length * HGAP, y: 0 };
    for (let row = 1; ; row++) {
      const candidate = { x: base.x, y: row * VGAP };
      const conflict = Object.values(positioned).some(
        (p) => Math.abs(p.x - candidate.x) < 160 && Math.abs(p.y - candidate.y) < 100
      );
      if (!conflict) { positioned[n.id] = candidate; break; }
    }
  });

  const nodes: Node[] = graphData.nodes.map((n) => ({
    id: n.id,
    type: "paper",
    position: positioned[n.id] ?? { x: 0, y: 0 },
    data: {
      ...n,
      onOpen: n.session_id ? () => onOpenSession(n.session_id!) : undefined,
      onFetch: !n.session_id && n.url ? () => onFetchPaper(n.url!) : undefined,
    },
  }));

  const edges: Edge[] = graphData.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.relationship as RelationshipType,
    style: { stroke: REL_COLORS[e.relationship] ?? "#666" },
    labelStyle: { fontSize: 10, fill: REL_COLORS[e.relationship] ?? "#666" },
    labelBgStyle: { fill: "#1a1a2e", fillOpacity: 0.8 },
  }));

  return { nodes, edges };
}

interface Props {
  onClose: () => void;
  onOpenSession: (sessionId: string) => void;
  onFetchPaper: (url: string) => void;
}

export function LiteratureMap({ onClose, onOpenSession, onFetchPaper }: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const load = useCallback(async () => {
    try {
      const graph = await fetchLiteratureGraph();
      const { nodes: n, edges: e } = buildLayout(graph, onOpenSession, onFetchPaper);
      setNodes(n);
      setEdges(e);
    } catch { /* empty graph is fine */ }
  }, [onOpenSession, onFetchPaper, setNodes, setEdges]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="literature-map-overlay">
      <div className="literature-map-header">
        <h2>Literature Map</h2>
        <div className="lit-legend">
          {Object.entries(REL_COLORS).map(([rel, color]) => (
            <span key={rel} className="lit-legend-item">
              <span className="lit-legend-dot" style={{ background: color }} />
              {rel}
            </span>
          ))}
        </div>
        <button className="btn-ghost" onClick={onClose}>✕ Close</button>
      </div>

      {nodes.length === 0 ? (
        <div className="literature-map-empty">
          <p>No papers in the literature graph yet.</p>
          <p>Open a paper and click "Find related papers" to start building the map.</p>
        </div>
      ) : (
        <div className="literature-map-canvas">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.2 }}
          >
            <Background color="#2a2a3e" gap={24} />
            <Controls />
            <MiniMap nodeColor={(n) => (n.data.session_id ? "#6c63ff" : "#444")} />
          </ReactFlow>
        </div>
      )}
    </div>
  );
}
