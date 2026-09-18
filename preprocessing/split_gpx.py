import xml.etree.ElementTree as ET
import uuid
import os
from copy import deepcopy

def split_gpx_file(input_file, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    tree = ET.parse(input_file)
    root = tree.getroot()

    # Detect namespace dynamically
    if root.tag.startswith("{"):
        ns_uri = root.tag.split("}")[0].strip("{")
        ns = {"gpx": ns_uri}
    else:
        ns = {"gpx": ""}

    for trk in root.findall("gpx:trk", ns):
        # Create a new GPX root
        new_root = ET.Element("gpx", xmlns=ns["gpx"])

        # Append a copy of the track
        new_root.append(trk)

        new_tree = ET.ElementTree(new_root)

        filename = f"trace_{uuid.uuid4()}.gpx"
        path = os.path.join(output_dir, filename)

        new_tree.write(path, encoding="utf-8", xml_declaration=True)
def split_gpx_by_trkseg(input_file, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    tree = ET.parse(input_file)
    root = tree.getroot()

    # Detect namespace dynamically
    if root.tag.startswith("{"):
        ns_uri = root.tag.split("}")[0].strip("{")
        ns = {"gpx": ns_uri}
    else:
        ns_uri = ""
        ns = {"gpx": ""}

    for trk in root.findall("gpx:trk", ns):

        trksegs = trk.findall("gpx:trkseg", ns)

        for seg in trksegs:

            # Create new GPX root
            new_root = ET.Element("gpx", xmlns=ns_uri)

            # Create track
            new_trk = ET.SubElement(new_root, "trk")

            # Copy optional track name
            name = trk.find("gpx:name", ns)
            if name is not None:
                new_name = ET.SubElement(new_trk, "name")
                new_name.text = name.text

            # Add copied segment
            new_trk.append(deepcopy(seg))

            filename = f"trace_{uuid.uuid4()}.gpx"
            path = os.path.join(output_dir, filename)

            new_tree = ET.ElementTree(new_root)
            new_tree.write(path, encoding="utf-8", xml_declaration=True)


folder = "londres_gpx"

for file in os.listdir(folder):
    if file.endswith(".gpx"):
        path = os.path.join(folder, file)
        #split_gpx_file(path, "./paris_traces")
for file in os.listdir("londres_traces"):
    if file.endswith(".gpx"):
        path = os.path.join("londres_traces", file)
        split_gpx_by_trkseg(path,"./londres_segment_traces")