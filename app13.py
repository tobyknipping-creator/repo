import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

st.title("☀️ Solar Canopy Simple View")

# Controls
depth = st.sidebar.slider("Canopy Depth (m)", 0.1, 2.0, 1.0)
alt = st.sidebar.slider("Sun Altitude (°)", 10.0, 90.0, 45.0)
win_h = st.sidebar.slider("Window Height (m)", 0.5, 3.0, 2.0)

# Math: Shadow length on the window
shadow_len = depth / np.tan(np.radians(alt))
shaded_pct = min(100, (shadow_len / win_h) * 100)

st.metric("Shading Coverage", f"{shaded_pct:.1f}%")

# The "Simple Way" to draw
fig, ax = plt.subplots(figsize=(4, 6))
# Draw Window
ax.add_patch(plt.Rectangle((0, 0), 1, win_h, color='skyblue', label='Window'))
# Draw Shadow
ax.add_patch(plt.Rectangle((0, win_h - min(shadow_len, win_h)), 1, min(shadow_len, win_h), color='navy', label='Shadow'))

ax.set_xlim(-0.5, 1.5)
ax.set_ylim(-0.5, win_h + 0.5)
ax.set_aspect('equal')
st.pyplot(fig)