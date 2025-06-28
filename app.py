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

# HOST_IP = "10.30.148.95"
HOST_IP = get_ip()
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
    root.geometry("800x500")
    root.configure(bg="#1a1a1a")

    style = ttk.Style()
    style.theme_use("clam")

    # Treeview styling
    style.configure("Treeview",
                    font=("Arial", 10),
                    rowheight=30,
                    background="#1e1e1e",
                    fieldbackground="#1e1e1e",
                    foreground="white",
                    borderwidth=0)
    style.configure("Treeview.Heading",
                    font=("Arial", 12, "bold"),
                    borderwidth=0,
                    background="#333333",
                    foreground="white")
    style.map("Treeview",
              background=[("selected", "#444444")],
              foreground=[("selected", "white")])

    # Filter section
    lines = fetch_lines()
    selected_line = tk.StringVar(value="All")

    filter_frame = tk.Frame(root, bg="#1a1a1a")
    filter_frame.pack(fill="x", padx=10, pady=5)

    tk.Label(filter_frame, text="Filter by Line:", fg="white", bg="#1a1a1a", font=("Arial", 10)).pack(side="left", padx=5)

    line_filter = ttk.Combobox(filter_frame, textvariable=selected_line, values=["All"] + lines, state="readonly", width=14)
    line_filter.pack(side="left", padx=5)

    tk.Label(filter_frame, text="Duration (optional):", fg="white", bg="#1a1a1a", font=("Arial", 10)).pack(side="left", padx=5)

    duration_entry = tk.Entry(filter_frame, width=6, bg="#2b2b2b", fg="white", insertbackground="white",
                              relief="flat", highlightbackground="#444", highlightthickness=1, bd=4)
    duration_entry.pack(side="left", padx=5)

    # Treeview
    columns = ("IP", "Port", "Line", "Station")
    tree = ttk.Treeview(root, columns=columns, show="headings", height=10)
    tree.configure(style="Custom.Treeview")

    style.configure("Custom.Treeview",
        bordercolor="#2a2a2a",  # giả lập màu viền
        borderwidth=1,
        relief="solid",
        background="#1e1e1e",
        fieldbackground="#1e1e1e",
        foreground="white"
    )
    
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=140)

    # Row background alternate colors
    tree.tag_configure("odd", background="#1e1e1e")
    tree.tag_configure("even", background="#262626")

    tree.pack(fill="both", expand=True, padx=10, pady=5)

    def update_device_list():
        tree.delete(*tree.get_children())
        selected = selected_line.get()
        devices = fetch_devices_by_line(selected)
        for idx, device in enumerate(devices):
            tag = "even" if idx % 2 == 0 else "odd"
            tree.insert("", "end", values=(device['ip'], device['port'], device['line'], device['station_name']), tags=(tag,))

    line_filter.bind("<<ComboboxSelected>>", lambda event: update_device_list())
    update_device_list()

    # Button area
    btn_frame = tk.Frame(root, bg="#1a1a1a")
    btn_frame.pack(fill="x", padx=10, pady=10)

    def send_to_selected_line(command):
        line = selected_line.get()
        duration = duration_entry.get().strip()
        send_command(line, command, duration)

    max_per_row = 6
    for i, cmd in enumerate(COMMANDS):
        btn = tk.Button(btn_frame, text=cmd, font=("Arial", 10, "bold"),
                        bg="#000000", fg="white", activebackground="#333333", activeforeground="white",
                        relief="flat", padx=15, pady=8, width=10)
        btn.configure(command=lambda c=cmd: send_to_selected_line(c))
        row = i // max_per_row
        col = i % max_per_row
        btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")

    root.mainloop()

app = Flask(__name__)
CORS(app)
app.register_blueprint(blueprint, url_prefix="/ch9120")


def run_flask():
    host_ip = get_ip() if get_ip() else '0.0.0.0'
    # host_ip = "10.30.148.95"
    app.run(host=host_ip, port=5000)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    create_ui()
