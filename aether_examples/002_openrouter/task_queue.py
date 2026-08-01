# task_queue.py
import asyncio
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

class PriorityTaskQueue:
    def __init__(self, concurrency_limit: int = 3):
        self.queue = asyncio.PriorityQueue()
        self.concurrency_limit = concurrency_limit
        self.workers = []

    async def add_task(self, priority: int, task_func: Callable, *args, **kwargs):
        await self.queue.put((priority, task_func, args, kwargs))

    async def start(self):
        self.workers = [asyncio.create_task(self._worker()) for _ in range(self.concurrency_limit)]

    async def _worker(self):
        while True:
            priority, task_func, args, kwargs = await self.queue.get()
            try:
                await task_func(*args, **kwargs)
            except Exception as e:
                logger.error(f'Task execution failed: {e}')
            finally:
                self.queue.task_done()
