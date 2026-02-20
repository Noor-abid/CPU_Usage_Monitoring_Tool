"""Shared configuration, styling, and font utilities for the app."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

# Timing and data limits
REFRESH_INTERVAL = 1000
GRAPH_HISTORY = 60
ALERT_THRESHOLD = 80.0
LOG_FILE = "cpu_log.csv"
MAX_PROCESSES = 30
GRAPH_INTERVAL_MS = 1000

# Color palette
BG_DARK = "#0d0f14"
BG_PANEL = "#13161e"
BG_ROW_ALT = "#1a1d27"
ACCENT = "#00e5ff"
ACCENT2 = "#ff4757"
ACCENT3 = "#2ed573"
TEXT_MAIN = "#e8eaf0"
TEXT_DIM = "#5a6070"
TEXT_HEAD = "#00e5ff"
BORDER = "#1e2230"
WARN_COLOR = "#ff6b35"
GRAPH_BG = "#0a0c10"


def resolve_mono_font_family(root: tk.Tk) -> str:
    """Pick a good cross-platform monospace font with fallbacks."""
    preferred = [
        "Cascadia Mono",
        "Consolas",
        "Menlo",
        "Monaco",
        "DejaVu Sans Mono",
        "Liberation Mono",
        "Courier New",
        "Courier",
    ]
    try:
        available = {name.lower(): name for name in tkfont.families(root)}
        for font_name in preferred:
            resolved = available.get(font_name.lower())
            if resolved:
                return resolved
    except Exception:
        pass
    return "TkFixedFont"


def build_fonts(root: tk.Tk) -> dict[str, tuple]:
    family = resolve_mono_font_family(root)
    return {
        "title": (family, 18, "bold"),
        "head": (family, 9, "bold"),
        "mono": (family, 9),
        "stats": (family, 13, "bold"),
        "label": (family, 8),
        "alert": (family, 10, "bold"),
    }

