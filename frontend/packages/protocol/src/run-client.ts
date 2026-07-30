/**
 * RunClient: the shared, framework-agnostic state machine both cockpits fold the event stream
 * through. See docs/frontend/architecture.md "RunClient: The Shared State Machine". FE-2 only
 * folds RunStarted; later sprints extend handleEvent as the event taxonomy grows — this is
 * intentionally the one place per architecture.md that turns "a stream of events" into "the
 * current state of the world."
 */
import type { RunContext, TaskSpec } from "./domain.js";
import type { SagihaEvent } from "./events.js";
import type { EventSource, Unsubscribe } from "./transport.js";

export interface RunSnapshot {
  task: TaskSpec | null;
  runContext: RunContext | null;
  connectionStatus: "idle" | "connected";
}

type Listener = (snapshot: RunSnapshot) => void;

function initialSnapshot(): RunSnapshot {
  return { task: null, runContext: null, connectionStatus: "idle" };
}

export class RunClient {
  private snapshot: RunSnapshot = initialSnapshot();
  private readonly listeners = new Set<Listener>();
  private readonly unsubscribeTransport: Unsubscribe;

  constructor(eventSource: EventSource, runId: string) {
    this.unsubscribeTransport = eventSource.subscribe(runId, (event) => {
      this.handleEvent(event);
    });
  }

  getSnapshot(): RunSnapshot {
    return this.snapshot;
  }

  subscribe(listener: Listener): Unsubscribe {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  destroy(): void {
    this.unsubscribeTransport();
    this.listeners.clear();
  }

  private handleEvent(event: SagihaEvent): void {
    switch (event.event) {
      case "run.started": {
        this.snapshot = {
          task: event.task,
          runContext: event.run_context,
          connectionStatus: "connected",
        };
        this.notify();
        break;
      }
    }
  }

  private notify(): void {
    for (const listener of this.listeners) {
      listener(this.snapshot);
    }
  }
}
