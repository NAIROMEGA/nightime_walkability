import geopandas as gpd

from astral import LocationInfo
from astral.sun import sun

import pandas as pd
import os
import xml.etree.ElementTree as ET
import numpy as np
import networkx as nx

from pyproj import Geod
import osmnx as ox
import folium

from shapely.geometry import Point

from leuvenmapmatching.map.inmem import InMemMap
from leuvenmapmatching.matcher.distance import DistanceMatcher


# =========================================================
# DATA
# =========================================================

ign_path = r"/Users/oussamanair/Downloads/stage/BDTOPO_Paris/BDTOPO_3-5_TOUSTHEMES_GPKG_LAMB93_D075_2026-06-15/BDTOPO/1_DONNEES_LIVRAISON_2026-06-00418/BDT_3-5_GPKG_LAMB93_D075_ED2026-06-15/BDT_3-5_GPKG_LAMB93_D075-ED2026-06-15.gpkg"
street_light_path = (
    "/Users/oussamanair/Downloads/stage/eclairage-public.csv"
)

GPX_FOLDER = "paris_traces_walking"


# =========================================================
# STREETLIGHTS
# =========================================================

STREETLIGHTS_FILE = "paris_streetlights.gpkg"

if os.path.exists(STREETLIGHTS_FILE):

    print("Loading saved streetlights...")

    streetlights = gpd.read_file(
        STREETLIGHTS_FILE,
        layer="streetlights"
    )

else:

    print("Loading streetlights CSV...")

    streetlights = pd.read_csv(
        street_light_path,
        sep=";",
        encoding="utf-8"
    )

    streetlights = gpd.GeoDataFrame(
        streetlights,
        geometry=gpd.points_from_xy(
            streetlights["Longitude X (Lambert93)"],
            streetlights["Latitude Y (Lambert93)"]
        ),
        crs="EPSG:2154"
    )

    streetlights.to_file(
        STREETLIGHTS_FILE,
        layer="streetlights",
        driver="GPKG"
    )

    print(
        f"Streetlights saved to {STREETLIGHTS_FILE}"
    )


print(
    f"Streetlights: {len(streetlights):,}"
)


# =========================================================
# CITY
# =========================================================

city = LocationInfo(
    "Paris",
    "France",
    "Europe/Paris",
    48.8566,
    2.3522
)


# =========================================================
# GRAPH
# =========================================================

G = ox.load_graphml(
    "paris_walk.graphml"
)


# =========================================================
# ROAD EDGES
# =========================================================

roads = ox.graph_to_gdfs(
    G,
    nodes=False
)

roads = roads.to_crs(
    2154
)

roads = roads.reset_index()

roads["edge_id"] = list(
    zip(
        roads["u"],
        roads["v"],
        roads["key"]
    )
)


# =========================================================
# BUILDINGS
# =========================================================

BUILDINGS_FILE = "paris_buildings.gpkg"

if os.path.exists(BUILDINGS_FILE):

    print("Loading saved buildings...")

    buildings = gpd.read_file(
        BUILDINGS_FILE,
        layer="buildings"
    )

else:

    print("Loading buildings from BDTOPO...")

    buildings = gpd.read_file(
        ign_path,
        layer="batiment"
    )

    buildings = buildings.to_crs(
        2154
    )

    buildings.to_file(
        BUILDINGS_FILE,
        layer="buildings",
        driver="GPKG"
    )

    print(
        f"Buildings saved to {BUILDINGS_FILE}"
    )


print(
    f"Buildings: {len(buildings):,}"
)


# =========================================================
# HMM MAP
# =========================================================

map_con = InMemMap(
    "paris_walk",
    use_latlon=True,
    use_rtree=False,
    index_edges=True
)


for node, data in G.nodes(data=True):

    map_con.add_node(
        node,
        (
            data["y"],
            data["x"]
        )
    )


for u, v in G.edges():

    map_con.add_edge(
        u,
        v
    )


# =========================================================
# MATCHER
# =========================================================

matcher = DistanceMatcher(
    map_con,

    max_dist=30,
    max_dist_init=30,

    obs_noise=10,
    obs_noise_ne=30,

    dist_noise=15,

    non_emitting_length_factor=0.5,

    max_lattice_width=10
)


