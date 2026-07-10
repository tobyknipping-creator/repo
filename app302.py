import streamlit as st
import numpy as np
import plotly.graph_objects as go
from shapely.geometry import Polygon, box

# 1. APP CONFIGURATION
st.set_page_config(page_title="Solar Canopy Visualizer", layout="wide")
st.title("☀️ Solar Canopy & Shading Visualizer")

# 2. SIDEBAR - CONTROLS
st.sidebar.header("☀️ Sun Position")
altitude = st.sidebar.slider("Sun Altitude Angle (°)", 1.0, 90.0, 45.0, 1.0)
azimuth = st.sidebar.slider("Sun Azimuth Angle (°)", 90.0, 270.0, 180.0, 1.0)

st.sidebar.header("📐 Canopy Dimensions")
canopy_width = st.sidebar.slider("Canopy Width (meters)", 1.0, 6.0, 4.0, 0.1)
canopy_depth = st.sidebar.slider("Canopy Depth (meters)", 0.0, 2.0, 1.0, 0.1)

st.sidebar.header("🪟 Window Dimensions")
window_width = st.sidebar.slider("Window Width (meters)", 0.5, 4.0, 3.0, 0.1)
window_height = st.sidebar.slider("Window Height (meters)", 0.5, 3.0, 2.0, 0.1)

# 3. MATH & PROJECTION SETUP
# Dynamically center the window on the wall (X-axis)
win_x_min = -window_width / 2.0
win_x_max = window_width / 2.0
# Base the window height off a standard sill height (e.g., 1.0m up the wall)
win_z_min = 1.0
win_z_max = win_z_min + window_height

window_area = (win_x_max - win_x_min) * (win_z_max - win_z_min)
alt_rad, az_rad = np.radians(altitude), np.radians(azimuth)

# Sun vector: pointing from the sun towards the wall
sun_vector = np.array([-np.sin(az_rad) * np.cos(alt_rad), -np.cos(az_rad) * np.cos(alt_rad), -np.sin(alt_rad)])

# Canopy positioning setup (centered at X=0, placed at Z=3.0m)
canopy_z = 3.0
half_cw = canopy_width / 2.0

if sun_vector[1] < 0.001:
    shading_pct, shadow_poly_coords = 0.0, None
else:
    # Canopy corners based on dynamic sidebar width
    c1 = np.array([-half_cw, -canopy_depth, canopy_z])
    c2 = np.array([half_cw, -canopy_depth, canopy_z])
    c3 = np.array([half_cw, 0.0, canopy_z])
    c4 = np.array([-half_cw, 0.0, canopy_z])
    
    # Ray-tracing projection function onto the wall plane (Y=0)
    def project(p): 
        return p + (-p[1] / sun_vector[1]) * sun_vector

    p = [project(c1), project(c2), project(c3), project(c4)]
    shadow_poly = Polygon([(pt[0], pt[2]) for pt in p])
    inter = shadow_poly.intersection(box(win_x_min, win_z_min, win_x_max, win_z_max))
    
    shading_pct = (inter.area / window_area) * 100 if not inter.is_empty else 0.0
    shadow_poly_coords = list(inter.exterior.coords) if not inter.is_empty and inter.geom_type == 'Polygon' else None

# 4. DISPLAY METRICS
c1, c2, c3 = st.columns(3)
c1.metric("Window Shaded", f"{shading_pct:.1f}%")
c2.metric("Status", "Protected" if shading_pct > 50 else "High Heat Risk")
c3.metric("Canopy Area", f"{canopy_width * canopy_depth:.2f} m²")

# 5. 3D GRAPHIC GENERATION
fig = go.Figure()

# Wall (Background)
fig.add_trace(go.Mesh3d(x=[-4, 4, 4, -4], y=[0, 0, 0, 0], z=[0, 0, 4, 4], color='lightgrey', opacity=0.5, name="Wall"))

# Dynamic Window
fig.add_trace(go.Mesh3d(x=[win_x_min, win_x_max, win_x_max, win_x_min], y=[0, 0, 0, 0], z=[win_z_min, win_z_min, win_z_max, win_z_max], color='deepskyblue', opacity=0.6, name="Window"))

# Dynamic Canopy (Using Scatter3d loop to prevent rendering distortion)
fig.add_trace(go.Scatter3d(
    x=[-half_cw, half_cw, half_cw, -half_cw, -half_cw],
    y=[0, 0, -canopy_depth, -canopy_depth, 0],
    z=[canopy_z, canopy_z, canopy_z, canopy_z, canopy_z],
    mode='lines',
    surfaceaxis=2, # Fills parallel to the Z plane
    surfacecolor='dimgrey',
    line=dict(color='black', width=2),
    name="Canopy"
))

# Dynamic Intersection Shadow
if shadow_poly_coords:
    sx = [pt[0] for pt in shadow_poly_coords]
    sz = [pt[1] for pt in shadow_poly_coords]
    sy = [-0.01] * len(sx)  # Slight offset out from the wall to prevent visual overlay glitching
    
    fig.add_trace(go.Scatter3d(
        x=sx, y=sy, z=sz,
        mode='lines',
        surfaceaxis=1,                  
        surfacecolor='rgba(10,30,80,0.6)', 
        line=dict(color='rgba(10,30,80,0.9)', width=3),
        name="Shadow"
    ))

# Graph layout configurations
fig.update_layout(
    scene=dict(
        xaxis_range=[-4,4], 
        yaxis_range=[-2,2], 
        zaxis_range=[0,4],
        aspectmode='manual',
        aspectratio=dict(x=1, y=0.5, z=0.5)
    ), 
    margin=dict(l=0, r=0, b=0, t=0)
)

st.plotly_chart(fig, use_container_width=True)