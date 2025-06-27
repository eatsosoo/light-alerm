from flask import Blueprint, jsonify, request
from services.CH9120Services import CH9120Services
from models.CH9120Model import CH9120Model
from configs.CH9120Config import CH9120_COMMANDS
import asyncio
import threading

blueprint = Blueprint('api', __name__)

@blueprint.route('/send-command/all', methods=['POST'])
async def send_command_all():
       data = request.get_json()
       mode = data.get('mode')
       duration = data.get('duration', 5)
       
       if mode not in CH9120_COMMANDS:
           return jsonify({"status": "error", "message": "Invalid mode."}), 400
       
       hex_command = CH9120_COMMANDS[mode]
       def run_command():
        asyncio.run(CH9120Model.send_command_to_all(hex_command, duration))
        
       thread = threading.Thread(target=run_command)
       thread.start()
       return jsonify({"status": "success", "message": "Command is being sent to all devices."})
   
@blueprint.route('/send-command/line', methods=['POST'])
async def send_command_to_line():
       data = request.get_json()
       line = data.get('line')
       mode = data.get('mode')
       duration = data.get('duration', 5)
       
       if mode not in CH9120_COMMANDS:
           return jsonify({"status": "error", "message": "Invalid mode."}), 400
       
       hex_command = CH9120_COMMANDS[mode]
       def run_command():
        asyncio.run(CH9120Model.send_command_by_line(line, hex_command, duration))
        
       thread = threading.Thread(target=run_command)
       thread.start()
       return jsonify({"status": "success", "message": "Command is being sent to all devices."})

@blueprint.route('/create_device', methods=['POST'])
def create_device():
    user_code_created = request.json.get('user_code_created')
    station_name = request.json.get('station_name')
    ip = request.json.get('ip')
    port = request.json.get('port')
    line = request.json.get('line')
    remark = request.json.get('remark')
    
    CH9120Model.create(user_code_created, station_name, ip, port, line, remark)
    
    return jsonify({"status": "success", "message": "Device created successfully."})


@blueprint.route('/update_device/<int:keyid>', methods=['PUT'])
def update_device(keyid):
    user_code_updated = request.json.get('user_code_updated')
    station_name = request.json.get('station_name')
    ip = request.json.get('ip')
    port = request.json.get('port')
    line = request.json.get('line')
    remark = request.json.get('remark')
    
    CH9120Model.update(keyid, user_code_updated, station_name, ip, port, line, remark)
    
    return jsonify({"status": "success", "message": "Device updated successfully."})


@blueprint.route('/delete_device/<int:keyid>', methods=['DELETE'])
def delete_device(keyid):
    CH9120Model.delete(keyid)
    
    return jsonify({"status": "success", "message": "Device deleted successfully."})


@blueprint.route('/get_device/<int:keyid>', methods=['GET'])
def get_device(keyid):
    device = CH9120Model.get_by_id(keyid)
    if device:
        return jsonify({"status": "success", "device": device})
    else:
        return jsonify({"status": "error", "message": "Device not found."})


@blueprint.route('/get_devices_by_line/<line>', methods=['GET'])
def get_devices_by_line(line):
    devices = CH9120Model.get_by_line(line)
    if devices:
        return jsonify({"status": "success", "devices": devices})
    else:
        return jsonify({"status": "error", "message": "No devices found for this line."})


@blueprint.route('/get-all-devices', methods=['GET'])
def get_all_devices():
    devices = CH9120Model.get_all()
    return jsonify({"status": "success", "devices": devices})

@blueprint.route('/get-all-lines', methods=['GET'])
def get_all_lines():
    lines = CH9120Model.get_lines()
    return jsonify({"status": "success", "lines": lines})
