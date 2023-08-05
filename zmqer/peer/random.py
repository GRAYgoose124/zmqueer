from random import randint
from typing import Any

from .json import JsonPeer
from .taskable import TaskablePeer


class RandomPeer(JsonPeer):
    # singleton class var for counter
    _counter = 0

    def handle_work(self, data: dict[str, Any]):
        """Handle the workload"""
        RandomPeer._counter += int(data["random"])
        print(f"GOT THAT RANDOM GOODNESS: {RandomPeer._counter}")

    def workload(self) -> dict[str, Any]:
        """Produces a random workload"""
        data = super().workload()
        data.update({"random": randint(1, 100)})

        return data


class RandomNetSeparatedPeer(JsonPeer):
    def __init__(self, *args, **kwargs):
        self._counter = 0
        super().__init__(*args, **kwargs)

    def handle_work(self, data: dict[str, Any]):
        """Handle the workload"""
        self._counter += int(data["random"])
        print(f"HAVE MY RANDOM GOODNESS: {self._counter}")

    def workload(self) -> dict[str, Any]:
        """Produces a random workload"""
        data = super().workload()
        data.update({"random": randint(1, 100)})

        return data


class RandomTaskablePeer(TaskablePeer):
    _counter = 0

    @staticmethod
    def ability(peer, data: dict[str, Any]):
        RandomTaskablePeer._counter += int(data["random"])
        print(
            f"{data['sender']} requested TaskablePeer.ability completed by {peer.address} on {data}\n\tResult: {RandomTaskablePeer._counter}"
        )

    def __post_init__(self):
        super().__post_init__()
        self.register_ability("print_ability", self.ability)

    def handle_completed_task(self, data: dict[str, Any]):
        print(f"Got my completed task back: {data}")

    def workload(self) -> dict[str, Any]:
        data = super().workload()
        data.update({"random": randint(1, 100)})

        data["todo"] = "print_ability"

        return data
