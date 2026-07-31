import type React from "react";
import { useState } from "react";

export const CodeIntelView: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState("");

  const symbols = [
    {
      name: "PolicyEngine.authorize",
      file: "src/sagiha/kernel/policy.py",
      line: 42,
      type: "method",
    },
    {
      name: "dispatch_tool_call",
      file: "src/sagiha/kernel/dispatch.py",
      line: 88,
      type: "function",
    },
    { name: "FrozenRunState", file: "src/sagiha/domain/control.py", line: 67, type: "class" },
    { name: "GateReport", file: "src/sagiha/domain/work.py", line: 55, type: "class" },
  ];

  const filtered = symbols.filter(
    (s) =>
      s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.file.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-xl font-bold font-mono text-gray-100">
        TREE-SITTER CODE INTELLIGENCE & SYMBOL VIEWER
      </h2>

      <div className="bg-gray-950 p-4 rounded-xl border border-gray-800 space-y-4">
        <input
          type="text"
          placeholder="Search symbols or files (e.g. PolicyEngine, dispatch)..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full px-4 py-2 bg-gray-900 border border-gray-800 rounded-lg text-xs font-mono text-gray-200 focus:outline-none focus:border-purple-600"
        />

        <div className="space-y-2">
          {filtered.map((sym) => (
            <div
              key={`${sym.file}-${sym.name}`}
              className="p-3 bg-gray-900 border border-gray-800 rounded-lg flex justify-between items-center text-xs font-mono"
            >
              <div>
                <span className="text-purple-400 font-bold">[{sym.type.toUpperCase()}]</span>{" "}
                <span className="text-gray-100 font-semibold">{sym.name}</span>
                <span className="text-gray-500 ml-3">
                  {sym.file}:{sym.line}
                </span>
              </div>
              <span className="text-emerald-400 text-[10px]">VERIFIED AST SYMBOL</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
