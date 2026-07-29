"""
dashboard_app.py
-----------------
Gradio dashboard for the Telemetry-Replay Simulator (v1).

Connects to TelemetryReplaySimulator and visualizes the live stream:
live table of the most recent messages, rolling metric charts, and
basic run stats. This is purely a *viewer* — there is no anomaly
detection / agent logic here yet. The ground-truth "Label" column from
the dataset is shown as-is (it's part of the CSV) but nothing in this
app interprets or acts on it.

Run:
    pip install -r requirements.txt
    python dashboard_app.py

Then open the printed local URL in your browser.
"""

from __future__ import annotations

from collections import deque

import gradio as gr
import pandas as pd

from telemetry_simulator import TelemetryReplaySimulator

DEFAULT_CSV = "consolidated_dataset_raw.csv"
PLOT_HISTORY = 300  # points kept for the rolling charts

# Metrics worth watching on the dashboard out of the box.
METRIC_CHOICES = [
    "MessageRateInWindow",
    "MemoryAnonMB",
    "MsgLength",
    "SlidingWindowMeanIntervalSec",
    "CommandErrorCounter",
    "MemoryPageFaults",
]

# ---------------------------------------------------------------------- #
# Single shared simulator instance (this is a single-user v1 demo — no
# per-session isolation yet).
# ---------------------------------------------------------------------- #
sim = TelemetryReplaySimulator(DEFAULT_CSV, buffer_size=100)
plot_history: deque = deque(maxlen=PLOT_HISTORY)


def do_load_csv(path: str):
    global sim, plot_history
    try:
        sim = TelemetryReplaySimulator(path.strip() or DEFAULT_CSV, buffer_size=100)
        plot_history = deque(maxlen=PLOT_HISTORY)
        return f"Loaded `{sim.csv_path}` — {sim.total_rows:,} rows, {len(sim.df.columns)} columns."
    except Exception as e:
        return f"Failed to load CSV: {e}"


def do_start(speed, order_mode, loop, buffer_size):
    global plot_history
    plot_history = deque(maxlen=PLOT_HISTORY)
    sim.configure(
        speed_rows_per_sec=speed,
        order_mode="sequential" if order_mode == "Sequential" else "shuffled",
        loop=loop,
        buffer_size=int(buffer_size),
    )
    sim.start()


def do_pause():
    sim.pause()


def do_resume():
    sim.resume()


def do_stop():
    sim.stop()


def do_apply_speed(speed, order_mode, loop, buffer_size):
    sim.configure(
        speed_rows_per_sec=speed,
        order_mode="sequential" if order_mode == "Sequential" else "shuffled",
        loop=loop,
        buffer_size=int(buffer_size),
    )


def poll(metric_a, metric_b):
    """Called on every timer tick to refresh the whole dashboard."""
    snap = sim.snapshot()

    # --- status line ---
    state = "FINISHED" if snap.finished else ("PAUSED" if snap.paused else ("RUNNING" if snap.running else "STOPPED"))
    pct = (snap.rows_emitted / snap.total_rows * 100) if snap.total_rows else 0
    status_md = (
        f"**State:** {state}  |  **Rows streamed:** {snap.rows_emitted:,} / {snap.total_rows:,} "
        f"({pct:.1f}%)  |  **Speed:** {snap.speed_rows_per_sec:.1f} rows/s  |  "
        f"**Order:** {snap.order_mode}  |  **Loop:** {snap.loop}  |  **Elapsed:** {snap.elapsed_sec:.1f}s"
    )

    # --- live table (most recent rows, newest first) ---
    if not snap.buffer.empty:
        table = snap.buffer.tail(20).iloc[::-1].reset_index(drop=True)
    else:
        table = snap.buffer

    # --- rolling metric history for charts ---
    if snap.last_row is not None:
        # only append a fresh point if a new row actually arrived
        if not plot_history or plot_history[-1]["_step"] != snap.rows_emitted:
            point = {"_step": snap.rows_emitted}
            for m in METRIC_CHOICES:
                if m in snap.last_row.index:
                    point[m] = snap.last_row[m]
            plot_history.append(point)

    hist_df = pd.DataFrame(list(plot_history)) if plot_history else pd.DataFrame(columns=["_step"] + METRIC_CHOICES)

    # --- ground-truth label mix currently in the live buffer (descriptive only) ---
    if not snap.buffer.empty and "Label" in snap.buffer.columns:
        counts = snap.buffer["Label"].value_counts().sort_index()
        label_df = pd.DataFrame({"Label": counts.index.astype(str), "Count": counts.values})
    else:
        label_df = pd.DataFrame(columns=["Label", "Count"])

    plot_a = gr.LinePlot(value=hist_df, x="_step", y=metric_a, title=metric_a) if metric_a in hist_df.columns else gr.LinePlot()
    plot_b = gr.LinePlot(value=hist_df, x="_step", y=metric_b, title=metric_b) if metric_b in hist_df.columns else gr.LinePlot()

    return status_md, table, plot_a, plot_b, label_df


