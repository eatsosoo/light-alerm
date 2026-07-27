import asyncio
from configs.config import Config
from services.LoggerService import setup_logger


logger = setup_logger(__name__)

class CH9120Services:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.commands = Config.get_commands()

    async def send_command(self, hex_command, duration):
        try:
            command = bytes.fromhex(hex_command)

            try:
                reader, writer = await asyncio.open_connection(self.ip, self.port)
            except (OSError, ConnectionRefusedError, asyncio.TimeoutError) as e:
                return {"status": "error", "response": str(e)}

            writer.write(command)
            await writer.drain()

            try:
                response = await asyncio.wait_for(reader.read(1024), timeout=5)
            except asyncio.TimeoutError:
                response = b''

            await asyncio.sleep(duration)

            turn_off_command = bytes.fromhex(self.commands['TURN_OFF'])
            writer.write(turn_off_command)
            await writer.drain()

            writer.close()
            await writer.wait_closed()

            return {"status": "success", "response": response.hex()}

        except Exception as e:
            logger.exception("Failed to send command to %s:%s: %s", self.ip, self.port, e)
            return {"status": "error", "response": str(e)}


