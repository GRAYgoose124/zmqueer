from abc import ABCMeta, abstractmethod
import asyncio
import json
import time
from random import randint
from typing import Any

from . import WorkloadPeer


# S/N: We don't need to explicitly state ABCMeta because the base Peer is an ABC.
class JsonPeer(WorkloadPeer, metaclass=ABCMeta):
    @staticmethod
    async def JSON_handler(peer: "JsonPeer", workload: str):
        """Parse json message"""
        try:
            data = json.loads(workload)

            results = peer.handle_work(data)
            if results is not None:
                await peer.broadcast("JSON", json.dumps(results))

        except json.JSONDecodeError as e:
            peer.logger.error(f"Error: {e}")

    def __post_init__(self):
        super().__post_init__()
        self.register_message_type("JSON", self.JSON_handler)

    @abstractmethod
    def workload(self) -> dict[str, Any]:
        output = {"time": time.time()}
        return output

    async def workload_wrapper(self) -> str:
        return json.dumps(getattr(self, "workload")())
