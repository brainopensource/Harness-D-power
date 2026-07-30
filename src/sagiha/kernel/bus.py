"""Asynchronous Event Bus & Interceptor System — see docs/02-architecture/event-bus-and-hooks.md."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Protocol

import anyio

from sagiha.domain.control import Decision
from sagiha.domain.events import Event

logger = logging.getLogger(__name__)


class Observer(Protocol):
    """Observer interface — runs after the fact, cannot influence execution."""

    async def on_event(self, event: Event) -> None: ...


class Interceptor(Protocol):
    """Interceptor interface — runs synchronously on critical path, can deny but not mutate."""

    async def before(self, event: Event) -> Decision: ...


ObserverFunc = Callable[[Event], Awaitable[None]]
InterceptorFunc = Callable[[Event], Awaitable[Decision]]


class EventBus:
    """Async-first event bus supporting observers and interceptors.

    Built on `anyio` structured concurrency (AGENTS.md), not raw `asyncio` primitives (D17):
    portable across the asyncio and trio backends `anyio` supports.
    """

    def __init__(self, default_timeout_s: float = 5.0, observer_timeout_s: float = 5.0) -> None:
        self._observers: list[ObserverFunc] = []
        self._interceptors: dict[str, list[InterceptorFunc]] = {}
        self._default_timeout_s = default_timeout_s
        self._observer_timeout_s = observer_timeout_s
        # Observers that raised or timed out are quarantined for the remainder of the run
        # (event-bus-and-hooks.md): a slow or broken observer must never be able to keep
        # slowing or breaking the run it is merely watching.
        self._quarantined: set[int] = set()

    def subscribe_observer(self, observer: ObserverFunc | Observer) -> None:
        """Subscribe an observer function or object to all emitted events."""
        if callable(observer):
            self._observers.append(observer)
        else:
            self._observers.append(observer.on_event)

    def subscribe_interceptor(self, hook_point: str, interceptor: InterceptorFunc | Interceptor) -> None:
        """Subscribe an interceptor function or object to a specific hook point."""
        if hook_point not in self._interceptors:
            self._interceptors[hook_point] = []

        if callable(interceptor):
            self._interceptors[hook_point].append(interceptor)
        else:
            self._interceptors[hook_point].append(interceptor.before)

    async def emit(self, event: Event) -> None:
        """Publish an event to all non-quarantined observers concurrently, with a hard timeout.

        An observer that raises or exceeds `observer_timeout_s` is logged and quarantined —
        it is never invoked again for the lifetime of this bus — but the run itself never fails
        because of it (D17).
        """
        active = [obs for obs in self._observers if id(obs) not in self._quarantined]
        if not active:
            return

        async def _safe_call(obs: ObserverFunc) -> None:
            try:
                with anyio.fail_after(self._observer_timeout_s):
                    await obs(event)
            except TimeoutError:
                logger.error(
                    "Observer timed out after %ss handling event %s; quarantining for the "
                    "remainder of the run",
                    self._observer_timeout_s,
                    event.event,
                )
                self._quarantined.add(id(obs))
            except Exception as exc:
                logger.error(
                    "Observer error handling event %s: %s; quarantining for the remainder of "
                    "the run",
                    event.event,
                    exc,
                    exc_info=True,
                )
                self._quarantined.add(id(obs))

        async with anyio.create_task_group() as tg:
            for obs in active:
                tg.start_soon(_safe_call, obs)

    async def intercept(self, hook_point: str, event: Event, timeout_s: float | None = None) -> Decision:
        """Run interceptors synchronously for a hook point.

        Fails closed (denies) if any interceptor returns a denial or times out.
        """
        interceptors = self._interceptors.get(hook_point, [])
        if not interceptors:
            return Decision(allowed=True, reason="No interceptors configured")

        effective_timeout = timeout_s if timeout_s is not None else self._default_timeout_s

        for interceptor in interceptors:
            try:
                with anyio.fail_after(effective_timeout):
                    decision = await interceptor(event)
                if not decision.allowed:
                    return decision
            except TimeoutError:
                return Decision(
                    allowed=False,
                    reason=f"Interceptor timed out after {effective_timeout}s on hook '{hook_point}'",
                )
            except Exception as exc:
                logger.error("Interceptor raised error on hook '%s': %s", hook_point, exc)
                return Decision(
                    allowed=False,
                    reason=f"Interceptor error on hook '{hook_point}': {exc}",
                )

        return Decision(allowed=True, reason=f"Passed {len(interceptors)} interceptors")
