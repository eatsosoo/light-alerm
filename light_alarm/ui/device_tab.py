"""Device table, filtering and asynchronous command feedback."""

import logging
import tkinter as tk
from tkinter import messagebox, ttk

logger = logging.getLogger(__name__)


class DeviceTab:
    def __init__(self, root, notebook, actions, commands, colors):
        self.root = root
        self.actions = actions
        self.commands = commands
        self.colors = colors
        self.selected_line = tk.StringVar(value="All")
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.records = []
        self.filtered_records = []
        self._closed = False
        self._loading = False
        self._poll_jobs = set()
        self._command_sequence = 0
        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Device Control")
        self.create_filter_section(self.frame)
        self.create_treeview(self.frame)
        self.create_buttons(self.frame)
        self.load_devices()

    def _watch(self, future, callback):
        handle = None

        def poll():
            nonlocal handle
            self._poll_jobs.discard(handle)
            if self._closed:
                return
            if future.done():
                callback(future)
            else:
                handle = self.root.after(100, poll)
                self._poll_jobs.add(handle)

        handle = self.root.after(100, poll)
        self._poll_jobs.add(handle)

    def close(self):
        self._closed = True
        for handle in self._poll_jobs:
            self.root.after_cancel(handle)
        self._poll_jobs.clear()

    def load_devices(self):
        if self._loading:
            return
        self._loading = True
        self.status_var.set("Loading devices...")
        try:
            future = self.actions.load_devices()
        except Exception as error:
            self._loading = False
            self.status_var.set("Failed to load devices")
            messagebox.showerror("Load failed", str(error), parent=self.root)
            return

        def loaded(completed):
            self._loading = False
            try:
                records = list(completed.result())
            except Exception:
                logger.exception("Device list load failed")
                self.status_var.set("Failed to load devices; see system logs")
                messagebox.showerror("Load failed", "Could not load devices. See system logs.", parent=self.root)
                return
            self.records = records
            self.refresh_line_options()
            self.apply_filters()

        self._watch(future, loaded)

    def send_to_selected_line(self, command):
        targets = self.get_command_targets()
        if not targets:
            messagebox.showwarning("No target", "No devices match the current filter.", parent=self.root)
            return
        try:
            future = self.actions.send_devices(targets, command, self.duration_entry.get().strip())
        except (ValueError, RuntimeError) as error:
            messagebox.showerror("Command rejected", str(error), parent=self.root)
            return
        self._command_sequence += 1
        sequence = self._command_sequence
        self.status_var.set(f"Running {command} for {len(targets)} device(s)...")

        def finished(completed):
            try:
                result = completed.result()
            except Exception:
                logger.exception("Desktop command failed | mode=%s", command)
                if sequence == self._command_sequence:
                    self.status_var.set(f"{command} failed; see system logs")
                return
            if sequence == self._command_sequence:
                self.status_var.set(
                    f"{command}: {result['success']} succeeded, "
                    f"{result['failure']} failed, {result['superseded']} replaced"
                )

        self._watch(future, finished)

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


    def refresh_line_options(self):
        lines = sorted({str(item.get("line", "")).strip() for item in self.records if item.get("line")})
        current = self.selected_line.get()
        self.line_filter["values"] = ["All"] + lines
        self.selected_line.set(current if current in lines else "All")


    def clear_filters(self):
        self.search_var.set("")
        self.selected_line.set("All")
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
            if (selected_line == "All" or str(device.get("line", "")).strip() == selected_line)
            and matches_keyword(device)
        ]
        self.render_device_rows()


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
        if total == 0:
            self.status_var.set("No devices found")
        else:
            target_count = len(self.get_command_targets())
            self.status_var.set(f"Showing {shown}/{total} devices | Targets visible: {target_count}")


    def get_command_targets(self):
        return list(self.filtered_records)


    def refetch_lines(self):
        self.load_devices()


