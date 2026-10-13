"""Small native Tk controls with a consistent rounded surface."""

import tkinter as tk
from tkinter import font as tkfont, ttk


def rounded(canvas, x1, y1, x2, y2, radius, **options):
    radius = max(0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    points = (x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
              x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
              x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1)
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **options)


def parent_color(parent, fallback):
    try:
        return parent.cget("bg")
    except tk.TclError:
        return fallback


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, palette, kind="secondary", **options):
        self.palette, self.command = palette, command
        self._text = text
        self._state = options.pop("state", "normal")
        self._fill = palette[{"primary": "accent", "danger": "danger", "tab": "bg"}.get(kind, "button")]
        self._hover_fill = palette[{"primary": "accent_hover", "danger": "danger_hover", "tab": "panel_alt"}.get(kind, "border")]
        self._foreground = options.pop("fg", palette["text"])
        self._hovered, self._focused, self._pressed = False, False, False
        self._padx = options.pop("padx", 14)
        pady = options.pop("pady", 9)
        self._anchor = options.pop("anchor", "center")
        self._font = tkfont.Font(font=options.pop("font", ("Segoe UI", 10, "bold")))
        width = options.pop("width", self._font.measure(text) + self._padx * 2 + 2)
        height = options.pop("height", max(38, self._font.metrics("linespace") + pady * 2))
        super().__init__(parent, width=width, height=height, bg=parent_color(parent, palette["panel"]),
                         bd=0, highlightthickness=0, takefocus=True, cursor="hand2", **options)
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", lambda event: self._change(hovered=True))
        self.bind("<Leave>", lambda event: self._change(hovered=False, pressed=False))
        self.bind("<FocusIn>", lambda event: self._change(focused=True))
        self.bind("<FocusOut>", lambda event: self._change(focused=False, pressed=False))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Return>", lambda event: self._invoke())
        self.bind("<KeyPress-space>", lambda event: self._change(pressed=True))
        self.bind("<KeyRelease-space>", lambda event: self._invoke())

    def _change(self, **values):
        for name, value in values.items():
            setattr(self, "_" + name, value)
        self._draw()

    def _press(self, event):
        if self._state != "disabled":
            self.focus_set()
            self._change(pressed=True)

    def _release(self, event):
        pressed = self._pressed
        self._change(pressed=False)
        if pressed and 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height():
            self._invoke()

    def _invoke(self):
        self._change(pressed=False)
        if self._state != "disabled" and self.command:
            self.command()
        return "break"

    def _draw(self, event=None):
        self.delete("all")
        width, height = self.winfo_width(), self.winfo_height()
        disabled = self._state == "disabled"
        fill = self.palette["panel_alt"] if disabled else self._hover_fill if self._hovered or self._pressed else self._fill
        outline = "#8eb6ff" if self._focused and not disabled else fill
        rounded(self, 1, 1, width - 1, height - 1, 8, fill=fill, outline=outline, width=1)
        x = self._padx if self._anchor == "w" else width / 2
        self.create_text(x, height / 2 + int(self._pressed), text=self._text, font=self._font,
                         anchor="w" if self._anchor == "w" else "center",
                         fill=self.palette["muted"] if disabled else self._foreground)

    def configure(self, cnf=None, **options):
        if cnf is not None and not isinstance(cnf, dict):
            return super().configure(cnf, **options)
        options = {**(cnf or {}), **options}
        text_changed = "text" in options
        for key, attribute in (("text", "_text"), ("state", "_state"), ("fg", "_foreground"), ("bg", "_fill")):
            if key in options:
                setattr(self, attribute, options.pop(key))
        if "command" in options:
            self.command = options.pop("command")
        if text_changed and "width" not in options:
            options["width"] = self._font.measure(self._text) + self._padx * 2 + 2
        result = super().configure(**options) if options else None
        if hasattr(self, "_font"):
            self._draw()
            super().configure(cursor="arrow" if self._state == "disabled" else "hand2")
        return result

    config = configure


class RoundedField(tk.Frame):
    def __init__(self, parent, variable, palette, select=False, **options):
        self.palette = palette
        width = options.pop("width", 20)
        super().__init__(parent, bg=parent_color(parent, palette["panel"]), width=width * 8 + 24, height=38)
        self.surface = tk.Canvas(self, bg=self.cget("bg"), highlightthickness=0, bd=0)
        self.surface.place(relwidth=1, relheight=1)
        self._focused = False
        if select:
            self.input = ttk.Combobox(self, textvariable=variable, style="Flat.TCombobox", **options)
        else:
            self.input = tk.Entry(self, textvariable=variable, bg=palette["panel_alt"], fg=palette["text"],
                                  insertbackground=palette["text"], selectbackground=palette["selection"],
                                  relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 10), **options)
        self.input.place(x=12, rely=0.5, anchor="w", relwidth=1, width=-24, height=25)
        super().bind("<Configure>", self._draw)
        self.input.bind("<FocusIn>", lambda event: self._focus(True), add="+")
        self.input.bind("<FocusOut>", lambda event: self._focus(False), add="+")

    def _focus(self, focused):
        self._focused = focused
        self._draw()

    def _draw(self, event=None):
        self.surface.delete("all")
        rounded(self.surface, 1, 1, self.winfo_width() - 1, self.winfo_height() - 1, 8,
                fill=self.palette["panel_alt"], outline=self.palette["accent"] if self._focused else self.palette["border"], width=1)

    def bind(self, sequence=None, func=None, add=None):
        return self.input.bind(sequence, func, add)

    def focus_set(self):
        self.input.focus_set()

    def get(self):
        return self.input.get()

    def __setitem__(self, key, value):
        if key in ("values", "state", "textvariable"):
            self.input[key] = value
        else:
            super().__setitem__(key, value)