# =========================================================
# GPX
# =========================================================

NS = {
    "gpx":
    "http://www.topografix.com/GPX/1/0"
}


def load_gpx(path):

    tree = ET.parse(path)

    root = tree.getroot()

    pts = []

    for pt in root.findall(
        ".//gpx:trkpt",
        NS
    ):

        time_elem = pt.find(
            "gpx:time",
            NS
        )

        pts.append({

            "lat":
                float(
                    pt.attrib["lat"]
                ),

            "lon":
                float(
                    pt.attrib["lon"]
                ),

            "datetime":
                (
                    pd.to_datetime(
                        time_elem.text
                    )
                    if time_elem is not None
                    else pd.NaT
                )
        })

    return pd.DataFrame(pts)


# =========================================================
# STATE -> NODE
# =========================================================

def state_to_node(state):

    if isinstance(
        state,
        tuple
    ):
        return state[0]

    return state


# =========================================================
# STATE SEQUENCE -> EDGE SEQUENCE
# =========================================================

def states_to_edges(states):

    edges = []

    for i in range(
        len(states) - 1
    ):

        u = state_to_node(
            states[i]
        )

        v = state_to_node(
            states[i + 1]
        )

        if not G.has_edge(
            u,
            v
        ):
            continue

        edge_data = G.get_edge_data(
            u,
            v
        )

        # If parallel edges exist,
        # choose the shortest one.

        key, data = min(
            edge_data.items(),
            key=lambda x:
                x[1].get(
                    "length",
                    np.inf
                )
        )

        edge_id = (
            u,
            v,
            key
        )

        edges.append(
            edge_id
        )

    return edges


# =========================================================
# STATES -> COORDINATES
# =========================================================

def states_to_coords(states):

    coords = []

    for s in states:

        try:

            node = state_to_node(
                s
            )

            coords.append(
                (
                    G.nodes[node]["y"],
                    G.nodes[node]["x"]
                )
            )

        except Exception:

            pass

    return coords


# =========================================================
# TRAJECTORY PERIOD
# =========================================================

def trajectory_period(df):

    times = pd.to_datetime(
        df["datetime"],
        errors="coerce"
    ).dropna()

    if len(times) == 0:

        return "unknown"

    timestamp = times.iloc[0]

    # GPX timestamps are normally UTC

    if timestamp.tzinfo is None:

        timestamp = timestamp.tz_localize(
            "UTC"
        )

    timestamp = timestamp.tz_convert(
        "Europe/Paris"
    )

    # Nautical twilight
    #
    # Astral depression = 12 degrees

    s_twilight = sun(
        city.observer,
        date=timestamp.date(),
        tzinfo="Europe/Paris",
        dawn_dusk_depression=12
    )

    if (
        timestamp < s_twilight["dawn"]
        or
        timestamp > s_twilight["dusk"]
    ):

        return "night"

    return "day"


# =========================================================
# SAMPLE POINTS ON MATCHED EDGES
# =========================================================

