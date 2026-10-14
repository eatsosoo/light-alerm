"""Desktop window and shared visual styles."""

import tkinter as tk
from tkinter import ttk

from light_alarm.ui.device_tab import DeviceTab
from light_alarm.ui.crc_tab import CRCTab
from light_alarm.ui.log_tab import LogTab
from light_alarm.ui.request_log_tab import RequestLogTab
from light_alarm.ui.settings_tab import SettingsTab
from light_alarm.ui.network_config_tab import NetworkConfigTab
from light_alarm.ui.theme import COLORS, label, tabs


class MainWindow:
    def __init__(self, root, runtime):
        self.root = root
        self.runtime = runtime
        self.colors = COLORS
        self._summary_job = None
        self.session_summary = tk.StringVar()
        root.title("Light Alarm · Điều khiển cảnh báo")
        root.geometry("1240x860")
        root.minsize(1040, 740)
        root.configure(bg=self.colors["bg"])
        root.option_add("*Font", ("Segoe UI", 10))
        self.setup_styles()
        header = tk.Frame(root, bg=COLORS["bg"], padx=24, pady=18)
        header.pack(fill="x")
        brand = tk.Frame(header, bg=COLORS["bg"])
        brand.pack(side="left")
        label(brand, "LIGHT ALARM", size=21, bold=True, bg=COLORS["bg"]).pack(anchor="w")
        label(brand, "Điều khiển thiết bị · Theo dõi yêu cầu", muted=True,
              bg=COLORS["bg"]).pack(anchor="w", pady=(3, 0))
        endpoint = tk.Frame(header, bg=COLORS["panel"], padx=14, pady=9)
        endpoint.pack(side="right")
        label(endpoint, "ĐỊA CHỈ API", size=8, muted=True).pack(anchor="w")
        scheme = "https" if runtime.settings.ssl_enabled else "http"
        label(endpoint, f"{scheme}://{runtime.settings.host}:{runtime.settings.port}", size=10).pack(anchor="w")
        notebook = tabs(root)
        notebook.pack(fill="both", expand=True, padx=18)
        self.devices = DeviceTab(root, notebook, runtime.actions, runtime.settings.commands, self.colors,
                                 default_duration=runtime.settings.default_duration)
        self.requests = RequestLogTab(root, notebook, runtime.worker.history, self.colors)
        self.logs = LogTab(root, notebook, runtime.settings.log_directory, self.colors)
        self.crc = CRCTab(root, notebook)
        self.settings_tab = SettingsTab(root, notebook, runtime, self.devices.apply_settings)
        self.network_config = NetworkConfigTab(root, notebook, runtime.actions)
        self.devices.on_request = self.open_request
        self.notebook = notebook
        footer = tk.Frame(root, bg=COLORS["bg"], padx=24, pady=9)
        footer.pack(fill="x")
        label(footer, variable=self.session_summary, size=9, muted=True, bg=COLORS["bg"]).pack(side="left")
        label(footer, "Lịch sử yêu cầu trong phiên hiện tại", size=9, muted=True,
              bg=COLORS["bg"]).pack(side="right")
        self.update_summary()
        root.protocol("WM_DELETE_WINDOW", self.close)

    def open_request(self, job_id):
        self.notebook.select(self.requests.frame)
        self.requests.select_request(job_id)

    def update_summary(self):
        records = self.runtime.worker.history.list()
        active = sum(item["status"] in ("queued", "running") for item in records)
        failed = sum(item["status"] in ("failed", "partial") for item in records)
        self.session_summary.set(f"{len(records)} yêu cầu trong lịch sử  ·  {active} đang xử lý  ·  {failed} có lỗi / một phần")
        self._summary_job = self.root.after(1000, self.update_summary)

    def close(self):
        if self._summary_job:
            self.root.after_cancel(self._summary_job)
        self.devices.close()
        self.requests.close()
        self.logs.close()
        self.crc.close()
        self.settings_tab.close()
        self.network_config.close()
        self.root.destroy()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.style.configure("TFrame", background=self.colors["bg"])
        self.style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        self.style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        self.style.configure(
            "TNotebook.Tab",
            background=self.colors["panel"],
            foreground=self.colors["text"],
            padding=[22, 12],
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
            lightcolor=self.colors["bg"],
            bordercolor=self.colors["bg"],
            darkcolor=self.colors["bg"],
            focuscolor=self.colors["bg"],
            relief="flat",
        )
        self.style.map("TNotebook.Tab", background=[("selected", self.colors["panel_alt"]),
                                                    ("active", self.colors["button"])])

        self.style.configure(
            "Treeview",
            font=("Segoe UI", 10),
            rowheight=34,
            background=self.colors["panel"],
            fieldbackground=self.colors["panel"],
            foreground=self.colors["text"],
            borderwidth=0,
            relief="flat",
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
            lightcolor=self.colors["panel_alt"],
            darkcolor=self.colors["panel_alt"],
            bordercolor=self.colors["panel_alt"],
            padding=[8, 8],
        )
        self.style.map(
            "Treeview",
            background=[("selected", self.colors["selection"])],
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
        self.style.configure("Vertical.TScrollbar", background=COLORS["border"],
                             troughcolor=COLORS["panel_alt"], borderwidth=0, arrowsize=12,
                             lightcolor=COLORS["border"], darkcolor=COLORS["border"],
                             bordercolor=COLORS["panel_alt"], arrowcolor=COLORS["muted"])
        self.style.configure("Horizontal.TScrollbar", background=COLORS["border"],
                             troughcolor=COLORS["bg"], borderwidth=0, arrowsize=12)
        self.style.configure("TPanedwindow", background=COLORS["bg"])
        self.style.layout("Flat.TCombobox", [("Combobox.padding", {"sticky": "nswe", "children": [
            ("Combobox.downarrow", {"side": "right", "sticky": "ns"}),
            ("Combobox.textarea", {"sticky": "nswe"}),
        ]})])
        self.style.configure("Flat.TCombobox", fieldbackground=COLORS["panel_alt"],
                             background=COLORS["panel_alt"], foreground=COLORS["text"],
                             arrowcolor=COLORS["muted"], borderwidth=0, relief="flat", padding=0,
                             lightcolor=COLORS["panel_alt"], darkcolor=COLORS["panel_alt"],
                             bordercolor=COLORS["panel_alt"], arrowsize=12)
        self.style.map("Flat.TCombobox", fieldbackground=[("readonly", COLORS["panel_alt"])],
                       foreground=[("readonly", COLORS["text"])],
                       selectbackground=[("readonly", COLORS["panel_alt"])],
                       selectforeground=[("readonly", COLORS["text"])],
                       background=[("active", COLORS["panel_alt"])])
        self.style.configure("TCheckbutton", background=COLORS["panel"], foreground=COLORS["text"])
        self.style.map("TCheckbutton", background=[("active", COLORS["panel"])])
        self.style.configure("Sash", background=COLORS["border"], borderwidth=0, sashthickness=4)
        self.root.option_add("*TCombobox*Listbox.background", COLORS["panel_alt"])
        self.root.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", COLORS["selection"])
        self.root.option_add("*TCombobox*Listbox.relief", "flat")
        self.root.option_add("*TCombobox*Listbox.borderWidth", 0)
        self.root.option_add("*TCombobox*Listbox.highlightThickness", 0)


