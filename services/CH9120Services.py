import asyncio
import logging
from configs.config import Config

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
            logging.error(f'Send command: {str(e)}')
            return {"status": "error", "response": str(e)}


