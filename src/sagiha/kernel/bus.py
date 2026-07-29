"""Asynchronous Event Bus & Interceptor System — see docs/02-architecture/event-bus-and-hooks.md."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Protocol

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
    """Async-first event bus supporting observers and interceptors."""

    def __init__(self, default_timeout_s: float = 5.0) -> None:
        self._observers: list[ObserverFunc] = []
        self._interceptors: dict[str, list[InterceptorFunc]] = {}
        self._default_timeout_s = default_timeout_s

    def subscribe_observer(self, observer: ObserverFunc | Observer) -> None:
        """Subscribe an observer function or object to all emitted events."""
        if callable(observer):
            self._observers.append(observer)
        else:
            self._observers.append(observer.on_event)

    def subscribe_interceptor(
        self, hook_point: str, interceptor: InterceptorFunc | Interceptor
    ) -> None:
        """Subscribe an interceptor function or object to a specific hook point."""
        if hook_point not in self._interceptors:
            self._interceptors[hook_point] = []

        if callable(interceptor):
            self._interceptors[hook_point].append(interceptor)
        else:
            self._interceptors[hook_point].append(interceptor.before)

    async def emit(self, event: Event) -> None:
        """Publish an event to all observers concurrently.

        Observer exceptions are caught and logged so an observer failure never aborts the run.
        """
        if not self._observers:
            return

        async def _safe_call(obs: ObserverFunc) -> None:
            try:
                await obs(event)
            except Exception as exc:
                logger.error(
                    "Observer error handling event %s: %s",
                    event.event,
                    exc,
                    exc_info=True,
                )

        await asyncio.gather(*[_safe_call(obs) for obs in self._observers])

    async def intercept(
        self, hook_point: str, event: Event, timeout_s: float | None = None
    ) -> Decision:
        """Run interceptors synchronously for a hook point.

        Fails closed (denies) if any interceptor returns a denial or times out.
        """
        interceptors = self._interceptors.get(hook_point, [])
        if not interceptors:
            return Decision(allowed=True, reason="No interceptors configured")

        effective_timeout = (
            timeout_s if timeout_s is not None else self._default_timeout_s
        )

        for interceptor in interceptors:
            try:
                decision = await asyncio.wait_for(
                    interceptor(event), timeout=effective_timeout
                )
                if not decision.allowed:
                    return decision
            except TimeoutError:
                return Decision(
                    allowed=False,
                    reason=f"Interceptor timed out after {effective_timeout}s on hook '{hook_point}'",
                )
            except Exception as exc:
                logger.error(
                    "Interceptor raised error on hook '%s': %s", hook_point, exc
                )
                return Decision(
                    allowed=False,
                    reason=f"Interceptor error on hook '{hook_point}': {exc}",
                )

        return Decision(
            allowed=True, reason=f"Passed {len(interceptors)} interceptors"
        )
