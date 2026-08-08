import React from "react";
import { useTaintAudit, Provenance } from "@aether/core";
import { Card, Badge } from "@aether/ui-components";

export const TaintAuditPanel: React.FC = () => {
  const { spans } = useTaintAudit();

  const mockSpans = spans.length > 0 ? spans : [
    { spanId: "s1", label: Provenance.TRUSTED_SYSTEM, text: "System prompt prefix L1", source: "policy_engine", at: "12:00:00" },
    { spanId: "s2", label: Provenance.OPERATOR, text: "Operator task instruction", source: "cli_input", at: "12:00:01" },
    { spanId: "s3", label: Provenance.UNTRUSTED_EXTERNAL, text: "Retrieved issue report from repo", source: "github_issue_442", at: "12:00:02" },
  ];

  const getBadgeVariant = (label: Provenance) => {
    switch (label) {
      case Provenance.TRUSTED_SYSTEM:
        return "info";
      case Provenance.OPERATOR:
        return "success";
      case Provenance.UNTRUSTED_EXTERNAL:
        return "danger";
      case Provenance.UNTRUSTED_DERIVED:
        return "warning";
      default:
        return "default";
    }
  };

  return (
    <Card title="🛡️ TaintGate Provenance Audit" style={{ marginTop: "16px" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        {mockSpans.map((span) => (
          <div
            key={span.spanId}
            style={{
              background: "#0f172a",
              border: "1px solid #1e293b",
              borderRadius: "8px",
              padding: "10px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
              <Badge variant={getBadgeVariant(span.label)}>{span.label}</Badge>
              <span style={{ fontSize: "11px", color: "#64748b" }}>{span.source}</span>
            </div>
            <div style={{ fontSize: "12px", color: "#cbd5e1" }}>{span.text}</div>
          </div>
        ))}
      </div>
    </Card>
  );
};
