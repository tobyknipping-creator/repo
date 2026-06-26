import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Solar Canopy Visualizer", layout="wide")
st.title("☀️ Solar Canopy & Shading Visualizer (Isometric)")

# --- SIDEBAR ---
canopy_depth = st.sidebar.slider("Canopy Depth (m)", 0.0, 2.0, 1.0, 0.1)
altitude = st.sidebar.slider("Sun Altitude (°)", 1.0, 90.0, 45.0, 1.0)
win_width = st.sidebar.slider("Window Width (m)", 0.5, 4.0, 1.0, 0.1)
win_height = st.sidebar.slider("Window Height (m)", 0.5, 3.0, 1.0, 0.1)

# --- MATH ---
shadow_len = canopy_depth / np.tan(np.radians(altitude))
shaded_h = min(win_height, shadow_len)
shading_pct = (shaded_h / win_height) * 100

# --- DISPLAY (Isometric 3D) ---
col1, col2 = st.columns([1, 3])
col1.metric("Window Shaded", f"{shading_pct:.1f}%")

fig = go.Figure()

# 1. Window (Blue)
fig.add_trace(go.Mesh3d(
    x=[-win_width/2, win_width/2, win_width/2, -win_width/2], y=[0,0,0,0], z=[0,0,win_height,win_height],
    color='cyan', opacity=0.4, name="Window"
))

# 2. Shadow (Dark Blue)
fig.add_trace(go.Mesh3d(
    x=[-win_width/2, win_width/2, win_width/2, -win_width/2], y=[0,0,0,0], z=[win_height-shaded_h, win_height-shaded_h, win_height, win_height],
    color='navy', opacity=0.7, name="Shadow"
))

# 3. ISOMETRIC CAMERA LOCK
camera = dict(eye=dict(x=1.5, y=1.5, z=1.5))
fig.update_layout(
    scene=dict(
        camera=camera,
        aspectmode='data',
        xaxis=dict(showticklabels=False),
        yaxis=dict(showticklabels=False),
        zaxis=dict(showticklabels=False)
    ),
    margin=dict(l=0, r=0, t=0, b=0),
    height=500
)
st.plotly_chart(fig, use_container_width=True)