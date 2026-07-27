from models.CH9120Model import CH9120Model

class CH9120Controller:
    @staticmethod
    def create_device(user_code_created, station_name, ip, port, line, remark):
        CH9120Model.create(user_code_created, station_name, ip, port, line, remark)
        
    @staticmethod
    def update_device(keyid, user_code_updated, station_name, ip, port, line, remark):
        CH9120Model.update(keyid, user_code_updated, station_name, ip, port, line, remark)
        
    @staticmethod
    def delete_device(keyid):
        CH9120Model.delete(keyid)
        
    @staticmethod
    def get_device_by_id(keyid):
        return CH9120Model.get_by_id(keyid)
    
    @staticmethod
    def get_devices_by_line(line):
        return CH9120Model.get_by_line(line)
    
    @staticmethod
    def get_all_devices():
        return CH9120Model.get_all()