import React from "react";
import { Handle, Position } from "@xyflow/react";
import { GateStatus } from "@aether/core";
import { Badge } from "@aether/ui-components";

export interface CustomNodeData {
  label: string;
  nodeKind: string;
  status: GateStatus;
  instrumentError?: string | null;
  detail?: string | null;
}

interface Props {
  data: CustomNodeData;
  selected?: boolean;
}

export const CustomNode: React.FC<Props> = ({ data, selected }) => {
  const getBorderColor = () => {
    switch (data.status) {
      case GateStatus.PASSED:
        return "#22c55e"; // green
      case GateStatus.FAILED:
        return "#ef4444"; // red
      case GateStatus.NONE:
        return "#f59e0b"; // amber warning
      default:
        return "#64748b"; // gray
    }
  };

  const getBadgeVariant = () => {
    switch (data.status) {
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
    <div
      style={{
        background: "rgba(15, 23, 42, 0.85)",
        backdropFilter: "blur(12px)",
        border: `2px solid ${selected ? "#38bdf8" : getBorderColor()}`,
        borderRadius: "12px",
        padding: "12px 16px",
        minWidth: "180px",
        boxShadow: selected
          ? "0 0 20px rgba(56, 189, 248, 0.4)"
          : "0 4px 20px rgba(0, 0, 0, 0.4)",
        color: "#f8fafc",
        transition: "all 0.2s ease",
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: "#38bdf8", width: 10, height: 10 }} />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
        <span style={{ fontSize: "11px", fontWeight: 700, color: "#94a3b8", textTransform: "uppercase" }}>
          {data.nodeKind}
        </span>
        <Badge variant={getBadgeVariant()}>{data.status.toUpperCase()}</Badge>
      </div>
      <div style={{ fontSize: "14px", fontWeight: 600, color: "#f8fafc", marginBottom: 4 }}>
        {data.label}
      </div>
      {data.status === GateStatus.NONE && data.instrumentError && (
        <div style={{ fontSize: "11px", color: "#fbbf24", fontStyle: "italic", marginTop: 4 }}>
          ⚠ {data.instrumentError}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} style={{ background: "#38bdf8", width: 10, height: 10 }} />
    </div>
  );
};
