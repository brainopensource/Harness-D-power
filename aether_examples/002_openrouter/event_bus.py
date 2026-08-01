# event_bus.py
import asyncio
from typing import Callable, Dict, List, Any

class AsyncEventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def publish(self, event_type: str, data: Any):
        if event_type in self._subscribers:
            await asyncio.gather(*(handler(data) for handler in self._subscribers[event_type]))
