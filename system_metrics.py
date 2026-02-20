"""System/process metric collection helpers."""

from __future__ import annotations

import os

import psutil


def get_system_snapshot() -> tuple[float, list[float], object, object, int, tuple[float | None, float | None, float | None]]:
    cpu_pct = psutil.cpu_percent(interval=None)
    per_cores = psutil.cpu_percent(percpu=True)
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    n_procs = len(psutil.pids())
    load = os.getloadavg() if hasattr(os, "getloadavg") else (None, None, None)
    return cpu_pct, per_cores, mem, swap, n_procs, load


def get_process_rows(filter_val: str) -> list[dict]:
    procs: list[dict] = []
    for proc in psutil.process_iter(
        [
            "pid",
            "name",
            "cpu_percent",
            "memory_percent",
            "memory_info",
            "status",
            "num_threads",
            "username",
        ]
    ):
        try:
            info = proc.info
            name = (info.get("name") or "")
            if filter_val and filter_val not in name.lower():
                continue
            procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return procs