class SlimScrollbar(tk.Canvas):
    """Arrow-free scrollbar that reserves space only when content overflows."""

    def __init__(self, parent, orient="vertical", command=None, palette=None, **options):
        self.palette = palette
        self.orient, self.command = orient, command
        self.first, self.last = 0.0, 1.0
        self._manager, self._geometry = None, {}
        self._hovered, self._dragging = False, False
        self._offset = 0
        vertical = orient == "vertical"
        super().__init__(parent, width=10 if vertical else 30, height=30 if vertical else 10,
                         bg=parent_color(parent, palette["panel"]), bd=0, highlightthickness=0,
                         takefocus=False, **options)
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", lambda event: self._hover(True))
        self.bind("<Leave>", lambda event: self._hover(False))
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", lambda event: self._release())
        self.bind("<MouseWheel>", self._wheel)

    def grid(self, **options):
        self._manager, self._geometry = "grid", options
        super().grid(**options)

    def pack(self, **options):
        self._manager, self._geometry = "pack", options
        super().pack(**options)

    def set(self, first, last):
        self.first, self.last = float(first), float(last)
        if self._manager == "grid":
            if self.last - self.first >= 0.999:
                super().grid_remove()
            else:
                super().grid(**self._geometry)
        elif self._manager == "pack":
            if self.last - self.first >= 0.999:
                super().pack_forget()
            else:
                super().pack(**self._geometry)
        self._draw()

    def _length(self):
        return self.winfo_height() if self.orient == "vertical" else self.winfo_width()

    def _position(self, event):
        return event.y if self.orient == "vertical" else event.x

    def _draw(self, event=None):
        self.delete("all")
        length = self._length()
        span = self.last - self.first
        if span >= 0.999 or length <= 2:
            return
        size = min(length, max(24, span * length))
        start = self.first / max(0.001, 1 - span) * max(0, length - size)
        self._thumb_start, self._thumb_size = start, size
        color = self.palette["muted"] if self._hovered or self._dragging else self.palette["border"]
        if self.orient == "vertical":
            rounded(self, 2, start, 8, start + size, 3, fill=color, outline="")
        else:
            rounded(self, start, 2, start + size, 8, 3, fill=color, outline="")

    def _hover(self, value):
        self._hovered = value
        self._draw()

    def _press(self, event):
        self._dragging = True
        start = getattr(self, "_thumb_start", 0)
        size = getattr(self, "_thumb_size", 24)
        position = self._position(event)
        self._offset = position - start if start <= position <= start + size else size / 2
        self._drag(event)

    def _drag(self, event):
        travel = max(1, self._length() - getattr(self, "_thumb_size", 24))
        value = (self._position(event) - self._offset) / travel * (1 - (self.last - self.first))
        if self.command:
            self.command("moveto", max(0, min(self.first + 1 - self.last, value)))
        self._draw()

    def _release(self):
        self._dragging = False
        self._draw()

    def _wheel(self, event):
        if self.command and event.delta:
            self.command("scroll", -1 if event.delta > 0 else 1, "units")
        return "break"


class ScrollText(tk.Frame):
    """Text API wrapped with the same slim scrollbar as the tables."""

    def __init__(self, parent, palette, **options):
        super().__init__(parent, bg=options.get("bg", palette["bg"]), bd=0, highlightthickness=0)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        options.update(bd=0, highlightthickness=0, padx=12, pady=10)
        self.text = tk.Text(self, **options)
        scroll = SlimScrollbar(self, command=self.text.yview, palette=palette)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

    def configure(self, cnf=None, **options):
        return self.text.configure(cnf, **options)

    config = configure

    def __getattr__(self, name):
        text = self.__dict__.get("text")
        if text is not None:
            return getattr(text, name)
        raise AttributeError(name)


class TabView(tk.Frame):
    """Borderless page switcher exposing the Notebook methods used by the UI."""

    def __init__(self, parent, palette):
        super().__init__(parent, bg=palette["bg"], bd=0, highlightthickness=0)
        self.palette, self._tabs, self._selected = palette, [], None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.navigation = tk.Frame(self, bg=palette["bg"])
        self.navigation.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.body = tk.Frame(self, bg=palette["bg"])
        self.body.grid(row=1, column=0, sticky="nsew")

    def add(self, child, text):
        control = RoundedButton(self.navigation, text, lambda: self.select(child), self.palette, kind="tab", padx=18)
        control.pack(side="left", padx=(0, 6))
        self._tabs.append((child, control))
        control.bind("<Left>", lambda event: self._step(child, -1))
        control.bind("<Right>", lambda event: self._step(child, 1))
        if self._selected is None:
            self.select(child)

    def _step(self, child, direction):
        index = next(index for index, (page, _) in enumerate(self._tabs) if page is child)
        page, control = self._tabs[(index + direction) % len(self._tabs)]
        self.select(page)
        control.focus_set()
        return "break"

    def select(self, child=None):
        if child is None:
            return self._selected
        if isinstance(child, int):
            child = self._tabs[child][0]
        if not any(page is child for page, _ in self._tabs):
            raise ValueError("Unknown page")
        self._selected = child
        for page, control in self._tabs:
            active = page is child
            control.configure(bg=self.palette["panel_alt"] if active else self.palette["bg"],
                              fg=self.palette["text"] if active else self.palette["muted"])
            if active:
                page.place(in_=self.body, x=0, y=0, relwidth=1, relheight=1)
                page.lift()
            else:
                page.place_forget()
