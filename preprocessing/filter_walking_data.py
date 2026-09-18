import xml.etree.ElementTree as ET
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
import os
import shutil
import pandas as pd
import matplotlib.pyplot as plt
import statistics
import numpy as np

NS = {"gpx": "http://www.topografix.com/GPX/1/0"}

def extract_points(path):
    tree = ET.parse(path)
    root = tree.getroot()

    points = []

    for pt in root.findall(".//gpx:trkpt", NS):
        time_elem = pt.find("gpx:time", NS)
        if time_elem is None:
            continue

        lat = float(pt.attrib["lat"])
        lon = float(pt.attrib["lon"])
        t = datetime.fromisoformat(time_elem.text.replace("Z", "+00:00"))

        points.append((lat, lon, t))

    return points


def distance_m(p1, p2):
    R = 6371000

    lat1, lon1 = radians(p1[0]), radians(p1[1])
    lat2, lon2 = radians(p2[0]), radians(p2[1])

     

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))

def compute_speeds(points):
    speeds = []
    for i in range(1, len(points)):
        dt = (points[i][2] - points[i-1][2]).total_seconds()
        if dt <= 0:
            continue
        speed = distance_m(points[i-1][:2], points[i][:2]) / dt
        speeds.append(speed)
    return speeds


def load_all_speeds(input_folder):
    rows = []
    for file in sorted(os.listdir(input_folder)):
        if not file.endswith(".gpx"):
            continue
        path = os.path.join(input_folder, file)
        try:
            points = extract_points(path)
            speeds = compute_speeds(points)
            for s in speeds:
                rows.append({"file": file, "speed_ms": s})
        except Exception as e:
            print(f"[ERROR] {file}: {e}")
    return pd.DataFrame(rows)


def plot_speed_distribution(df):
    speeds = df["speed_ms"]

    # Reference thresholds (m/s)
    thresholds = {
        "slow walk (0.3)":   0.3,
        "fast walk (2.5)":   2.5,
        "cycling (4.0)":     4.0,
        "slow vehicle (8)":  8.0,
    }

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle("Raw Speed Distribution — All Traces (no filter)", fontsize=14, fontweight="bold")

    # --- Full histogram ---
    axes[0].hist(speeds, bins=80, color="steelblue", edgecolor="white", linewidth=0.3)
    for label, v in thresholds.items():
        axes[0].axvline(v, linestyle="--", linewidth=1, label=label)
    axes[0].set_xlabel("Speed (m/s)")
    axes[0].set_ylabel("Count")
    axes[0].set_title("Full range")
    axes[0].legend(fontsize=8)

    # --- Zoomed histogram (0–6 m/s) to see walking range clearly ---
    zoomed = speeds[speeds <= 6]
    axes[1].hist(zoomed, bins=80, color="steelblue", edgecolor="white", linewidth=0.3)
    for label, v in thresholds.items():
        if v <= 6:
            axes[1].axvline(v, linestyle="--", linewidth=1, label=label)
    axes[1].axvline(speeds.mean(),   color="red",    linestyle="-", linewidth=1.2, label=f"Mean {speeds.mean():.2f}")
    axes[1].axvline(speeds.median(), color="orange", linestyle="-", linewidth=1.2, label=f"Median {speeds.median():.2f}")
    axes[1].set_xlabel("Speed (m/s)")
    axes[1].set_title("Zoomed 0–6 m/s")
    axes[1].legend(fontsize=8)

    # --- Box plot ---
    axes[2].boxplot(speeds, vert=True, patch_artist=True,
                    boxprops=dict(facecolor="steelblue", color="navy"),
                    medianprops=dict(color="red", linewidth=2),
                    flierprops=dict(marker=".", markersize=1.5, alpha=0.2))
    for label, v in thresholds.items():
        axes[2].axhline(v, linestyle="--", linewidth=1, label=label)
    axes[2].set_ylabel("Speed (m/s)")
    axes[2].set_title("Box plot")
    axes[2].set_xticks([])
    axes[2].legend(fontsize=8)

    plt.tight_layout()
    plt.savefig("speed_distribution_raw.png", dpi=150)
    plt.show()

    # --- Percentile breakdown ---
    print("\nRaw Speed Distribution Summary")
    print(f"  Total speed samples : {len(speeds):,}")
    print(f"  Total traces        : {df['file'].nunique():,}")
    print(f"  Mean                : {speeds.mean():.3f} m/s")
    print(f"  Median              : {speeds.median():.3f} m/s")
    print(f"  Std dev             : {speeds.std():.3f} m/s")
    print(f"  Max                 : {speeds.max():.3f} m/s")
    print()
    print("  Percentile breakdown:")
    for p in [5, 10, 25, 50, 75, 90, 95, 99]:
        print(f"    p{p:>2}: {speeds.quantile(p/100):.3f} m/s")
    print()
    print("  Proportion by mode (raw thresholds):")
    print(f"    stationary  (< 0.3 m/s)  : {(speeds < 0.3).mean():.1%}")
    print(f"    walking  (0.3–2.5 m/s)   : {speeds.between(0.3, 2.5).mean():.1%}")
    print(f"    cycling  (2.5–4.0 m/s)   : {speeds.between(2.5, 4.0).mean():.1%}")
    print(f"    vehicle  (> 4.0 m/s)     : {(speeds > 4.0).mean():.1%}")

def is_walking(points):

    # Too short
    if len(points) < 20:
        return False

    speeds = []

    for i in range(1, len(points)):

        lat1, lon1, t1 = points[i - 1]
        lat2, lon2, t2 = points[i]

        dt = (t2 - t1).total_seconds()

        if dt <= 0:
            continue

        dist = distance_m((lat1, lon1), (lat2, lon2))
        speed = dist / dt

        # Remove impossible GPS spikes
        if 0 <= speed < 15:
            speeds.append(speed)

    if len(speeds) < 10:
        return False

    speeds = np.array(speeds)

    # Separate moving speeds
    moving = speeds[speeds >= 0.3]

    if len(moving) < 10:
        return False

    # Robust statistics
    median_speed = np.median(moving)
    p95_speed = np.percentile(moving, 95)
    max_speed = np.max(moving)

    walking_ratio = np.mean((moving >= 0.5) & (moving <= 2.5))
    vehicle_ratio = np.mean(moving > 4.0)

    stationary_ratio = np.mean(speeds < 0.3)

    return (

        # Main walking behavior
        walking_ratio >= 0.65

        # Very little vehicle behavior
        and vehicle_ratio <= 0.03

        # Typical walking median
        and 0.7 <= median_speed <= 2.2

        # Avoid fast traces
        and p95_speed <= 3.5

        # Reject strong spikes
        and max_speed <= 7.0

        # Avoid traces that are mostly standing still
        and stationary_ratio <= 0.6
    )


def filter_walking(input_folder, output_folder):

    os.makedirs(output_folder, exist_ok=True)

    kept = 0
    rejected = 0

    for file in os.listdir(input_folder):

        if not file.endswith(".gpx"):
            continue

        path = os.path.join(input_folder, file)

        try:

            points = extract_points(path)

            if is_walking(points):

                shutil.copy(
                    path,
                    os.path.join(output_folder, file)
                )

                kept += 1

            else:
                rejected += 1

        except Exception as e:
            print("ERROR:", file, e)

    print(f"Kept: {kept}")
    print(f"Rejected: {rejected}")


input_folder = "paris_traces_clean"
output_folder = "paris_traces_walking"
df_speeds = load_all_speeds(output_folder)
plot_speed_distribution(df_speeds)
#filter_walking(input_folder, output_folder)
