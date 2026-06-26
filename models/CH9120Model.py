import asyncio
from configs.config import Config
from services.CH9120Services import CH9120Services
from services.LoggerService import setup_logger

logger = setup_logger(__name__)
CH9120_COMMANDS = Config.get_commands()


def _device_label(device):
    station = device.get("station_name") or "Unknown station"
    ip = device.get("ip") or "unknown-ip"
    port = device.get("port") or "unknown-port"
    line = device.get("line") or "unknown-line"
    return f"station={station} | line={line} | endpoint={ip}:{port}"


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
        query = "SELECT * FROM dbo.dv_warning_light_devices WHERE line LIKE ?"
        cursor.execute(query, (f"%{line}%",))
        devices = cursor.fetchall()
        result = [dict(zip([column[0] for column in cursor.description], device)) for device in devices]
        return result
    
    @staticmethod
    def get_device_office():
        conn = Config.get_db_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM dbo.dv_warning_light_devices WHERE line = 'OFFICE'"
        cursor.execute(query)
        devices = cursor.fetchall()
        conn.close()
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
            time_duration = int(duration) if duration else 5

            logger.info(
                "Command started | scope=all | command_hex=%s | duration=%ss | devices=%s",
                hex_command,
                time_duration,
                len(devices),
            )

            for device in devices:
                service = CH9120Services(device['ip'], device['port'])
                task = asyncio.create_task(service.send_command(hex_command, time_duration))
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            success_count = 0
            failure_count = 0

            for i, result in enumerate(results):
                dev = devices[i]
                identity = _device_label(dev)

                if isinstance(result, Exception):
                    logger.error("Command failed | %s | error=%s", identity, result)
                    failure_count += 1
                elif result.get("status") == "success":
                    logger.info("Command succeeded | %s | response=%s", identity, result.get("response") or "-")
                    success_count += 1
                else:
                    logger.warning("Command returned unexpected response | %s | response=%s", identity, result)
                    failure_count += 1

            logger.info(
                "Command finished | scope=all | success=%s | failure=%s | total=%s",
                success_count,
                failure_count,
                len(devices),
            )

            return success_count > 0

        except Exception as e:
            logger.exception("Command failed before completion | scope=all | error=%s", e)
            return False

    
    @staticmethod
    async def send_command_by_line(line, mode, duration):
        try:
            hex_command = CH9120_COMMANDS[mode]
            devices = CH9120Model.get_by_line(line)
            tasks = []
            time_duration = int(duration) if duration else 5

            logger.info(
                "Command started | scope=line | line=%s | mode=%s | duration=%ss | devices=%s",
                line,
                mode,
                time_duration,
                len(devices),
            )

            for device in devices:
                service = CH9120Services(device['ip'], device['port'])
                task = asyncio.create_task(service.send_command(hex_command, time_duration))
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            success_count = 0
            failure_count = 0

            for i, result in enumerate(results):
                dev = devices[i]
                identity = _device_label(dev)

                if isinstance(result, Exception):
                    logger.error("Command failed | %s | mode=%s | error=%s", identity, mode, result)
                    failure_count += 1
                elif result.get("status") == "success":
                    logger.info("Command succeeded | %s | mode=%s | response=%s", identity, mode, result.get("response") or "-")
                    success_count += 1
                else:
                    logger.warning("Command returned unexpected response | %s | mode=%s | response=%s", identity, mode, result)
                    failure_count += 1

            logger.info(
                "Command finished | scope=line | line=%s | mode=%s | success=%s | failure=%s | total=%s",
                line,
                mode,
                success_count,
                failure_count,
                len(devices),
            )

            return success_count == len(devices)

        except Exception as e:
            logger.exception("Command failed before completion | scope=line | line=%s | error=%s", line, e)
            return False

    @staticmethod
    async def send_command_to_devices(devices, mode, duration, scope="ui-visible"):
        try:
            hex_command = CH9120_COMMANDS[mode]
            target_devices = list(devices)
            tasks = []
            time_duration = int(duration) if duration else 5

            logger.info(
                "Command started | scope=%s | mode=%s | duration=%ss | devices=%s",
                scope,
                mode,
                time_duration,
                len(target_devices),
            )

            for device in target_devices:
                service = CH9120Services(device["ip"], device["port"])
                task = asyncio.create_task(service.send_command(hex_command, time_duration))
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            success_count = 0
            failure_count = 0

            for dev, result in zip(target_devices, results):
                identity = _device_label(dev)

                if isinstance(result, Exception):
                    logger.error("Command failed | %s | mode=%s | error=%s", identity, mode, result)
                    failure_count += 1
                elif result.get("status") == "success":
                    logger.info("Command succeeded | %s | mode=%s | response=%s", identity, mode, result.get("response") or "-")
                    success_count += 1
                else:
                    logger.warning("Command returned unexpected response | %s | mode=%s | response=%s", identity, mode, result)
                    failure_count += 1

            logger.info(
                "Command finished | scope=%s | mode=%s | success=%s | failure=%s | total=%s",
                scope,
                mode,
                success_count,
                failure_count,
                len(target_devices),
            )

            return success_count == len(target_devices)

        except Exception as e:
            logger.exception("Command failed before completion | scope=%s | mode=%s | error=%s", scope, mode, e)
            return False
        
    @staticmethod
    async def send_command_device_office(line, mode, duration):
        try:
            hex_command1 = CH9120_COMMANDS[mode]
            hex_command2 = CH9120_COMMANDS['OFFICE']

            if mode == 'TURN_OFF':
                hex_command2 = CH9120_COMMANDS['TURN_OFF']

            time_duration = int(duration) if duration else 5
            device = CH9120Model.get_by_line(line)
            office_devices = CH9120Model.get_device_office()

            targets = []
            if device:
                targets.append((device[0], hex_command1))
            for off_dev in office_devices:
                targets.append((off_dev, hex_command2))

            logger.info(
                "Command started | scope=device+office | line=%s | mode=%s | duration=%ss | office_devices=%s | total=%s",
                line,
                mode,
                time_duration,
                len(office_devices),
                len(targets),
            )

            tasks = [
            CH9120Services(dev['ip'], dev['port']).send_command(cmd, time_duration)
                for dev, cmd in targets
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            summary = {"success": 0, "failure": 0, "devices": []}
            for dev, result in zip([t[0] for t in targets], results):
                status = "success" if not isinstance(result, Exception) and isinstance(result, dict) and result.get("status") == "success" else "failure"
                summary[status] += 1
                summary["devices"].append({
                    "station": dev['station_name'],
                    "ip": dev['ip'],
                    "port": dev['port'],
                    "status": status,
                    "error": str(result) if isinstance(result, Exception) else None
                })

                if status == "success":
                    logger.info("Command succeeded | %s | mode=%s", _device_label(dev), mode)
                else:
                    logger.error("Command failed | %s | mode=%s | response=%s", _device_label(dev), mode, result)

            logger.info(
                "Command finished | scope=device+office | line=%s | mode=%s | success=%s | failure=%s | total=%s",
                line,
                mode,
                summary["success"],
                summary["failure"],
                len(targets),
            )
            return summary

        except Exception as e:
            logger.exception("Command failed before completion | scope=device+office | line=%s | error=%s", line, e)
            return {"success": 0, "failure": 0, "devices": [], "error": str(e)}
        
    @staticmethod
    async def turn_off_device_and_office(line):
        try:
            hex_command = CH9120_COMMANDS['TURN_OFF']

            # Lấy device theo line
            device = CH9120Model.get_by_line(line)
            # Lấy office devices
            office_devices = CH9120Model.get_device_office()

            targets = []
            if device:
                targets.append(device[0])  # chỉ lấy thiết bị đầu tiên theo line
            targets.extend(office_devices)

            logger.info(
                "Command started | scope=turn-off-device+office | line=%s | devices=%s",
                line,
                len(targets),
            )

            tasks = [
                CH9120Services(dev['ip'], dev['port']).send_command(hex_command, 0)
                for dev in targets
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            summary = {"success": 0, "failure": 0, "devices": []}
            for dev, result in zip(targets, results):
                status = "success" if not isinstance(result, Exception) and isinstance(result, dict) and result.get("status") == "success" else "failure"
                summary[status] += 1
                device_log = {
                    "station": dev['station_name'],
                    "ip": dev['ip'],
                    "port": dev['port'],
                    "status": status,
                    "error": str(result) if isinstance(result, Exception) else None
                }
                summary["devices"].append(device_log)

                if status == "success":
                    logger.info("Command succeeded | %s | mode=TURN_OFF", _device_label(dev))
                else:
                    logger.error(
                        "Command failed | %s | mode=TURN_OFF | error=%s",
                        _device_label(dev),
                        device_log["error"],
                    )

            logger.info(
                "Command finished | scope=turn-off-device+office | line=%s | success=%s | failure=%s | total=%s",
                line,
                summary["success"],
                summary["failure"],
                len(targets),
            )
            return summary

        except Exception as e:
            logger.exception("Command failed before completion | scope=turn-off-device+office | line=%s | error=%s", line, e)
            return {"success": 0, "failure": 0, "devices": [], "error": str(e)}




       
            
