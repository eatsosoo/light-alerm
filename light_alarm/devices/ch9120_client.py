"""Bounded TCP operations; alarm scheduling belongs to AlarmService."""

import asyncio
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class DeviceConnection:
    def __init__(self, reader, writer, endpoint, timeout):
        self.reader = reader
        self.writer = writer
        self.endpoint = endpoint
        self.timeout = timeout

    async def write(self, hex_command):
        started = asyncio.get_running_loop().time()
        self.writer.write(bytes.fromhex(hex_command))
        await asyncio.wait_for(self.writer.drain(), self.timeout)
        return started

    async def read(self, timeout):
        if timeout <= 0:
            return ""
        try:
            response = await asyncio.wait_for(self.reader.read(1024), timeout)
        except asyncio.TimeoutError:
            logger.warning("No response received | endpoint=%s:%s", *self.endpoint)
            return ""
        if not response:
            logger.warning("Connection closed without a response | endpoint=%s:%s", *self.endpoint)
        return response.hex()


class CH9120Client:
    def __init__(self, settings):
        self.connect_timeout = settings.connect_timeout
        self.response_timeout = settings.response_timeout

    @asynccontextmanager
    async def connection(self, ip, port):
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, int(port)), self.connect_timeout,
        )
        try:
            yield DeviceConnection(reader, writer, (ip, port), self.connect_timeout)
        finally:
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), self.connect_timeout)
            except (OSError, asyncio.TimeoutError):
                logger.warning("Connection close failed | endpoint=%s:%s", ip, port)

    async def send_once(self, ip, port, hex_command):
        async with self.connection(ip, port) as connection:
            await connection.write(hex_command)
            return await connection.read(self.response_timeout)
