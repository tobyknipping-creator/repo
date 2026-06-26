import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("☀️ 3D Solar Canopy")

# --- CONTROLS ---
canopy_depth = st.sidebar.slider("Canopy Depth", 0.5, 2.0, 1.0)
win_w = st.sidebar.slider("Window Width", 0.5, 4.0, 1.0)
win_h = st.sidebar.slider("Window Height", 0.5, 3.0, 1.0)
alt = np.radians(st.sidebar.slider("Sun Altitude", 10.0, 90.0, 45.0))

# --- MATH ---
shadow_h = canopy_depth / np.tan(alt)
shaded_h = min(win_h, shadow_h)

# --- 3D PLOT ---
fig = go.Figure()

# 1. Window Plane
fig.add_trace(go.Mesh3d(x=[-win_w/2, win_w/2, win_w/2, -win_w/2], 
                        y=[0, 0, 0, 0], 
                        z=[0, 0, win_h, win_h], color='cyan', opacity=0.3))

# 2. Shadow Plane (The rectangle part)
fig.add_trace(go.Mesh3d(x=[-win_w/2, win_w/2, win_w/2, -win_w/2], 
                        y=[0, 0, 0, 0], 
                        z=[win_h-shaded_h, win_h-shaded_h, win_h, win_h], color='navy', opacity=0.8))

# 3. FIX PERSPECTIVE
fig.update_layout(scene=dict(aspectmode='data'), margin=dict(l=0,r=0,b=0,t=0))

st.plotly_chart(fig, use_container_width=True)