import streamlit as st
import numpy as np
import plotly.graph_objects as go
from shapely.geometry import Polygon, box

# 1. APP CONFIGURATION
st.set_page_config(page_title="Solar Canopy Visualizer", layout="wide")
st.title("☀️ Solar Canopy & Shading Visualizer")

# 2. SIDEBAR
st.sidebar.header("Controls")
canopy_depth = st.sidebar.slider("Canopy Depth (meters)", 0.0, 2.0, 1.0, 0.1)
altitude = st.sidebar.slider("Sun Altitude Angle (°)", 1.0, 90.0, 45.0, 1.0)
azimuth = st.sidebar.slider("Sun Azimuth Angle (°)", 90.0, 270.0, 180.0, 1.0)

st.sidebar.markdown("---")
st.sidebar.header("Window Dimensions")
win_width = st.sidebar.slider("Window Width (m)", 0.5, 4.0, 3.0, 0.1)
win_height = st.sidebar.slider("Window Height (m)", 0.5, 3.0, 2.0, 0.1)

# 3. MATH & PROJECTION
win_x_min, win_x_max = -win_width/2, win_width/2
win_z_min, win_z_max = 1.0, 1.0 + win_height
window_area = win_width * win_height

alt_rad, az_rad = np.radians(altitude), np.radians(azimuth)
sun_vector = np.array([-np.sin(az_rad) * np.cos(alt_rad), -np.cos(az_rad) * np.cos(alt_rad), -np.sin(alt_rad)])

if sun_vector[1] < 0.001:
    shading_pct, shadow_poly_coords = 0.0, None
else:
    canopy_z = 3.0
    c1, c2, c3, c4 = np.array([-2.0, -canopy_depth, canopy_z]), np.array([2.0, -canopy_depth, canopy_z]), np.array([2.0, 0.0, canopy_z]), np.array([-2.0, 0.0, canopy_z])
    def project(p): return p + (-p[1] / sun_vector[1]) * sun_vector
    p = [project(c1), project(c2), project(c3), project(c4)]
    shadow_poly = Polygon([(pt[0], pt[2]) for pt in p])
    inter = shadow_poly.intersection(box(win_x_min, win_z_min, win_x_max, win_z_max))
    shading_pct = (inter.area / window_area) * 100 if not inter.is_empty else 0.0
    shadow_poly_coords = list(inter.exterior.coords) if not inter.is_empty and inter.geom_type == 'Polygon' else None

# 4. DISPLAY
c1, c2, c3 = st.columns(3)
c1.metric("Window Shaded", f"{shading_pct:.1f}%")
c2.metric("Status", "Protected" if shading_pct > 50 else "High Heat Risk")
c3.metric("Canopy", f"{canopy_depth} m")

fig = go.Figure()

# Background Reference Plane
fig.add_trace(go.Mesh3d(x=[-4, 4, 4, -4], y=[0, 0, 0, 0], z=[0, 0, 4, 4], color='lightgrey', opacity=0.1))

# The Window (Dynamic)
fig.add_trace(go.Mesh3d(
    x=[win_x_min, win_x_max, win_x_max, win_x_min], 
    y=[0, 0, 0, 0], 
    z=[win_z_min, win_z_min, win_z_max, win_z_max], 
    color='deepskyblue', opacity=0.8, name="Window"
))

# The Canopy
fig.add_trace(go.Mesh3d(
    x=[-2, 2, 2, -2], 
    y=[0, 0, -canopy_depth, -canopy_depth], 
    z=[3, 3, 3, 3], 
    color='dimgrey', name="Canopy"
))

# The Shadow
if shadow_poly_coords and len(shadow_poly_coords) >= 3:
    sx, sz = [pt[0] for pt in shadow_poly_coords], [pt[1] for pt in shadow_poly_coords]
    fig.add_trace(go.Mesh3d(
        x=sx, y=[0]*len(sx), z=sz, 
        color='navy', opacity=0.9, name="Shadow"
    ))

fig.update_layout(
    scene=dict(
        xaxis=dict(range=[-4, 4]),
        yaxis=dict(range=[-3, 3]),
        zaxis=dict(range=[0, 5])
    ), 
    margin=dict(l=0,r=0,b=0,t=0)
)
st.plotly_chart(fig, use_container_width=True)