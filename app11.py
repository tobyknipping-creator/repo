import streamlit as st
import numpy as np
import plotly.graph_objects as go
from shapely.geometry import box

st.set_page_config(page_title="Solar Canopy Visualizer", layout="wide")
st.title("☀️ Solar Canopy Shading Visualizer (2D)")

# --- SIDEBAR ---
canopy_depth = st.sidebar.slider("Canopy Depth (m)", 0.0, 2.0, 1.0, 0.1)
altitude = st.sidebar.slider("Sun Altitude (°)", 1.0, 90.0, 45.0, 1.0)
win_width = st.sidebar.slider("Window Width (m)", 0.5, 4.0, 1.0, 0.1)
win_height = st.sidebar.slider("Window Height (m)", 0.5, 3.0, 1.0, 0.1)

# --- CALCULATIONS ---
# Simplified projection
shadow_length = canopy_depth / np.tan(np.radians(altitude))
shading_pct = min(100, (shadow_length / win_height) * 100)

# --- DISPLAY ---
col1, col2 = st.columns([1, 3])
col1.metric("Window Shaded", f"{shading_pct:.1f}%")

fig = go.Figure()
# Window
fig.add_shape(type="rect", x0=0, y0=0, x1=win_width, y1=win_height, fillcolor="cyan", opacity=0.3, line=dict(width=2))
# Shadow
fig.add_shape(type="rect", x0=0, y0=win_height - min(shadow_length, win_height), x1=win_width, y1=win_height, fillcolor="navy", opacity=0.6)

# FORCE SQUARE PROPORTIONS
fig.update_layout(
    xaxis=dict(range=[-0.5, win_width + 0.5], scaleanchor="y", scaleratio=1),
    yaxis=dict(range=[-0.5, win_height + 0.5]),
    margin=dict(l=20, r=20, t=20, b=20),
    height=500
)
st.plotly_chart(fig, use_container_width=True)