def sample_points_on_edges(
    edge_sequence,
    roads,
    trace_id,
    period,
    random_state=42
):

    """
    For each matched edge, generate as many random
    points as there are occurrences of that edge
    in the matched sequence.
    """

    rng = np.random.default_rng(
        random_state
    )

    # -----------------------------------------------------
    # Count occurrences of each edge
    # -----------------------------------------------------

    edge_counts = {}

    for edge_id in edge_sequence:

        edge_counts[edge_id] = (
            edge_counts.get(edge_id, 0) + 1
        )

    # -----------------------------------------------------
    # Build lookup dictionary
    #
    # (u, v, key) -> geometry
    # -----------------------------------------------------

    roads_lookup = (
        roads[
            [
                "edge_id",
                "geometry"
            ]
        ]
        .drop_duplicates(
            subset="edge_id"
        )
    )

    roads_lookup = dict(
        zip(
            roads_lookup["edge_id"],
            roads_lookup["geometry"]
        )
    )

    sampled = []

    # -----------------------------------------------------
    # Sample points
    # -----------------------------------------------------

    for edge_id, n in edge_counts.items():

        geometry = roads_lookup.get(
            edge_id
        )

        if geometry is None:
            continue

        if geometry.is_empty:
            continue

        # -------------------------------------------------
        # Generate n random points on this edge
        # -------------------------------------------------

        for sample_idx in range(n):

            fraction = rng.uniform(
                0,
                1
            )

            point = geometry.interpolate(
                fraction,
                normalized=True
            )

            sampled.append({

                "trace_id":
                    trace_id,

                "period":
                    period,

                "edge_id":
                    edge_id,

                "sample_idx":
                    sample_idx,

                "fraction":
                    fraction,

                "geometry":
                    point

            })

    # -----------------------------------------------------
    # Return GeoDataFrame
    # -----------------------------------------------------

    if len(sampled) == 0:

        return gpd.GeoDataFrame(
            columns=[
                "trace_id",
                "period",
                "edge_id",
                "sample_idx",
                "fraction",
                "geometry"
            ],
            geometry="geometry",
            crs=roads.crs
        )

    return gpd.GeoDataFrame(
        sampled,
        geometry="geometry",
        crs=roads.crs
    )
# =========================================================
# PROCESS ONE TRACE
# =========================================================

def process_trace(
    gpx_path
):

    df = load_gpx(
        gpx_path
    )

    if len(df) < 5:

        return None

    # =====================================================
    # PERIOD
    # =====================================================

    period = trajectory_period(
        df
    )

    pts = list(
        zip(
            df["lat"],
            df["lon"]
        )
    )

    # =====================================================
    # FORWARD MATCHING
    # =====================================================

    try:

        forward_states, _ = matcher.match(
            pts
        )

    except Exception as e:

        print(
            "Forward error:",
            e
        )

        forward_states = []

    # =====================================================
    # BACKWARD MATCHING
    # =====================================================

    try:

        backward_states, _ = matcher.match(
            pts[::-1]
        )

        backward_states = (
            backward_states[::-1]
        )

    except Exception as e:

        print(
            "Backward error:",
            e
        )

        backward_states = []

    # =====================================================
    # COVERAGE
    # =====================================================

    forward_ratio = (

        len(forward_states)
        /
        len(df)

        if len(df) > 0
        else 0
    )

    backward_ratio = (

        len(backward_states)
        /
        len(df)

        if len(df) > 0
        else 0
    )

    # =====================================================
    # BEST DIRECTION
    # =====================================================

    if forward_ratio >= backward_ratio:

        best_direction = "forward"

        best_states = (
            forward_states
        )

        best_ratio = (
            forward_ratio
        )

    else:

        best_direction = "backward"

        best_states = (
            backward_states
        )

        best_ratio = (
            backward_ratio
        )

    # =====================================================
    # MATCHED EDGES
    # =====================================================

    best_edges = states_to_edges(
        best_states
    )

    # =====================================================
    # SAMPLE FEATURE POINTS
    # =====================================================

    feature_points = (
        sample_points_on_edges(
            best_edges,
            roads,
            os.path.basename(
                gpx_path
            ),
            period,
            random_state=42
        )
    )

    return {

        "trace":
            os.path.basename(
                gpx_path
            ),

        "df":
            df,

        "forward_states":
            forward_states,

        "backward_states":
            backward_states,

        "forward_ratio":
            forward_ratio,

        "backward_ratio":
            backward_ratio,

        "best_direction":
            best_direction,

        "best_states":
            best_states,

        "best_edges":
            best_edges,

        "best_ratio":
            best_ratio,

        "period":
            period,

        "feature_points":
            feature_points
    }


# =========================================================
# RUN ALL TRACES
# =========================================================

results = []

feature_points_all = []


files = sorted([

    f

    for f in os.listdir(
        GPX_FOLDER
    )

    if f.endswith(".gpx")

])


