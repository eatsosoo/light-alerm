"""Desktop command generator sharing the CRC implementation with the CLI."""

import re
import tkinter as tk
from tkinter import ttk

from light_alarm.devices.protocol import build_command
from light_alarm.ui.theme import COLORS, button, entry, label, separator


class CRCTab:
    FIELDS = (
        ("flash", "Flash · chế độ nháy", "01", "Ví dụ 01. Nhập một byte HEX."),
        ("volume", "Volume · âm lượng", "01", "00 để tắt âm thanh."),
        ("play", "Play · chế độ phát", "00", "00 để phát lặp."),
        ("track", "Track · bài âm thanh", "01", "Ví dụ 01 để chọn bài số 1."),
    )

    def __init__(self, root, notebook):
        self.root = root
        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Tạo mã CRC16")
        self.values = {key: tk.StringVar(value=default) for key, _, default, _ in self.FIELDS}
        self.command = tk.StringVar()
        self.crc = tk.StringVar()
        self.preview = tk.StringVar()
        self.status = tk.StringVar()
        self._generated = ""
        self._traces = []
        header = tk.Frame(self.frame, bg=COLORS["bg"], padx=16, pady=16)
        header.pack(fill="x")
        label(header, "Tạo mã lệnh thiết bị", size=16, bold=True, bg=COLORS["bg"]).pack(anchor="w")
        label(header, "Nhập 4 byte điều khiển để tạo mã HEX kèm CRC16 Modbus.",
              muted=True, bg=COLORS["bg"]).pack(anchor="w", pady=(5, 0))

        panel = tk.Frame(self.frame, bg=COLORS["panel"], padx=22, pady=22)
        panel.pack(fill="x", padx=16, pady=(0, 16))
        fields = tk.Frame(panel, bg=COLORS["panel"])
        fields.pack(fill="x")
        self.inputs = {}
        for index, (key, title, _, hint) in enumerate(self.FIELDS):
            fields.columnconfigure(index, weight=1, uniform="crc-fields")
            cell = tk.Frame(fields, bg=COLORS["panel"])
            cell.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 14, 0))
            label(cell, title, size=10, bold=True).pack(anchor="w")
            control = entry(cell, self.values[key], width=8)
            control.pack(fill="x", pady=(9, 6))
            control.bind("<Return>", lambda event: self.generate())
            label(cell, hint, size=9, muted=True, wraplength=210, justify="left").pack(anchor="w")
            self.inputs[key] = control
        actions = tk.Frame(panel, bg=COLORS["panel"])
        actions.pack(fill="x", pady=(20, 0))
        button(actions, "Tạo mã lệnh", self.generate, kind="primary").pack(side="left")
        button(actions, "Giá trị mẫu", self.reset).pack(side="left", padx=10)
        label(actions, "Mỗi ô: 2 ký tự HEX, từ 00 đến FF.", muted=True, size=9).pack(side="left", padx=6)
        separator(panel).pack(fill="x", pady=22)

        label(panel, "MÃ HEX ĐẦY ĐỦ", size=9, muted=True).pack(anchor="w")
        output = entry(panel, self.command, width=65)
        output.input.configure(state="readonly", readonlybackground=COLORS["panel_alt"], font=("Consolas", 12))
        output.pack(fill="x", pady=(8, 12))
        result = tk.Frame(panel, bg=COLORS["panel"])
        result.pack(fill="x")
        label(result, "CRC16 (little-endian):", muted=True).pack(side="left")
        label(result, variable=self.crc, bold=True, fg=COLORS["success"]).pack(side="left", padx=10)
        self.copy_button = button(result, "Sao chép mã HEX", self.copy_command)
        self.copy_button.pack(side="right")
        label(panel, variable=self.preview, size=10, font=("Consolas", 10),
              muted=True, wraplength=950, justify="left").pack(anchor="w", pady=(18, 8))
        self.feedback = label(panel, variable=self.status, size=10, wraplength=950, justify="left")
        self.feedback.pack(anchor="w")
        label(self.frame, "Dùng cùng thuật toán với tools/crc16_cli.py. Mã được tạo theo frame CH9120 của dự án; "
              "giá trị điều khiển cần phù hợp với tài liệu thiết bị.", bg=COLORS["bg"], muted=True,
              size=9, wraplength=1000, justify="left").pack(anchor="w", padx=20)
        for variable in self.values.values():
            self._traces.append((variable, variable.trace_add("write", self._invalidate)))
        self.generate()

    def _invalidate(self, *args):
        self._generated = ""
        self.command.set("")
        self.crc.set("—")
        self.preview.set("")
        self.copy_button.configure(state="disabled", text="Sao chép mã HEX")
        self.status.set("Thông số đã thay đổi. Bấm Tạo mã lệnh để cập nhật.")
        self.feedback.configure(fg=COLORS["muted"])

    def generate(self):
        values = {}
        for key, title, _, _ in self.FIELDS:
            value = self.values[key].get().strip().upper()
            if re.fullmatch(r"[0-9A-F]{2}", value) is None:
                self._invalidate()
                self.status.set(f"{title}: nhập đúng 2 ký tự HEX (00–FF), ví dụ 01 hoặc 0A.")
                self.feedback.configure(fg=COLORS["warning"])
                self.inputs[key].focus_set()
                return
            values[key] = value
        for key, value in values.items():
            if self.values[key].get() != value:
                self.values[key].set(value)
        command = build_command(values["flash"], values["volume"], values["play"], values["track"])
        self._generated = command
        self.command.set(command)
        self.crc.set(command[-4:])
        self.preview.set("Theo byte: " + " ".join(command[index:index + 2] for index in range(0, len(command), 2)))
        self.status.set("Đã tạo mã lệnh. Có thể sao chép để sử dụng trong cấu hình thiết bị.")
        self.feedback.configure(fg=COLORS["success"])
        self.copy_button.configure(state="normal", text="Sao chép mã HEX")

    def copy_command(self):
        if self._generated:
            self.root.clipboard_clear()
            self.root.clipboard_append(self._generated)
            self.copy_button.configure(text="Đã sao chép")

    def reset(self):
        for key, _, default, _ in self.FIELDS:
            self.values[key].set(default)
        self.generate()

    def close(self):
        for variable, trace in self._traces:
            variable.trace_remove("write", trace)
        self._traces.clear()
