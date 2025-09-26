import tkinter as tk
from tkinter import ttk, scrolledtext
from services.NetworkService import NetworkService
import os
from datetime import datetime

class DeviceControlUI:
    def __init__(self, root, host_ip, port, commands):
        self.root = root
        self.host_ip = host_ip
        self.port = port
        self.commands = commands
        self.selected_line = tk.StringVar(value="All")
        self.setup_ui()
    
    def setup_ui(self):
        self.root.title("Device Control Panel")
        self.root.geometry("800x700")
        self.root.configure(bg="#000")
        
        # Tạo Notebook (tab)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True)
        
        # Tab 1: Điều khiển thiết bị
        self.setup_device_control_tab()
        
        # Tab 2: Xem log
        self.setup_log_viewer_tab()

    def setup_device_control_tab(self):
        # Frame chứa nội dung tab điều khiển
        control_frame = ttk.Frame(self.notebook)
        self.notebook.add(control_frame, text="Device Control")
        
        self.setup_styles()
        self.create_filter_section(control_frame)
        self.create_treeview(control_frame)
        self.create_buttons(control_frame)

    def setup_log_viewer_tab(self):
        # Frame chứa nội dung tab log
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="System Logs")
        
        # Tạo text area để hiển thị log
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            width=120,
            height=30,
            bg="#1e1e1e",
            fg="white",
            insertbackground="white",
            font=("Consolas", 10)
        )
        self.log_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Nút làm mới log
        refresh_btn = tk.Button(
            log_frame,
            text="Refresh Logs",
            command=self.load_log_file,
            bg="#333333",
            fg="white",
            relief="flat",
            padx=10,
            pady=5
        )
        refresh_btn.pack(side="bottom", pady=5)
        
        # Tải log ngay khi mở tab
        self.load_log_file()

    def load_log_file(self):
        """Đọc và hiển thị nội dung file log"""
        log_file = "logs/app.log"
        self.log_text.delete(1.0, tk.END)
        
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                logs = f.read()
                self.log_text.insert(tk.END, logs)
        else:
            self.log_text.insert(tk.END, "No log file found")
        
        # Tự động cuộn xuống dòng mới nhất
        self.log_text.see(tk.END)
    
    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Treeview styling
        self.style.configure("Treeview",
                            font=("Arial", 10),
                            rowheight=30,
                            background="#1e1e1e",
                            fieldbackground="#1e1e1e",
                            foreground="white",
                            borderwidth=1,
                            relief="solid",  # để hiển thị đường viền rõ hơn
                            lightcolor="#2b2b2b",
                            darkcolor="#2b2b2b",
                            bordercolor="#2b2b2b")
        self.style.configure("Treeview.Heading",
                            font=("Arial", 12, "bold"),
                            borderwidth=0,
                            relief="flat",
                            background="#333333",
                            foreground="white")
        self.style.map("Treeview",
                      background=[("selected", "#444444")],
                      foreground=[("selected", "white")])
        
        # Notebook background (tab + content)
        self.style.configure("TNotebook", background="#000000", borderwidth=0)
        self.style.configure("TNotebook.Tab",
            background="#1a1a1a",
            foreground="white",
            padding=[10, 5],
            borderwidth=0,            # Xoá viền trắng
            lightcolor="#000000",     # Màu viền sáng
            bordercolor="#000000",    # Màu viền chính
            darkcolor="#000000",      # Màu viền tối
            focuscolor="#000000",     # Màu viền khi focus
            relief="flat"             # Kiểu hiển thị không nhô
        )
        self.style.map("TNotebook.Tab", background=[("selected", "#2b2b2b")])

        # Frame styling (applies to ttk.Frame)
        self.style.configure("TFrame", background="#000000")

        # Combobox styling
        self.style.configure("TCombobox",
            fieldbackground="#1a1a1a",
            background="#1a1a1a",
            foreground="white",
            bordercolor="#2b2b2b",
            lightcolor="#2b2b2b",
            darkcolor="#2b2b2b",
            borderwidth=1,
            relief="flat"
        )
        self.style.map("TCombobox",
                    fieldbackground=[("readonly", "#1a1a1a")],
                    background=[("readonly", "#1a1a1a")],
                    foreground=[("readonly", "white")])
    
    def create_filter_section(self, parent):
        filter = tk.Frame(parent, bg="#1a1a1a")
        filter.pack(fill="x", padx=10, pady=10)

        tk.Label(filter, text="Filter by Line:", fg="white", bg="#1a1a1a", 
                font=("Arial", 10)).pack(side="left", padx=5)

        # Lưu NetworkService vào biến để tái sử dụng
        self.network_service = NetworkService(self.host_ip, self.port)

        # Khởi tạo combobox
        lines = list(self.network_service.fetch_lines())
        self.line_filter = ttk.Combobox(
            filter, textvariable=self.selected_line, 
            values=["All"] + lines, state="readonly", width=14
        )
        self.line_filter.pack(side="left", padx=5)
        self.line_filter.bind("<<ComboboxSelected>>", lambda event: self.update_device_list())

        # Nút Refetch Lines
        refetch_btn = tk.Button(
            filter,
            text="Refetch Lines",
            command=self.refetch_lines,
            bg="#333333",
            fg="white",
            relief="flat",
            padx=10,
            pady=5
        )
        refetch_btn.pack(side="left", padx=10)

        tk.Label(filter, text="Duration (optional):", fg="white", bg="#1a1a1a", 
                font=("Arial", 10)).pack(side="left", padx=5)

        self.duration_entry = tk.Entry(
            filter, width=6, bg="#2b2b2b", fg="white", 
            insertbackground="white", relief="flat", 
            highlightbackground="#444", highlightthickness=1, bd=4
        )
        self.duration_entry.pack(side="left", padx=5)
    
    def create_treeview(self, parent):
        columns = ("IP", "Port", "Line", "Station")
        self.tree = ttk.Treeview(parent, columns=columns, show="headings", height=10)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=140)

        self.tree.tag_configure("odd", background="#1e1e1e")
        self.tree.tag_configure("even", background="#262626")
        
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.update_device_list()
    
    def create_buttons(self, parent):
        btn_frame = tk.Frame(parent, bg="#1a1a1a")
        btn_frame.pack(fill="x", padx=10, pady=10)

        max_per_row = 6
        for i, cmd in enumerate(self.commands):
            btn = tk.Button(btn_frame, text=cmd, font=("Arial", 10, "bold"),
                          bg="#000000", fg="white", activebackground="#333333", 
                          activeforeground="white", relief="flat", 
                          padx=15, pady=8, width=10)
            btn.configure(command=lambda c=cmd: self.send_to_selected_line(c))
            row = i // max_per_row
            col = i % max_per_row
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
    
    def update_device_list(self):
        self.tree.delete(*self.tree.get_children())
        selected = self.selected_line.get()
        devices = NetworkService(self.host_ip, self.port).fetch_devices_by_line(selected)
        for idx, device in enumerate(devices):
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.insert("", "end", 
                           values=(device['ip'], device['port'], device['line'], device['station_name']), 
                           tags=(tag,))
    
    def send_to_selected_line(self, command):
        line = self.selected_line.get()
        duration = self.duration_entry.get().strip()
        NetworkService(self.host_ip, self.port).send_command(line, command, duration)

    def refetch_lines(self):
        """Làm mới danh sách lines và treeview"""
        # Lấy lại danh sách lines từ NetworkService
        new_lines = list(self.network_service.fetch_lines())
        
        # Cập nhật lại combobox Line filter
        self.line_filter["values"] = ["All"] + new_lines
        
        # Reset về 'All' (có thể giữ nguyên line cũ nếu bạn muốn)
        self.selected_line.set("All")
        
        # Làm mới treeview với line vừa chọn
        self.update_device_list()