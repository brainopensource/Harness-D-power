# **Native Async Microkernel & Event Bus**

> [!NOTE]
> **Working Proposal Disclaimer**: This document represents a working architectural proposal for SAGIHA2 and will be iteratively refined as practical evaluations progress.

## **Overview**
The core orchestration engine is a lightweight, deterministic `AsyncStateMachine` event-bus microkernel implemented in Python 3.12+.

## **Key Design Features**
* **Zero Framework Lock-in**: Fully decoupled from external agent frameworks; LangGraph or Microsoft Agent Framework are supported strictly as optional external adapters.
* **Event-Stream Orchestration**: Non-blocking asynchronous event bus with step checkpointing, time-travel state recovery, and OpenTelemetry instrumentation.
* **Deterministic Execution**: Keeps state transitions, budget evaluation, and step dispatch strictly reproducible and observable.
