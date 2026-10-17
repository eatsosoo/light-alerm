"""Request table with statuses, per-device results and correlated log events."""

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from light_alarm.ui.theme import COLORS, button, entry, label, metric, scrollbar, select, scroll_text, tabs


STATUS_LABELS = {
    "queued": "Chờ xử lý", "running": "Đang chạy", "completed": "Hoàn tất",
    "partial": "Một phần", "failed": "Lỗi", "cancelled": "Đã hủy",
    "superseded": "Đã thay thế",
}
DEVICE_STATUS_LABELS = {"success": "Đã gửi", "failure": "Lỗi", "superseded": "Đã thay thế"}


class RequestLogTab:
    def __init__(self, root, notebook, history, colors):
        self.root = root
        self.history = history
        self.closed = False
        self.refresh_job = None
        self.search = tk.StringVar()
        self.status_filter = tk.StringVar(value="Tất cả")
        self.summary = tk.StringVar()
        self.details = tk.StringVar(value="Chọn một yêu cầu để xem kết quả và log liên quan.")
        self._selected_id = None
        self._last_content = None
        self._last_devices = None
        self.frame = frame = ttk.Frame(notebook)
        notebook.add(frame, text="Yêu cầu")
        header = tk.Frame(frame, bg=COLORS["bg"])
        header.pack(fill="x", padx=16, pady=(16, 10))
        label(header, "Theo dõi yêu cầu", size=16, bold=True, bg=COLORS["bg"]).pack(anchor="w")
        label(header, "Mỗi lần gửi là một yêu cầu. Chọn một dòng để xem kết quả và log tương ứng.",
              muted=True, size=9, bg=COLORS["bg"]).pack(anchor="w", pady=(4, 0))
        metrics = tk.Frame(frame, bg=COLORS["bg"])
        metrics.pack(fill="x", padx=16, pady=(0, 12))
        self.total_var, self.active_var, self.error_var = (tk.StringVar(value="0") for _ in range(3))
        metric(metrics, "YÊU CẦU TRONG LỊCH SỬ", self.total_var, 0)
        metric(metrics, "ĐANG XỬ LÝ", self.active_var, 1, COLORS["accent"])
        metric(metrics, "LỖI / MỘT PHẦN", self.error_var, 2, COLORS["warning"])

        toolbar = tk.Frame(frame, bg=colors["panel"], padx=12, pady=10)
        toolbar.pack(fill="x", padx=14, pady=(14, 8))
        toolbar.columnconfigure(0, weight=1)
        label(toolbar, "Tìm theo mã, lệnh hoặc line", size=9, muted=True).grid(row=0, column=0, sticky="w")
        label(toolbar, "Trạng thái", size=9, muted=True).grid(row=0, column=1, sticky="w", padx=10)
        search_entry = entry(toolbar, self.search, width=24)
        search_entry.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        search_entry.bind("<KeyRelease>", lambda event: self.refresh_table())
        search_entry.bind("<Escape>", lambda event: self.clear_filters())
        status = select(toolbar, self.status_filter, state="readonly", width=16,
                        values=["Tất cả"] + list(STATUS_LABELS.values()))
        status.grid(row=1, column=1, padx=10, pady=(5, 0))
        status.bind("<<ComboboxSelected>>", lambda event: self.refresh_table())
        button(toolbar, "Xóa lọc", self.clear_filters).grid(row=1, column=2, padx=(0, 10), pady=(5, 0))
        self.copy_button = button(toolbar, "Sao chép mã", self.copy_id)
        self.copy_button.grid(row=1, column=3, pady=(5, 0))
        label(toolbar, variable=self.summary, size=9, muted=True).grid(row=0, column=3, sticky="e")

        panes = ttk.Panedwindow(frame, orient="vertical")
        panes.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        table_frame = ttk.Frame(panes)
        panes.add(table_frame, weight=2)
        columns = (
            ("time", "Thời gian", 150), ("id", "Request ID", 105),
            ("source", "Nguồn", 75), ("mode", "Lệnh", 120),
            ("scope", "Line / phạm vi", 150), ("targets", "Thiết bị", 75),
            ("status", "Trạng thái", 120), ("counts", "Gửi / Lỗi / Thay thế", 155),
        )
        self.table = self._table(table_frame, columns, height=6)
        self.empty_label = label(table_frame, "Chưa có yêu cầu nào\nGửi lệnh từ màn hình Điều khiển để bắt đầu.",
                                 muted=True, justify="center", anchor="center")
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        self.table.bind("<<TreeviewSelect>>", lambda event: self.show_details())
        for state, color in {"failed": "#ff8585", "partial": "#f2c66d", "completed": "#76d7a4",
                             "running": "#8bbcff", "queued": "#8bbcff", "superseded": "#aeb6c2",
                             "cancelled": "#aeb6c2"}.items():
            self.table.tag_configure(state, foreground=color)

        detail_frame = ttk.Frame(panes)
        panes.add(detail_frame, weight=3)
        tk.Label(detail_frame, textvariable=self.details, anchor="w", justify="left", wraplength=950,
                 bg=colors["bg"], fg=colors["text"], padx=4, pady=8).pack(fill="x")
        self.detail_tabs = detail_tabs = tabs(detail_frame)
        detail_tabs.pack(fill="both", expand=True)
        self.device_frame = device_frame = ttk.Frame(detail_tabs)
        detail_tabs.add(device_frame, text="Kết quả thiết bị")
        self.devices = self._table(device_frame, (
            ("station", "Trạm", 130), ("line", "Line", 90), ("endpoint", "IP:Port", 150),
            ("mode", "Lệnh", 100), ("status", "Kết quả", 110), ("error", "Lỗi / phản hồi HEX", 300),
        ), height=4)
        self.log_frame = log_frame = ttk.Frame(detail_tabs)
        detail_tabs.add(log_frame, text="Log của yêu cầu")
        log_toolbar = tk.Frame(log_frame, bg=COLORS["panel"], padx=10, pady=6)
        log_toolbar.pack(fill="x")
        label(log_toolbar, "Log được nhóm theo Request ID", muted=True, size=9).pack(side="left")
        button(log_toolbar, "Sao chép log", self.copy_logs, pady=5).pack(side="right")
        self.log_text = scroll_text(
            log_frame, height=7, wrap=tk.WORD, bg=COLORS["bg"], fg=COLORS["text"],
            font=("Consolas", 9), state="disabled", relief="flat",
        )
        self.log_text.pack(fill="both", expand=True, pady=(8, 0))
        self.log_text.tag_configure("error", foreground="#ff8585")
        self.log_text.tag_configure("warning", foreground=COLORS["warning"])
        self.refresh()

    @staticmethod
    def _table(parent, columns, height):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        table = ttk.Treeview(parent, columns=[column[0] for column in columns],
                             show="headings", selectmode="browse", height=height)
        for key, label, width in columns:
            anchor = "center" if key in ("targets", "status", "counts") else "w"
            table.heading(key, text=label, anchor=anchor)
            table.column(key, width=width, minwidth=60, anchor=anchor)
        vertical = scrollbar(parent, orient="vertical", command=table.yview)
        horizontal = scrollbar(parent, orient="horizontal", command=table.xview)
        table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        table.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        return table

    @staticmethod
    def _time(value):
        return datetime.fromisoformat(value).strftime("%d/%m %H:%M:%S") if value else "—"

    def refresh_table(self):
        records = self.history.list()
        self.total_var.set(str(len(records)))
        self.active_var.set(str(sum(item["status"] in ("queued", "running") for item in records)))
        self.error_var.set(str(sum(item["status"] in ("failed", "partial") for item in records)))
        keyword = self.search.get().strip().lower()
        status = self.status_filter.get()
        visible = [item for item in records
                   if (status == "Tất cả" or STATUS_LABELS.get(item["status"]) == status)
                   and (not keyword or keyword in " ".join(str(item.get(key, ""))
                        for key in ("job_id", "mode", "scope", "source", "message")).lower())]
        ids = {item["job_id"] for item in visible}
        for existing in self.table.get_children():
            if existing not in ids:
                self.table.delete(existing)
        for index, item in enumerate(visible):
            counts = item["counts"]
            result = "—" if counts is None else f"{counts['success']} / {counts['failure']} / {counts['superseded']}"
            values = (self._time(item["created_at"]), item["job_id"][:8],
                      {"api": "API", "desktop": "Giao diện"}.get(item["source"], item["source"]), item["mode"],
                      item["scope"], item["target_count"] if item["target_count"] is not None else "—",
                      STATUS_LABELS.get(item["status"], item["status"]), result)
            if self.table.exists(item["job_id"]):
                self.table.item(item["job_id"], values=values, tags=(item["status"],))
            else:
                self.table.insert("", "end", iid=item["job_id"], values=values, tags=(item["status"],))
            self.table.move(item["job_id"], "", index)
        self.summary.set(f"{len(visible)}/{len(records)} yêu cầu")
        if visible:
            self.empty_label.place_forget()
        else:
            self.empty_label.configure(text="Không có yêu cầu phù hợp\nThử xóa bộ lọc." if records else
                                       "Chưa có yêu cầu nào\nGửi lệnh từ màn hình Điều khiển để bắt đầu.")
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        if not self.table.selection() and visible:
            self.table.selection_set(visible[0]["job_id"])
        self.show_details()

    def show_details(self):
        selection = self.table.selection()
        item = self.history.get(selection[0]) if selection else None
        selected = item["job_id"] if item else None
        changed = selected != self._selected_id
        self._selected_id = selected
        self.copy_button.configure(state="normal" if selected else "disabled")
        if changed:
            self.copy_button.configure(text="Sao chép mã")
        if item is None:
            self.details.set("Chọn một yêu cầu để xem kết quả và log liên quan.")
            devices = []
            content = ""
        else:
            elapsed = ""
            if item["started_at"]:
                start = datetime.fromisoformat(item["started_at"])
                end = datetime.fromisoformat(item["finished_at"]) if item["finished_at"] else datetime.now().astimezone()
                elapsed = f" | Đã chạy: {max(0, (end - start).total_seconds()):.0f}s"
            self.details.set(
                f"Request ID: {selected}\n"
                f"{item['source']} | {item['mode']} | {item['scope']} | "
                f"Thời lượng yêu cầu: {item['duration']}s | {STATUS_LABELS.get(item['status'], item['status'])}{elapsed}\n"
                f"Bắt đầu: {self._time(item['started_at'])} | Kết thúc: {self._time(item['finished_at'])}"
            )
            devices = (item["result"] or {}).get("devices", [])
            events = [f"{self._time(event['time'])} | {event['level']} | {event['message']}" for event in item["events"]]
            if item["events_dropped"]:
                events.insert(0, f"Đã lược bớt {item['events_dropped']} dòng log cũ; xem Nhật ký hệ thống với Request ID đầy đủ.")
            if item["message"]:
                events.append(f"Lỗi: {item['message']}")
            content = "\n".join(events) or "Đang chờ log của yêu cầu..."
        if changed or devices != self._last_devices:
            self.devices.delete(*self.devices.get_children())
            for device in devices:
                self.devices.insert("", "end", values=(device.get("station"), device.get("line"),
                    f"{device['ip']}:{device['port']}", device.get("mode"),
                    DEVICE_STATUS_LABELS.get(device["status"], device["status"]),
                    device.get("error") or device.get("response") or "—"))
            self._last_devices = devices
        if changed:
            self.detail_tabs.select(self.device_frame if devices else self.log_frame)
        if changed or content != self._last_content:
            position = self.log_text.yview()
            follow = changed or position[1] >= 0.999
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", tk.END)
            self.log_text.insert(tk.END, content)
            for index, line in enumerate(content.splitlines(), start=1):
                tag = "error" if "| ERROR |" in line or line.startswith("Lỗi:") else "warning" if "| WARNING |" in line else None
                if tag:
                    self.log_text.tag_add(tag, f"{index}.0", f"{index}.end")
            self.log_text.configure(state="disabled")
            if follow:
                self.log_text.see(tk.END)
            else:
                self.log_text.yview_moveto(position[0])
            self._last_content = content

    def copy_id(self):
        if self._selected_id:
            self.root.clipboard_clear()
            self.root.clipboard_append(self._selected_id)
            self.copy_button.configure(text="Đã sao chép")

    def copy_logs(self):
        if self._selected_id:
            self.root.clipboard_clear()
            self.root.clipboard_append(f"Request ID: {self._selected_id}\n" + self.log_text.get("1.0", "end-1c"))

    def clear_filters(self):
        self.search.set("")
        self.status_filter.set("Tất cả")
        self.refresh_table()

    def select_request(self, job_id):
        if self.history.get(job_id, include_events=False) is None:
            messagebox.showinfo("Lịch sử yêu cầu", "Yêu cầu này không còn trong lịch sử của phiên hiện tại.",
                                parent=self.root)
            return
        self.clear_filters()
        if self.table.exists(job_id):
            self.table.selection_set(job_id)
            self.table.focus(job_id)
            self.table.see(job_id)
            self.show_details()
        else:
            messagebox.showinfo("Lịch sử yêu cầu", "Yêu cầu này không còn trong lịch sử của phiên hiện tại.",
                                parent=self.root)

    def refresh(self):
        self.refresh_job = None
        if self.closed:
            return
        try:
            self.refresh_table()
        finally:
            self.refresh_job = self.root.after(500, self.refresh)

    def close(self):
        self.closed = True
        if self.refresh_job:
            self.root.after_cancel(self.refresh_job)
            self.refresh_job = None
