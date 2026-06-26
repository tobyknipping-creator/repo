import streamlit as st
import numpy as np
import plotly.graph_objects as go
from shapely.geometry import Polygon, box

st.set_page_config(page_title="Solar Canopy Visualizer", layout="wide")
st.title("☀️ Solar Canopy Shading Visualizer (2D View)")

# --- SIDEBAR ---
canopy_depth = st.sidebar.slider("Canopy Depth (m)", 0.0, 2.0, 1.0, 0.1)
altitude = st.sidebar.slider("Sun Altitude (°)", 1.0, 90.0, 45.0, 1.0)
win_width = st.sidebar.slider("Window Width (m)", 0.5, 4.0, 3.0, 0.1)
win_height = st.sidebar.slider("Window Height (m)", 0.5, 3.0, 2.0, 0.1)

# --- CALCULATIONS ---
# Simplified projection: shadow length = depth / tan(altitude)
shadow_length = canopy_depth / np.tan(np.radians(altitude))
shading_pct = min(100, (shadow_length / win_height) * 100)

# --- DISPLAY ---
col1, col2 = st.columns([1, 2])
col1.metric("Window Shaded", f"{shading_pct:.1f}%")
col1.metric("Status", "Protected" if shading_pct > 50 else "High Heat Risk")

# Simple 2D Bar Plot to represent the window
fig = go.Figure()
fig.add_shape(type="rect", x0=0, y0=0, x1=win_width, y1=win_height, fillcolor="cyan", opacity=0.5)
fig.add_shape(type="rect", x0=0, y0=win_height - (shadow_length if shadow_length < win_height else win_height), x1=win_width, y1=win_height, fillcolor="navy", opacity=0.8)
fig.update_xaxes(range=[-1, win_width+1], showticklabels=False)
fig.update_yaxes(range=[-1, win_height+1], showticklabels=False)
st.plotly_chart(fig)
