import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading
from flask import Flask
from flask_cors import CORS
from routes.api import blueprint
import netifaces as ni
from configs.CH9120Config import CH9120_COMMANDS


def get_ip():
    interfaces = ni.interfaces()
    for interface in interfaces:
        try:
            ipv4_info = ni.ifaddresses(interface).get(ni.AF_INET)
            if ipv4_info:
                ip_address = ipv4_info[0]['addr']
                print(f"IP Address: {ip_address}")
                return ip_address
        except ValueError:
            continue
    return None

HOST_IP = "10.30.148.95"
API_BASE_URL = f"http://{HOST_IP}:5000/ch9120"
COMMANDS = CH9120_COMMANDS

def fetch_lines():
    try:
        response = requests.get(f"{API_BASE_URL}/get-all-lines")
        data = response.json()
        return [item["line"] for item in data.get("lines", [])]
    except requests.RequestException as e:
        messagebox.showerror("Error", f"Failed to fetch lines: {e}")
        return []

def fetch_devices_by_line(line):
    try:
        url = f"{API_BASE_URL}/get-all-devices" if line == "All" else f"{API_BASE_URL}/get_devices_by_line/{line}"
        response = requests.get(url)
        data = response.json()
        return data.get("devices", [])
    except requests.RequestException as e:
        messagebox.showerror("Error", f"Failed to fetch devices: {e}")
        return []
def send_command(line, command, duration):
    url = f"{API_BASE_URL}"
    if line == "All":
        url = f"{API_BASE_URL}/send-command/all"
        payload = {"mode": command}
        if duration:
            payload["duration"] = int(duration)
    else:
        url = f"{API_BASE_URL}/send-command/line"
        payload = {"line": line, "mode": command}
        if duration:
            payload["duration"] = int(duration)
        print(f"[API] Sending to {line} - {command} - {duration}")

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            messagebox.showinfo("Success", f"Command {command} sent to {line}")
        else:
            messagebox.showerror("Error", f"Failed to send command: {response.json().get('message', 'Unknown error')}")
    except requests.RequestException as e:
        messagebox.showerror("Error", f"Request failed: {e}")

def create_ui():
    root = tk.Tk()
    root.title("Device Control Panel")
    root.geometry("900x500")

    lines = fetch_lines()
    devices = fetch_devices_by_line("All")
    selected_line = tk.StringVar(value="All")

    filter_frame = tk.Frame(root)
    filter_frame.pack(fill="x", padx=10, pady=5)

    tk.Label(filter_frame, text="Filter by Line:").pack(side="left", padx=5)
    line_filter = ttk.Combobox(filter_frame, textvariable=selected_line, values=["All"] + lines, state="readonly")
    line_filter.pack(side="left", padx=5)

    tk.Label(filter_frame, text="Duration (optional):").pack(side="left", padx=5)
    duration_entry = tk.Entry(filter_frame, width=5)
    duration_entry.pack(side="left", padx=5)

    columns = ("IP", "Port", "Line", "Station")
    tree = ttk.Treeview(root, columns=columns, show="headings", height=10)

    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=120)

    tree.pack(fill="both", expand=True, padx=10, pady=5)

    def update_device_list():
        selected = selected_line.get()
        tree.delete(*tree.get_children())

        filtered_devices = fetch_devices_by_line(selected)
        for device in filtered_devices:
            tree.insert("", "end", values=(device['ip'], device['port'], device['line'], device['station_name']))

    line_filter.bind("<<ComboboxSelected>>", lambda event: update_device_list())

    update_device_list()

    btn_frame = tk.Frame(root)
    btn_frame.pack(fill="x", padx=10, pady=10)

    def send_to_selected_line(command):
        line = selected_line.get()
        duration = duration_entry.get().strip()
        if line == "All":
            send_command("All", command, duration)
        else:
            send_command(line, command, duration)

    for cmd in COMMANDS:
        btn = tk.Button(btn_frame, text=cmd, font=("Arial", 10), command=lambda c=cmd: send_to_selected_line(c))
        btn.pack(side="left", padx=5, pady=5)

    root.mainloop()

app = Flask(__name__)
CORS(app)
app.register_blueprint(blueprint, url_prefix="/ch9120")


def run_flask():
    # host_ip = get_ip() if get_ip() else '0.0.0.0'
    host_ip = "10.30.148.95"
    app.run(host=host_ip, port=5000)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    create_ui()