with gr.Blocks(title="Telemetry Replay Simulator — Live Stream") as demo:
    gr.Markdown(
        "# 🛰️ Telemetry Replay Simulator — Live Stream\n"
        "Replays rows from the satellite bus telemetry CSV as a live stream at a "
        "configurable speed. This view is a pure passthrough — no anomaly detection "
        "or agent logic is applied here yet."
    )

    with gr.Row():
        csv_path = gr.Textbox(value=DEFAULT_CSV, label="CSV path", scale=3)
        load_btn = gr.Button("Load CSV", scale=1)
    load_status = gr.Markdown(f"Loaded `{DEFAULT_CSV}` — {sim.total_rows:,} rows, {len(sim.df.columns)} columns.")

    with gr.Row():
        speed = gr.Slider(1, 200, value=10, step=1, label="Speed (rows / sec)")
        order_mode = gr.Radio(["Sequential", "Shuffled"], value="Sequential", label="Playback order")
        loop = gr.Checkbox(value=True, label="Loop when finished")
        buffer_size = gr.Slider(20, 500, value=100, step=10, label="Live buffer size (rows)")

    with gr.Row():
        start_btn = gr.Button("▶ Start", variant="primary")
        pause_btn = gr.Button("⏸ Pause")
        resume_btn = gr.Button("⏵ Resume")
        stop_btn = gr.Button("⏹ Stop / Reset")

    status = gr.Markdown("**State:** STOPPED")

    gr.Markdown("### Live message stream (most recent first)")
    live_table = gr.Dataframe(headers=list(sim.df.columns), row_count=(20, "fixed"), wrap=True)

    gr.Markdown("### Rolling metrics")
    with gr.Row():
        metric_a = gr.Dropdown(METRIC_CHOICES, value="MessageRateInWindow", label="Chart 1 metric")
        metric_b = gr.Dropdown(METRIC_CHOICES, value="MemoryAnonMB", label="Chart 2 metric")
    with gr.Row():
        plot_a = gr.LinePlot(label="Chart 1")
        plot_b = gr.LinePlot(label="Chart 2")

    gr.Markdown("### Ground-truth label mix in current buffer (descriptive only, not a detection)")
    label_bar = gr.BarPlot(x="Label", y="Count", label=" ") if hasattr(gr, "BarPlot") else gr.Dataframe()

    # --- wiring ---
    load_btn.click(do_load_csv, inputs=[csv_path], outputs=[load_status])

    start_btn.click(do_start, inputs=[speed, order_mode, loop, buffer_size], outputs=[])
    pause_btn.click(do_pause, inputs=[], outputs=[])
    resume_btn.click(do_resume, inputs=[], outputs=[])
    stop_btn.click(do_stop, inputs=[], outputs=[])
    speed.release(do_apply_speed, inputs=[speed, order_mode, loop, buffer_size], outputs=[])
    order_mode.change(do_apply_speed, inputs=[speed, order_mode, loop, buffer_size], outputs=[])
    loop.change(do_apply_speed, inputs=[speed, order_mode, loop, buffer_size], outputs=[])

    timer = gr.Timer(0.5)
    timer.tick(
        poll,
        inputs=[metric_a, metric_b],
        outputs=[status, live_table, plot_a, plot_b, label_bar],
    )

if __name__ == "__main__":
    demo.queue().launch()
