"""Packet spacing is verified with fake writers, without TCP connections."""

import asyncio
import unittest

from light_alarm.devices.ch9120_client import PacketPacer
from light_alarm.devices.protocol import MIN_PACKET_INTERVAL


class PacketPacingTests(unittest.IsolatedAsyncioTestCase):
    async def test_packet_gap_applies_across_connections_to_same_endpoint(self):
        writes = []

        class Writer:
            def write(self, command):
                writes.append(asyncio.get_running_loop().time())

            async def drain(self):
                pass

        pacer = PacketPacer()
        endpoint = ("fake", 6800)
        await pacer.write(endpoint, Writer(), b"\x01", 1)
        await pacer.write(endpoint, Writer(), b"\x00", 1)
        self.assertGreaterEqual(writes[1] - writes[0], MIN_PACKET_INTERVAL)

    async def test_different_devices_do_not_share_packet_deadline(self):
        writes = []

        class Writer:
            def write(self, command):
                writes.append(asyncio.get_running_loop().time())

            async def drain(self):
                pass

        pacer = PacketPacer()
        await pacer.write(("fake-a", 6800), Writer(), b"\x01", 1)
        self.assertNotIn(("fake-b", 6800), pacer._next_write)
        await pacer.write(("fake-b", 6800), Writer(), b"\x01", 1)
        self.assertEqual(len(writes), 2)
