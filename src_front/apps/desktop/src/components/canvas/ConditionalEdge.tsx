import React from "react";
import { BaseEdge, EdgeProps, getBezierPath } from "@xyflow/react";
import { EdgeRoutingCondition } from "@aether/core";

export interface ConditionalEdgeData {
  when?: EdgeRoutingCondition;
}

export const ConditionalEdge: React.FC<EdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  style = {},
  markerEnd,
}) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const condition = (data as ConditionalEdgeData)?.when ?? "always";

  const getEdgeStyle = (): React.CSSProperties => {
    switch (condition) {
      case "on_pass":
        return { stroke: "#22c55e", strokeWidth: 2.5 };
      case "on_fail":
        return { stroke: "#ef4444", strokeWidth: 2, strokeDasharray: "5 5" };
      case "on_instrument_error":
        return { stroke: "#f59e0b", strokeWidth: 2, strokeDasharray: "2 2" };
      default:
        return { stroke: "#64748b", strokeWidth: 2 };
    }
  };

  return (
    <>
      <BaseEdge path={edgePath} markerEnd={markerEnd} style={{ ...getEdgeStyle(), ...style }} />
      {condition !== "always" && (
        <text
          x={labelX}
          y={labelY}
          style={{
            fill: "#cbd5e1",
            fontSize: "10px",
            fontWeight: 600,
            pointerEvents: "none",
            textAnchor: "middle",
            dominantBaseline: "central",
          }}
        >
          {condition}
        </text>
      )}
    </>
  );
};
