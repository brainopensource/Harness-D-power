import { Button } from "@sagiha/ui";
import type React from "react";

export const ExporterView: React.FC = () => {
  return (
    <div className="p-6 space-y-6 font-mono">
      <h2 className="text-xl font-bold text-gray-100">
        BENCHMARK CASSETTE PLAYER & DATASET EXPORTER
      </h2>

      <div className="grid grid-cols-2 gap-4">
        <div className="p-4 bg-gray-900 border border-gray-800 rounded-lg">
          <div className="text-xs text-gray-400">BENCHMARK PASS RATE (BEST-OF-N)</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">94.2%</div>
          <div className="text-[10px] text-gray-500 mt-1">Evaluated over 120 run cassettes</div>
        </div>
        <div className="p-4 bg-gray-900 border border-gray-800 rounded-lg">
          <div className="text-xs text-gray-400">EXPORT FORMATS</div>
          <div className="text-sm font-bold text-purple-400 mt-2">SFT JSONL / DPO JSONL</div>
          <div className="text-[10px] text-gray-500 mt-1">
            Schema-valid trajectory training format
          </div>
        </div>
      </div>

      <div className="bg-gray-950 p-6 rounded-xl border border-gray-800 space-y-4">
        <h3 className="text-sm font-bold text-gray-300">EXPORT TRAJECTORY CASSETTES</h3>
        <p className="text-xs text-gray-400">
          Export recorded run steps and gate reports to fine-tune open-weights models for SAGIHA
          microkernel tasks.
        </p>

        <div className="flex gap-4 pt-2">
          <Button variant="primary" size="sm" onClick={() => {}}>
            📦 EXPORT SFT DATASET (JSONL)
          </Button>
          <Button variant="secondary" size="sm" onClick={() => {}}>
            ⚖️ EXPORT DPO DATASET (JSONL)
          </Button>
        </div>
      </div>
    </div>
  );
};
