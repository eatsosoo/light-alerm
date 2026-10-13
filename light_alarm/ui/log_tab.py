"""Incremental daily log viewer with bounded display size."""

import logging
import tkinter as tk
from tkinter import ttk

from light_alarm.logging_setup import today_log_path
from light_alarm.ui.theme import COLORS, button, label, scroll_text

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
        self.follow = tk.BooleanVar(value=True)
        self.file_label = tk.StringVar()
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Nhật ký hệ thống")
        header = tk.Frame(frame, bg=COLORS["bg"], padx=16, pady=16)
        header.pack(fill="x")
        label(header, "Nhật ký hệ thống", size=16, bold=True, bg=COLORS["bg"]).pack(anchor="w")
        label(header, "Xem toàn bộ log trong ngày. Để theo dõi từng lần gửi, mở tab Yêu cầu.",
              muted=True, size=9, bg=COLORS["bg"]).pack(anchor="w", pady=(4, 0))
        toolbar = tk.Frame(frame, bg=COLORS["panel"], padx=12, pady=10)
        toolbar.pack(fill="x", padx=16)
        label(toolbar, variable=self.file_label, muted=True, size=9).pack(side="left")
        button(toolbar, "Tải lại", self.reload, pady=6).pack(side="right")
        button(toolbar, "Sao chép", self.copy_logs, pady=6).pack(side="right", padx=8)
        ttk.Checkbutton(toolbar, text="Theo dõi dòng mới", variable=self.follow).pack(side="right", padx=8)
        self.text = scroll_text(
            frame, wrap=tk.WORD, bg=COLORS["bg"], fg=COLORS["text"], insertbackground=COLORS["text"],
            font=("Consolas", 10), relief="flat", state="disabled",
        )
        self.text.pack(fill="both", expand=True, padx=14, pady=14)
        self.reload()
        self.schedule_refresh()

    def _display(self, content, reset=False):
        position = self.text.yview()[0]
        follow = self.follow.get() and (reset or self.text.yview()[1] >= 0.999)
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
        elif reset:
            self.text.yview_moveto(position)

    def reload(self):
        self.path = today_log_path(self.log_directory)
        self.file_label.set(f"{self.path.name}  ·  Tự cập nhật mỗi giây")
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
            self._display("Chưa có log cho hôm nay.", reset=True)
        except OSError:
            self._display("Không đọc được file log. Bấm Tải lại để thử lại.", reset=True)

    def copy_logs(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.text.get("1.0", "end-1c"))

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
