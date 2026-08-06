import React from "react";
import { useWorkflowStore, useNodeTrace, GateStatus } from "@aether/core";
import { Card, Badge } from "@aether/ui-components";

export const LiveTraceInspector: React.FC = () => {
  const selectedNodeId = useWorkflowStore((state) => state.selectedNodeId);
  const { node, nodeEvents } = useNodeTrace(selectedNodeId);

  if (!selectedNodeId) {
    return (
      <Card title="🔍 Execution Trace Inspector" style={{ height: "100%", overflowY: "auto" }}>
        <p style={{ color: "#94a3b8", fontSize: "14px", fontStyle: "italic" }}>
          Click any node on the workflow canvas to inspect prompt layers, LLM streams, and gate evaluation reports.
        </p>
      </Card>
    );
  }

  const getStatusBadgeVariant = (status?: GateStatus) => {
    switch (status) {
      case GateStatus.PASSED:
        return "success";
      case GateStatus.FAILED:
        return "danger";
      case GateStatus.NONE:
        return "warning";
      default:
        return "default";
    }
  };

  return (
    <Card title={`🔍 Node Trace: ${node?.label ?? selectedNodeId}`} style={{ height: "100%", overflowY: "auto" }}>
      <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
        <Badge variant="info">Kind: {node?.nodeKind ?? "Unknown"}</Badge>
        <Badge variant={getStatusBadgeVariant(node?.status)}>
          Status: {node?.status?.toUpperCase() ?? "IDLE"}
        </Badge>
      </div>

      {node?.status === GateStatus.NONE && node?.instrumentError && (
        <div
          style={{
            background: "rgba(245, 158, 11, 0.15)",
            border: "1px solid #f59e0b",
            borderRadius: "8px",
            padding: "12px",
            marginBottom: "16px",
            color: "#fbbf24",
            fontSize: "13px",
          }}
        >
          <strong>⚠ Instrument Error (GateStatus.NONE):</strong>
          <br />
          {node.instrumentError}
          <div style={{ fontSize: "11px", color: "#fcd34d", marginTop: "4px" }}>
            * Note: Excluded from statistical denominator per B4 rule; never treated as test failure.
          </div>
        </div>
      )}

      {node?.detail && (
        <div style={{ background: "#0f172a", borderRadius: "8px", padding: "12px", marginBottom: "16px" }}>
          <div style={{ fontSize: "12px", fontWeight: 700, color: "#38bdf8", marginBottom: "4px" }}>
            Gate Detail
          </div>
          <div style={{ fontSize: "13px", color: "#cbd5e1" }}>{node.detail}</div>
        </div>
      )}

      <div style={{ background: "#0f172a", borderRadius: "8px", padding: "12px" }}>
        <div style={{ fontSize: "12px", fontWeight: 700, color: "#38bdf8", marginBottom: "8px" }}>
          Event Trace Stream ({nodeEvents.length} events)
        </div>
        {nodeEvents.length === 0 ? (
          <div style={{ color: "#64748b", fontSize: "13px", fontStyle: "italic" }}>
            No event deltas recorded for this node yet.
          </div>
        ) : (
          nodeEvents.map((evt, i) => (
            <div key={i} style={{ fontSize: "12px", color: "#cbd5e1", borderBottom: "1px solid #1e293b", padding: "4px 0" }}>
              <span style={{ color: "#94a3b8" }}>[{evt.seq}] {evt.eventType}: </span>
              {JSON.stringify(evt.payload)}
            </div>
          ))
        )}
      </div>
    </Card>
  );
};
