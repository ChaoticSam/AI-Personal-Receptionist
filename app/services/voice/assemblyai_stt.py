import asyncio
import contextlib
import json
import os
from typing import AsyncIterator, Optional
from urllib.parse import urlencode

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

from app.services.voice.events import STTChunkEvent, STTEvent, STTOutputEvent


class AssemblyAISTT:
    def __init__(
        self,
        api_key: Optional[str] = None,
        sample_rate: int = 16000,
        format_turns: bool = True,
    ):
        self.api_key = api_key or os.getenv("ASSEMBLYAI_API_KEY")
        if not self.api_key:
            raise ValueError("AssemblyAI API key is required")

        self.sample_rate = sample_rate
        self.format_turns = format_turns
        self._ws: Optional[ClientConnection] = None
        self._connection_signal = asyncio.Event()
        self._close_signal = asyncio.Event()

    async def receive_events(self) -> AsyncIterator[STTEvent]:
        while not self._close_signal.is_set():
            _, pending = await asyncio.wait(
                [
                    asyncio.create_task(self._close_signal.wait()),
                    asyncio.create_task(self._connection_signal.wait()),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            with contextlib.suppress(asyncio.CancelledError):
                for task in pending:
                    task.cancel()

            if self._close_signal.is_set():
                break

            if self._ws is not None:
                self._connection_signal.clear()
                try:
                    async for raw_message in self._ws:
                        try:
                            message = json.loads(raw_message)
                            msg_type = message.get("type")
                            if msg_type == "Turn":
                                transcript = message.get("transcript", "")
                                if message.get("turn_is_formatted"):
                                    if transcript:
                                        yield STTOutputEvent.create(transcript)
                                else:
                                    yield STTChunkEvent.create(transcript)
                        except json.JSONDecodeError:
                            continue
                except ConnectionClosed:
                    pass

    async def send_audio(self, audio_chunk: bytes) -> None:
        ws = await self._ensure_connection()
        await ws.send(audio_chunk)

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
        self._close_signal.set()

    async def _ensure_connection(self) -> ClientConnection:
        if self._close_signal.is_set():
            raise RuntimeError("AssemblyAISTT: connection closed")
        if self._ws is not None:
            return self._ws

        params = urlencode({
            "sample_rate": self.sample_rate,
            "format_turns": str(self.format_turns).lower(),
        })
        url = f"wss://streaming.assemblyai.com/v3/ws?{params}"
        self._ws = await connect(url, additional_headers={"Authorization": self.api_key})
        self._connection_signal.set()
        return self._ws
