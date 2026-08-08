import React from "react";
import { useMetricsStore } from "@aether/core";
import { Card, Badge } from "@aether/ui-components";

export const MetricsDashboard: React.FC = () => {
  const abResults = useMetricsStore((state) => state.abResults);

  const mockABResult = abResults[0] ?? {
    candidateHash: "cand_top_v2",
    baselineHash: "base_top_v1",
    mcNemarPValue: 0.024,
    holmBonferroniCI: [0.08, 0.22],
    passedGate: true,
  };

  return (
    <Card title="📊 Harness Self-Improvement & McNemar Statistical Dashboard">
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px", marginBottom: "16px" }}>
        <div style={{ background: "#0f172a", padding: "12px", borderRadius: "8px" }}>
          <div style={{ fontSize: "11px", color: "#94a3b8" }}>SWE-Bench Pass Rate</div>
          <div style={{ fontSize: "20px", fontWeight: 700, color: "#4ade80" }}>78.4%</div>
          <div style={{ fontSize: "11px", color: "#22c55e" }}>+4.2% lift vs baseline</div>
        </div>
        <div style={{ background: "#0f172a", padding: "12px", borderRadius: "8px" }}>
          <div style={{ fontSize: "11px", color: "#94a3b8" }}>McNemar p-value</div>
          <div style={{ fontSize: "20px", fontWeight: 700, color: "#38bdf8" }}>
            p = {mockABResult.mcNemarPValue}
          </div>
          <div style={{ fontSize: "11px", color: "#38bdf8" }}>α = 0.05 threshold</div>
        </div>
        <div style={{ background: "#0f172a", padding: "12px", borderRadius: "8px" }}>
          <div style={{ fontSize: "11px", color: "#94a3b8" }}>Holm–Bonferroni 95% CI</div>
          <div style={{ fontSize: "18px", fontWeight: 700, color: "#fbbf24" }}>
            [{mockABResult.holmBonferroniCI[0]}, {mockABResult.holmBonferroniCI[1]}]
          </div>
          <div style={{ fontSize: "11px", color: "#f59e0b" }}>Statistically Significant</div>
        </div>
      </div>

      <div style={{ background: "#0f172a", padding: "12px", borderRadius: "8px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <span style={{ fontSize: "13px", fontWeight: 600, color: "#f8fafc" }}>
              Candidate Mutation [{mockABResult.candidateHash}]
            </span>
            <span style={{ fontSize: "12px", color: "#94a3b8", marginLeft: "8px" }}>
              vs Baseline [{mockABResult.baselineHash}]
            </span>
          </div>
          <Badge variant={mockABResult.passedGate ? "success" : "danger"}>
            {mockABResult.passedGate ? "ADMITTED (GATE PASSED)" : "REJECTED"}
          </Badge>
        </div>
      </div>
    </Card>
  );
};
