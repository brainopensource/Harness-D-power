import type React from "react";

export const ContextInspector: React.FC = () => {
  const promptLayers = [
    { level: "Layer 1", name: "System Prompt", tokens: 2500, cached: true },
    { level: "Layer 2", name: "System Policy & CAR Grants", tokens: 1800, cached: true },
    { level: "Layer 3", name: "Memory Index & Retrieval", tokens: 3200, cached: false },
    { level: "Layer 4", name: "Repository Skeleton Context", tokens: 12000, cached: true },
    { level: "Layer 5", name: "User Spec & Acceptance Criteria", tokens: 4100, cached: false },
    { level: "Layer 6", name: "Anchored State & Plan", tokens: 1500, cached: false },
    { level: "Layer 7", name: "Trajectory History & Tool Turns", tokens: 34000, cached: false },
  ];

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-xl font-bold font-mono text-gray-100">
        PROMPT LAYER & EXCHANGE COMPACTOR INSPECTOR
      </h2>

      <div className="grid grid-cols-3 gap-4">
        <div className="p-4 bg-gray-900 border border-gray-800 rounded-lg font-mono">
          <div className="text-xs text-gray-400">PREFIX DIGEST CACHE RATE</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">71.4%</div>
          <div className="text-[10px] text-gray-500 mt-1">Layers 1, 2 & 4 hit cache</div>
        </div>
        <div className="p-4 bg-gray-900 border border-gray-800 rounded-lg font-mono">
          <div className="text-xs text-gray-400">HEADROOM RESERVED</div>
          <div className="text-2xl font-bold text-purple-400 mt-1">20.0%</div>
          <div className="text-[10px] text-gray-500 mt-1">Exchange compactor threshold</div>
        </div>
        <div className="p-4 bg-gray-900 border border-gray-800 rounded-lg font-mono">
          <div className="text-xs text-gray-400">ACTIVE PROMPT LENGTH</div>
          <div className="text-2xl font-bold text-sky-400 mt-1">59,100 TOKENS</div>
          <div className="text-[10px] text-gray-500 mt-1">Within 128k context window</div>
        </div>
      </div>

      <div className="bg-gray-950 p-4 rounded-xl border border-gray-800 space-y-3">
        <h3 className="text-sm font-bold font-mono text-gray-300">
          PROMPT STACK BREAKDOWN (LAYERS 1–7)
        </h3>
        <div className="space-y-2 font-mono text-xs">
          {promptLayers.map((layer) => (
            <div
              key={layer.level}
              className="p-3 bg-gray-900 border border-gray-800 rounded-lg flex justify-between items-center"
            >
              <div className="flex items-center gap-3">
                <span className="text-purple-400 font-bold">{layer.level}</span>
                <span className="text-gray-200">{layer.name}</span>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-gray-400">{layer.tokens.toLocaleString()} tokens</span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${layer.cached ? "bg-emerald-950 text-emerald-400 border border-emerald-800" : "bg-gray-800 text-gray-400"}`}
                >
                  {layer.cached ? "PREFIX CACHED" : "DYNAMIC"}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
