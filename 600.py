import streamlit as st
import numpy as np
import plotly.graph_objects as go
from shapely.geometry import Polygon, box
import requests
import pandas as pd
from datetime import datetime
from pvlib.location import Location

# 1. APP CONFIGURATION
st.set_page_config(page_title="Annual Solar Gain & Orientation Simulator", layout="wide")
st.title("☀️ Building Orientation & Annual Solar Gain Simulator")

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

# 2. SIDEBAR CONTROLS
st.sidebar.header("📍 Location & Glass Properties")
postcode_input = st.sidebar.text_input("UK Postcode", "SW1A 1AA")
shgc = st.sidebar.slider("Glass SHGC (Solar Heat Gain Coeff.)", 0.1, 0.9, 0.6, 0.05)

st.sidebar.header("Compass Orientation")
wall_orientation = st.sidebar.slider(
    "Wall Faces Towards (° Azimuth)", 
    0, 360, 180, 5,
    help="0° = North, 90° = East, 180° = South, 270° = West"
)

def get_cardinal(deg):
    if deg in range(338, 361) or deg in range(0, 23): return "North 🧭"
    if deg in range(23, 68): return "Northeast 📐"
    if deg in range(68, 113): return "East 🌅"
    if deg in range(113, 158): return "Southeast 📐"
    if deg in range(158, 203): return "South ☀️"
    if deg in range(203, 248): return "Southwest 📐"
    if deg in range(248, 293): return "West 🌇"
    return "Northwest 📐"

st.sidebar.markdown(f"**Current Facing:** `{get_cardinal(wall_orientation)}` ({wall_orientation}°)")

st.sidebar.header("📐 Canopy Dimensions")
canopy_width = st.sidebar.slider("Canopy Width (m)", 1.0, 6.0, 4.0, 0.1)
canopy_depth = st.sidebar.slider("Canopy Depth (m)", 0.0, 2.0, 1.0, 0.1)

st.sidebar.header("🪟 Window Dimensions")
window_width = st.sidebar.slider("Window Width (m)", 0.5, 4.0, 2.5, 0.1)
window_height = st.sidebar.slider("Window Height (m)", 0.5, 3.0, 2.0, 0.1)

# Geolocation Lookup
coords = get_lat_lon(postcode_input)
lat, lon = coords if coords else (51.507, -0.127)

# 3. CORE MATH: ANNUAL SIMULATION ENGINE
@st.cache_data(show_spinner="Simulating solar tracking across 8,760 hours...")
def run_annual_simulation(lat, lon, w_width, w_height, c_width, c_depth, shgc_val, wall_ori):
    win_x_min, win_x_max = -w_width / 2.0, w_width / 2.0
    win_z_min, win_z_max = 1.0, 1.0 + w_height
    window_area = (win_x_max - win_x_min) * (win_z_max - win_z_min)
    win_box = box(win_x_min, win_z_min, win_x_max, win_z_max)
    
    canopy_z = win_z_max 
    half_cw = c_width / 2.0
    
    times = pd.date_range(start='2026-01-01 00:00', end='2026-12-31 23:00', freq='h', tz='Europe/London')
    
    loc_obj = Location(latitude=lat, longitude=lon, tz='Europe/London')
    solpos = loc_obj.get_solarposition(times)
    cs_irrad = loc_obj.get_clearsky(times)
    
    ghi = cs_irrad['ghi'].values 
    altitudes = solpos['apparent_elevation'].values
    azimuths = solpos['azimuth'].values
    
    shaded_percentages = []
    solar_gains_with_canopy = []
    solar_gains_no_canopy = []
    
    for i in range(len(times)):
        alt = altitudes[i]
        az = azimuths[i]
        rad = ghi[i] 
        
        if alt <= 0 or rad <= 0:
            shaded_percentages.append(0.0)
            solar_gains_with_canopy.append(0.0)
            solar_gains_no_canopy.append(0.0)
            continue
            
        relative_azimuth = az - (wall_ori - 180)
        alt_rad, az_rad = np.radians(alt), np.radians(relative_azimuth)
        
        sun_vector = np.array([
            -np.sin(az_rad) * np.cos(alt_rad),
            -np.cos(az_rad) * np.cos(alt_rad),
            -np.sin(alt_rad)
        ])
        
        cos_incidence = np.cos(alt_rad) * np.cos(az_rad)
        if cos_incidence < 0: cos_incidence = 0 
        
        effective_rad = rad * cos_incidence
        base_gain_kw = (window_area * effective_rad * shgc_val) / 1000.0
        solar_gains_no_canopy.append(base_gain_kw)
        
        if sun_vector[1] < 0.001 or base_gain_kw == 0: 
            shaded_percentages.append(100.0)
            solar_gains_with_canopy.append(0.0)
        else:
            c1 = np.array([-half_cw, -c_depth, canopy_z])
            c2 = np.array([half_cw, -c_depth, canopy_z])
            c3 = np.array([half_cw, 0.0, canopy_z])
            c4 = np.array([-half_cw, 0.0, canopy_z])
            
            def project(p): return p + (-p[1] / sun_vector[1]) * sun_vector
            p = [project(c1), project(c2), project(c3), project(c4)]
            
            shadow_poly = Polygon([(pt[0], pt[2]) for pt in p])
            inter = shadow_poly.intersection(win_box)
            
            pct = (inter.area / window_area) * 100 if not inter.is_empty else 0.0
            shaded_percentages.append(pct)
            
            adjusted_gain_kw = base_gain_kw * (1.0 - (pct / 100.0))
            solar_gains_with_canopy.append(adjusted_gain_kw)
            
    df = pd.DataFrame({
        'Time': times, 'Month': times.month_name(), 'Hour': times.hour,
        'Shading_Pct': shaded_percentages,
        'Gain_No_Canopy_kWh': solar_gains_no_canopy, 'Gain_With_Canopy_kWh': solar_gains_with_canopy,
        'Altitude': altitudes, 'Azimuth': azimuths
    })
    return df

# Run simulation calculations
df_results = run_annual_simulation(lat, lon, window_width, window_height, canopy_width, canopy_depth, shgc, wall_orientation)

# 4. LIVE INTERACTIVE 3D VISUALIZER
st.subheader("👁️ Interactive 3D Preview Shadow Analyzer")

months_ordered = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
t_col1, t_col2 = st.columns(2)
with t_col1:
    select_m = st.selectbox("Select Preview Month", months_ordered, index=5) 
with t_col2:
    select_h = st.slider("Select Preview Hour (24h)", 0, 23, 12)

filtered_df = df_results[(df_results['Month'] == select_m) & (df_results['Hour'] == select_h)]

if not filtered_df.empty:
    preview_row = filtered_df.iloc[0]
    p_alt = preview_row['Altitude']
    p_az = preview_row['Azimuth'] - (wall_orientation - 180)
    p_shading = preview_row['Shading_Pct']
    
    st.info(f"**Visualizing:** {select_m} at {select_h}:00 | **Calculated Window Shading:** {p_shading:.1f}%")

    p_alt_rad, p_az_rad = np.radians(p_alt), np.radians(p_az)
    
    p_sun = np.array([
        -np.sin(p_az_rad) * np.cos(p_alt_rad),
        -np.cos(p_az_rad) * np.cos(p_alt_rad),
        -np.sin(p_alt_rad)
    ])

    win