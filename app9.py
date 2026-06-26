import streamlit as st
import numpy as np
import plotly.graph_objects as go
from shapely.geometry import Polygon, box

st.set_page_config(page_title="Solar Canopy Visualizer", layout="wide")
st.title("☀️ Solar Canopy & Shading Visualizer")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Controls")
canopy_depth = st.sidebar.slider("Canopy Depth (m)", 0.0, 2.0, 1.0, 0.1)
altitude = st.sidebar.slider("Sun Altitude (°)", 1.0, 90.0, 45.0, 1.0)
azimuth = st.sidebar.slider("Sun Azimuth (°)", 90.0, 270.0, 180.0, 1.0)

st.sidebar.header("Window Dimensions")
win_width = st.sidebar.slider("Window Width (m)", 0.5, 4.0, 3.0, 0.1)
win_height = st.sidebar.slider("Window Height (m)", 0.5, 3.0, 2.0, 0.1)

# --- MATH ENGINE ---
win_x1, win_x2 = -win_width/2, win_width/2
win_z1, win_z2 = 1.0, 1.0 + win_height
window_area = win_width * win_height

alt_rad, az_rad = np.radians(altitude), np.radians(azimuth)
sun_vec = np.array([-np.sin(az_rad)*np.cos(alt_rad), -np.cos(az_rad)*np.cos(alt_rad), -np.sin(alt_rad)])

# Project canopy corners to ground (Z=0)
canopy_z = 3.0
corners = [[-2, 0, canopy_z], [2, 0, canopy_z], [2, -canopy_depth, canopy_z], [-2, -canopy_depth, canopy_z]]
projected = [np.array(c) + (-c[2]/sun_vec[2])*sun_vec if sun_vec[2] < 0 else c for c in corners]
shadow_poly = Polygon([(p[0], p[1]) for p in projected])
window_box = box(win_x1, -0.1, win_x2, 0.1) # Simplified intersection
intersect = shadow_poly.intersection(window_box)
shading_pct = (intersect.area / window_area) * 100 if not intersect.is_empty else 0.0

# --- DISPLAY ENGINE ---
col1, col2, col3 = st.columns(3)
col1.metric("Window Shaded", f"{shading_pct:.1f}%")
col2.metric("Status", "Protected" if shading_pct > 10 else "High Heat")
col3.metric("Canopy Depth", f"{canopy_depth} m")

fig = go.Figure()

# 1. DRAW WINDOW (Blue Plane)
fig.add_trace(go.Mesh3d(x=[win_x1, win_x2, win_x2, win_x1], y=[0,0,0,0], z=[win_z1, win_z1, win_z2, win_z2], color='cyan', opacity=0.6))

# 2. DRAW CANOPY (Grey Plane)
fig.add_trace(go.Mesh3d(x=[-2, 2, 2, -2], y=[0, 0, -canopy_depth, -canopy_depth], z=[3,3,3,3], color='grey', opacity=0.9))

# 3. DRAW SHADOW (Dark Blue)
if not intersect.is_empty:
    s_coords = list(intersect.exterior.coords)
    sx, sy = [p[0] for p in s_coords], [p[1] for p in s_coords]
    fig.add_trace(go.Mesh3d(x=sx, y=sy, z=[1]*len(sx), color='navy', opacity=0.9))

fig.update_layout(scene=dict(xaxis_range=[-4,4], yaxis_range=[-4,4], zaxis_range=[0,5]), margin=dict(l=0,r=0,b=0,t=0))
st.plotly_chart(fig, use_container_width=True)