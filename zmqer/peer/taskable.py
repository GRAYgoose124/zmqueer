from abc import abstractmethod
import asyncio
import json
from random import randint
import random
import time
from typing import Any

from .json import JsonPeer

# Note the usage of tasks here refers to taskable peer abilities, not asyncio tasks.


class TaskablePeer(JsonPeer):
    OLD_TASK_THRESHOLD = 30.0

    def __init__(self, *args, group_broadcast_delay=5, **kwargs):
        self.abilities = {}
        self.queue = []
        super().__init__(*args, group_broadcast_delay=group_broadcast_delay, **kwargs)

    def register_ability(self, task: str, handler, overwrite=False):
        """Register a task"""
        if task not in self.abilities or overwrite:
            self.abilities[task] = [handler]
        else:
            self.abilities[task].append(handler)

    def do_abilities(self, data: dict[str, Any]):
        """Complete tasks"""
        todo_abilities = data["todo"].split(";")

        for ability in todo_abilities:
            if data["todo"] in self.abilities:
                for handler in self.abilities[ability]:
                    handler(self, data)
            else:
                self.logger.error(f"Task {ability} not registered")

        data["status"] = "complete"
        data["results"] = f"Task completed by {self.address}"
        self.logger.debug(f"Task completed by {self.address}")

        return data

    def remove_from_queue(self, data: dict[str, Any]):
        """Remove a task from the queue"""
        # TODO: UUIDs
        times = enumerate([task["time"] for task in self.queue])
        for i, t in times:
            if t == data["time"]:
                ignored = self.queue.pop(i)
                self.logger.debug(f"Removed task {ignored} from queue")
                break

    def append_to_queue(self, data: dict[str, Any]):
        """Append a task to the queue"""
        # if it's not already in the queue
        times = enumerate([task["time"] for task in self.queue])
        for i, t in times:
            if t == data["time"]:
                return

        self.queue.append(data)

    @abstractmethod
    def handle_completed_task(self, data: dict[str, Any]):
        """Handle a completed task"""
        pass

    def handle_work(self, data: dict[str, Any]):
        """Handle the workload"""
        # Ignore self-broadcasts
        if (
            data["sender"] == self.address
            and data["priority"] != self.address
            and data["status"] != "complete"
        ):
            return

        # Complete old tasks not completed by the priority peer
        if data["status"] != "complete":
            if (
                data["status"] == "pending"
                and data["time"] < time.time() - TaskablePeer.OLD_TASK_THRESHOLD
            ):
                data = self.do_abilities(data)
            # If a priority address is given, then that address is the only one that can complete the task.
            # Otherwise, any peer can complete the task.
            elif data["priority"] is None or data["priority"] == self.address:
                data = self.do_abilities(data)
            else:
                data["status"] = "pending"
                self.append_to_queue(data)

        if data["status"] == "complete":
            self.remove_from_queue(data)

            if data["sender"] == self.address:
                return self.handle_completed_task(data)
            else:
                # TODO: SENDER NEEDS TO ACKNOWLEDGE THE COMPLETION
                # This is a rebroadcast to bounce the results back to the sender.
                # We need to invalidate this bounce when the sender receives the results.
                return data

        # broadcast the results
        # await self.broadcast("COMPLETE", json.dumps(data))

    async def workload_wrapper(self) -> str:
        # Let it be known that this sleep is kinda freaking important.
        # We need some sort of async load balancing between processing requests and working on tasks.
        # Without this sleep, suffice to say the peer will become completely unresponsive while working on a series of tasks.
        await asyncio.sleep(random.uniform(0.5, 1))
        return await super().workload_wrapper()

    def workload(self) -> dict[str, Any]:
        data = super().workload()
        # get any peer in the group
        peer = list(self.group.keys())[randint(0, len(self.group) - 1)]

        if len(self.queue) > 0:
            data = self.queue[0]
            self.queue.remove(data)
        else:
            data.update(
                {
                    "sender": self.address,
                    "priority": peer,  # or None, if not given any Peer can complete the task and broadcast the results.
                    "todo": None,
                    "status": False,
                    "results": None,
                }
            )

        return data
