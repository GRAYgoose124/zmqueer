from abc import ABC, abstractmethod
import zmq.asyncio
import asyncio
import logging


class Peer(ABC):
    def __init__(self, address, log_to=None, log_level=logging.INFO):
        # Peer setup
        self.address = address
        self._done = False
        self._tasks = []

        # ZMQ / asyncio setup
        self.loop = asyncio.get_event_loop()
        self.ctx = zmq.asyncio.Context()
        self.pub_socket = self.ctx.socket(zmq.PUB)
        self.sub_socket = self.ctx.socket(zmq.SUB)
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        self.message_types = {}

        # Logging setup
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.propagate = False

        handler = None
        if log_to == "file":
            handler = logging.FileHandler(f"logs/{self.address[6:]}.log")
        elif log_to == "stdout":
            handler = logging.StreamHandler()

        if handler is not None and log_level is not None:
            handler.setLevel(log_level)
            handler.addFilter(logging.Filter(self.__class__.__name__))
            handler.setFormatter(
                logging.Formatter("%(filename)s:%(lineno)d>\t%(message)s")
            )
            self.logger.addHandler(handler)

        self.__post_init__()

    def __post_init__(self):
        pass

    @abstractmethod
    async def broadcast_loop(self):
        pass

    async def broadcast(self, type: str, message: str):
        packet = f"{type}={message}"
        await self.pub_socket.send_string(packet)
        self.logger.debug(f"{self.address}:\n\tSent message: {packet}")

    @property
    def tasks(self) -> list[asyncio.Task]:
        return self._tasks

    @property
    def done(self) -> bool:
        return self._done

    @property
    def peers(self) -> list["Peer"]:
        return [self.address] + list(self.group.keys())

    @property
    def types(self) -> list[str]:
        return self.message_types.keys()

    def register_message_type(self, message_type, handler, overwrite=False):
        if message_type not in self.message_types or overwrite:
            self.message_types[message_type] = [handler]
        else:
            self.message_types[message_type].append(handler)

        self.logger.debug(
            f"Registered message type: {message_type}, {handler.__class__.__name__} {overwrite=}"
        )

    async def message_type_handler(self, message):
        for message_type, handlers in self.message_types.items():
            if message.startswith(f"{message_type}="):
                received_data = message[len(message_type) + 1 :]
                self.logger.debug(
                    f"Received PACKET: {message_type}={received_data}, {handlers=}"
                )
                # TODO: can gather this?
                for handler in handlers:
                    await handler(self, received_data)

    async def recv_loop(self):
        while not self.done:
            try:
                message = await self.sub_socket.recv_string()

                await self.message_type_handler(message)
            except Exception as e:
                # traceback.print_exc()
                self.logger.error(
                    f"Error: {e}, {type(self)} {type(self.sub_socket)} {type(message)}, {type(self.sub_socket.recv_string)}"
                )

    def setup(self):
        self._done = False
        self.pub_socket.bind(self.address)
        self.sub_socket.connect(self.address)

        self._tasks = [
            self.loop.create_task(self.recv_loop()),
            self.loop.create_task(self.broadcast_loop()),
        ]

        return self._tasks

    async def teardown(self):
        self._done = True
        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks = []

        self.sub_socket.close()
        self.pub_socket.close()

    def __repr__(self):
        return f"<Peer {str(self)}>"

    def __str__(self):
        return self.address

    def __hash__(self):
        return hash(self.address)

    def __eq__(self, other):
        return self.address == other.address

    def __ne__(self, other):
        return self.address != other.address

    def __gt__(self, other):
        return int(self.address.split(":")[1]) > int(other.address.split(":")[1])

    def __lt__(self, other):
        return int(self.address.split(":")[1]) < int(other.address.split(":")[1])
