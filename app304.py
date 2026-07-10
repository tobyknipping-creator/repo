import streamlit as st
import numpy as np
import plotly.graph_objects as go
from shapely.geometry import Polygon, box
import requests
import pandas as pd
from datetime import datetime, time as datetime_time
from pvlib.solarposition import get_solarposition

# 1. APP CONFIGURATION
st.set_page_config(page_title="Solar Canopy Visualizer", layout="wide")
st.title("☀️ Solar Canopy & Shading Visualizer")

# Helper function to fetch coordinates from a UK Postcode
def get_lat_lon(postcode):
    if not postcode or postcode.strip() == "":
        return None
    try:
        clean_postcode = postcode.replace(" ", "").strip().upper()
        url = f"https://api.postcodes.io/postcodes/{clean_postcode}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data['result']['latitude'], data['result']['longitude']
    except Exception:
        pass
    return None

# 2. SIDEBAR - ENVIRONMENT CONTROLS
st.sidebar.header("📍 Location & Time")
postcode_input = st.sidebar.text_input("UK Postcode", "SW1A 1AA")
selected_date = st.sidebar.date_input("Select Date", datetime.today())
selected_hour = st.sidebar.slider("Select Hour of Day", 0, 23, 12, 1)

# Geolocation lookup logic
coords = get_lat_lon(postcode_input)
if coords:
    lat, lon = coords
    st.sidebar.success(f"📍 Found: Lat {lat:.3f}, Lon {lon:.3f}")
    
    # Calculate Solar Position via pvlib
    dt = datetime.combine(selected_date, datetime_time(selected_hour, 0))
    times = pd.DatetimeIndex([dt]).tz_localize('Europe/London')
    solpos = get_solarposition(times, lat, lon)
    
    altitude = float(solpos['apparent_elevation'].iloc[0])
    azimuth = float(solpos['azimuth'].iloc[0])
else:
    st.sidebar.warning("Using default sun position (Noon, Equinox equivalent).")
    altitude, azimuth = 45.0, 180.0

st.sidebar.markdown(f"**Computed Sun Angle:** Altitude: {altitude:.1f}°, Azimuth: {azimuth:.1f}°")

# STRUCTURE CONTROLS
st.sidebar.header("📐 Canopy Dimensions")
canopy_width = st.sidebar.slider("Canopy Width (meters)", 1.0, 6.0, 4.0, 0.1)
canopy_depth = st.sidebar.slider("Canopy Depth (meters)", 0.0, 2.0, 1.0, 0.1)

st.sidebar.header("🪟 Window Dimensions")
window_width = st.sidebar.slider("Window Width (meters)", 0.5, 4.0, 2.5, 0.1)
window_height = st.sidebar.slider("Window Height (meters)", 0.5, 3.0, 2.0, 0.1)

# 3. MATH & PROJECTION SETUP
win_x_min, win_x_max = -window_width / 2.0, window_width / 2.0
win_z_min, win_z_max = 1.0, 1.0 + window_height
window_area = (win_x_max - win_x_min) * (win_z_max - win_z_min)

alt_rad, az_rad = np.radians(altitude), np.radians(azimuth)
sun_vector = np.array([-np.sin(az_rad) * np.cos(alt_rad), -np.cos(az_rad) * np.cos(alt_rad), -np.sin(alt_rad)])

canopy_z = 3.0
half_cw = canopy_width / 2.0

# Calculate shadow boundaries if the sun is up
if altitude <= 0 or sun_vector[1] < 0.001:
    shading_pct, shadow_poly_coords = 0.0, None
else:
    c1 = np.array([-half_cw, -canopy_depth, canopy_z])
    c2 = np.array([half_cw, -canopy_depth, canopy_z])
    c3 = np.array([half_cw, 0.0, canopy_z])
    c4 = np.array([-half_cw, 0.0, canopy_z])
    
    def project(p): return p + (-p[1] / sun_vector[1]) * sun_vector

    p = [project(c1), project(c2), project(c3), project(c4)]
    shadow_poly = Polygon([(pt[0], pt[2]) for pt in p])
    inter = shadow_poly.intersection(box(win_x_min, win_z_min, win_x_max, win_z_max))
    
    shading_pct = (inter.area / window_area) * 100 if not inter.is_empty else 0.0
    shadow_poly_coords = list(inter.exterior.coords) if not inter.is_empty and inter.geom_type == 'Polygon' else None

# 4. DISPLAY METRICS
c1, c2, c3 = st.columns(3)
c1.metric("Window Shaded", f"{shading_pct:.1f}%")
c2.metric("Status", "Protected" if shading_pct > 50 else "High Heat Risk" if altitude > 0 else "Nighttime")
c3.metric("Location Mode", "Postcode Lookup" if coords else "Default Manual")

# 5. 3D GRAPHIC GENERATION
fig = go.Figure()

# --- FIXED: Wall (Now using Scatter3d closed loop at Y = 0) ---
fig.add_trace(go.Scatter3d(
    x=[-4, 4, 4, -4, -4],
    y=[0, 0, 0, 0, 0],
    z=[0, 0, 4, 4, 0],
    mode='lines',
    surfaceaxis=1,
    surfacecolor='rgba(220, 220, 220, 0.9)', # Solid crisp grey wall
    line=dict(color='darkgrey', width=1),
    name="Wall"
))

# --- FIXED: Full Window (Now using Scatter3d layered slightly in front of the wall at Y = -0.01) ---
fig.add_trace(go.Scatter3d(
    x=[win_x_min, win_x_max, win_x_max, win_x_min, win_x_min],
    y=[-0.01, -0.01, -0.01, -0.01, -0.01],
    z=[win_z_min, win_z_min, win_z_max, win_z_max, win_z_min],
    mode='lines',
    surfaceaxis=1,
    surfacecolor='rgba(0, 191, 255, 0.7)', # Deep sky blue glass
    line=dict(color='white', width=2),
    name="Window"
))

# Canopy (Floating horizontal structure)
fig.add_trace(go.Scatter3d(
    x=[-half_cw, half_cw, half_cw, -half_cw, -half_cw],
    y=[0, 0, -canopy_depth, -canopy_depth, 0],
    z=[canopy_z, canopy_z, canopy_z, canopy_z, canopy_z],
    mode='lines', surfaceaxis=2, surfacecolor='dimgrey',
    line=dict(color='black', width=2), name="Canopy"
))

# Intersection Shadow (Layered slightly in front of the window at Y = -0.02)
if shadow_poly_coords:
    sx = [pt[0] for pt in shadow_poly_coords]
    sz = [pt[1] for pt in shadow_poly_coords]
    sy = [-0.02] * len(sx)  
    
    fig.add_trace(go.Scatter3d(
        x=sx, y=sy, z=sz,
        mode='lines', surfaceaxis=1, surfacecolor='rgba(15, 25, 45, 0.65)', 
        line=dict(color='rgba(10,20,40,0.8)', width=2), name="Shadow"
    ))

# Graph layout configurations
fig.update_layout(
    scene=dict(
        xaxis_range=[-4, 4], yaxis_range=[-3, 3], zaxis_range=[0, 4],
        aspectmode='manual',
        aspectratio=dict(x=1, y=0.7, z=0.5),
        camera=dict(eye=dict(x=1.5, y=-2.2, z=1.5))
    ),
    margin=dict(l=0, r=0, b=0, t=0)
)

st.plotly_chart(fig, use_container_width=True)