"""
AudioBuffer — async queue-based buffer for incoming audio chunks.

In the current MVP architecture, audio flows directly to Deepgram without
buffering. This module exists as a clean abstraction for future use cases
such as local VAD pre-processing or recording.
"""

import asyncio


class AudioBuffer:
    def __init__(self, maxsize: int = 0):
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=maxsize)
        self._total_bytes = 0

    async def push(self, chunk: bytes) -> None:
        self._total_bytes += len(chunk)
        await self._queue.put(chunk)

    async def pop(self) -> bytes | None:
        """Returns next chunk, or None sentinel when buffer is closed."""
        return await self._queue.get()

    def close(self) -> None:
        """Signal consumers that no more audio will arrive."""
        self._queue.put_nowait(None)

    @property
    def total_bytes(self) -> int:
        return self._total_bytes
