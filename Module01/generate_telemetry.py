"""Manufacture a few days of machine-shop telemetry as CSV.

Run with:  uv run python Module01/generate_telemetry.py
Writes telemetry.csv next to this script, so it works from any working directory.
"""
import csv, math, random
from pathlib import Path
from datetime import datetime, timedelta

random.seed(42)
machines = ["cnc-01", "cnc-02", "cnc-03"]
start = datetime(2026, 1, 5, 6, 0, 0)          # Monday 06:00, shift start
days = 2
step = 3                                        # one reading every 3 s per machine
points = days * 24 * 60 * 60 // step            # 57,600 points x 3 machines

out = Path(__file__).with_name("telemetry.csv")
with out.open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["ts", "machine", "temp_c", "vib_rms", "spindle_load"])
    for i in range(points):
        ts = (start + timedelta(seconds=i * step)).isoformat(sep=" ")
        for mach in machines:
            temp = 42 + 3 * math.sin(i / 500.0) + random.gauss(0, 0.6)
            vib = 1.2 + 0.4 * math.sin(i / 90.0) + random.gauss(0, 0.08)
            load = 60 + 15 * math.sin(i / 300.0) + random.gauss(0, 3)
            if mach == "cnc-02":                 # bearing wear: vibration creeps up over the 2 days
                vib += 0.9 * (i / points)
            if random.random() < 0.0008:         # rare tool-chatter spike
                vib += random.uniform(0.4, 0.9)
            w.writerow([ts, mach, f"{temp:.2f}", f"{vib:.3f}", f"{load:.1f}"])
print(f"wrote {out} ({out.stat().st_size/1e6:.1f} MB, {points * len(machines)} rows)")
