import asyncio
from configs.config import Config
from services.CH9120Services import CH9120Services

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

            for device in devices:
                print(f"[APP] Sending to {device['ip']}:{device['port']} - {device['station_name']}")

                service = CH9120Services(device['ip'], device['port'])
                task = asyncio.create_task(service.send_command(hex_command, duration))
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            success_count = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"Error with device {devices[i]['ip']}:{devices[i]['port']} - {result}")
                elif result.get("status") == "success":
                    success_count += 1
                    print(f"Success: {devices[i]['ip']}:{devices[i]['port']}")
                else:
                    print(f"Unknown response from {devices[i]['ip']}:{devices[i]['port']} - {result}")

            print(f"{success_count}/{len(devices)} devices executed successfully.")

            return success_count > 0  

        except Exception as e:
            print(f"send_command_to_all() failed: {e}")
            return False
    
    @staticmethod
    async def send_command_by_line(line, hex_command, duration):
        devices = CH9120Model.get_by_line(line)
        tasks = []
        for device in devices:
            # print(f'START SEND COMMAND TO LINE[{device['station_name']}]: {device['ip']}')
            service = CH9120Services(device['ip'], device['port'])
            task = asyncio.create_task(service.send_command(hex_command, duration))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        if all(result['status'] == 'success' for result in results):
            return True
        else:
            return False
       
            
