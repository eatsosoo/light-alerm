"""Desktop window and shared visual styles."""

from tkinter import ttk

from light_alarm.ui.device_tab import DeviceTab
from light_alarm.ui.log_tab import LogTab


class MainWindow:
    def __init__(self, root, runtime):
        self.root = root
        self.runtime = runtime
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
        root.title("Device Control Panel")
        root.geometry("1040x800")
        root.minsize(900, 640)
        root.configure(bg=self.colors["bg"])
        self.setup_styles()
        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)
        self.devices = DeviceTab(root, notebook, runtime.actions, runtime.settings.commands, self.colors)
        self.logs = LogTab(root, notebook, runtime.settings.log_directory, self.colors)
        root.protocol("WM_DELETE_WINDOW", self.close)

    def close(self):
        self.devices.close()
        self.logs.close()
        self.root.destroy()

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


