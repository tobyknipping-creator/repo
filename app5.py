# 4. DISPLAY
c1, c2, c3 = st.columns(3)
c1.metric("Window Shaded", f"{shading_pct:.1f}%")
c2.metric("Status", "Protected" if shading_pct > 50 else "High Heat Risk")
c3.metric("Canopy", f"{canopy_depth} m")

fig = go.Figure()
# Background/Reference structure
fig.add_trace(go.Mesh3d(x=[-4, 4, 4, -4], y=[0, 0, 0, 0], z=[0, 0, 4, 4], color='lightgrey', opacity=0.3))

# UPDATED: Window Mesh using dynamic slider values
fig.add_trace(go.Mesh3d(
    x=[win_x_min, win_x_max, win_x_max, win_x_min], 
    y=[0, 0, 0, 0], 
    z=[win_z_min, win_z_min, win_z_max, win_z_max], 
    color='deepskyblue', opacity=0.6, name="Window"
))

# Canopy Mesh
fig.add_trace(go.Mesh3d(
    x=[-2, 2, 2, -2], 
    y=[0, 0, -canopy_depth, -canopy_depth], 
    z=[3, 3, 3, 3], 
    color='dimgrey', name="Canopy"
))

# Shading Path/Projection Mesh
if shadow_poly_coords:
    sx, sz = [pt[0] for pt in shadow_poly_coords], [pt[1] for pt in shadow_poly_coords]
    fig.add_trace(go.Mesh3d(
        x=sx, y=[0]*len(sx), z=sz, 
        color='rgba(10,30,80,0.6)', opacity=0.7, name="Shadow"
    ))

fig.update_layout(scene=dict(xaxis_range=[-4,4], yaxis_range=[-2,2], zaxis_range=[0,4]), margin=dict(l=0,r=0,b=0,t=0))
st.plotly_chart(fig, use_container_width=True)