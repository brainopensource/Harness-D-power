import { create } from "zustand";
import type { GateReport, RunContext, TrajectoryStep } from "./domain.js";

export interface HarnessState {
  runContext: RunContext | null;
  status: "idle" | "running" | "frozen" | "tainted" | "error";
  steps: TrajectoryStep[];
  latestGateReport: GateReport | null;
  isTainted: boolean;
  pendingApproval: { callId: string; envelope: string } | null;
  totalPromptTokens: number;
  totalCompletionTokens: number;
  totalCostUsd: number;

  // Actions
  setRunContext: (ctx: RunContext) => void;
  setStatus: (status: HarnessState["status"]) => void;
  addStep: (step: TrajectoryStep) => void;
  setGateReport: (report: GateReport) => void;
  setPendingApproval: (approval: { callId: string; envelope: string } | null) => void;
  resolveApproval: (approved: boolean) => void;
  reset: () => void;
}

export const useHarnessStore = create<HarnessState>((set) => ({
  runContext: null,
  status: "idle",
  steps: [],
  latestGateReport: null,
  isTainted: false,
  pendingApproval: null,
  totalPromptTokens: 0,
  totalCompletionTokens: 0,
  totalCostUsd: 0,

  setRunContext: (ctx) => set({ runContext: ctx }),
  setStatus: (status) => set({ status }),
  addStep: (step) =>
    set((state) => ({
      steps: [...state.steps, step],
      totalPromptTokens: state.totalPromptTokens + (step.token_usage?.prompt_tokens || 0),
      totalCompletionTokens:
        state.totalCompletionTokens + (step.token_usage?.completion_tokens || 0),
      totalCostUsd: state.totalCostUsd + (step.token_usage?.cost_usd || 0),
      isTainted: state.isTainted || Boolean(step.tainted),
    })),
  setGateReport: (report) => set({ latestGateReport: report }),
  setPendingApproval: (approval) => set({ pendingApproval: approval }),
  resolveApproval: (_approved) => set({ pendingApproval: null }),
  reset: () =>
    set({
      runContext: null,
      status: "idle",
      steps: [],
      latestGateReport: null,
      isTainted: false,
      pendingApproval: null,
      totalPromptTokens: 0,
      totalCompletionTokens: 0,
      totalCostUsd: 0,
    }),
}));
