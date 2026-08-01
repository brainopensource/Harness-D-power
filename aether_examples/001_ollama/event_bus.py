# event_bus.py
import asyncio
from collections import defaultdict, deque

class EventBus:
    def __init__(self):
        self.subscribers = defaultdict(deque)

    async def publish(self, event_name, data):
        if event_name in self.subscribers:
            for callback in self.subscribers[event_name]:
                await callback(data)

    def subscribe(self, event_name, callback):
        self.subscribers[event_name].append(callback)
