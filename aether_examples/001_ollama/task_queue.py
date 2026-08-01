# task_queue.py
import asyncio
from collections import deque
import time

class TaskQueue:
    def __init__(self, max_attempts=3):
        self.tasks = deque()
        self.max_attempts = max_attempts

    def add_task(self, task_func, *args, **kwargs):
        self.tasks.append((task_func, args, kwargs))

    async def worker(self):
        while self.tasks:
            task_func, args, kwargs = self.tasks.popleft()
            attempt = 0
            while attempt < self.max_attempts:
                try:
                    await task_func(*args, **kwargs)
                    break
                except Exception as e:
                    print(f'Task failed: {e}, retrying in {2**attempt} seconds')
                    time.sleep(2**attempt)
                    attempt += 1
