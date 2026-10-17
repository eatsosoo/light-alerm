"""Shared palette and styled components for every application page."""

import tkinter as tk

from light_alarm.ui.widgets import RoundedButton, RoundedField, ScrollText, SlimScrollbar, TabView

COLORS = {
    "bg": "#0b1220", "panel": "#121d30", "panel_alt": "#19263b",
    "border": "#26364e", "text": "#ecf2fc", "muted": "#9aabc4",
    "accent": "#3069db", "accent_hover": "#3c78eb", "button": "#1e2d45",
    "danger": "#462531", "danger_hover": "#5b2c3c", "danger_text": "#ffb1bf",
    "success": "#70d9b1", "warning": "#f2c66d", "selection": "#28466e",
}


def label(parent, text=None, variable=None, size=10, bold=False, muted=False, bg=None, **kwargs):
    options = {"bg": bg or COLORS["panel"], "fg": COLORS["muted" if muted else "text"],
               "font": ("Segoe UI", size, "bold" if bold else "normal"), "anchor": "w"}
    options["textvariable" if variable is not None else "text"] = variable if variable is not None else text
    options.update(kwargs)
    return tk.Label(parent, **options)


def button(parent, text, command, kind="secondary", **kwargs):
    if kind == "danger":
        kwargs.setdefault("fg", COLORS["danger_text"])
    return RoundedButton(parent, text, command, COLORS, kind=kind, **kwargs)


def entry(parent, variable, **kwargs):
    return RoundedField(parent, variable, COLORS, **kwargs)


def select(parent, variable, **kwargs):
    return RoundedField(parent, variable, COLORS, select=True, **kwargs)


def scrollbar(parent, **kwargs):
    return SlimScrollbar(parent, palette=COLORS, **kwargs)


def scroll_text(parent, **kwargs):
    return ScrollText(parent, COLORS, **kwargs)


def tabs(parent):
    return TabView(parent, COLORS)


def separator(parent):
    return tk.Frame(parent, height=1, bg=COLORS["border"], bd=0, highlightthickness=0)


def metric(parent, title, variable, column, color=None):
    card = tk.Frame(parent, bg=COLORS["panel"], padx=16, pady=10, bd=0, highlightthickness=0)
    card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 0))
    parent.columnconfigure(column, weight=1, uniform="metrics")
    label(card, title, size=9, muted=True).pack(anchor="w")
    label(card, variable=variable, size=22, bold=True, fg=color or COLORS["text"]).pack(anchor="w", pady=(2, 0))
    return card
