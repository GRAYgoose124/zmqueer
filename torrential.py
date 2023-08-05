import asyncio
from enum import Enum
from pathlib import Path
from dataclasses import dataclass
import lzma


from zmqer.peer import TaskablePeer
from zmqer.misc import connect_all


@dataclass
class Package:
    """A package is an arbitrary file structure which is named and broadcastable through a packet stream."""

    name: str
    path: Path  # path is locally managed, but used for broadcasting the packet stream.

    def __post_init__(self):
        self.path: Path = Path(self.path)
        self._archive: Path = self.path.parent / f"{self.name}.tar.gz"
        # Allow the archive to be invalidated if the package is modified. We set this to true for first run, but you can change this if you know what you're doing.
        self.__can_invalidate_archive: bool = True
        self.__archive_needs_update: bool = False

    @property
    def archive(self):
        if self.__archive_needs_update() and self.__can_invalidate_archive:
            self.__update_archive()
            # This should only be enabled when we know there are no active transactions using Package.
            self.__can_invalidate_archive = False

        return self._archive

    def __update_archive(self):
        """Update the archive of the package."""
        # save it next to the package root as a tar.gz. We could stream, but this is more convenient.
        with open(self._archive, "wb") as archive:
            archive.write(lzma.compress(self.path.read_bytes()))

    def __check_archive_age(self) -> int:
        """Check the age of the archive in seconds."""
        return (self._archive.stat().st_mtime - self.path.stat().st_mtime).seconds

    def __archive_needs_update(self) -> bool:
        """Check if the archive needs updating by comparing the modified times of the archive and the package."""
        return self.__check_archive_age() > 0 or self.__archive_needs_update

    def stream_iter(self, chunk_size: int = 1024) -> bytes:
        """Return a byte stream of the package."""
        with open(self.archive, "rb") as archive:
            while True:
                chunk = archive.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    def __len__(self):
        """Return the size of the package in bytes."""
        return self.archive.stat().st_size


@dataclass
class Transaction:
    """A Transaction is a wrapper for a package which is being transmitted to a recipient from many peers."""

    class Status(Enum):
        """The status of a transaction."""

        not_started = 0
        pending = 1
        transmitting = 2
        complete = 3
        failed = 4

    status: Status = Status.not_started
    package: Package = None
    recipient: str = None
    providers: list[str] = None


class TorrentialPeer(TaskablePeer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transactions = {}

    async def broadcast(self, type: str, package: Package):
        # Create a new transaction and register it
        transaction = Transaction(
            status=Transaction.Status.pending,
            package=package,
            recipient=self.address,
            providers=[self.address],
        )
        self.transactions[package.name] = transaction

        # Start the transaction
        await self.start_transaction(transaction)

    async def start_transaction(self, transaction: Transaction):
        transaction.status = Transaction.Status.transmitting
        package_stream = transaction.package.stream_iter()

        for chunk in package_stream:
            packet = f"{transaction.package.name}={chunk}"
            await self.pub_socket.send_string(packet)
            self.logger.debug(f"{self.address}:\n\tSent message: {packet}")

        transaction.status = Transaction.Status.complete

    async def message_type_handler(self, message):
        package_name, chunk = message.split("=")
        if package_name not in self.transactions:
            package = Package(name=package_name, path=Path())
            self.transactions[package_name] = Transaction(
                status=Transaction.Status.pending,
                package=package,
                recipient=self.address,
                providers=[self.address],
            )
        transaction = self.transactions[package_name]
        transaction.status = Transaction.Status.transmitting
        transaction.package.path.write_bytes(chunk)

        if len(transaction.package) >= len(chunk):
            transaction.status = Transaction.Status.complete
        else:
            transaction.status = Transaction.Status.pending


def main():
    peers = [TorrentialPeer(f"tcp://localhost:{port})") for port in range(5555, 5565)]
    peers[0].packages = [Package(name="test", path=Path("tests"))]

    connect_all(peers)

    try:
        loop = asyncio.get_event_loop()
        fut = asyncio.gather(*[peer.run() for peer in peers])
        loop.run_until_complete(fut)
    except KeyboardInterrupt:
        print("Exiting...")
        fut.cancel()
        loop.run_until_complete(
            asyncio.gather(*(p.teardown() for p in peers), return_exceptions=True)
        )
    finally:
        loop.close()
