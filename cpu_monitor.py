"""
╔══════════════════════════════════════════════════════╗
║         CPU Usage Monitoring Tool — Python           ║
║  Real-time process tracking + graphs + alerts + log  ║
╚══════════════════════════════════════════════════════╝
Requirements: pip install psutil matplotlib
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import datetime
import os
import csv
import psutil
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from collections import deque

# ─── Configuration ─────────────────────────────────────────────────────────────
REFRESH_INTERVAL   = 1000        # ms — how often the process table refreshes
GRAPH_HISTORY      = 60          # seconds of history shown in line graph
ALERT_THRESHOLD    = 80.0        # % CPU — triggers a warning alert
LOG_FILE           = "cpu_log.csv"
MAX_PROCESSES      = 30          # max rows in table
GRAPH_INTERVAL_MS  = 1000        # graph refresh in ms

# ─── Color Palette (dark industrial theme) ────────────────────────────────────
BG_DARK    = "#0d0f14"
BG_PANEL   = "#13161e"
BG_ROW_ALT = "#1a1d27"
ACCENT     = "#00e5ff"
ACCENT2    = "#ff4757"
ACCENT3    = "#2ed573"
TEXT_MAIN  = "#e8eaf0"
TEXT_DIM   = "#5a6070"
TEXT_HEAD  = "#00e5ff"
BORDER     = "#1e2230"
WARN_COLOR = "#ff6b35"
GRAPH_BG   = "#0a0c10"

# ─── Fonts ─────────────────────────────────────────────────────────────────────
FONT_TITLE  = ("Courier New", 18, "bold")
FONT_HEAD   = ("Courier New", 9, "bold")
FONT_MONO   = ("Courier New", 9)
FONT_STATS  = ("Courier New", 13, "bold")
FONT_LABEL  = ("Courier New", 8)
FONT_ALERT  = ("Courier New", 10, "bold")


# ══════════════════════════════════════════════════════════════════════════════
class CPUMonitorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("⚡ CPU Usage Monitor")
        self.root.configure(bg=BG_DARK)
        self.root.geometry("1200x820")
        self.root.minsize(1000, 700)

        # ── State ──────────────────────────────────────────────────────────
        self.sort_by      = tk.StringVar(value="cpu")
        self.sort_asc     = False
        self.filter_text  = tk.StringVar()
        self.logging_on   = tk.BooleanVar(value=False)
        self.alert_on     = tk.BooleanVar(value=True)
        self.alert_thresh = tk.DoubleVar(value=ALERT_THRESHOLD)
        self._alert_shown = False
        self._running     = True

        # ── History buffers ────────────────────────────────────────────────
        self.cpu_history     = deque([0.0] * GRAPH_HISTORY, maxlen=GRAPH_HISTORY)
        self.mem_history     = deque([0.0] * GRAPH_HISTORY, maxlen=GRAPH_HISTORY)
        self.time_labels     = deque([""] * GRAPH_HISTORY, maxlen=GRAPH_HISTORY)
        self.load_history    = deque([0.0] * GRAPH_HISTORY, maxlen=GRAPH_HISTORY)

        # ── Log file ───────────────────────────────────────────────────────
        self._log_file = None
        self._log_writer = None

        self._build_ui()
        self._start_refresh()

    # ─────────────────────────────────────────────────────────────────────────
    # UI BUILD
    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Title bar ─────────────────────────────────────────────────────
        title_frame = tk.Frame(self.root, bg=BG_DARK, pady=10)
        title_frame.pack(fill=tk.X, padx=20)

        tk.Label(title_frame, text="⚡ CPU USAGE MONITOR",
                 font=FONT_TITLE, fg=ACCENT, bg=BG_DARK).pack(side=tk.LEFT)

        self.clock_lbl = tk.Label(title_frame, text="", font=FONT_MONO,
                                   fg=TEXT_DIM, bg=BG_DARK)
        self.clock_lbl.pack(side=tk.RIGHT, padx=10)

        # ── Top stats bar ──────────────────────────────────────────────────
        stats_frame = tk.Frame(self.root, bg=BG_PANEL, pady=10, padx=20)
        stats_frame.pack(fill=tk.X, padx=20, pady=(0, 6))

        self._stat_boxes = {}
        stats = [
            ("CPU Total",  "cpu_total",  ACCENT),
            ("Per Core",   "per_core",   "#a29bfe"),
            ("Memory",     "memory",     ACCENT3),
            ("Swap",       "swap",       WARN_COLOR),
            ("Processes",  "proc_count", TEXT_MAIN),
            ("Load Avg",   "load_avg",   "#fdcb6e"),
        ]
        for label, key, color in stats:
            box = tk.Frame(stats_frame, bg=BG_DARK, padx=14, pady=8,
                           relief=tk.FLAT, bd=0)
            box.pack(side=tk.LEFT, padx=6, fill=tk.Y)
            tk.Label(box, text=label.upper(), font=FONT_LABEL,
                     fg=TEXT_DIM, bg=BG_DARK).pack()
            val_lbl = tk.Label(box, text="—", font=FONT_STATS,
                               fg=color, bg=BG_DARK)
            val_lbl.pack()
            self._stat_boxes[key] = val_lbl

        # ── CPU usage bar ──────────────────────────────────────────────────
        bar_frame = tk.Frame(self.root, bg=BG_DARK, padx=20)
        bar_frame.pack(fill=tk.X, padx=20, pady=2)
        tk.Label(bar_frame, text="SYSTEM CPU  ", font=FONT_LABEL,
                 fg=TEXT_DIM, bg=BG_DARK).pack(side=tk.LEFT)
        self.cpu_canvas = tk.Canvas(bar_frame, height=14, bg=BG_PANEL,
                                    highlightthickness=0)
        self.cpu_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.cpu_pct_lbl = tk.Label(bar_frame, text="0%", font=FONT_LABEL,
                                     fg=ACCENT, bg=BG_DARK, width=6)
        self.cpu_pct_lbl.pack(side=tk.LEFT)

        # ── Toolbar (sort / filter / controls) ────────────────────────────
        toolbar = tk.Frame(self.root, bg=BG_DARK, padx=20, pady=6)
        toolbar.pack(fill=tk.X, padx=20)

        tk.Label(toolbar, text="SORT:", font=FONT_LABEL,
                 fg=TEXT_DIM, bg=BG_DARK).pack(side=tk.LEFT)
        sort_opts = [("CPU %", "cpu"), ("Memory %", "mem"),
                     ("PID", "pid"), ("Name", "name")]
        for text, val in sort_opts:
            rb = tk.Radiobutton(toolbar, text=text, variable=self.sort_by,
                                value=val, font=FONT_LABEL,
                                fg=TEXT_MAIN, bg=BG_DARK,
                                selectcolor=BG_PANEL, activebackground=BG_DARK,
                                activeforeground=ACCENT,
                                command=self._refresh_table)
            rb.pack(side=tk.LEFT, padx=4)

        tk.Label(toolbar, text="  ↑↓", font=FONT_LABEL,
                 fg=TEXT_DIM, bg=BG_DARK).pack(side=tk.LEFT)
        tk.Button(toolbar, text="FLIP ORDER", font=FONT_LABEL,
                  fg=ACCENT, bg=BG_PANEL, relief=tk.FLAT,
                  command=self._flip_sort).pack(side=tk.LEFT, padx=6)

        # Filter
        tk.Label(toolbar, text="  FILTER:", font=FONT_LABEL,
                 fg=TEXT_DIM, bg=BG_DARK).pack(side=tk.LEFT)
        filter_entry = tk.Entry(toolbar, textvariable=self.filter_text,
                                font=FONT_MONO, bg=BG_PANEL, fg=TEXT_MAIN,
                                insertbackground=ACCENT, relief=tk.FLAT,
                                width=14)
        filter_entry.pack(side=tk.LEFT, padx=4)
        self.filter_text.trace_add("write", lambda *_: self._refresh_table())

        # Log toggle
        tk.Checkbutton(toolbar, text=" LOG TO FILE", variable=self.logging_on,
                       font=FONT_LABEL, fg=ACCENT3, bg=BG_DARK,
                       selectcolor=BG_PANEL, activebackground=BG_DARK,
                       command=self._toggle_log).pack(side=tk.LEFT, padx=10)

        # Alert toggle
        tk.Checkbutton(toolbar, text=" ALERTS", variable=self.alert_on,
                       font=FONT_LABEL, fg=WARN_COLOR, bg=BG_DARK,
                       selectcolor=BG_PANEL,
                       activebackground=BG_DARK).pack(side=tk.LEFT, padx=4)

        tk.Label(toolbar, text="@", font=FONT_LABEL,
                 fg=TEXT_DIM, bg=BG_DARK).pack(side=tk.LEFT)
        tk.Spinbox(toolbar, textvariable=self.alert_thresh,
                   from_=10, to=100, increment=5, width=5,
                   font=FONT_LABEL, bg=BG_PANEL, fg=WARN_COLOR,
                   buttonbackground=BG_PANEL, relief=tk.FLAT).pack(side=tk.LEFT)
        tk.Label(toolbar, text="%", font=FONT_LABEL,
                 fg=TEXT_DIM, bg=BG_DARK).pack(side=tk.LEFT)

        # ── Main pane: process table LEFT + graphs RIGHT ───────────────────
        main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL,
                                   bg=BG_DARK, sashwidth=4,
                                   sashrelief=tk.FLAT)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=20, pady=6)

        # ── Process Table ─────────────────────────────────────────────────
        table_frame = tk.Frame(main_pane, bg=BG_DARK)
        main_pane.add(table_frame, minsize=380)

        tk.Label(table_frame, text="RUNNING PROCESSES",
                 font=FONT_HEAD, fg=TEXT_HEAD, bg=BG_DARK,
                 anchor=tk.W).pack(fill=tk.X, pady=(0, 4))

        cols = ("PID", "Name", "CPU %", "MEM %", "MEM MB",
                "Status", "Threads", "User")
        self.tree = ttk.Treeview(table_frame, columns=cols,
                                  show="headings", height=22)
        col_widths = [55, 160, 65, 65, 70, 80, 65, 90]
        for col, w in zip(cols, col_widths):
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_by_col(c))
            self.tree.column(col, width=w, anchor=tk.CENTER)
        self.tree.column("Name", anchor=tk.W)

        # Style
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                        background=BG_PANEL,
                        foreground=TEXT_MAIN,
                        fieldbackground=BG_PANEL,
                        rowheight=22,
                        font=FONT_MONO,
                        borderwidth=0)
        style.configure("Treeview.Heading",
                        background=BG_DARK,
                        foreground=TEXT_HEAD,
                        font=FONT_HEAD,
                        relief=tk.FLAT,
                        borderwidth=0)
        style.map("Treeview",
                  background=[("selected", "#1e2c3a")],
                  foreground=[("selected", ACCENT)])

        self.tree.tag_configure("high",  background="#2a0a0a", foreground=ACCENT2)
        self.tree.tag_configure("med",   background="#1a1a0a", foreground=WARN_COLOR)
        self.tree.tag_configure("alt",   background=BG_ROW_ALT)
        self.tree.tag_configure("norm",  background=BG_PANEL)

        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL,
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.LEFT, fill=tk.Y)

        # ── Graph Panel ───────────────────────────────────────────────────
        graph_frame = tk.Frame(main_pane, bg=BG_DARK)
        main_pane.add(graph_frame, minsize=420)

        tk.Label(graph_frame, text="REAL-TIME GRAPHS",
                 font=FONT_HEAD, fg=TEXT_HEAD, bg=BG_DARK,
                 anchor=tk.W).pack(fill=tk.X, pady=(0, 4))

        self._build_graphs(graph_frame)

        # ── Status bar ────────────────────────────────────────────────────
        status_bar = tk.Frame(self.root, bg=BG_PANEL, pady=3)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_lbl = tk.Label(status_bar,
                                    text="⚡ Monitoring started",
                                    font=FONT_LABEL, fg=ACCENT3,
                                    bg=BG_PANEL, anchor=tk.W, padx=12)
        self.status_lbl.pack(side=tk.LEFT)
        self.log_status = tk.Label(status_bar, text="",
                                    font=FONT_LABEL, fg=TEXT_DIM,
                                    bg=BG_PANEL, padx=12)
        self.log_status.pack(side=tk.RIGHT)

    def _build_graphs(self, parent):
        """Create the matplotlib figures embedded in tkinter."""
        self.fig = Figure(figsize=(5.5, 7), facecolor=GRAPH_BG)
        self.fig.subplots_adjust(hspace=0.45, left=0.12, right=0.96,
                                  top=0.95, bottom=0.07)

        # ── CPU Line Graph ────────────────────────────────────────────────
        self.ax_cpu = self.fig.add_subplot(3, 1, 1)
        self.ax_cpu.set_facecolor(GRAPH_BG)
        self.ax_cpu.set_title("CPU Usage %", color=ACCENT,
                               fontsize=8, fontfamily="monospace", pad=4)
        self.ax_cpu.set_ylim(0, 100)
        self.ax_cpu.set_xlim(0, GRAPH_HISTORY)
        self.ax_cpu.tick_params(colors=TEXT_DIM, labelsize=7)
        for spine in self.ax_cpu.spines.values():
            spine.set_color(BORDER)
        self.ax_cpu.yaxis.label.set_color(TEXT_DIM)
        self.line_cpu, = self.ax_cpu.plot([], [], color=ACCENT,
                                           linewidth=1.5, antialiased=True)
        self.fill_cpu = None

        # ── Memory Line Graph ─────────────────────────────────────────────
        self.ax_mem = self.fig.add_subplot(3, 1, 2)
        self.ax_mem.set_facecolor(GRAPH_BG)
        self.ax_mem.set_title("Memory Usage %", color=ACCENT3,
                               fontsize=8, fontfamily="monospace", pad=4)
        self.ax_mem.set_ylim(0, 100)
        self.ax_mem.set_xlim(0, GRAPH_HISTORY)
        self.ax_mem.tick_params(colors=TEXT_DIM, labelsize=7)
        for spine in self.ax_mem.spines.values():
            spine.set_color(BORDER)
        self.line_mem, = self.ax_mem.plot([], [], color=ACCENT3,
                                           linewidth=1.5, antialiased=True)

        # ── Per-Core Bar Graph ────────────────────────────────────────────
        self.ax_cores = self.fig.add_subplot(3, 1, 3)
        self.ax_cores.set_facecolor(GRAPH_BG)
        self.ax_cores.set_title("Per-Core CPU %", color="#a29bfe",
                                 fontsize=8, fontfamily="monospace", pad=4)
        self.ax_cores.set_ylim(0, 100)
        self.ax_cores.tick_params(colors=TEXT_DIM, labelsize=7)
        for spine in self.ax_cores.spines.values():
            spine.set_color(BORDER)
        self._core_bars = None

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # ─────────────────────────────────────────────────────────────────────────
    # REFRESH LOGIC
    # ─────────────────────────────────────────────────────────────────────────
    def _start_refresh(self):
        self._refresh_stats()
        self._refresh_table()
        self._update_graphs()
        self._tick_clock()

    def _tick_clock(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        self.clock_lbl.config(text=now)
        self.root.after(1000, self._tick_clock)

    def _refresh_stats(self):
        if not self._running:
            return
        try:
            cpu_pct   = psutil.cpu_percent(interval=None)
            per_cores = psutil.cpu_percent(percpu=True)
            mem       = psutil.virtual_memory()
            swap      = psutil.swap_memory()
            n_procs   = len(psutil.pids())
            load      = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)

            # Update stat boxes
            self._stat_boxes["cpu_total"].config(text=f"{cpu_pct:.1f}%")
            cores_str = "  ".join(f"{c:.0f}%" for c in per_cores[:4])
            if len(per_cores) > 4:
                cores_str += " …"
            self._stat_boxes["per_core"].config(text=cores_str,
                                                 font=("Courier New", 9, "bold"))
            self._stat_boxes["memory"].config(
                text=f"{mem.percent:.1f}%  ({mem.used//1024//1024}MB)")
            self._stat_boxes["swap"].config(
                text=f"{swap.percent:.1f}%  ({swap.used//1024//1024}MB)")
            self._stat_boxes["proc_count"].config(text=str(n_procs))
            self._stat_boxes["load_avg"].config(
                text=f"{load[0]:.2f}  {load[1]:.2f}  {load[2]:.2f}")

            # CPU bar
            self._draw_cpu_bar(cpu_pct)
            self.cpu_pct_lbl.config(text=f"{cpu_pct:.1f}%")

            # History
            self.cpu_history.append(cpu_pct)
            self.mem_history.append(mem.percent)
            self.load_history.append(load[0] * 10)
            self.time_labels.append(datetime.datetime.now().strftime("%H:%M:%S"))
            self._per_cores = per_cores

            # Alert check
            if (self.alert_on.get() and cpu_pct >= self.alert_thresh.get()
                    and not self._alert_shown):
                self._alert_shown = True
                self._show_alert(cpu_pct)
            elif cpu_pct < self.alert_thresh.get():
                self._alert_shown = False

            # Log
            if self.logging_on.get() and self._log_writer:
                self._log_writer.writerow([
                    datetime.datetime.now().isoformat(),
                    f"{cpu_pct:.2f}",
                    f"{mem.percent:.2f}",
                    f"{swap.percent:.2f}",
                    n_procs,
                ])
                self._log_file.flush()

        except Exception as e:
            self._set_status(f"Stats error: {e}", error=True)

        self.root.after(REFRESH_INTERVAL, self._refresh_stats)

    def _draw_cpu_bar(self, pct):
        self.cpu_canvas.update_idletasks()
        w = self.cpu_canvas.winfo_width()
        h = 14
        fill_w = int(w * pct / 100)
        color = ACCENT3 if pct < 50 else WARN_COLOR if pct < 80 else ACCENT2
        self.cpu_canvas.delete("all")
        self.cpu_canvas.create_rectangle(0, 0, fill_w, h, fill=color, outline="")
        self.cpu_canvas.create_rectangle(fill_w, 0, w, h,
                                          fill=BG_PANEL, outline="")

    def _refresh_table(self, *_):
        if not self._running:
            return
        try:
            filter_val = self.filter_text.get().lower()
            sort_key   = self.sort_by.get()

            procs = []
            for p in psutil.process_iter(
                    ["pid", "name", "cpu_percent", "memory_percent",
                     "memory_info", "status", "num_threads", "username"]):
                try:
                    info = p.info
                    if filter_val and filter_val not in info["name"].lower():
                        continue
                    procs.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Sort
            key_map = {
                "cpu":  lambda x: x.get("cpu_percent") or 0,
                "mem":  lambda x: x.get("memory_percent") or 0,
                "pid":  lambda x: x.get("pid") or 0,
                "name": lambda x: (x.get("name") or "").lower(),
            }
            procs.sort(key=key_map.get(sort_key, key_map["cpu"]),
                       reverse=not self.sort_asc
                       if sort_key != "name" else self.sort_asc)

            procs = procs[:MAX_PROCESSES]

            # Populate treeview
            self.tree.delete(*self.tree.get_children())
            for i, p in enumerate(procs):
                cpu   = p.get("cpu_percent") or 0
                mem   = p.get("memory_percent") or 0
                mi    = p.get("memory_info")
                mb    = round(mi.rss / 1024 / 1024, 1) if mi else 0
                name  = (p.get("name") or "")[:28]
                stat  = p.get("status") or ""
                thrs  = p.get("num_threads") or 0
                user  = (p.get("username") or "")[-14:]

                tag = ("high" if cpu >= 50
                       else "med" if cpu >= 20
                       else "alt" if i % 2 == 0
                       else "norm")

                self.tree.insert("", tk.END,
                                  values=(p["pid"], name, f"{cpu:.1f}",
                                          f"{mem:.1f}", f"{mb:.1f}",
                                          stat, thrs, user),
                                  tags=(tag,))
            self._set_status(
                f"Showing {len(procs)} processes  •  "
                f"sort: {sort_key}  •  "
                f"filter: '{filter_val or 'none'}'")
        except Exception as e:
            self._set_status(f"Table error: {e}", error=True)

        self.root.after(REFRESH_INTERVAL, self._refresh_table)

    def _update_graphs(self):
        if not self._running:
            return
        try:
            xs = list(range(GRAPH_HISTORY))
            cpu_data = list(self.cpu_history)
            mem_data = list(self.mem_history)

            # CPU line + fill
            self.line_cpu.set_data(xs, cpu_data)
            for coll in self.ax_cpu.collections:
                coll.remove()
            self.ax_cpu.fill_between(xs, cpu_data, alpha=0.15, color=ACCENT)

            # Mem line + fill
            self.line_mem.set_data(xs, mem_data)
            for coll in self.ax_mem.collections:
                coll.remove()
            self.ax_mem.fill_between(xs, mem_data, alpha=0.15, color=ACCENT3)

            # Per-core bars
            self.ax_cores.cla()
            self.ax_cores.set_facecolor(GRAPH_BG)
            self.ax_cores.set_title("Per-Core CPU %", color="#a29bfe",
                                     fontsize=8, fontfamily="monospace", pad=4)
            self.ax_cores.set_ylim(0, 100)
            self.ax_cores.tick_params(colors=TEXT_DIM, labelsize=7)
            for spine in self.ax_cores.spines.values():
                spine.set_color(BORDER)

            if hasattr(self, "_per_cores"):
                cores = self._per_cores
                bar_colors = [
                    ACCENT2 if c >= 80 else WARN_COLOR if c >= 50 else "#a29bfe"
                    for c in cores
                ]
                bars = self.ax_cores.bar(range(len(cores)), cores,
                                          color=bar_colors, width=0.7)
                self.ax_cores.set_xticks(range(len(cores)))
                self.ax_cores.set_xticklabels(
                    [f"C{i}" for i in range(len(cores))],
                    color=TEXT_DIM, fontsize=7)
                for bar, val in zip(bars, cores):
                    self.ax_cores.text(bar.get_x() + bar.get_width() / 2,
                                       bar.get_height() + 1,
                                       f"{val:.0f}", ha="center", va="bottom",
                                       fontsize=6, color=TEXT_DIM)

            self.canvas.draw_idle()
        except Exception as e:
            pass  # silently skip graph errors

        self.root.after(GRAPH_INTERVAL_MS, self._update_graphs)

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    def _flip_sort(self):
        self.sort_asc = not self.sort_asc
        self._refresh_table()

    def _sort_by_col(self, col):
        mapping = {
            "PID": "pid", "Name": "name",
            "CPU %": "cpu", "MEM %": "mem"
        }
        if col in mapping:
            self.sort_by.set(mapping[col])
            self._refresh_table()

    def _show_alert(self, cpu_pct):
        def _popup():
            win = tk.Toplevel(self.root)
            win.title("⚠ CPU Alert")
            win.configure(bg=BG_DARK)
            win.geometry("320x140")
            win.grab_set()
            tk.Label(win, text="⚠  HIGH CPU USAGE",
                     font=FONT_ALERT, fg=ACCENT2, bg=BG_DARK).pack(pady=(20, 4))
            tk.Label(win,
                     text=f"CPU is at {cpu_pct:.1f}%\n"
                          f"(threshold: {self.alert_thresh.get():.0f}%)",
                     font=FONT_MONO, fg=TEXT_MAIN, bg=BG_DARK).pack(pady=4)
            tk.Button(win, text="  DISMISS  ", font=FONT_MONO,
                      fg=BG_DARK, bg=ACCENT2, relief=tk.FLAT,
                      command=win.destroy).pack(pady=12)
        self.root.after(0, _popup)

    def _toggle_log(self):
        if self.logging_on.get():
            try:
                self._log_file = open(LOG_FILE, "a", newline="")
                self._log_writer = csv.writer(self._log_file)
                # Write header if new file
                if os.path.getsize(LOG_FILE) == 0:
                    self._log_writer.writerow(
                        ["timestamp", "cpu_pct", "mem_pct",
                         "swap_pct", "num_processes"])
                self.log_status.config(
                    text=f"📝 Logging → {LOG_FILE}", fg=ACCENT3)
                self._set_status(f"Logging started → {LOG_FILE}")
            except Exception as e:
                self._set_status(f"Log error: {e}", error=True)
                self.logging_on.set(False)
        else:
            if self._log_file:
                self._log_file.close()
                self._log_file = None
                self._log_writer = None
            self.log_status.config(text="")
            self._set_status("Logging stopped.")

    def _set_status(self, msg, error=False):
        color = ACCENT2 if error else ACCENT3
        self.status_lbl.config(text=f"  {msg}", fg=color)

    def on_close(self):
        self._running = False
        if self._log_file:
            self._log_file.close()
        plt.close("all")
        self.root.destroy()


# ══════════════════════════════════════════════════════════════════════════════
def main():
    root = tk.Tk()
    app = CPUMonitorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)

    # Make window resizable & centered
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    ww, wh = 1200, 820
    root.geometry(f"{ww}x{wh}+{(sw-ww)//2}+{(sh-wh)//2}")

    root.mainloop()


if __name__ == "__main__":
    main()