for file in files:

    path = os.path.join(
        GPX_FOLDER,
        file
    )

    result = process_trace(
        path
    )

    if result is None:

        continue

    print(
        f"{file} | "
        f"Period={result['period']} | "
        f"Forward={result['forward_ratio']:.3f} | "
        f"Backward={result['backward_ratio']:.3f} | "
        f"Winner={result['best_direction']} | "
        f"Edges={len(result['best_edges'])} | "
        f"Feature points={len(result['feature_points'])}"
    )

    results.append(
        result
    )

    if len(
        result["feature_points"]
    ) > 0:

        feature_points_all.append(
            result["feature_points"]
        )


# =========================================================
# COMBINE FEATURE POINTS
# =========================================================

if len(feature_points_all) > 0:

    feature_points = gpd.GeoDataFrame(

        pd.concat(
            feature_points_all,
            ignore_index=True
        ),

        geometry="geometry",

        crs=roads.crs
    )

else:

    feature_points = gpd.GeoDataFrame(

        columns=[
            "trace_id",
            "period",
            "edge_id",
            "sample_idx",
            "fraction",
            "geometry"
        ],

        geometry="geometry",

        crs=roads.crs
    )


print(
    "\nTotal feature points:",
    len(feature_points)
)


# =========================================================
# SAVE FEATURE POINTS
# =========================================================

FEATURE_POINTS_FILE = (
    "trajectory_feature_points.gpkg"
)

feature_points.to_file(
    FEATURE_POINTS_FILE,
    layer="feature_points",
    driver="GPKG"
)

print(
    f"Feature points saved to: "
    f"{FEATURE_POINTS_FILE}"
)


# =========================================================
# SUMMARY
# =========================================================

summary = pd.DataFrame([

    {

        "trace":
            r["trace"],

        "gps_points":
            len(r["df"]),

        "forward_states":
            len(r["forward_states"]),

        "backward_states":
            len(r["backward_states"]),

        "forward_ratio":
            r["forward_ratio"],

        "backward_ratio":
            r["backward_ratio"],

        "winner":
            r["best_direction"],

        "best_ratio":
            r["best_ratio"],

        "period":
            r["period"],

        "matched_edges":
            len(r["best_edges"]),

        "feature_points":
            len(r["feature_points"])

    }

    for r in results

])


summary.to_csv(
    "matching_summary.csv",
    index=False
)


print(
    "\nMatching summary:"
)

print(
    summary.head()
)


print(
    "\nMean coverage:"
)

print(
    summary[
        [
            "forward_ratio",
            "backward_ratio",
            "best_ratio"
        ]
    ].mean()
)


# =========================================================
# UNIQUE MATCHED EDGES
# =========================================================

all_edges = []

for r in results:

    all_edges.extend(
        r["best_edges"]
    )


unique_edges = set(
    all_edges
)


print(
    f"\nUnique traversed edges: "
    f"{len(unique_edges):,}"
)


# =========================================================
# ROADS USED
# =========================================================

roads_used = roads[
    roads["edge_id"].isin(
        unique_edges
    )
].copy()


print(
    f"Road segments retained: "
    f"{len(roads_used):,}"
)


roads_used.to_file(
    "roads_used.gpkg",
    layer="roads_used",
    driver="GPKG"
)


# =========================================================
# UNIQUE EDGES CSV
# =========================================================

pd.DataFrame({

    "edge_id":
        list(unique_edges)

}).to_csv(
    "unique_edges.csv",
    index=False
)


# =========================================================
# FINAL OUTPUT SUMMARY
# =========================================================

print("\n" + "=" * 60)
print("OUTPUT FILES")
print("=" * 60)

print(
    "1. trajectory_feature_points.gpkg"
)
print(
    "   -> sampled points used for feature computation"
)

print(
    "2. paris_buildings.gpkg"
)
print(
    "   -> Paris building geometries"
)

print(
    "3. paris_streetlights.gpkg"
)
print(
    "   -> Paris streetlight points"
)

print(
    "4. roads_used.gpkg"
)
print(
    "   -> road edges traversed by matched trajectories"
)

print(
    "5. unique_edges.csv"
)
print(
    "   -> unique matched edge IDs"
)

print(
    "6. matching_summary.csv"
)
print(
    "   -> map-matching statistics per trajectory"
)

print("=" * 60)