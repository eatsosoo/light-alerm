"""Desktop command generator sharing the CRC implementation with the CLI."""

import tkinter as tk
from tkinter import ttk

from light_alarm.devices.protocol import FLASH_MODES, build_command
from light_alarm.ui.theme import COLORS, button, entry, label, select, separator


class CRCTab:
    FIELDS = (
        ("flash", "Flash · chế độ nháy", "01", "Chế độ 1–7 theo tài liệu thiết bị."),
        ("volume", "Volume · âm lượng", "01", "00 để tắt âm thanh."),
        ("play", "Play · chế độ phát", "00", "00 để phát lặp."),
        ("track", "Track · bài âm thanh", "01", "Bài 1–250, theo thứ tự chép file."),
    )
    OPTIONS = {
        "flash": {f"{value:02X} · {title}": f"{value:02X}" for value, title in FLASH_MODES.items()},
        "volume": {f"{value:02X} · " + ("Tắt âm thanh" if value == 0 else f"Âm lượng {value}"): f"{value:02X}"
                   for value in range(9)},
        "play": {f"{value:02X} · " + ("Phát lặp" if value == 0 else f"Phát {value} lần"): f"{value:02X}"
                 for value in range(17)},
        "track": {f"{value:02X} · Bài {value}": f"{value:02X}" for value in range(1, 251)},
    }

    @classmethod
    def option_label(cls, key, value):
        return next(title for title, code in cls.OPTIONS[key].items() if code == value)

    def __init__(self, root, notebook):
        self.root = root
        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Tạo mã CRC16")
        self.values = {key: tk.StringVar(value=self.option_label(key, default)) for key, _, default, _ in self.FIELDS}
        self.command = tk.StringVar()
        self.crc = tk.StringVar()
        self.preview = tk.StringVar()
        self.status = tk.StringVar()
        self._generated = ""
        self._traces = []
        header = tk.Frame(self.frame, bg=COLORS["bg"], padx=16, pady=16)
        header.pack(fill="x")
        label(header, "Tạo mã lệnh thiết bị", size=16, bold=True, bg=COLORS["bg"]).pack(anchor="w")
        label(header, "Chọn 4 thông số điều khiển để tạo mã HEX kèm CRC16 Modbus.",
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
            control = select(cell, self.values[key], width=18, state="readonly", values=list(self.OPTIONS[key]))
            control.pack(fill="x", pady=(9, 6))
            control.bind("<Return>", lambda event: self.generate())
            label(cell, hint, size=9, muted=True, wraplength=210, justify="left").pack(anchor="w")
            self.inputs[key] = control
        actions = tk.Frame(panel, bg=COLORS["panel"])
        actions.pack(fill="x", pady=(20, 0))
        button(actions, "Tạo mã lệnh", self.generate, kind="primary").pack(side="left")
        button(actions, "Giá trị mẫu", self.reset).pack(side="left", padx=10)
        label(actions, "Giá trị HEX được hiển thị trước mỗi lựa chọn.", muted=True, size=9).pack(side="left", padx=6)
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
        label(self.frame, "Theo PDF thiết bị, mục 8-1 / 8-2 (trang 9–10). Track được đánh số theo thứ tự chép file, "
              "không theo tên file. Muốn tắt đèn, dùng lệnh TURN_OFF trong màn hình Điều khiển.", bg=COLORS["bg"], muted=True,
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
            value = self.OPTIONS[key].get(self.values[key].get())
            if value is None:
                self._invalidate()
                self.status.set(f"{title}: chọn một giá trị trong danh sách.")
                self.feedback.configure(fg=COLORS["warning"])
                self.inputs[key].focus_set()
                return
            values[key] = value
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
            self.values[key].set(self.option_label(key, default))
        self.generate()

    def close(self):
        for variable, trace in self._traces:
            variable.trace_remove("write", trace)
        self._traces.clear()
