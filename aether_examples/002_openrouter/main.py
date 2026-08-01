# main.py
import asyncio
from task_queue import PriorityTaskQueue
from event_bus import AsyncEventBus

async def main():
    bus = AsyncEventBus()
    queue = PriorityTaskQueue(concurrency_limit=2)

    completed = []
    def on_complete(data):
        completed.append(data)
        print(f'[EVENT BUS] Completed task: {data}')

    bus.subscribe('task_done', on_complete)

    async def sample_task(task_id):
        await asyncio.sleep(0.1)
        await bus.publish('task_done', f'Task-{task_id}')

    await queue.start()
    for i in range(5):
        await queue.add_task(i, sample_task, i)

    await asyncio.sleep(1)
    print(f'Total completed: {len(completed)}')

if __name__ == '__main__':
    asyncio.run(main())
