"""Short-lived, process-local sharing of identical authorized news read work.

The durable qbus journal remains authoritative. No subscriptions, credentials or
news text persist here. The caller includes current rights and database identity
in the key; a revoked audience therefore cannot reuse an earlier grant's result.
"""
from __future__ import annotations

import asyncio
from collections import OrderedDict
from collections.abc import Callable


class SharedChangeReader:
    def __init__(self, *, ttl_seconds: float = 0.05, max_keys: int = 128, concurrency: int = 8):
        if ttl_seconds < 0 or max_keys < 1 or concurrency < 1:
            raise ValueError("invalid_shared_reader_bounds")
        self.ttl_seconds = ttl_seconds
        self.max_keys = max_keys
        self.concurrency = concurrency
        self._loop = None
        self._entries = OrderedDict()
        self._semaphore = None

    async def read(self, key: tuple, reader: Callable):
        loop = asyncio.get_running_loop()
        if self._loop is not loop:
            self._loop = loop
            self._entries = OrderedDict()
            self._semaphore = asyncio.Semaphore(self.concurrency)
        now = loop.time()
        cached = self._entries.get(key)
        if cached is not None:
            expires, task = cached
            if not task.done() or expires > now:
                self._entries.move_to_end(key)
                return await asyncio.shield(task)
            del self._entries[key]
        while len(self._entries) >= self.max_keys:
            done = next((k for k, (_, task) in self._entries.items() if task.done()), None)
            if done is not None:
                del self._entries[done]
                break
            # Backpressure on unique scopes; never accumulate unbounded tasks or
            # let a slow/cancelled subscriber cancel another reader's work.
            await asyncio.wait(
                [task for _, task in self._entries.values()],
                return_when=asyncio.FIRST_COMPLETED,
            )
        cached = self._entries.get(key)
        if cached is not None and (not cached[1].done() or cached[0] > loop.time()):
            return await asyncio.shield(cached[1])
        async def read_once():
            async with self._semaphore:
                return await asyncio.to_thread(reader)
        task = loop.create_task(read_once())
        self._entries[key] = (now + self.ttl_seconds, task)
        def finished(completed):
            if completed.cancelled():
                return
            error = completed.exception()  # retrieve even if every waiter left
            if error is not None and self._entries.get(key, (None, None))[1] is completed:
                self._entries.pop(key, None)
        task.add_done_callback(finished)
        return await asyncio.shield(task)


class BlockingReadPool:
    """Bound fresh blocking reads without caching an authorization decision.

    Capacity belongs to each submitted task until the actual read finishes.
    Cancelling a waiting stream cannot release its still-running thread slot.
    At most concurrency tasks are submitted per event loop; other callers wait
    before creating work.
    """

    def __init__(self, *, concurrency: int = 8):
        if concurrency < 1:
            raise ValueError("invalid_blocking_read_bound")
        self.concurrency = concurrency
        self._loop = None
        self._pending = set()

    async def read(self, reader: Callable):
        loop = asyncio.get_running_loop()
        if self._loop is not loop:
            self._loop = loop
            self._pending = set()
        pending = self._pending
        while len(pending) >= self.concurrency:
            await asyncio.wait(tuple(pending), return_when=asyncio.FIRST_COMPLETED)
        task = loop.create_task(asyncio.to_thread(reader))
        pending.add(task)

        def finished(completed):
            pending.discard(completed)
            if not completed.cancelled():
                completed.exception()  # retrieve even if the requesting stream left

        task.add_done_callback(finished)
        return await asyncio.shield(task)
