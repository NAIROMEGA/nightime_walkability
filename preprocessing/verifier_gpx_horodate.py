import os
import shutil

def has_time_fast(path):
    with open(path, "rb") as f:
        return b"time>" in f.read()

def verifier_gpx_horodate(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    for file in os.listdir(input_folder):
        if not file.endswith(".gpx"):
            continue

        path = os.path.join(input_folder, file)

        if has_time_fast(path):
            shutil.copy(path, os.path.join(output_folder, file))

input_folder = "londres_segment_traces"
output_folder = "londres_traces_clean"

verifier_gpx_horodate(input_folder, output_folder)