import os
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from services.NetworkService import NetworkService


class DeviceControlUI:
    def __init__(self, root, host_ip, port, commands):
        self.root = root
        self.host_ip = host_ip
        self.port = port
        self.commands = commands

        self.selected_line = tk.StringVar(value="All")
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.records = []
        self.filtered_records = []
        self.network_service = NetworkService(self.host_ip, self.port)

        self.colors = {
            "bg": "#0f1115",
            "panel": "#171a21",
            "panel_alt": "#20242d",
            "border": "#303642",
            "text": "#f4f6f8",
            "muted": "#aeb6c2",
            "accent": "#2f80ed",
            "accent_hover": "#1f6ed4",
            "button": "#111827",
            "danger": "#c84c4c",
        }

        self.setup_ui()

    def setup_ui(self):
        self.root.title("Device Control Panel")
        self.root.geometry("1040x800")
        self.root.minsize(900, 640)
        self.root.configure(bg=self.colors["bg"])

        self.setup_styles()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        self.setup_device_control_tab()
        self.setup_log_viewer_tab()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.style.configure("TFrame", background=self.colors["bg"])
        self.style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        self.style.configure(
            "TNotebook.Tab",
            background=self.colors["panel"],
            foreground=self.colors["text"],
            padding=[14, 8],
            borderwidth=0,
            lightcolor=self.colors["bg"],
            bordercolor=self.colors["bg"],
            darkcolor=self.colors["bg"],
            focuscolor=self.colors["bg"],
            relief="flat",
        )
        self.style.map("TNotebook.Tab", background=[("selected", self.colors["panel_alt"])])

        self.style.configure(
            "Treeview",
            font=("Segoe UI", 10),
            rowheight=32,
            background=self.colors["panel"],
            fieldbackground=self.colors["panel"],
            foreground=self.colors["text"],
            borderwidth=1,
            relief="solid",
            lightcolor=self.colors["border"],
            darkcolor=self.colors["border"],
            bordercolor=self.colors["border"],
        )
        self.style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
            relief="flat",
            background=self.colors["panel_alt"],
            foreground=self.colors["text"],
            padding=[8, 8],
        )
        self.style.map(
            "Treeview",
            background=[("selected", self.colors["accent"])],
            foreground=[("selected", "white")],
        )

        self.style.configure(
            "TCombobox",
            fieldbackground=self.colors["panel_alt"],
            background=self.colors["panel_alt"],
            foreground=self.colors["text"],
            bordercolor=self.colors["border"],
            lightcolor=self.colors["border"],
            darkcolor=self.colors["border"],
            borderwidth=1,
            relief="flat",
            padding=[8, 4],
            arrowsize=14,
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.colors["panel_alt"])],
            background=[("readonly", self.colors["panel_alt"])],
            foreground=[("readonly", self.colors["text"])],
        )

    def setup_device_control_tab(self):
        control_frame = ttk.Frame(self.notebook)
        self.notebook.add(control_frame, text="Device Control")

        self.create_filter_section(control_frame)
        self.create_treeview(control_frame)
        self.create_buttons(control_frame)
        self.load_devices()

    def setup_log_viewer_tab(self):
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="System Logs")

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            width=120,
            height=30,
            bg="#1e1e1e",
            fg="white",
            insertbackground="white",
            font=("Consolas", 10),
            relief="flat",
        )
        self.log_text.pack(fill="both", expand=True, padx=14, pady=14)

        refresh_btn = self.create_action_button(
            log_frame,
            text="Refresh Logs",
            command=self.load_log_file,
            bg=self.colors["panel_alt"],
            active_bg=self.colors["border"],
            width=14,
        )
        refresh_btn.pack(side="bottom", pady=(0, 10))

        self.load_log_file()

    def create_filter_section(self, parent):
        filter_frame = tk.Frame(parent, bg=self.colors["panel"], padx=14, pady=12)
        filter_frame.pack(fill="x", padx=14, pady=(14, 8))
        filter_frame.columnconfigure(0, weight=1)

        title_row = tk.Frame(filter_frame, bg=self.colors["panel"])
        title_row.grid(row=0, column=0, columnspan=5, sticky="ew", pady=(0, 10))
        title_row.columnconfigure(0, weight=1)

        tk.Label(
            title_row,
            text="Devices",
            fg=self.colors["text"],
            bg=self.colors["panel"],
            font=("Segoe UI", 14, "bold"),
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            title_row,
            textvariable=self.status_var,
            fg=self.colors["muted"],
            bg=self.colors["panel"],
            font=("Segoe UI", 9),
        ).grid(row=0, column=1, sticky="e")

        self.create_field_label(filter_frame, "Search").grid(row=1, column=0, sticky="w", padx=(0, 8))
        self.create_field_label(filter_frame, "Line").grid(row=1, column=1, sticky="w", padx=8)
        self.create_field_label(filter_frame, "Duration").grid(row=1, column=2, sticky="w", padx=8)

        self.search_entry = tk.Entry(
            filter_frame,
            textvariable=self.search_var,
            bg=self.colors["panel_alt"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat",
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["accent"],
            highlightthickness=1,
            bd=6,
            font=("Segoe UI", 10),
        )
        self.search_entry.grid(row=2, column=0, sticky="ew", padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", lambda event: self.apply_filters())
        self.search_entry.bind("<Escape>", lambda event: self.clear_filters())

        self.line_filter = ttk.Combobox(
            filter_frame,
            textvariable=self.selected_line,
            values=["All"],
            state="readonly",
            width=20,
        )
        self.line_filter.grid(row=2, column=1, sticky="ew", padx=8)
        self.line_filter.bind("<<ComboboxSelected>>", lambda event: self.apply_filters())

        self.duration_entry = tk.Entry(
            filter_frame,
            width=10,
            bg=self.colors["panel_alt"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat",
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["accent"],
            highlightthickness=1,
            bd=6,
            font=("Segoe UI", 10),
        )
        self.duration_entry.grid(row=2, column=2, sticky="ew", padx=8)

        clear_btn = self.create_action_button(
            filter_frame,
            text="Clear",
            command=self.clear_filters,
            bg=self.colors["panel_alt"],
            active_bg=self.colors["border"],
            width=9,
        )
        clear_btn.grid(row=2, column=3, sticky="ew", padx=(8, 4))

        refresh_btn = self.create_action_button(
            filter_frame,
            text="Refresh",
            command=self.refetch_lines,
            bg=self.colors["accent"],
            active_bg=self.colors["accent_hover"],
            width=10,
        )
        refresh_btn.grid(row=2, column=4, sticky="ew", padx=(4, 0))

    def create_treeview(self, parent):
        table_frame = tk.Frame(parent, bg=self.colors["bg"])
        table_frame.pack(fill="both", expand=True, padx=14, pady=8)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = ("IP", "Port", "Line", "Station")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)

        column_config = {
            "IP": {"width": 170, "anchor": "w"},
            "Port": {"width": 90, "anchor": "center"},
            "Line": {"width": 180, "anchor": "w"},
            "Station": {"width": 320, "anchor": "w"},
        }
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(
                col,
                anchor=column_config[col]["anchor"],
                width=column_config[col]["width"],
                stretch=True,
            )

        self.tree.tag_configure("odd", background=self.colors["panel"])
        self.tree.tag_configure("even", background=self.colors["panel_alt"])

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

    def create_buttons(self, parent):
        btn_frame = tk.Frame(parent, bg=self.colors["panel"], padx=12, pady=10)
        btn_frame.pack(fill="x", padx=14, pady=(8, 14))

        tk.Label(
            btn_frame,
            text="Commands",
            fg=self.colors["text"],
            bg=self.colors["panel"],
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 8))

        max_per_row = 6
        for i, cmd in enumerate(self.commands):
            btn = tk.Button(
                btn_frame,
                text=cmd,
                font=("Segoe UI", 9, "bold"),
                bg=self.colors["button"],
                fg="white",
                activebackground=self.colors["accent"],
                activeforeground="white",
                relief="flat",
                padx=14,
                pady=8,
                width=12,
                cursor="hand2",
            )
            btn.configure(command=lambda c=cmd: self.send_to_selected_line(c))
            row = (i // max_per_row) + 1
            col = i % max_per_row
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")

        for col in range(max_per_row):
            btn_frame.columnconfigure(col, weight=1, uniform="commands")

    def create_field_label(self, parent, text):
        return tk.Label(
            parent,
            text=text,
            fg=self.colors["muted"],
            bg=self.colors["panel"],
            font=("Segoe UI", 9, "bold"),
        )

    def create_action_button(self, parent, text, command, bg, active_bg, width=None):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=self.colors["text"],
            activebackground=active_bg,
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            width=width,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        )

    def load_devices(self):
        self.status_var.set("Loading devices...")
        self.root.update_idletasks()
        self.records = list(self.network_service.fetch_devices_by_line("All"))
        self.refresh_line_options()
        self.apply_filters()

    def refresh_line_options(self):
        lines = sorted({str(item.get("line", "")).strip() for item in self.records if item.get("line")})
        current = self.selected_line.get()
        self.line_filter["values"] = ["All"] + lines
        self.selected_line.set(current if current in lines else "All")

    def clear_filters(self):
        self.search_var.set("")
        self.selected_line.set("All")
        self.apply_filters()

    def apply_search_filter(self):
        self.apply_filters()

    def apply_filters(self):
        keyword = self.search_var.get().strip().lower()
        selected_line = self.selected_line.get()

        def matches_keyword(device):
            if not keyword:
                return True
            searchable = (
                str(device.get("line", "")),
                str(device.get("station_name", "")),
                str(device.get("ip", "")),
                str(device.get("port", "")),
            )
            return any(keyword in value.lower() for value in searchable)

        self.filtered_records = [
            device
            for device in self.records
            if (selected_line == "All" or str(device.get("line", "")) == selected_line)
            and matches_keyword(device)
        ]
        self.render_device_rows()

    def update_device_list(self):
        self.apply_filters()

    def render_device_rows(self):
        self.tree.delete(*self.tree.get_children())
        for idx, device in enumerate(self.filtered_records):
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.insert(
                "",
                "end",
                values=(
                    device.get("ip", ""),
                    device.get("port", ""),
                    device.get("line", ""),
                    device.get("station_name", ""),
                ),
                tags=(tag,),
            )

        total = len(self.records)
        shown = len(self.filtered_records)
        line = self.selected_line.get()
        if total == 0:
            self.status_var.set("No devices found")
        else:
            target_count = len(self.get_command_targets())
            self.status_var.set(f"Showing {shown}/{total} devices | Target: {line} ({target_count})")

    def get_command_targets(self):
        line = self.selected_line.get()
        if line == "All":
            return self.records
        return [device for device in self.records if str(device.get("line", "")) == line]

    def load_log_file(self):
        log_file = "logs/app.log"
        self.log_text.delete(1.0, tk.END)

        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                self.log_text.insert(tk.END, f.read())
        else:
            self.log_text.insert(tk.END, "No log file found")

        self.log_text.see(tk.END)

    def send_to_selected_line(self, command):
        line = self.selected_line.get()
        duration = self.duration_entry.get().strip()

        if duration and not duration.isdigit():
            messagebox.showerror("Invalid duration", "Duration must be a number of seconds.")
            self.duration_entry.focus_set()
            return

        target_count = len(self.get_command_targets())
        if target_count == 0:
            messagebox.showwarning("No target", "No devices match the current filter.")
            return

        self.status_var.set(f"Sending {command} to {target_count} device(s)...")
        self.network_service.send_alert_from_app(line, command, duration)
        self.status_var.set(f"Sent {command} to line {line} ({target_count} device(s))")

    def refetch_lines(self):
        self.load_devices()
