import React, { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useWorkflowStore, GateStatus } from "@aether/core";
import { CustomNode } from "./CustomNode";
import { ConditionalEdge } from "./ConditionalEdge";

export const WorkflowCanvas: React.FC = () => {
  const nodesState = useWorkflowStore((state) => state.nodes);
  const edgesState = useWorkflowStore((state) => state.edges);
  const setSelectedNodeId = useWorkflowStore((state) => state.setSelectedNodeId);

  const nodeTypes = useMemo(() => ({ customNode: CustomNode }), []);
  const edgeTypes = useMemo(() => ({ conditionalEdge: ConditionalEdge }), []);

  // Map Zustand store nodes to xyflow Node[]
  const initialNodes: Node[] = useMemo(() => {
    if (nodesState.length === 0) {
      // Default linear repair DAG fallback for demonstration
      return [
        {
          id: "retrieve_context",
          type: "customNode",
          position: { x: 250, y: 50 },
          data: { label: "Retrieve Context", nodeKind: "Retrieve", status: GateStatus.PASSED, detail: "4 files retrieved" },
        },
        {
          id: "generate_patch",
          type: "customNode",
          position: { x: 250, y: 180 },
          data: { label: "Generate Patch", nodeKind: "Generate", status: GateStatus.PASSED, detail: "Valid AST patch generated" },
        },
        {
          id: "apply_patch",
          type: "customNode",
          position: { x: 250, y: 310 },
          data: { label: "Apply Patch", nodeKind: "Apply", status: GateStatus.PASSED, detail: "Diff applied to workspace" },
        },
        {
          id: "evaluate_gate",
          type: "customNode",
          position: { x: 250, y: 440 },
          data: { label: "Evaluate Hard Gate", nodeKind: "Evaluate", status: GateStatus.FAILED, detail: "2 test failures" },
        },
        {
          id: "instrument_check",
          type: "customNode",
          position: { x: 500, y: 440 },
          data: { label: "Instrument Check", nodeKind: "Evaluate", status: GateStatus.NONE, instrumentError: "OOM killer container timeout" },
        },
        {
          id: "repair_node",
          type: "customNode",
          position: { x: 250, y: 570 },
          data: { label: "Repair Iteration", nodeKind: "Repair", status: GateStatus.PASSED, detail: "Passed on iteration 2" },
        },
      ];
    }
    return nodesState.map((n, idx) => ({
      id: n.id,
      type: "customNode",
      position: { x: 250, y: 50 + idx * 130 },
      data: { label: n.label, nodeKind: n.nodeKind, status: n.status, instrumentError: n.instrumentError, detail: n.detail },
    }));
  }, [nodesState]);

  const initialEdges: Edge[] = useMemo(() => {
    if (edgesState.length === 0) {
      return [
        { id: "e1", source: "retrieve_context", target: "generate_patch", type: "conditionalEdge", data: { when: "always" } },
        { id: "e2", source: "generate_patch", target: "apply_patch", type: "conditionalEdge", data: { when: "on_pass" } },
        { id: "e3", source: "apply_patch", target: "evaluate_gate", type: "conditionalEdge", data: { when: "always" } },
        { id: "e4", source: "evaluate_gate", target: "repair_node", type: "conditionalEdge", data: { when: "on_fail" } },
        { id: "e5", source: "evaluate_gate", target: "instrument_check", type: "conditionalEdge", data: { when: "on_instrument_error" } },
      ];
    }
    return edgesState.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      type: "conditionalEdge",
      data: { when: e.when },
    }));
  }, [edgesState]);

  return (
    <div style={{ width: "100%", height: "100%", background: "#090d16" }}>
      <ReactFlow
        nodes={initialNodes}
        edges={initialEdges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodeClick={(_, node) => setSelectedNodeId(node.id)}
        onPaneClick={() => setSelectedNodeId(null)}
        fitView
      >
        <Background color="#1e293b" gap={20} />
        <Controls style={{ background: "#1e293b", color: "#f8fafc", border: "1px solid #334155" }} />
        <MiniMap nodeColor={() => "#38bdf8"} style={{ background: "#0f172a", border: "1px solid #334155" }} />
      </ReactFlow>
    </div>
  );
};
