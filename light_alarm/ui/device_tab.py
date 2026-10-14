"""Device browser and command panel with explicit target scope."""

import logging
import tkinter as tk
from tkinter import messagebox, ttk

from light_alarm.ui.theme import COLORS, button, entry, label, metric, scrollbar, select, separator

logger = logging.getLogger(__name__)


class DeviceTab:
    def __init__(self, root, notebook, actions, commands, colors, default_duration=5):
        self.root, self.actions, self.commands = root, actions, commands
        self.colors = colors
        self.selected_line = tk.StringVar(value="Tất cả")
        self.search_var = tk.StringVar()
        self.duration_var = tk.StringVar(value=str(default_duration))
        self.status_var = tk.StringVar(value="Đang tải danh sách thiết bị…")
        self.target_var = tk.StringVar(value="0 thiết bị sẽ nhận lệnh")
        self.total_var, self.visible_var, self.lines_var = (tk.StringVar(value="0") for _ in range(3))
        self.records, self.filtered_records = [], []
        self._closed, self._loading = False, False
        self._poll_jobs = set()
        self._command_sequence = 0
        self._sort_key, self._sort_reverse = "station_name", False
        self._last_job_id = None
        self.on_request = None
        self.command_buttons = []
        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Điều khiển")
        metrics = tk.Frame(self.frame, bg=COLORS["bg"])
        metrics.pack(fill="x", padx=16, pady=(16, 12))
        metric(metrics, "THIẾT BỊ ĐÃ TẢI", self.total_var, 0)
        metric(metrics, "ĐANG HIỂN THỊ / NHẬN LỆNH", self.visible_var, 1, COLORS["success"])
        metric(metrics, "LINE", self.lines_var, 2)

        body = tk.Frame(self.frame, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, minsize=280)
        body.rowconfigure(0, weight=1)
        browser = tk.Frame(body, bg=COLORS["panel"], padx=14, pady=14)
        browser.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._build_browser(browser)
        controls = tk.Frame(body, bg=COLORS["panel"], padx=16, pady=16, width=280)
        controls.grid(row=0, column=1, sticky="nsew")
        self._build_controls(controls)
        self.load_devices()

    def _build_browser(self, parent):
        label(parent, "Danh sách thiết bị", size=13, bold=True).pack(anchor="w")
        label(parent, "Lọc theo trạm, IP hoặc line. Bấm tiêu đề cột để sắp xếp.", size=9,
              muted=True).pack(anchor="w", pady=(3, 14))
        filters = tk.Frame(parent, bg=COLORS["panel"])
        filters.pack(fill="x", pady=(0, 12))
        filters.columnconfigure(0, weight=1)
        label(filters, "Tìm thiết bị", size=9, muted=True).grid(row=0, column=0, sticky="w")
        label(filters, "Line", size=9, muted=True).grid(row=0, column=1, sticky="w", padx=8)
        self.search_entry = entry(filters, self.search_var, width=20)
        self.search_entry.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        self.search_entry.bind("<KeyRelease>", lambda event: self.apply_filters())
        self.search_entry.bind("<Escape>", lambda event: self.clear_filters())
        self.line_filter = select(filters, self.selected_line, state="readonly", values=["Tất cả"], width=13)
        self.line_filter.grid(row=1, column=1, sticky="ew", padx=8, pady=(5, 0))
        self.line_filter.bind("<<ComboboxSelected>>", lambda event: self.apply_filters())
        self.refresh_button = button(filters, "Tải lại", self.load_devices)
        self.refresh_button.grid(row=1, column=2, pady=(5, 0))
        button(filters, "Xóa lọc", self.clear_filters, padx=8).grid(row=1, column=3, padx=(8, 0), pady=(5, 0))
        table_frame = tk.Frame(parent, bg=COLORS["panel"])
        table_frame.pack(fill="both", expand=True)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        columns = (("station_name", "Trạm", 190), ("line", "Line", 100),
                   ("ip", "Địa chỉ IP", 140), ("port", "Port", 70))
        self._headings = {key: title for key, title, _ in columns}
        self.tree = ttk.Treeview(table_frame, columns=[item[0] for item in columns],
                                 show="headings", selectmode="browse", height=9)
        for key, title, width in columns:
            anchor = "center" if key == "port" else "w"
            self.tree.heading(key, text=title, anchor=anchor, command=lambda column=key: self.sort_by(column))
            self.tree.column(key, width=width, minwidth=65, anchor=anchor)
        self.tree.tag_configure("even", background=COLORS["panel"])
        self.tree.tag_configure("odd", background=COLORS["panel_alt"])
        vertical = scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        horizontal = scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.empty_label = label(table_frame, "Đang tải thiết bị…", muted=True, justify="center", anchor="center")
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")

    def _build_controls(self, parent):
        label(parent, "Gửi lệnh", size=13, bold=True).pack(anchor="w")
        label(parent, variable=self.target_var, size=11, bold=True,
              fg=COLORS["success"]).pack(anchor="w", pady=(12, 4))
        label(parent, "Áp dụng cho toàn bộ danh sách\nđang hiển thị sau khi lọc.", muted=True,
              size=9, justify="left").pack(anchor="w", pady=(0, 16))
        label(parent, "Thời lượng cảnh báo (giây)", size=9, muted=True).pack(anchor="w")
        self.duration_entry = entry(parent, self.duration_var, width=18)
        self.duration_entry.pack(fill="x", pady=(6, 3))
        label(parent, "Không áp dụng cho tắt và đọc trạng thái.", size=8, muted=True).pack(anchor="w", pady=(0, 14))

        command_frame = tk.Frame(parent, bg=COLORS["panel"])
        command_frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(command_frame, bg=COLORS["panel"], bd=0, highlightthickness=0, width=245, height=180)
        scroll = scrollbar(command_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        contents = tk.Frame(canvas, bg=COLORS["panel"])
        window = canvas.create_window((0, 0), window=contents, anchor="nw")
        contents.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))
        def scroll_commands(event):
            if canvas.bbox("all") and canvas.bbox("all")[3] > canvas.winfo_height():
                canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
            return "break"

        canvas.bind("<MouseWheel>", scroll_commands)
        contents.bind("<MouseWheel>", scroll_commands)
        self._command_contents = contents
        self._scroll_commands = scroll_commands
        self._build_command_buttons()

        separator(parent).pack(fill="x", pady=12)
        self.feedback = label(parent, variable=self.status_var, size=9, muted=True, justify="left", wraplength=245)
        self.feedback.pack(fill="x")
        self.request_button = button(parent, "Xem yêu cầu vừa gửi →", self.open_last_request)
        self.request_button.pack(fill="x", pady=(10, 0))
        self.request_button.configure(state="disabled")

    def _build_command_buttons(self):
        for control in self.command_buttons:
            control.destroy()
        self.command_buttons.clear()
        ordered = (["TURN_OFF"] if "TURN_OFF" in self.commands else [])
        ordered += [name for name in self.commands if name not in ("TURN_OFF", "READ_ALL")]
        ordered += (["READ_ALL"] if "READ_ALL" in self.commands else [])
        for name in ordered:
            title = {"TURN_OFF": "Tắt cảnh báo", "READ_ALL": "Đọc trạng thái",
                     "FLASH_ONLY": "Nháy đèn", "SOUND_FLASH": "Âm thanh và nháy đèn"}.get(name, name.replace("_", " "))
            kind = "danger" if name == "TURN_OFF" else "secondary"
            control = button(self._command_contents, title, lambda mode=name: self.send_to_selected_line(mode), kind=kind, anchor="w")
            control.pack(fill="x", pady=(0, 7))
            control.bind("<MouseWheel>", self._scroll_commands)
            self.command_buttons.append(control)

    def apply_settings(self, settings):
        self.commands = dict(settings.commands)
        self.duration_var.set(str(settings.default_duration))
        self._build_command_buttons()
        self._update_buttons()
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

    def _update_buttons(self):
        enabled = bool(self.filtered_records) and not self._loading
        for control in self.command_buttons:
            control.configure(state="normal" if enabled else "disabled")
        self.refresh_button.configure(state="disabled" if self._loading else "normal",
                                      text="Đang tải…" if self._loading else "Tải lại")

    def load_devices(self):
        if self._loading:
            return
        self._loading = True
        self.status_var.set("Đang tải danh sách thiết bị…")
        self._update_buttons()
        try:
            future = self.actions.load_devices()
        except Exception:
            self._load_failed()
            return

        def loaded(completed):
            try:
                records = list(completed.result())
            except Exception:
                self._load_failed()
                return
            self._loading = False
            self.records = records
            self.refresh_line_options()
            self.apply_filters()
            self.status_var.set("Danh sách đã cập nhật. Chọn lệnh để gửi.")
            self.feedback.configure(fg=COLORS["muted"])

        self._watch(future, loaded)

    def _load_failed(self):
        logger.exception("Device list load failed")
        self._loading = False
        self.status_var.set("Không tải được thiết bị. Hãy thử tải lại hoặc xem nhật ký.")
        self.feedback.configure(fg=COLORS["warning"])
        if not self.records:
            self.empty_label.configure(text="Không tải được danh sách\nBấm Tải lại để thử lại.")
        self._update_buttons()

    def send_to_selected_line(self, command):
        targets = self.get_command_targets()
        if not targets or self._loading:
            return
        try:
            job_id, future = self.actions.send_devices(targets, command, self.duration_var.get().strip())
        except (ValueError, RuntimeError) as error:
            message = {
                "Duration must be a non-negative integer.": "Thời lượng phải là số nguyên không âm, tính bằng giây.",
                "Application is shutting down.": "Ứng dụng đang đóng. Không thể gửi thêm lệnh.",
                "Invalid mode.": "Lệnh không có trong cấu hình hiện tại.",
            }.get(str(error), str(error))
            messagebox.showerror("Không thể gửi lệnh", message, parent=self.root)
            self.duration_entry.focus_set()
            return
        self._last_job_id = job_id
        self.request_button.configure(state="normal")
        self._command_sequence += 1
        sequence = self._command_sequence
        self.status_var.set(f"#{job_id[:8]} · {command}\nĐang xử lý {len(targets)} thiết bị…")
        self.feedback.configure(fg=COLORS["text"])

        def finished(completed):
            try:
                result = completed.result()
            except Exception:
                logger.exception("Desktop command failed | request=%s | mode=%s", job_id, command)
                if sequence == self._command_sequence:
                    self.status_var.set(f"#{job_id[:8]} · Yêu cầu lỗi.\nMở chi tiết để xem nguyên nhân.")
                    self.feedback.configure(fg=COLORS["warning"])
                return
            if sequence == self._command_sequence:
                self.status_var.set(f"#{job_id[:8]} · Đã xử lý\n{result['success']} đã gửi · {result['failure']} lỗi\n"
                                    f"{result['superseded']} bị thay thế")
                self.feedback.configure(fg=COLORS["warning"] if result["failure"] else COLORS["success"])

        self._watch(future, finished)

    def open_last_request(self):
        if self._last_job_id and self.on_request:
            self.on_request(self._last_job_id)

    def refresh_line_options(self):
        lines = sorted({str(item.get("line") or "").strip() for item in self.records if item.get("line")})
        current = self.selected_line.get()
        self.line_filter["values"] = ["Tất cả"] + lines
        self.selected_line.set(current if current in lines else "Tất cả")
        self.lines_var.set(str(len(lines)))

    def clear_filters(self):
        self.search_var.set("")
        self.selected_line.set("Tất cả")
        self.apply_filters()

    def sort_by(self, key):
        self._sort_reverse = not self._sort_reverse if key == self._sort_key else False
        self._sort_key = key
        self.apply_filters()

    def apply_filters(self):
        keyword = self.search_var.get().strip().casefold()
        line = self.selected_line.get()
        self.filtered_records = [device for device in self.records
            if (line == "Tất cả" or str(device.get("line") or "").strip() == line)
            and (not keyword or any(keyword in str(device.get(key) or "").casefold()
                                    for key in ("station_name", "line", "ip", "port")))]
        def sort_value(item):
            value = item.get(self._sort_key)
            if self._sort_key == "port":
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return -1
            return str(value or "").casefold()

        self.filtered_records.sort(key=sort_value, reverse=self._sort_reverse)
        self.render_device_rows()

    def render_device_rows(self):
        for key, title in self._headings.items():
            suffix = (" ↓" if self._sort_reverse else " ↑") if key == self._sort_key else ""
            self.tree.heading(key, text=title + suffix)
        self.tree.delete(*self.tree.get_children())
        for index, device in enumerate(self.filtered_records):
            self.tree.insert("", "end", values=tuple(device.get(key) or "—"
                for key in ("station_name", "line", "ip", "port")), tags=("odd" if index % 2 else "even",))
        count = len(self.filtered_records)
        self.total_var.set(str(len(self.records)))
        self.visible_var.set(str(count))
        self.target_var.set(f"{count} thiết bị sẽ nhận lệnh")
        if count:
            self.empty_label.place_forget()
        else:
            self.empty_label.configure(text="Không có thiết bị phù hợp\nThử xóa bộ lọc hoặc tải lại danh sách.")
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        self._update_buttons()

    def get_command_targets(self):
        return list(self.filtered_records)

    def close(self):
        self._closed = True
        for handle in self._poll_jobs:
            self.root.after_cancel(handle)
        self._poll_jobs.clear()
