import folium
import pandas as pd

df_cams = pd.read_csv('data/cameras.csv')
semarang_map = folium.Map(
    location=[-6.9932, 110.4203], 
    zoom_start=13, 
    tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
    attr='Google Maps'
)

for idx, cam in df_cams.iterrows():
    folium.Marker(
        location=[cam['latitude'], cam['longitude']],
        popup=f"<b>{cam['camera_id']} - {cam['camera_name']}</b><br>Zona: {cam['zone']}",
        tooltip=f"{cam['camera_id']}: {cam['camera_name']}",
        icon=folium.Icon(color='red' if 'Pusat' in str(cam['zone']) else 'blue', icon='info-sign')
    ).add_to(semarang_map)

semarang_map.save('data/semarang_map.html')
print("Peta Semarang Google Maps berhasil di-generate ke data/semarang_map.html!")
