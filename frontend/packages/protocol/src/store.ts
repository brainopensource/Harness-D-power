import { create } from "zustand";
import type { GateReport, RunContext, TrajectoryStep } from "./domain.js";

export type ConnectionState = "Connected" | "Reconnecting" | "Offline";
export type LogLevel = "info" | "warn" | "error" | "tool";

export interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
  source: string;
}

export interface SystemMetrics {
  cpuUsagePct: number;
  memoryMb: number;
}

export interface ControlCard {
  id: string;
  title: string;
  status: "active" | "idle" | "warning";
  description: string;
  lastRun?: string;
}

export type ProviderPreset = "ollama" | "openrouter" | "custom";

export interface ProviderConfig {
  providerPreset: ProviderPreset;
  modelName: string;
  baseUrl: string;
  apiKey?: string;
}

export interface HarnessState {
  connectionState: ConnectionState;
  systemMetrics: SystemMetrics;
  providerConfig: ProviderConfig;
  runContext: RunContext | null;
  status: "idle" | "running" | "frozen" | "tainted" | "error";
  steps: TrajectoryStep[];
  logs: LogEntry[];
  logFilter: "all" | LogLevel;
  activeTab: "logs" | "control";
  commandHistory: string[];
  controlCards: ControlCard[];
  latestGateReport: GateReport | null;
  isTainted: boolean;
  pendingApproval: { callId: string; envelope: string } | null;
  totalPromptTokens: number;
  totalCompletionTokens: number;
  totalCostUsd: number;

  // Actions
  setConnectionState: (state: ConnectionState) => void;
  setSystemMetrics: (metrics: SystemMetrics) => void;
  setProviderConfig: (config: ProviderConfig) => void;
  setRunContext: (ctx: RunContext) => void;
  setStatus: (status: HarnessState["status"]) => void;
  addStep: (step: TrajectoryStep) => void;
  addLog: (log: LogEntry) => void;
  setLogFilter: (filter: HarnessState["logFilter"]) => void;
  setActiveTab: (tab: HarnessState["activeTab"]) => void;
  addCommandToHistory: (cmd: string) => void;
  setGateReport: (report: GateReport) => void;
  setPendingApproval: (approval: { callId: string; envelope: string } | null) => void;
  resolveApproval: (approved: boolean) => void;
  toggleControlCard: (id: string) => void;
  reset: () => void;
}

const DEFAULT_CARDS: ControlCard[] = [
  { id: "evaluator", title: "Gate Evaluator Engine", status: "active", description: "Enforces tests_unmodified, diff bounds, and syntax safety." },
  { id: "taintgate", title: "TaintGate Isolation", status: "active", description: "Monotonic untrusted payload containment & mutation refusal." },
  { id: "compactor", title: "Exchange Compactor", status: "active", description: "Token-budgeted context compactor headroom management." },
  { id: "sandbox", title: "Podman Container Perimeter", status: "idle", description: "Rootless sandbox isolation & egress allowlist proxy." },
];

export const useHarnessStore = create<HarnessState>((set) => ({
  connectionState: "Connected",
  systemMetrics: { cpuUsagePct: 24, memoryMb: 182 },
  providerConfig: {
    providerPreset: "ollama",
    modelName: "qwen2.5-coder:7b",
    baseUrl: "http://localhost:11434/v1",
    apiKey: "",
  },
  runContext: null,
  status: "idle",
  steps: [],
  logs: [
    {
      id: "log-1",
      timestamp: new Date().toISOString(),
      level: "info",
      message: "SAGIHA Orchestration Kernel Initialized",
      source: "kernel",
    },
  ],
  logFilter: "all",
  activeTab: "logs",
  commandHistory: ["/status", "/logs --tail", "/help"],
  controlCards: DEFAULT_CARDS,
  latestGateReport: null,
  isTainted: false,
  pendingApproval: null,
  totalPromptTokens: 0,
  totalCompletionTokens: 0,
  totalCostUsd: 0,

  setConnectionState: (connectionState) => set({ connectionState }),
  setSystemMetrics: (systemMetrics) => set({ systemMetrics }),
  setProviderConfig: (providerConfig) => set({ providerConfig }),
  setRunContext: (ctx) => set({ runContext: ctx }),
  setStatus: (status) => set({ status }),
  addStep: (step) =>
    set((state) => {
      const newLog: LogEntry = {
        id: `log-step-${step.step_id.seq}`,
        timestamp: step.timestamp,
        level: step.error ? "error" : step.tainted ? "warn" : "tool",
        message: `[${step.tool_name || step.kind}] ${JSON.stringify(step.arguments || {})}`,
        source: "dispatch",
      };
      return {
        steps: [...state.steps, step],
        logs: [newLog, ...state.logs].slice(0, 100),
        totalPromptTokens: state.totalPromptTokens + (step.token_usage?.prompt_tokens || 0),
        totalCompletionTokens:
          state.totalCompletionTokens + (step.token_usage?.completion_tokens || 0),
        totalCostUsd: state.totalCostUsd + (step.token_usage?.cost_usd || 0),
        isTainted: state.isTainted || Boolean(step.tainted),
      };
    }),
  addLog: (log) => set((state) => ({ logs: [log, ...state.logs].slice(0, 100) })),
  setLogFilter: (logFilter) => set({ logFilter }),
  setActiveTab: (activeTab) => set({ activeTab }),
  addCommandToHistory: (cmd) => set((state) => ({ commandHistory: [cmd, ...state.commandHistory] })),
  setGateReport: (report) => set({ latestGateReport: report }),
  setPendingApproval: (approval) => set({ pendingApproval: approval }),
  resolveApproval: (_approved) => set({ pendingApproval: null }),
  toggleControlCard: (id) =>
    set((state) => ({
      controlCards: state.controlCards.map((card) =>
        card.id === id
          ? { ...card, status: card.status === "active" ? "idle" : "active" }
          : card,
      ),
    })),
  reset: () =>
    set({
      connectionState: "Connected",
      systemMetrics: { cpuUsagePct: 15, memoryMb: 140 },
      runContext: null,
      status: "idle",
      steps: [],
      logs: [],
      logFilter: "all",
      activeTab: "logs",
      commandHistory: [],
      controlCards: DEFAULT_CARDS,
      latestGateReport: null,
      isTainted: false,
      pendingApproval: null,
      totalPromptTokens: 0,
      totalCompletionTokens: 0,
      totalCostUsd: 0,
    }),
}));

