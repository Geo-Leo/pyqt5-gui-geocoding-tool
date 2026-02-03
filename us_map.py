import folium

map = folium.Map([39.77, -101.39], zoom_start=4, tiles='cartodb positron') # coordinates for USA           
# tooltip = folium.GeoJsonTooltip(
#     fields=fields,
#     aliases=aliases,
#     localize=True,
#     sticky=False,
#     labels=True,
#     style="background-color: #F0EFEF; border: 2px solid black; border-radius: 3px; box-shadow: 3px;",
#     max_width=800)

# circlemarker = folium.CircleMarker(
#     radius=5,
#     color="blue",
#     weight=1,
#     fill=True,
#     fill_opacity=0.25,
#     opacity=1)

# features = folium.features.GeoJson(gdf, name="sites", tooltip=tooltip, marker=circlemarker)
# features.add_to(map)
# map.fit_bounds(map.get_bounds())

ws = r'C:\PSU\Geog489-Advanced_Python\FinalProject\Geocoding'
url = ws + r"\us_map.html" 
print("url:", url)
map.save(url)            