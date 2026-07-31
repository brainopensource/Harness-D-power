import { spawn, ChildProcess } from "node:child_process";
import { useHarnessStore, LogEntry } from "./store.js";
import { TrajectoryStep, GateReport } from "./domain.js";

export interface RunOptions {
  goal: string;
  mode?: "live" | "replay" | "record" | undefined;
  modelName?: string | undefined;
  baseUrl?: string | undefined;
  acceptance?: string[] | undefined;
  workspace?: string | undefined;
  cassette?: string | undefined;
}

export class SagihaBackendBridge {
  private currentProcess: ChildProcess | null = null;

  /**
   * Run a real SAGIHA backend coding task and stream execution events into useHarnessStore.
   */
  public runTask(options: RunOptions): Promise<{ success: boolean; runId?: string | undefined }> {
    const {
      goal,
      mode = "live",
      modelName = "qwen2.5-coder:7b",
      baseUrl = "http://localhost:11434/v1",
      acceptance = [],
      workspace = ".",
      cassette,
    } = options;

    const store = useHarnessStore.getState();
    store.setStatus("running");

    store.addLog({
      id: `bridge-start-${Date.now()}`,
      timestamp: new Date().toISOString(),
      level: "info",
      message: `Spawning Python SAGIHA kernel: goal="${goal}" [mode=${mode}]`,
      source: "bridge",
    });

    const args = [
      "run",
      "sagiha",
      "run",
      goal,
      "--mode",
      mode,
      "--model-name",
      modelName,
      "--base-url",
      baseUrl,
      "--workspace",
      workspace,
      "--stream-json",
    ];

    if (cassette) {
      args.push("--cassette", cassette);
    }

    for (const check of acceptance) {
      args.push("-a", check);
    }

    return new Promise((resolve) => {
      let runId: string | undefined = undefined;
      let admitted = false;

      try {
        const proc = spawn("uv", args, {
          cwd: process.cwd(),
          env: process.env,
        });

        this.currentProcess = proc;

        let buffer = "";

        proc.stdout.on("data", (chunk: Buffer) => {
          buffer += chunk.toString("utf8");
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;

            if (trimmed.startsWith('{"type": "EVENT"')) {
              try {
                const parsed = JSON.parse(trimmed);
                this.handlePythonEvent(parsed);
                if (parsed.data?.run_id) {
                  runId = parsed.data.run_id;
                }
              } catch (e) {
                // Ignore parse errors
              }
            } else if (trimmed.startsWith("run_id=")) {
              runId = trimmed.split("=")[1];
            } else if (trimmed.startsWith("admitted=")) {
              admitted = trimmed.split("=")[1] === "True";
            }
          }
        });

        proc.stderr.on("data", (chunk: Buffer) => {
          const text = chunk.toString("utf8").trim();
          if (text) {
            store.addLog({
              id: `err-${Date.now()}`,
              timestamp: new Date().toISOString(),
              level: text.includes("Traceback") || text.includes("Error") ? "error" : "info",
              message: text.slice(0, 300),
              source: "python-stderr",
            });
          }
        });

        proc.on("close", (code) => {
          this.currentProcess = null;
          const finalStatus = code === 0 ? "idle" : "error";
          store.setStatus(finalStatus);

          store.addLog({
            id: `bridge-done-${Date.now()}`,
            timestamp: new Date().toISOString(),
            level: code === 0 ? "info" : "error",
            message: `SAGIHA process exited with code ${code} (admitted=${admitted})`,
            source: "bridge",
          });

          resolve({ success: code === 0, runId: runId ?? undefined });
        });

        proc.on("error", (err) => {
          this.currentProcess = null;
          store.setStatus("error");
          store.addLog({
            id: `bridge-err-${Date.now()}`,
            timestamp: new Date().toISOString(),
            level: "error",
            message: `Failed to spawn uv sagiha: ${err.message}`,
            source: "bridge",
          });
          resolve({ success: false, runId: undefined });
        });
      } catch (err: any) {
        store.setStatus("error");
        resolve({ success: false, runId: undefined });
      }
    });
  }

  private handlePythonEvent(parsed: { type: string; event?: string; data?: any }): void {
    const store = useHarnessStore.getState();
    const data = parsed.data || {};
    const eventName = parsed.event || data.event;

    if (eventName === "run.started") {
      store.setRunContext({
        run_id: data.run_id || "run-live",
        autonomy_level: data.run_context?.autonomy_level || "interactive",
        workspace_root: data.run_context?.workspace_root || ".",
        budget_remaining_usd: data.run_context?.budget_remaining_usd || 1.0,
      });
      store.addLog({
        id: `ev-${Date.now()}`,
        timestamp: data.timestamp || new Date().toISOString(),
        level: "info",
        message: `Run Started: ${data.task?.goal || "Coding task"}`,
        source: "kernel",
      });
    } else if (eventName === "step.completed" || eventName === "tool.execution_completed") {
      const step: TrajectoryStep = {
        step_id: data.step_id || { run_id: data.run_id, branch_id: "main", seq: store.steps.length + 1 },
        kind: "tool_execution",
        timestamp: data.timestamp || new Date().toISOString(),
        tool_name: data.tool_name || data.tool_call?.name || "run_command",
        arguments: data.arguments || data.tool_call?.arguments || {},
        output: data.output || data.result?.output || "",
        token_usage: data.token_usage || { prompt_tokens: 500, completion_tokens: 100, total_tokens: 600, cost_usd: 0.001 },
        tainted: Boolean(data.tainted || data.result?.tainted),
      };
      store.addStep(step);
    } else if (eventName === "compaction.applied") {
      store.addLog({
        id: `ev-${Date.now()}`,
        timestamp: data.timestamp || new Date().toISOString(),
        level: "info",
        message: `Compaction Applied: saved ${data.saved_tokens || 0} tokens`,
        source: "compactor",
      });
    } else if (eventName === "taint.introduced") {
      store.addLog({
        id: `ev-${Date.now()}`,
        timestamp: data.timestamp || new Date().toISOString(),
        level: "warn",
        message: `Taint Introduced from envelope: ${data.source_envelope || "untrusted source"}`,
        source: "taintgate",
      });
    } else if (eventName === "gate.evaluated") {
      if (data.gate_report) {
        store.setGateReport(data.gate_report as GateReport);
      }
      store.addLog({
        id: `ev-${Date.now()}`,
        timestamp: data.timestamp || new Date().toISOString(),
        level: data.gate_report?.admitted ? "info" : "warn",
        message: `Gate Evaluated: admitted=${data.gate_report?.admitted}`,
        source: "evaluator",
      });
    } else if (eventName === "run.completed") {
      store.addLog({
        id: `ev-${Date.now()}`,
        timestamp: data.timestamp || new Date().toISOString(),
        level: "info",
        message: `Run Completed: cost=$${data.cost?.usd?.toFixed(4) || "0.0000"}`,
        source: "kernel",
      });
    }
  }

  public kill(): void {
    if (this.currentProcess) {
      this.currentProcess.kill("SIGINT");
      this.currentProcess = null;
    }
  }
}

export const backendBridge = new SagihaBackendBridge();
