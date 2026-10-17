"""Desktop interface for discovering and configuring CH9120 modules."""

import tkinter as tk
from tkinter import messagebox, ttk

from light_alarm.devices.ch9120_config import MODES
from light_alarm.ui.theme import COLORS, button, entry, label, scrollbar, separator


class NetworkConfigTab:
    FIELDS = (
        ("name", "Tên thiết bị"), ("ip", "Địa chỉ IP"),
        ("subnet", "Subnet mask"), ("gateway", "Gateway"),
        ("local_port", "Port thiết bị"), ("destination_ip", "IP đích"),
        ("destination_port", "Port đích"), ("baud_rate", "Baud rate"),
    )

    def __init__(self, root, notebook, actions):
        self.root, self.actions = root, actions
        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Cấu hình mạng")
        self.modules = []
        self.selected_module = None
        self.current_config = None
        self.poll_jobs = set()
        self.closed = False
        self.busy = False
        self.status_var = tk.StringVar(value="Cùng kết nối LAN với CH9120 rồi bấm Tìm thiết bị.")
        self.vars = {name: tk.StringVar() for name, _ in self.FIELDS}
        self.mode_var = tk.StringVar(value="TCP Server")
        self.dhcp_var = tk.BooleanVar(value=False)
        self.adapter_var = tk.StringVar(value="Tự động")
        self.adapters = {}
        self._build()

    def _build(self):
        wrapper = tk.Frame(self.frame, bg=COLORS["bg"])
        wrapper.pack(fill="both", expand=True, padx=16, pady=16)
        toolbar = tk.Frame(wrapper, bg=COLORS["bg"])
        toolbar.pack(fill="x", pady=(0, 12))
        label(toolbar, "Card mạng", muted=True).pack(side="left", padx=(0, 7))
        self.adapter_select = ttk.Combobox(toolbar, textvariable=self.adapter_var,
                                           state="readonly", width=22)
        self.adapter_select.pack(side="left")
        label(toolbar, "Tìm CH9120 qua UDP trên cùng mạng LAN.", muted=True).pack(side="left", padx=12)
        self.search_button = button(toolbar, "Tìm thiết bị", self.discover, kind="primary")
        self.search_button.pack(side="right")

        body = tk.Frame(wrapper, bg=COLORS["bg"])
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2, minsize=320)
        body.rowconfigure(0, weight=1)
        left = tk.Frame(body, bg=COLORS["panel"], padx=14, pady=14)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        label(left, "Thiết bị được tìm thấy", size=13, bold=True).pack(anchor="w", pady=(0, 12))
        table = tk.Frame(left, bg=COLORS["panel"])
        table.pack(fill="both", expand=True)
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(table, columns=("name", "ip", "mac", "firmware"),
                                 show="headings", selectmode="browse", height=12)
        for key, title, width in (("name", "Tên", 150), ("ip", "IP hiện tại", 125),
                                  ("mac", "MAC", 145), ("firmware", "FW", 60)):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=60, anchor="w")
        bar = scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=bar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        bar.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self._select_module)

        right = tk.Frame(body, bg=COLORS["panel"], padx=16, pady=14)
        right.grid(row=0, column=1, sticky="nsew")
        label(right, "Thông số mạng", size=13, bold=True).pack(anchor="w")
        label(right, "Chọn module để đọc cấu hình hiện tại.", size=9, muted=True).pack(anchor="w", pady=(4, 12))
        self.read_button = button(right, "Đọc cấu hình", self.read_config)
        self.read_button.pack(fill="x", pady=(0, 10))
        separator(right).pack(fill="x", pady=(0, 12))
        fields = tk.Frame(right, bg=COLORS["panel"])
        fields.pack(fill="x")
        fields.columnconfigure(1, weight=1)
        for row, (key, title) in enumerate(self.FIELDS):
            label(fields, title, size=9, muted=True).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 8))
            entry(fields, self.vars[key], width=18).grid(row=row, column=1, sticky="ew", pady=3)
        label(fields, "Chế độ mạng", size=9, muted=True).grid(row=len(self.FIELDS), column=0, sticky="w", pady=4, padx=(0, 8))
        self.mode_select = ttk.Combobox(fields, textvariable=self.mode_var,
                                        values=list(MODES.values()), state="readonly", width=18)
        self.mode_select.grid(row=len(self.FIELDS), column=1, sticky="ew", pady=3)
        self.dhcp_check = ttk.Checkbutton(fields, text="Bật DHCP", variable=self.dhcp_var)
        self.dhcp_check.grid(row=len(self.FIELDS) + 1, column=0, columnspan=2, sticky="w", pady=(5, 3))
        self.configure_button = button(right, "Ghi cấu hình", self.configure, kind="primary")
        self.configure_button.pack(fill="x", pady=(12, 0))
        self.status_label = label(wrapper, variable=self.status_var, size=9, muted=True, wraplength=1000)
        self.status_label.pack(anchor="w", pady=(10, 0))
        self.adapters = {"Tự động": "0.0.0.0"}
        for address in self.actions.local_network_adapters():
            self.adapters[address] = address
        self.adapter_select["values"] = list(self.adapters)
        self._set_controls()

    def _bind_ip(self):
        return self.adapters.get(self.adapter_var.get(), "0.0.0.0")

    def _watch(self, future, callback):
        handle = None
        def poll():
            nonlocal handle
            self.poll_jobs.discard(handle)
            if self.closed:
                return
            if future.done():
                self.busy = False
                self._set_controls()
                try:
                    callback(future.result())
                except Exception as error:
                    self.status_var.set(f"Thao tác thất bại: {error}")
            else:
                handle = self.root.after(100, poll)
                self.poll_jobs.add(handle)
        handle = self.root.after(100, poll)
        self.poll_jobs.add(handle)

    def _set_controls(self):
        self.search_button.configure(state="disabled" if self.busy else "normal",
                                     text="Đang tìm…" if self.busy else "Tìm thiết bị")
        selected = bool(self.selected_module)
        self.read_button.configure(state="normal" if selected and not self.busy else "disabled")
        self.configure_button.configure(state="normal" if self.current_config and not self.busy else "disabled")

    def discover(self):
        if self.busy:
            return
        self.busy = True
        self.status_var.set("Đang gửi UDP broadcast và chờ CH9120 phản hồi…")
        self._set_controls()
        self._watch(self.actions.discover_modules(self._bind_ip()), self._show_modules)

    def _show_modules(self, modules):
        self.modules = modules
        self.tree.delete(*self.tree.get_children())
        self.selected_module = None
        self.current_config = None
        for i, module in enumerate(modules):
            fw = "—" if module["firmware_version"] is None else str(module["firmware_version"])
            self.tree.insert("", "end", iid=str(i), values=(module["name"], module["ip"], module["mac"], fw))
        self.status_var.set(f"Đã tìm thấy {len(modules)} module. Chọn một module để đọc hoặc cấu hình.")
        self._clear_fields()
        self._set_controls()

    def _clear_fields(self):
        for variable in self.vars.values():
            variable.set("")
        self.mode_var.set("TCP Server")
        self.dhcp_var.set(False)

    def _select_module(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        self.selected_module = self.modules[int(selection[0])]
        self.current_config = None
        self._clear_fields()
        self.status_var.set(f"Đã chọn {self.selected_module['name']} · {self.selected_module['ip']} · {self.selected_module['mac']}")
        self._set_controls()

    def read_config(self):
        if not self.selected_module or self.busy:
            return
        self.busy = True
        self.status_var.set("Đang đọc cấu hình từ module…")
        self._set_controls()
        self._watch(self.actions.read_module_config(self.selected_module, self._bind_ip()), self._show_config)

    def _show_config(self, config):
        self.current_config = config
        for key in self.vars:
            self.vars[key].set(str(config[key]))
        self.mode_var.set(config["mode_name"])
        self.dhcp_var.set(config["dhcp"])
        self.status_var.set(f"Đã đọc cấu hình {config['mac']} · {config['mode_name']} · {config['baud_rate']} bps")
        self._set_controls()

    def configure(self):
        if not self.current_config or self.busy:
            return
        if not messagebox.askyesno("Ghi cấu hình mạng", "Ghi cấu hình vào CH9120? Module sẽ khởi động lại và IP có thể thay đổi.", parent=self.root):
            return
        updates = {key: variable.get().strip() for key, variable in self.vars.items()}
        updates["mode"] = next((mode for mode, name in MODES.items() if name == self.mode_var.get()), None)
        updates["dhcp"] = self.dhcp_var.get()
        self.busy = True
        self.status_var.set("Đang ghi cấu hình. Thiết bị sẽ khởi động lại…")
        self._set_controls()
        self._watch(self.actions.configure_module(self.current_config, updates, self._bind_ip()), self._configured)

    def _configured(self, _response):
        self.current_config = None
        self.status_var.set("Đã nhận xác nhận ghi cấu hình. Chờ thiết bị khởi động lại rồi bấm Tìm thiết bị để kiểm tra.")
        self._set_controls()

    def close(self):
        self.closed = True
        for handle in self.poll_jobs:
            self.root.after_cancel(handle)
        self.poll_jobs.clear()
