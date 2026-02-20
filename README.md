# ⚡ CPU Usage Monitoring Tool — Python Desktop App

Real-time CPU & memory monitoring with live graphs, process table, alerts, and logging.

---

## Features
- Live process table (PID, Name, CPU%, MEM%, Status, Threads, User)
- Sort by CPU, Memory, PID, or Name
- Filter processes by name
- Real-time line graphs: CPU usage + Memory usage (last 60 seconds)
- Per-core CPU bar chart
- System-wide CPU usage progress bar
- High CPU alert popup (configurable threshold)
- Log CPU/memory stats to a CSV file
- Load average display (1min / 5min / 15min)

---

## Tech Stack
- `tkinter` — GUI (built into Python)
- `psutil` — OS process & CPU data
- `matplotlib` — real-time graphs

---

## How to Run

### Step 1 — Install Python
Go to https://python.org/downloads and install Python 3.9 or newer.
On Windows: check "Add Python to PATH" during install.

### Step 2 — Create project folder
Create a folder called `cpu_monitor` anywhere (e.g. your Desktop).
Put `cpu_monitor.py` and `requirements.txt` inside it.

### Step 3 — Open terminal in that folder
- **Windows**: Open the folder → click address bar → type `cmd` → Enter
- **Mac**: Right-click folder → "New Terminal at Folder"
- **Linux**: `Ctrl+Alt+T`, then `cd ~/Desktop/cpu_monitor`

### Step 4 — Install dependencies
```
pip install -r requirements.txt
```
If `pip` doesn't work, try `pip3`.

### Step 5 — Run the app
```
python cpu_monitor.py
```
Or on Mac/Linux:
```
python3 cpu_monitor.py
```

A desktop window opens immediately showing live data.

---

## Using the App

| Feature | Where |
|---|---|
| Sort processes | Click radio buttons: CPU / Memory / PID / Name |
| Flip order | Click "FLIP ORDER" button |
| Filter by name | Type in the FILTER box |
| Enable logging | Check "LOG TO FILE" — saves to `cpu_log.csv` |
| Set alert threshold | Check "ALERTS" and change the % number |
| View graphs | Right panel — CPU line, Memory line, Per-core bars |

---

## Output Files
- `cpu_log.csv` — created when logging is enabled. Contains: timestamp, cpu_pct, mem_pct, swap_pct, num_processes

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: psutil` | Run `pip install psutil` |
| `ModuleNotFoundError: matplotlib` | Run `pip install matplotlib` |
| No window appears on Mac | Try `python3 cpu_monitor.py` |
| Colors look wrong on Windows | Use Windows Terminal instead of old cmd |
| Load avg not showing | Normal on Windows — shows 0.00 (Windows has no loadavg API) |
