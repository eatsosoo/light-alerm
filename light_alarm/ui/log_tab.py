"""Incremental daily log viewer with bounded display size."""

import logging
import tkinter as tk
from tkinter import scrolledtext, ttk

from light_alarm.logging_setup import today_log_path

logger = logging.getLogger(__name__)


class LogTab:
    MAX_BYTES = 1024 * 1024
    MAX_LINES = 5000

    def __init__(self, root, notebook, log_directory, colors):
        self.root = root
        self.log_directory = log_directory
        self.path = None
        self.position = 0
        self.refresh_job = None
        self.closed = False
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="System Logs")
        self.text = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD, bg="#1e1e1e", fg="white", insertbackground="white",
            font=("Consolas", 10), relief="flat", state="disabled",
        )
        self.text.pack(fill="both", expand=True, padx=14, pady=14)
        tk.Button(
            frame, text="Refresh Logs", command=self.reload, bg=colors["panel_alt"],
            fg=colors["text"], activebackground=colors["border"], relief="flat",
            padx=12, pady=7, font=("Segoe UI", 9, "bold"), cursor="hand2",
        ).pack(side="bottom", pady=(0, 10))
        self.reload()
        self.schedule_refresh()

    def _display(self, content, reset=False):
        follow = reset or self.text.yview()[1] >= 0.999
        self.text.configure(state="normal")
        if reset:
            self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, content)
        count = int(self.text.index("end-1c").split(".")[0])
        if count > self.MAX_LINES:
            self.text.delete("1.0", f"{count - self.MAX_LINES + 1}.0")
        self.text.configure(state="disabled")
        if follow:
            self.text.see(tk.END)

    def reload(self):
        self.path = today_log_path(self.log_directory)
        self.position = 0
        try:
            with self.path.open("rb") as stream:
                stream.seek(0, 2)
                size = stream.tell()
                stream.seek(max(0, size - self.MAX_BYTES))
                content = stream.read(self.MAX_BYTES)
                self.position = stream.tell()
            self._display(content.decode("utf-8", errors="replace"), reset=True)
        except FileNotFoundError:
            self._display(f"No log file found for today: {self.path}", reset=True)
        except OSError:
            self._display("Could not read log file.", reset=True)

    def append_new_logs(self):
        path = today_log_path(self.log_directory)
        try:
            size = path.stat().st_size
            if path != self.path or size < self.position or self.position == 0:
                self.reload()
                return
            if size == self.position:
                return
            with path.open("rb") as stream:
                stream.seek(self.position)
                content = stream.read(self.MAX_BYTES)
                self.position = stream.tell()
            self._display(content.decode("utf-8", errors="replace"))
        except FileNotFoundError:
            if path != self.path or self.position:
                self.reload()
        except OSError:
            # A temporary read error must not stop subsequent refreshes.
            return

    def schedule_refresh(self):
        if not self.closed:
            self.refresh_job = self.root.after(1000, self.refresh)

    def refresh(self):
        self.refresh_job = None
        if self.closed:
            return
        try:
            self.append_new_logs()
        finally:
            self.schedule_refresh()

    def close(self):
        self.closed = True
        if self.refresh_job:
            self.root.after_cancel(self.refresh_job)
            self.refresh_job = None
