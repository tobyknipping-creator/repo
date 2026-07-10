import streamlit as st
import numpy as np
import plotly.graph_objects as go
from shapely.geometry import Polygon, box
import requests
import pandas as pd
from datetime import datetime, time as datetime_time
from pvlib.solarposition import get_solarposition
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

st.sidebar.header("🧭 Building Orientation")
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

# 3. CORE MATH: ANNUAL SIMULATION ENGINE (USING LOCATION)
@st.cache_data(show_spinner="Simulating solar tracking across 8,760 hours...")
def run_annual_simulation(lat, lon, w_width, w_height, c_width, c_depth, shgc_val, wall_ori):
    win_x_min, win_x_max = -w_width / 2.0, w_width / 2.0
    win_z_min, win_z_max = 1.0, 1.0 + w_height
    window_area = (win_x_max - win_x_min) * (win_z_max - win_z_min)
    win_box = box(win_x_min, win_z_min, win_x_max, win_z_max)
    
    canopy_z = win_z_max 
    half_cw = c_width / 2.0
    
    times = pd.date_range(start='2026-01-01 00:00', end='2026-12-31 23:00', freq='h', tz='Europe/London')
    
    # Clean implementation using pvlib Location object
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
        sun_vector = np.array([-np.sin(az_rad) * np.cos(alt_rad), -np.cos(az_rad) * np.cos(alt_rad), -np.sin(alt_rad)])
        
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
        'Gain_No_Canopy_kWh': solar_gains_no_canopy, 'Gain_With_Canopy_kWh': solar_gains_with_canopy
    })
    return df, altitudes, azimuths

# Run simulation calculations
df_results, annual_alts, annual_azs = run_annual_simulation(lat, lon, window_width, window_height, canopy_width, canopy_depth, shgc, wall_orientation)

# 4. SPLIT LAYOUT: LIVE 3D VISUALIZER (TOP) & ANNUAL GRAPHS (BOTTOM)
st.subheader("👁️ Live 3D Preview (Mid-day Summer Solstice Snapshot)")

preview_idx = 4116 
p_alt = annual_alts[preview_idx]
p_az = annual_azs[preview_idx] - (wall_orientation - 180)

p_alt_rad, p_az_rad = np.radians(p_alt), np.radians(p_az)
p_sun = np.array([-np.sin(p_az_rad) * np.cos(p_alt_rad), -np.cos(p_az_rad) * np.cos(p_alt_rad), -np.sin(p_alt_rad)])

win_x_min, win_x_max = -window_width / 2.0, window_width / 2.0
win_z_min, win_z_max = 1.0, 1.0 + window_height
canopy_z = win_z_max
half_cw = canopy_width / 2.0

preview_shadow = None
if p_alt > 0 and p_sun[1] >= 0.001:
    c1 = np.array([-half_cw, -canopy_depth, canopy_z])
    c2 = np.array([half_cw, -canopy_depth, canopy_z])
    c3 = np.array([half_cw, 0.0, canopy_z])
    c4 = np.array([-half_cw, 0.0, canopy_z])
    p_shapes = [c1 + (-pt[1] / p_sun[1]) * p_sun for pt in [c1, c2, c3, c4]]
    s_poly = Polygon([(pt[0], pt[2]) for pt in p_shapes])
    s_inter = s_poly.intersection(box(win_x_min, win_z_min, win_x_max, win_z_max))
    if not s_inter.is_empty and s_inter.geom_type == 'Polygon':
        preview_shadow = list(s_inter.exterior.coords)

fig3d = go.Figure()
fig3d.add_trace(go.Scatter3d(x=[-4, 4, 4, -4, -4], y=[0, 0, 0, 0, 0], z=[0, 0, 4, 4, 0], mode='lines', surfaceaxis=1, surfacecolor='rgba(230, 230, 230, 0.9)', name="Wall"))
fig3d.add_trace(go.Scatter3d(x=[win_x_min, win_x_max, win_x_max, win_x_min, win_x_min], y=[-0.01]*5, z=[win_z_min, win_z_min, win_z_max, win_z_max, win_z_min], mode='lines', surfaceaxis=1, surfacecolor='rgba(0, 191, 255, 0.7)', name="Window"))
fig3d.add_trace(go.Scatter3d(x=[-half_cw, half_cw, half_cw, -half_cw, -half_cw], y=[0, 0, -canopy_depth, -canopy_depth, 0], z=[canopy_z]*5, mode='lines', surfaceaxis=2, surfacecolor='dimgrey', name="Canopy"))

if preview_shadow:
    fig3d.add_trace(go.Scatter3d(x=[pt[0] for pt in preview_shadow], y=[-0.02]*len(preview_shadow), z=[pt[1] for pt in preview_shadow], mode='lines', surfaceaxis=1, surfacecolor='rgba(15, 25, 45, 0.65)', name="Shadow"))

fig3d.update_layout(scene=dict(xaxis_range=[-4, 4], yaxis_range=[-3, 3], zaxis_range=[0, 4], aspectmode='manual', aspectratio=dict(x=1, y=0.7, z=0.5), camera=dict(eye=dict(x=1.5, y=-2.2, z=1.5))), margin=dict(l=0, r=0, b=0, t=0), height=400)
st.plotly_chart(fig3d, use_container_width=True)

# 5. DISPLAY ANNUAL METRICS & GRAPHS
st.markdown("---")
st.subheader("📊 Annual Performance Dashboard")

totals_no_canopy = df_results['Gain_No_Canopy_kWh'].sum()
totals_with_canopy = df_results['Gain_With_Canopy_kWh'].sum()
energy_saved = totals_no_canopy - totals_with_canopy
avg_summer_shading = df_results[df_results['Month'].isin(['June', 'July', 'August'])]['Shading_Pct'].mean()

m1, m2, m3 = st.columns(3)
m1.metric("Annual Solar Heat Gain (No Canopy)", f"{totals_no_canopy:.0f} kWh")
m2.metric("Annual Solar Heat Gain (With Canopy)", f"{totals_with_canopy:.0f} kWh", delta=f"-{energy_saved:.0f} kWh Saved")
m3.metric("Average Summer Shading Exposure", f"{avg_summer_shading:.1f}%")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Monthly Heat Gain Summary**")
    monthly_summary = df_results.groupby('Month')[['Gain_No_Canopy_kWh', 'Gain_With_Canopy_kWh']].sum()
    months_ordered = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    monthly_summary = monthly_summary.reindex(months_ordered)
    
    fig_bars = go.Figure()
    fig_bars.add_trace(go.Bar(x=monthly_summary.index, y=monthly_summary['Gain_No_Canopy_kWh'], name='Unprotected', marker_color='crimson'))
    fig_bars.add_trace(go.Bar(x=monthly_summary.index, y=monthly_summary['Gain_With_Canopy_kWh'], name='With Canopy', marker_color='seagreen'))
    fig_bars.update_layout(barmode='group', margin=dict(l=20, r=20, b=20, t=20))
    st.plotly_chart(fig_bars, use_container_width=True)

with col2:
    st.markdown("**Hourly Shading Heatmap Matrix**")
    heatmap_data = df_results.pivot_table(index='Hour', columns='Month', values='Shading_Pct', aggfunc='mean')[months_ordered]
    fig_map = go.Figure(data=go.Heatmap(z=heatmap_data.values, x=heatmap_data.columns, y=heatmap_data.index, colorscale='YlOrRd', colorbar=dict(title='%')))
    fig_map.update_layout(margin=dict(l=20, r=20, b=20, t=20), yaxis=dict(autorange='reversed'))
    st.plotly_chart(fig_map, use_container_width=True)