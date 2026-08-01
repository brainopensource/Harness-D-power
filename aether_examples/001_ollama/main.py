# main.py
from task_queue import TaskQueue
from event_bus import EventBus
import asyncio

class Event:
    pass

def create_task(event_bus):
    async def task():
        await asyncio.sleep(1)
        event = Event()
        await event_bus.publish('task_completed', event)
    return task

event_bus = EventBus()
task_queue = TaskQueue()
task_queue.add_task(create_task(event_bus))
asyncio.run(task_queue.worker())
