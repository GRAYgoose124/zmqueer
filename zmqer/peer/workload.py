from abc import abstractmethod, ABCMeta
import json
from typing import Any

from . import GroupPeer

from pydantic import BaseModel


class WorkloadPeer(GroupPeer, metaclass=ABCMeta):
    def register_message_type(self, message_type, handler, overwrite=False):
        self.__workload_type = message_type
        return super().register_message_type(message_type, handler, overwrite)

    @abstractmethod
    def handle_work(self, data: str):
        """Handle the workload"""
        pass

    @abstractmethod
    async def workload_wrapper(self) -> str:
        """Produce the workload"""
        pass

    async def broadcast_loop(self):
        """Broadcast the workload"""
        while not self.done:
            try:
                # TODO: multiple workloads so we can register and run awaitables
                data = await getattr(self, "workload_wrapper")()
                await self.broadcast(self.__workload_type, data)
            except Exception as e:
                self.logger.error(f"Error: {e}")
