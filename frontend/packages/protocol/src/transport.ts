/**
 * The transport seam — see docs/frontend/architecture.md "The Transport Seam: EventSource".
 * Implemented by @sagiha/mock-engine during the mocked phase, and later by
 * packages/transport-live's RealEventSource (FE-7) over SSE/ndjson. No component in apps/cli or
 * apps/gui may import a concrete EventSource implementation directly — only this interface.
 */
import type { TaskSpec } from "./domain.js";
import type { SagihaEvent } from "./events.js";

export type Unsubscribe = () => void;

export interface EventSource {
  /** Subscribe to a run's event stream. Mirrors Orchestrator.execute()'s AsyncIterator<Event>. */
  subscribe(runId: string, onEvent: (event: SagihaEvent) => void): Unsubscribe;

  /** Submit a new task. Mirrors the TaskSpec-in side of the headless entry point. */
  submitTask(task: TaskSpec): Promise<{ runId: string }>;

  /** Resolve a pending ApprovalRequested. Mirrors the CLI's rendering of that event as a decision. */
  resolveApproval(runId: string, callId: string, approved: boolean, note?: string): Promise<void>;

  /** Resume from a step (mirrors SSE `?since=<step_id>` resumability). */
  subscribeSince(
    runId: string,
    sinceStepId: string,
    onEvent: (event: SagihaEvent) => void,
  ): Unsubscribe;
}
