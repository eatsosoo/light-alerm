"""Bounded TCP operations; alarm scheduling belongs to AlarmService."""

import asyncio
import logging
from contextlib import asynccontextmanager

from light_alarm.devices.protocol import MIN_PACKET_INTERVAL

logger = logging.getLogger(__name__)


class DeviceConnectionError(ConnectionError):
    """An expected device connection failure with an actionable message."""


class PacketPacer:
    """Enforce the manufacturer's 200 ms packet gap across endpoint connections."""

    def __init__(self):
        self._locks = {}
        self._next_write = {}

    async def write(self, endpoint, writer, command, timeout):
        lock = self._locks.setdefault(endpoint, asyncio.Lock())
        async with lock:
            loop = asyncio.get_running_loop()
            remaining = self._next_write.get(endpoint, 0) - loop.time()
            while remaining > 0:
                await asyncio.sleep(remaining)
                remaining = self._next_write.get(endpoint, 0) - loop.time()
            started = loop.time()
            writer.write(command)
            try:
                await asyncio.wait_for(writer.drain(), timeout)
            finally:
                self._next_write[endpoint] = loop.time() + MIN_PACKET_INTERVAL
            return started


class DeviceConnection:
    def __init__(self, reader, writer, endpoint, timeout, pacer):
        self.reader = reader
        self.writer = writer
        self.endpoint = endpoint
        self.timeout = timeout
        self.pacer = pacer

    async def write(self, hex_command):
        return await self.pacer.write(self.endpoint, self.writer, bytes.fromhex(hex_command), self.timeout)

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
    def __init__(self, settings, pacer=None):
        self.connect_timeout = settings.connect_timeout
        self.response_timeout = settings.response_timeout
        self.pacer = pacer if pacer is not None else PacketPacer()

    @asynccontextmanager
    async def connection(self, ip, port):
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, int(port)), self.connect_timeout,
            )
        except asyncio.TimeoutError as error:
            raise DeviceConnectionError(
                f"Không kết nối được tới {ip}:{port} sau {self.connect_timeout:g} giây. "
                "Kiểm tra IP, port, nguồn thiết bị và kết nối mạng."
            ) from error
        except OSError as error:
            raise DeviceConnectionError(f"Không mở được kết nối tới {ip}:{port}: {error}") from error
        try:
            yield DeviceConnection(reader, writer, (ip, int(port)), self.connect_timeout, self.pacer)
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
