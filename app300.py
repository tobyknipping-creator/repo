# 4. DISPLAY
c1, c2, c3 = st.columns(3)
c1.metric("Window Shaded", f"{shading_pct:.1f}%")
c2.metric("Status", "Protected" if shading_pct > 50 else "High Heat Risk")
c3.metric("Canopy", f"{canopy_depth} m")

fig = go.Figure()

# Wall
fig.add_trace(go.Mesh3d(x=[-4, 4, 4, -4], y=[0, 0, 0, 0], z=[0, 0, 4, 4], color='lightgrey', opacity=0.5, name="Wall"))
# Window
fig.add_trace(go.Mesh3d(x=[win_x_min, win_x_max, win_x_max, win_x_min], y=[0, 0, 0, 0], z=[win_z_min, win_z_min, win_z_max, win_z_max], color='deepskyblue', opacity=0.6, name="Window"))
# Canopy
fig.add_trace(go.Mesh3d(x=[-2, 2, 2, -2], y=[0, 0, -canopy_depth, -canopy_depth], z=[3, 3, 3, 3], color='dimgrey', name="Canopy"))

# FIXED: Drawing the shadow using Scatter3d with surfaceaxis=1
if shadow_poly_coords:
    sx = [pt[0] for pt in shadow_poly_coords]
    sz = [pt[1] for pt in shadow_poly_coords]
    sy = [-0.01] * len(sx)  # Offset slightly in front of the wall to avoid visual clipping
    
    fig.add_trace(go.Scatter3d(
        x=sx, y=sy, z=sz,
        mode='lines',
        surfaceaxis=1,                  # 1 means fill perpendicular to the Y-axis
        surfacecolor='rgba(10,30,80,0.6)', # Sets the filled face color
        line=dict(color='rgba(10,30,80,0.9)', width=3),
        name="Shadow"
    ))

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