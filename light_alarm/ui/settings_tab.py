"""Edit YAML settings and command definitions without editing source files."""

import copy
import secrets
import tkinter as tk
from tkinter import ttk

from light_alarm.config_document import ConfigDocument
from light_alarm.config import local_host_ip
from light_alarm.ui.widgets import EyeButton, SwitchButton
from light_alarm.ui.theme import COLORS, button, entry, label, scrollbar, tabs


class SettingsTab:
    GROUPS = (
        ("Máy chủ", (
            ("HOST_IP", "IP server", "", "text"),
            ("PORT", "Port server", "5000", "int"),
            ("API_KEY", "API key", "", "secret"),
            ("SSL.CERT_PATH", "Đường dẫn chứng chỉ SSL", "", "text"),
            ("SSL.KEY_PATH", "Đường dẫn private key SSL", "", "text"),
        )),
        ("Database", (
            ("DATABASE.SQL_SERVER", "SQL Server (IP,port)", "", "text"),
            ("DATABASE.SQL_DATABASE", "Tên database", "", "text"),
            ("DATABASE.SQL_DRIVER", "ODBC driver", "ODBC Driver 17 for SQL Server", "text"),
            ("DATABASE.SQL_USER", "Tài khoản SQL", "", "text"),
            ("DATABASE.SQL_PASSWORD", "Mật khẩu SQL", "", "secret"),
        )),
        ("Thời gian", (
            ("TIMING.DEFAULT_DURATION", "Thời lượng mặc định (giây)", "5", "int"),
            ("TIMING.CONNECT_TIMEOUT", "Timeout kết nối thiết bị (giây)", "5", "float"),
            ("TIMING.RESPONSE_TIMEOUT", "Timeout phản hồi thiết bị (giây)", "5", "float"),
            ("TIMING.DATABASE_TIMEOUT", "Timeout SQL (giây)", "5", "int"),
        )),
    )

    def __init__(self, root, notebook, runtime, on_applied):
        self.root, self.runtime, self.on_applied = root, runtime, on_applied
        self.document = ConfigDocument(runtime.settings.config_path)
        self.variables, self.kinds = {}, {}
        self.commands = {}
        self._editing = None
        self._poll_job = None
        self._closed = False
        self.status = tk.StringVar()
        self.ssl_enabled = tk.BooleanVar()
        self.secret_fields = {}
        self.secret_buttons = {}
        self.secret_visibility = {}
        self.ssl_fields = []
        self.name, self.hex_value = tk.StringVar(), tk.StringVar()
        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Cấu hình")
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)
        header = tk.Frame(self.frame, bg=COLORS["bg"], padx=16, pady=16)
        header.grid(row=0, column=0, sticky="ew")
        label(header, "Cấu hình ứng dụng", size=16, bold=True, bg=COLORS["bg"]).pack(anchor="w")
        label(header, f"File: {self.document.path}", muted=True, size=9, bg=COLORS["bg"]).pack(anchor="w", pady=(5, 0))
        label(header, "Lệnh, database và timeout áp dụng cho yêu cầu mới. IP, port và SSL server cần khởi động lại.",
              muted=True, size=9, bg=COLORS["bg"]).pack(anchor="w", pady=(5, 0))
        pages = tabs(self.frame)
        pages.grid(row=1, column=0, sticky="nsew", padx=16)
        for title, specs in self.GROUPS:
            page = tk.Frame(pages, bg=COLORS["panel"], padx=20, pady=20)
            pages.add(page, text=title)
            for index, (path, caption, default, kind) in enumerate(specs):
                column, row = index % 2, index // 2
                page.columnconfigure(column, weight=1)
                cell = tk.Frame(page, bg=COLORS["panel"])
                cell.grid(row=row, column=column, sticky="ew", padx=(0 if column == 0 else 20, 0), pady=(0, 16))
                label(cell, caption, size=10).pack(anchor="w")
                variable = tk.StringVar(value=default)
                self.variables[path], self.kinds[path] = variable, kind
                field_row = tk.Frame(cell, bg=COLORS["panel"])
                field_row.pack(fill="x", pady=(7, 0))
                field = entry(field_row, variable)
                field.pack(side="left", fill="x", expand=True)
                if path in ("SSL.CERT_PATH", "SSL.KEY_PATH"):
                    self.ssl_fields.append(field.input)
                if kind == "secret":
                    field.input.configure(show="•")
                    self.secret_fields[path] = field.input
                    self.secret_visibility[path] = False
                    eye = EyeButton(field_row, COLORS, command=lambda key=path: self._toggle_secret(key))
                    eye.pack(side="right", padx=(4, 0))
                    self.secret_buttons[path] = eye
                if path == "API_KEY":
                    self.generate_key_button = button(field_row, "Tạo khóa", self.generate_api_key)
                    self.generate_key_button.pack(side="right", padx=(4, 0))
            if title == "Máy chủ":
                self.ssl_switch = SwitchButton(page, "HTTPS / SSL", self.ssl_enabled, COLORS,
                                                command=self._update_ssl_fields)
                self.ssl_switch.grid(row=3, column=0, sticky="w")
                label(page, "LIGHT_ALARM_API_KEY trong môi trường được ưu tiên. IP / port ở đây là HTTP API; "
                      "kết nối đèn cần thiết bị ở TCP Server (PDF ghi mặc định là TCP Client).",
                      muted=True, size=9, wraplength=850, justify="left").grid(
                          row=4, column=0, columnspan=2, sticky="w", pady=14)
        self.command_page = tk.Frame(pages, bg=COLORS["panel"], padx=20, pady=20)
        pages.add(self.command_page, text="Lệnh HEX")
        self.pages = pages
        self._build_commands()
        footer = tk.Frame(self.frame, bg=COLORS["panel"], padx=16, pady=12)
        footer.grid(row=2, column=0, sticky="ew", padx=16, pady=12)
        self.save_button = button(footer, "Lưu và áp dụng", self.save, kind="primary")
        self.save_button.pack(side="left")
        self.apply_button = button(footer, "Áp dụng lại", self.apply_saved)
        self.apply_button.pack(side="left", padx=8)
        self.reload_button = button(footer, "Đọc lại YAML", self.reload)
        self.reload_button.pack(side="left")
        self.feedback = label(self.frame, variable=self.status, muted=True, wraplength=1000, justify="left",
                              bg=COLORS["bg"])
        self.feedback.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 12))
        self._load_form()

    def _build_commands(self):
        page = self.command_page
        page.columnconfigure(0, weight=1)
        page.rowconfigure(1, weight=1)
        label(page, "Danh sách lệnh tạo nút trên màn hình Điều khiển. TURN_OFF là lệnh bắt buộc.",
              muted=True, size=9, wraplength=900, justify="left").grid(row=0, column=0, sticky="ew", pady=(0, 12))
        table_frame = tk.Frame(page, bg=COLORS["panel"])
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        self.table = ttk.Treeview(table_frame, columns=("name", "hex"), show="headings", height=6, selectmode="browse")
        for key, title, width in (("name", "Tên lệnh", 190), ("hex", "Mã HEX", 600)):
            self.table.heading(key, text=title, anchor="w")
            self.table.column(key, width=width, anchor="w")
        scroll = scrollbar(table_frame, command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.table.bind("<<TreeviewSelect>>", self._select_command)
        form = tk.Frame(page, bg=COLORS["panel"])
        form.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        form.columnconfigure(1, weight=1)
        label(form, "Tên lệnh", size=9, muted=True).grid(row=0, column=0, sticky="w")
        label(form, "Mã HEX (dán kết quả từ tab CRC16)", size=9, muted=True).grid(row=0, column=1, sticky="w", padx=12)
        self.name_input = entry(form, self.name, width=20)
        self.name_input.grid(row=1, column=0, sticky="ew", pady=6)
        entry(form, self.hex_value).grid(row=1, column=1, sticky="ew", padx=12, pady=6)
        button(form, "Thêm / cập nhật", self.update_command).grid(row=1, column=2, pady=6)
        actions = tk.Frame(page, bg=COLORS["panel"])
        actions.grid(row=3, column=0, sticky="ew", pady=(6, 0))
        button(actions, "Lệnh mới", self.new_command).pack(side="left")
        button(actions, "Xóa lệnh đang chọn", self.delete_command, kind="danger").pack(side="left", padx=10)

    def _set_status(self, text, error=False):
        self.status.set(text)
        self.feedback.configure(fg=COLORS["warning"] if error else COLORS["muted"])

    def _load_form(self):
        data = self.document.data
        for path, variable in self.variables.items():
            value = data
            for key in path.split("."):
                value = value.get(key) if isinstance(value, dict) else None
            if value is None:
                value = next(default for _, specs in self.GROUPS for field, _, default, _ in specs if field == path)
            if path == "HOST_IP" and not value:
                value = local_host_ip()
            variable.set(str(value))
        self.ssl_enabled.set(bool((data.get("SSL") or {}).get("ENABLED", False)))
        self._update_ssl_fields()
        self.commands = dict((data.get("CH9120") or {}).get("COMMANDS", {}))
        self.new_command()
        self._render_commands()
        self._set_status("Đã đọc YAML. Chỉnh sửa, cập nhật lệnh vào bảng, sau đó bấm Lưu và áp dụng.")

    def _render_commands(self):
        self.table.delete(*self.table.get_children())
        for name, command in self.commands.items():
            self.table.insert("", "end", iid=name, values=(name, command))

    def _select_command(self, event=None):
        selected = self.table.selection()
        if selected and selected[0] in self.commands:
            self._editing = selected[0]
            self.name.set(self._editing)
            self.hex_value.set(self.commands[self._editing])

    def new_command(self):
        self._editing = None
        self.name.set("")
        self.hex_value.set("")
        self.table.selection_remove(self.table.selection())

    def update_command(self):
        name = self.name.get().strip()
        command = "".join(self.hex_value.get().split()).upper()
        try:
            if not name or not command or not bytes.fromhex(command):
                raise ValueError("Tên lệnh và mã HEX hợp lệ là bắt buộc.")
            if self._editing == "TURN_OFF" and name != "TURN_OFF":
                raise ValueError("Không thể đổi tên lệnh TURN_OFF.")
            if name in self.commands and name != self._editing:
                raise ValueError("Tên lệnh đã tồn tại. Chọn dòng đó để sửa.")
            if self._editing and self._editing != name:
                self.commands.pop(self._editing, None)
            self.commands[name] = command
            self._editing = name
            self._render_commands()
            self.table.selection_set(name)
            self._set_status("Đã cập nhật lệnh vào bảng. Bấm Lưu và áp dụng để ghi YAML.")
            return True
        except ValueError as error:
            self._set_status(str(error), error=True)
            return False

    def delete_command(self):
        selected = self.table.selection()
        if not selected:
            return
        if selected[0] == "TURN_OFF":
            self._set_status("Không thể xóa lệnh TURN_OFF.", error=True)
            return
        self.commands.pop(selected[0], None)
        self.new_command()
        self._render_commands()
        self._set_status("Đã xóa khỏi bảng. Bấm Lưu và áp dụng để ghi YAML.")

    def _collect(self):
        if self.name.get().strip() or self.hex_value.get().strip():
            if not self.update_command():
                raise ValueError(self.status.get())
        data = copy.deepcopy(self.document.data)
        for path, variable in self.variables.items():
            raw = variable.get()
            kind = self.kinds[path]
            try:
                value = int(raw) if kind == "int" else float(raw) if kind == "float" else raw if kind == "secret" else raw.strip()
            except ValueError as error:
                raise ValueError(f"{path}: cần nhập {'số nguyên' if kind == 'int' else 'số' }.") from error
            target = data
            keys = path.split(".")
            for key in keys[:-1]:
                if not isinstance(target.get(key), dict):
                    target[key] = {}
                target = target[key]
            target[keys[-1]] = value
        data.setdefault("SSL", {})["ENABLED"] = self.ssl_enabled.get()
        data.setdefault("CH9120", {})["COMMANDS"] = dict(self.commands)
        return data

    def save(self):
        try:
            settings = self.document.save(self._collect())
        except (ValueError, OSError) as error:
            self._set_status(str(error), error=True)
            return
        self._set_status("Đã lưu YAML và bản sao .yaml.bak. Đang áp dụng…")
        self._apply(settings)

    def apply_saved(self):
        from light_alarm.config import Settings
        try:
            settings = Settings.from_mapping(self.document.data, self.document.path)
        except ValueError as error:
            self._set_status(str(error), error=True)
            return
        self._apply(settings)

    def _apply(self, settings):
        try:
            future = self.runtime.apply_settings(settings)
        except RuntimeError as error:
            self._set_status(str(error), error=True)
            return
        for control in (self.save_button, self.apply_button, self.reload_button):
            control.configure(state="disabled")

        def poll():
            self._poll_job = None
            if self._closed:
                return
            if not future.done():
                self._poll_job = self.root.after(100, poll)
                return
            for control in (self.save_button, self.apply_button, self.reload_button):
                control.configure(state="normal")
            try:
                restart = future.result()
            except Exception as error:
                self._set_status(str(error), error=True)
                return
            self.on_applied(self.runtime.settings)
            self._set_status("Đã áp dụng lệnh, database, API key và thời gian. " +
                             ("Khởi động lại ứng dụng để đổi IP / port / SSL server." if restart else ""))
        self._poll_job = self.root.after(100, poll)

    def reload(self):
        try:
            self.document.reload()
            self._load_form()
        except (ValueError, OSError) as error:
            self._set_status(str(error), error=True)

    def _update_ssl_fields(self):
        for control in self.ssl_fields:
            control.configure(state="normal" if self.ssl_enabled.get() else "disabled",
                              disabledbackground=COLORS["panel_alt"], disabledforeground=COLORS["muted"])

    def generate_api_key(self):
        self.variables["API_KEY"].set(secrets.token_urlsafe(32))
        self._set_status("Đã tạo API key mới. Bấm Lưu và áp dụng để sử dụng. "
                         "LIGHT_ALARM_API_KEY trong môi trường vẫn được ưu tiên.")

    def _toggle_secret(self, path):
        visible = not self.secret_visibility[path]
        self.secret_visibility[path] = visible
        self.secret_fields[path].configure(show="" if visible else "•")
        self.secret_buttons[path].set_visible(visible)

    def close(self):
        self._closed = True
        if self._poll_job:
            self.root.after_cancel(self._poll_job)
