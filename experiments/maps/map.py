import folium
import os
import xml.etree.ElementTree as ET

NS = {"gpx": "http://www.topografix.com/GPX/1/0"}

def extract_coords(path):
    tree = ET.parse(path)
    root = tree.getroot()

    coords = []

    for pt in root.findall(".//gpx:trkpt", NS):
        lat = float(pt.attrib["lat"])
        lon = float(pt.attrib["lon"])
        coords.append((lat, lon))

    return coords

# Colors
day_color = "blue"
night_color = "red"
input_folder = "londres_traces_walking"

# center map roughly on London
m = folium.Map(location=[51.5, -0.12], zoom_start=12)

for file in os.listdir(input_folder):
    if not file.endswith(".gpx"):
        continue

    path = os.path.join(input_folder, file)
    coords = extract_coords(path)

    if len(coords) > 1:
        folium.PolyLine(coords, weight=2, opacity=0.6).add_to(m)

# save map
m.save("walking_traces_map.html")