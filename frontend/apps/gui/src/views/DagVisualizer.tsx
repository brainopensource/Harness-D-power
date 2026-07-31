import type React from "react";

export const DagVisualizer: React.FC = () => {
  const nodes = [
    { id: "S1", name: "Macro Story: Kernel Refactor", status: "completed", x: 50, y: 100 },
    { id: "S2", name: "Task: CAR Authorization", status: "running", x: 300, y: 50 },
    { id: "S3", name: "Task: Monotonic Taint Gate", status: "pending", x: 300, y: 150 },
    { id: "S4", name: "Gate: Unmodified Tests Check", status: "passed", x: 550, y: 100 },
  ];

  return (
    <div className="p-6 space-y-4">
      <h2 className="text-xl font-bold font-mono text-gray-100">
        STORY-DAG & WORKFLOW NODE EDITOR
      </h2>
      <p className="text-xs font-mono text-gray-400">
        Interactive macro story topology, subtasks, disjoint closures, and gate checkpoints.
      </p>

      <div className="bg-gray-950 p-6 rounded-xl border border-gray-800 relative min-h-[400px]">
        <svg className="absolute inset-0 w-full h-full pointer-events-none">
          <title>Node Graph Edges</title>
          <line x1="180" y1="110" x2="300" y2="70" stroke="#4B5563" strokeWidth="2" />
          <line x1="180" y1="110" x2="300" y2="170" stroke="#4B5563" strokeWidth="2" />
          <line x1="430" y1="70" x2="550" y2="110" stroke="#4B5563" strokeWidth="2" />
          <line x1="430" y1="170" x2="550" y2="110" stroke="#4B5563" strokeWidth="2" />
        </svg>

        {nodes.map((node) => (
          <div
            key={node.id}
            style={{ left: `${node.x}px`, top: `${node.y}px` }}
            className="absolute p-4 bg-gray-900 border border-purple-800/80 rounded-lg shadow-lg w-52 z-10"
          >
            <div className="text-xs font-mono text-purple-400 font-bold">{node.id}</div>
            <div className="text-sm font-mono text-gray-200 mt-1 font-semibold">{node.name}</div>
            <div className="text-[10px] font-mono text-emerald-400 mt-2 uppercase font-medium">
              ● {node.status}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
