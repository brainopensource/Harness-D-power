import React from "react";
import { DiffEditor } from "@monaco-editor/react";
import { usePatchStore } from "@aether/core";
import { Card, Button } from "@aether/ui-components";

export const MonacoDiffEditor: React.FC = () => {
  const pendingDiffs = usePatchStore((state) => state.pendingDiffs);
  const acceptDiff = usePatchStore((state) => state.acceptDiff);
  const rejectDiff = usePatchStore((state) => state.rejectDiff);

  const activeDiff = pendingDiffs[0] ?? {
    diffId: "diff_001",
    filePath: "django/db/models/sql/compiler.py",
    patchContent: "@@ -12,4 +12,6 @@\n- old_compiler_statement()\n+ new_optimized_compiler_statement()\n",
    status: "pending",
  };

  const originalCode = `def compile_query(self):\n    # Original baseline code\n    statement = self.old_compiler_statement()\n    return statement\n`;
  const modifiedCode = `def compile_query(self):\n    # Agent generated patch\n    statement = self.new_optimized_compiler_statement()\n    return statement\n`;

  return (
    <Card title={`📝 Patch Diff Reviewer: ${activeDiff.filePath}`} style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <span style={{ fontSize: "12px", color: "#94a3b8" }}>
          Status: <strong style={{ color: "#38bdf8" }}>{activeDiff.status.toUpperCase()}</strong>
        </span>
        <div style={{ display: "flex", gap: "8px" }}>
          <Button variant="secondary" size="sm" onClick={() => rejectDiff(activeDiff.diffId, "Rejected by operator")}>
            Reject Patch
          </Button>
          <Button variant="primary" size="sm" onClick={() => acceptDiff(activeDiff.diffId)}>
            Accept Patch
          </Button>
        </div>
      </div>
      <div style={{ flex: 1, minHeight: "280px", border: "1px solid #1e293b", borderRadius: "8px", overflow: "hidden" }}>
        <DiffEditor
          height="100%"
          language="python"
          original={originalCode}
          modified={modifiedCode}
          theme="vs-dark"
          options={{
            renderSideBySide: true,
            readOnly: true,
            minimap: { enabled: false },
          }}
        />
      </div>
    </Card>
  );
};
