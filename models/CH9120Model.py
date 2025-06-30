import asyncio
from configs.config import Config
from services.CH9120Services import CH9120Services
from services.LoggerService import setup_logger

logger = setup_logger()
CH9120_COMMANDS = Config.get_commands()

class CH9120Model:
    @staticmethod
    def get_lines():
        conn = Config.get_db_connection()
        cursor = conn.cursor()
        query = "SELECT DISTINCT line FROM dbo.dv_warning_light_devices"
        cursor.execute(query)
        lines = cursor.fetchall()
        result = [dict(zip([column[0] for column in cursor.description], line)) for line in lines]
        conn.close()
        return result
    @staticmethod
    def create(user_code_created, station_name, ip, port, line, remark):
        conn = Config.get_db_connection()
        cursor = conn.cursor()
        query = """
        INSERT INTO dbo.dv_warning_light_devices (user_code_created, station_name, ip, port, line, remark)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor.execute(query, (user_code_created, station_name, ip, port, line, remark))
        conn.commit()
        conn.close()
        
    @staticmethod
    def update(keyid, user_code_updated, station_name, ip, port, line, remark):
        conn = Config.get_db_connection()
        cursor = conn.cursor()
        query = """
        UPDATE dbo.dv_warning_light_devices
        SET user_code_updated = ?, station_name = ?, ip = ?, port = ?, line = ?, remark = ?, updated = GETDATE()
        WHERE keyid = ?
        """
        cursor.execute(query, (user_code_updated, station_name, ip, port, line, remark, keyid))
        conn.commit()
        conn.close()
    
    @staticmethod
    def delete(keyid):
        conn = Config.get_db_connection()
        cursor = conn.cursor()
        query = "DELETE FROM dbo.dv_warning_light_devices WHERE keyid = ?"
        cursor.execute(query, (keyid,))
        conn.commit()
        conn.close()
        
    @staticmethod
    def get_by_id(keyid):
        conn = Config.get_db_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM dbo.dv_warning_light_devices WHERE keyid = ?"
        cursor.execute(query, (keyid,))
        devices = cursor.fetchone()
        result = [dict(zip([column[0] for column in cursor.description], device)) for device in devices]
        return result

    @staticmethod
    def get_by_line(line):
        conn = Config.get_db_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM dbo.dv_warning_light_devices WHERE line = ?"
        cursor.execute(query, (line,))
        devices = cursor.fetchall()
        result = [dict(zip([column[0] for column in cursor.description], device)) for device in devices]
        return result

    @staticmethod
    def get_all():
        conn = Config.get_db_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM dbo.dv_warning_light_devices"
        cursor.execute(query)
        devices = cursor.fetchall()
        conn.close()
        result = [dict(zip([column[0] for column in cursor.description], device)) for device in devices]
        return result
    
    @staticmethod
    async def send_command_to_all(hex_command, duration):
        try:
            devices = CH9120Model.get_all()
            tasks = []

            logger.info(f"[COMMAND START] Sending command to {len(devices)} device(s)...")

            for device in devices:
                service = CH9120Services(device['ip'], device['port'])
                task = asyncio.create_task(service.send_command(hex_command, duration))
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            success_count = 0
            failure_count = 0

            for i, result in enumerate(results):
                dev = devices[i]
                identity = f"{dev['station_name']} ({dev['ip']}:{dev['port']})"

                if isinstance(result, Exception):
                    logger.error(f"[{identity}] Error: {result}")
                    failure_count += 1
                elif result.get("status") == "success":
                    logger.info(f"[{identity}] Success")
                    success_count += 1
                else:
                    logger.warning(f"[{identity}] Unknown response: {result}")
                    failure_count += 1

            logger.info(f"[COMMAND SUMMARY] {success_count}/{len(devices)} success, {failure_count} failure(s).")

            return success_count > 0

        except Exception as e:
            logger.exception(f"[COMMAND ERROR] send_command_to_all() failed: {e}")
            return False

    
    @staticmethod
    async def send_command_by_line(line, mode, duration):
        try:
            hex_command = CH9120_COMMANDS[mode]
            devices = CH9120Model.get_by_line(line)
            tasks = []

            logger.info(f"[LINE {line}] Sending command '{mode}' to {len(devices)} device(s)...")

            for device in devices:
                service = CH9120Services(device['ip'], device['port'])
                task = asyncio.create_task(service.send_command(hex_command, duration))
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            success_count = 0
            failure_count = 0

            for i, result in enumerate(results):
                dev = devices[i]
                identity = f"{dev['station_name']} ({dev['ip']}:{dev['port']})"

                if isinstance(result, Exception):
                    logger.error(f"[{identity}] Exception: {result}")
                    failure_count += 1
                elif result.get("status") == "success":
                    logger.info(f"[{identity}] Success")
                    success_count += 1
                else:
                    logger.warning(f"[{identity}] Unexpected result: {result}")
                    failure_count += 1

            logger.info(f"[LINE {line} SUMMARY] {success_count}/{len(devices)} success, {failure_count} failure(s).")

            return success_count == len(devices)

        except Exception as e:
            logger.exception(f"[LINE {line} ERROR] send_command_by_line() failed: {e}")
            return False

       
            
