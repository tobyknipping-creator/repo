import streamlit as st
import numpy as np
import plotly.graph_objects as go
from shapely.geometry import Polygon, box

# 1. APP CONFIGURATION
st.set_page_config(page_title="Solar Canopy Visualizer", layout="wide")
st.title("☀️ Solar Canopy & Shading Visualizer")

# 2. SIDEBAR
st.sidebar.header("Controls")
canopy_depth = st.sidebar.slider("Canopy Depth (m)", 0.0, 2.0, 1.0, 0.1)
altitude = st.sidebar.slider("Sun Altitude (°)", 1.0, 90.0, 45.0, 1.0)
azimuth = st.sidebar.slider("Sun Azimuth (°)", 90.0, 270.0, 180.0, 1.0)

st.sidebar.markdown("---")
st.sidebar.header("Window Dimensions")
win_width = st.sidebar.slider("Window Width (m)", 0.5, 4.0, 3.0, 0.1)
win_height = st.sidebar.slider("Window Height (m)", 0.5, 3.0, 2.0, 0.1)

# 3. MATH
win_x_min, win_x_max = -win_width/2, win_width/2
win_z_min, win_z_max = 1.0, 1.0 + win_height
window_area = win_width * win_height

alt_rad, az_rad = np.radians(altitude), np.radians(azimuth)
sun_vector = np.array([-np.sin(az_rad) * np.cos(alt_rad), -np.cos(az_rad) * np.cos(alt_rad), -np.sin(alt_rad)])

# Canopy corners
canopy_z = 3.0
c1, c2, c3, c4 = [-2.0, -canopy_depth, canopy_z], [2.0, -canopy_depth, canopy_z], [2.0, 0.0, canopy_z], [-2.0, 0.0, canopy_z]

# Project canopy shadow to Z=0
def project(p): return np.array(p) + (-np.array(p)[2] / sun_vector[2]) * sun_vector
p = [project(c1), project(c2), project(c3), project(c4)]
shadow_poly = Polygon([(pt[0], pt[1]) for pt in p])
inter = shadow_poly.intersection(box(win_x_min, 0, win_x_max, 0)) # simplified 2D intersect

shading_pct = (inter.area / window_area) * 100 if not inter.is_empty else 0.0

# 4. DISPLAY
c1, c2, c3 = st.columns(3)
c1.metric("Window Shaded", f"{shading_pct:.1f}%")
c2.metric("Status", "Protected" if shading_pct > 50 else "High Heat Risk")
c3.metric("Canopy", f"{canopy_depth} m")

fig = go.Figure()

# Draw Window (Blue)
fig.add_trace(go.Mesh3d(
    x=[win_x_min, win_x_max, win_x_max, win_x_min], y=[0,0,0,0], z=[win_z_min, win_z_min, win_z_max, win_z_max],
    color='cyan', opacity=0.5, name="Window"
))

# Draw Canopy (Grey)
fig.add_trace(go.Mesh3d(
    x=[-2, 2, 2, -2], y=[0, 0, -canopy_depth, -canopy_depth], z=[3, 3, 3, 3],
    color='grey', opacity=0.8, name="Canopy"
))

fig.update_layout(scene=dict(
    xaxis=dict(range=[-4,4]), yaxis=dict(range=[-3,3]), zaxis=dict(range=[0,5])
))
st.plotly_chart(fig, use_container_width=True)