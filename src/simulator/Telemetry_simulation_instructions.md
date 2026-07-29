# Telemetry Replay Simulator — v1

Streams rows from `consolidated_dataset_raw.csv` (from
[Sentinel_Satellite_AI_Detection_System](https://github.com/vgamush-user/Sentinel_Satellite_AI_Detection_System))
as a live, speed-controllable stream, and shows it on a Gradio dashboard.
This step is **stream + visibility only** — no anomaly detection / agent
logic is wired in yet. That's the next step.

## Files

- `telemetry_simulator.py` — the core replay engine (`TelemetryReplaySimulator`).
  Framework-agnostic: reads a CSV, plays rows back on a background thread at a
  configurable rows/sec rate, with pause/resume/stop, sequential or shuffled
  order, and looping. Exposes a thread-safe `snapshot()` for any UI to poll.
- `dashboard_app.py` — Gradio dashboard that connects to the simulator: live
  table of the most recent messages, two configurable rolling-metric charts,
  run status, and a live label-mix bar chart (ground truth from the CSV,
  shown descriptively — not a detection).
- `consolidated_dataset_raw.csv` — the sample dataset (25,000 rows, 31
  columns: CCSDS-style message fields + sliding-window traffic stats +
  memory stats + `Label`).
- `requirements.txt`

## Run it

```bash
pip install -r requirements.txt
python dashboard_app.py
```

Open the local URL Gradio prints (usually `http://127.0.0.1:7860`).

1. (Optional) Point "CSV path" at a different file and click **Load CSV**
   — e.g. swap in `noised_dataset.csv` from the same repo.
2. Set **Speed (rows/sec)**, **Playback order** (Sequential replays the file
   as-is; note the raw CSV is grouped in contiguous blocks by `Label`, so
   Shuffled gives a more realistic mixed traffic feel), and whether to
   **Loop**.
3. Click **▶ Start**. The table and charts update twice a second.
4. **Pause/Resume** freezes/unfreezes playback without losing position;
   **Stop/Reset** rewinds to row 0.

## Using it standalone (no UI)

```python
from telemetry_simulator import TelemetryReplaySimulator

sim = TelemetryReplaySimulator("consolidated_dataset_raw.csv", buffer_size=50)
sim.configure(speed_rows_per_sec=25, order_mode="shuffled", loop=False)
sim.start()

while True:
    snap = sim.snapshot()
    print(snap.rows_emitted, snap.last_row["MsgId"] if snap.last_row is not None else None)
    if snap.finished:
        break
```

## Notes / next steps

- This is a **single-user, single-process v1**: the dashboard uses one
  shared simulator instance (no per-browser-session isolation). Fine for a
  local demo; would need `gr.State` + per-session simulators for multi-user.
- The dashboard polls on a 0.5s `gr.Timer` — fine up to a few hundred
  rows/sec; for very high speeds the *table* will visibly skip rows even
  though the simulator itself hasn't dropped anything (`rows_emitted` is
  always accurate).
- Next step per your plan: wire an agent (e.g. the CrewAI setup in
  `helloworldagent.py`) to consume `sim.snapshot().buffer` / individual rows
  and layer on real anomaly scoring, without touching the simulator or
  dashboard's plumbing.
