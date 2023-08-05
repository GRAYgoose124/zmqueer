import asyncio
from enum import Enum
from pathlib import Path
from dataclasses import dataclass
import lzma
import random
import tarfile
from typing import Any
import uuid
import logging
import os

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
        self.__force_archive_needs_update: bool = True
        self.__held_by: list[str] = []

    @property
    def archive(self):
        if self._archive_needs_update() and self.can_invalidate_archive:
            self._update_archive()

        return self._archive

    @property
    def can_invalidate_archive(self):
        """Set whether the archive can be invalidated."""
        self.__can_invalidate_archive = not self.__held_by

        return self.__can_invalidate_archive

    def _update_archive(self):
        """Update the archive of the package."""
        xz_file = lzma.LZMAFile(self._archive, "w")
        with tarfile.open(mode="w", fileobj=xz_file) as tar_xz_file:
            tar_xz_file.add(str(self.path.resolve()))

        xz_file.close()

        self.__force_archive_needs_update = False

    def _check_archive_age(self) -> int:
        """Check the age of the archive in seconds."""
        try:
            return (self._archive.stat().st_mtime - self.path.stat().st_mtime).seconds
        except FileNotFoundError:
            self.__force_archive_needs_update = True
            return 0

    def _archive_needs_update(self) -> bool:
        """Check if the archive needs updating by comparing the modified times of the archive and the package."""
        return self._check_archive_age() > 0 or self.__force_archive_needs_update

    def stream_iter(self, chunk_size: int = 1024) -> bytes:
        """Return a byte stream of the package."""
        self.__held_by.append("stream_iter")

        with open(self.archive, "rb") as archive:
            while True:
                chunk = archive.read(chunk_size)
                if not chunk:
                    break
                yield chunk

        self.__held_by.remove("stream_iter")

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

    ID: str = uuid.uuid4().hex
    status: Status = Status.not_started
    package: Package = None
    recipient: str = None
    providers: list[str] = None


class TorrentialPeer(TaskablePeer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transactions = {}

    async def start_transaction(self, transaction: Transaction):
        transaction.status = Transaction.Status.transmitting
        self.logger.info(
            f"Transaction {transaction.ID} started for package {transaction.package.name}"
        )
        package_stream = transaction.package.stream_iter()

        for chunk in package_stream:
            packet = f"{transaction.package.name}={chunk}"
            await self.pub_socket.send_string(packet)
            self.logger.debug(f"{self.address}:\n\tSent message: {packet}")

        transaction.status = Transaction.Status.complete
        self.logger.info(
            f"Transaction {transaction.ID} completed for package {transaction.package.name}"
        )

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
            self.logger.info(
                f"New transaction {self.transactions[package_name].ID} created for package {package_name}"
            )

        transaction = self.transactions[package_name]
        transaction.status = Transaction.Status.transmitting
        self.logger.info(
            f"Transaction {transaction.ID} started for package {transaction.package.name}"
        )
        transaction.package.path.write_bytes(chunk)

        if len(transaction.package) >= len(chunk):
            transaction.status = Transaction.Status.complete
            self.logger.info(
                f"Transaction {transaction.ID} completed for package {transaction.package.name}"
            )
        else:
            transaction.status = Transaction.Status.pending
            self.logger.info(
                f"Transaction {transaction.ID} still pending for package {transaction.package.name}"
            )

    def handle_completed_task(self, data: dict[str, Any]):
        print(f"Completed task, results: {data=}")


def main():
    logging.basicConfig(level=logging.DEBUG)

    if os.name == "nt":
        from asyncio import WindowsSelectorEventLoopPolicy

        asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

    start_port = 5555 + random.randint(0, 1000)
    peers = [
        TorrentialPeer(f"tcp://127.0.0.1:{port}")
        for port in range(start_port, start_port + 10)
    ]
    peers[0].packages = [Package(name="test", path=Path("tests"))]

    connect_all(peers)

    try:
        loop = asyncio.get_event_loop()

        tasks = set()
        for peer in peers:
            tasks.update(peer.setup())

        # add a custom start transaction task, providers must be part of the same group as recipient
        tasks.add(
            peers[0].start_transaction(
                Transaction(
                    package=Package(name="test", path=Path("./tests").resolve()),
                    providers=[peers[0].address],
                    recipient=peers[1].address,
                )
            )
        )

        fut = asyncio.gather(*tasks)
        loop.run_until_complete(fut)
    except KeyboardInterrupt:
        print("Exiting...")
        fut.cancel()
        loop.run_until_complete(
            asyncio.gather(*(p.teardown() for p in peers), return_exceptions=True)
        )
    finally:
        loop.close()


if __name__ == "__main__":
    main()
