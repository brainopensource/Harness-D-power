import type React from "react";

export const AetherSwarmView: React.FC = () => {
  const agents = [
    {
      id: "Conductor-01",
      role: "Swarm Conductor",
      status: "Active",
      task: "Self-Evolution & Meta-Optimization",
    },
    {
      id: "Coder-Alpha",
      role: "Senior Code Engineer",
      status: "Coding",
      task: "Refactoring Policy Engine",
    },
    {
      id: "Reviewer-Beta",
      role: "Safety & Gate Evaluator",
      status: "Evaluating",
      task: "Verifying test unmodified gate",
    },
    {
      id: "Researcher-Gamma",
      role: "Codebase Researcher",
      status: "Idle",
      task: "Awaiting next macro story",
    },
  ];

  return (
    <div className="p-6 space-y-6 font-mono">
      <h2 className="text-xl font-bold text-gray-100">
        AETHER SWARM OVERVIEW & SELF-IMPROVEMENT MONITOR
      </h2>

      <div className="grid grid-cols-3 gap-4">
        <div className="p-4 bg-gray-900 border border-gray-800 rounded-lg">
          <div className="text-xs text-gray-400">ACTIVE SWARM AGENTS</div>
          <div className="text-2xl font-bold text-purple-400 mt-1">4 AGENTS</div>
          <div className="text-[10px] text-gray-500 mt-1">Structured memory exchange connected</div>
        </div>
        <div className="p-4 bg-gray-900 border border-gray-800 rounded-lg">
          <div className="text-xs text-gray-400">CONDUCTOR EVOLUTION SCORE</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">+18.4%</div>
          <div className="text-[10px] text-gray-500 mt-1">Improvement over baseline floor</div>
        </div>
        <div className="p-4 bg-gray-900 border border-gray-800 rounded-lg">
          <div className="text-xs text-gray-400">MEMORY GRAPH EDGES</div>
          <div className="text-2xl font-bold text-sky-400 mt-1">1,420 EDGES</div>
          <div className="text-[10px] text-gray-500 mt-1">Shared inter-agent memory bus</div>
        </div>
      </div>

      <div className="bg-gray-950 p-4 rounded-xl border border-gray-800 space-y-3">
        <h3 className="text-sm font-bold text-gray-300">SWARM TOPOLOGY & AGENT ROSTER</h3>
        <div className="space-y-2 text-xs">
          {agents.map((ag) => (
            <div
              key={ag.id}
              className="p-3 bg-gray-900 border border-gray-800 rounded-lg flex justify-between items-center"
            >
              <div>
                <span className="text-purple-400 font-bold">{ag.id}</span>{" "}
                <span className="text-gray-400 font-semibold">({ag.role})</span>
                <div className="text-gray-300 mt-1">Task: {ag.task}</div>
              </div>
              <span className="px-2.5 py-1 rounded bg-purple-950 text-purple-300 border border-purple-800 text-[10px]">
                ● {ag.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
