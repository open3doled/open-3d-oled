import plotly.graph_objects as go

import pandas as pd

# Load data
df = pd.read_csv("./2024-08-19_180919_debug_opt_stream_readings.csv")
# df = df.iloc[100000:200000]  # or use the condition method above

# Create figure
fig = go.Figure()


fig.add_trace(
    go.Scatter(
        x=list(df.opt_current_time),
        y=list(df.left_sensor),
        name="left_sensor",
        yaxis="y1",
    )
)
fig.add_trace(
    go.Scatter(
        x=list(df.opt_current_time),
        y=list(df.right_sensor),
        name="right_sensor",
        yaxis="y1",
    )
)

# cols = df.keys()
cols = (
    "opt_current_time",
    "left_sensor",
    "right_sensor",
    "opt_block_signal_detection_until",
    # "left_sent_ir",
    # "right_sent_ir",
    "opt_reading_triggered_left",
    "opt_reading_triggered_right",
)
for col in cols:
    if col in ("opt_current_time", "left_sensor", "right_sensor"):
        continue
    print(col)
    fig.add_trace(
        go.Scatter(
            x=list(df.opt_current_time), y=list(getattr(df, col)), name=col, yaxis="y2"
        )
    )

# Add range slider
fig.update_layout(
    xaxis=dict(
        rangeslider=dict(visible=True),
        type="linear",
    ),
    # yaxis_range=[0, 64],
    yaxis_range=[0, 255],
    yaxis=dict(title="Sensor Intensity"),
    yaxis2=dict(
        title="State Data",
        overlaying="y",
        side="right",
        range=[0, 1.2],
    ),
)

fig.show()
