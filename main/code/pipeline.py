import os
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox

from astral import LocationInfo
from astral.sun import sun

from leuvenmapmatching.map.inmem import InMemMap
from leuvenmapmatching.matcher.distance import DistanceMatcher


# =========================================================
# CONFIGURATION
# =========================================================

CONFIG = {

    # -----------------------------------------------------
    # CITY
    # -----------------------------------------------------

    "city_name": "London",
    "country": "United Kingdom",
    "timezone": "Europe/London",

    # Approximate city coordinates
    # Used only for solar calculations.
    "latitude": 51.5074,
    "longitude": -0.1278,


    # -----------------------------------------------------
    # INPUT DATA
    # -----------------------------------------------------

    # Folder containing GPX walking traces
    "gpx_folder": "londres_traces_walking",

    # Walking network
    "graph_file": "london_walk.graphml",


    # -----------------------------------------------------
    # BUILDINGS
    # -----------------------------------------------------

    # Can be:
    #   - GeoPackage
    #   - Shapefile
    #   - other geopandas-readable format
    "buildings_file": "london_buildings.gpkg",

    # Layer name if using GeoPackage
    "buildings_layer": "buildings",

    # Building height attribute
    "building_height_column": "height",


    # -----------------------------------------------------
    # STREETLIGHTS
    # -----------------------------------------------------

    # Option 1: already converted GeoPackage
    "streetlights_file": "london_streetlights.gpkg",

    # Layer name if using GeoPackage
    "streetlights_layer": "streetlights",

    # Optional CSV source.
    # Used only if streetlights_file does not exist.
    "streetlights_csv": "streetlights.csv",

    # CSV separator
    "streetlights_csv_separator": ";",

    # CSV coordinate columns
    "streetlights_lon_column": "longitude",
    "streetlights_lat_column": "latitude",

    # CRS of CSV coordinates
    # Use EPSG:4326 for normal longitude/latitude CSVs.
    "streetlights_csv_crs": "EPSG:4326",


    # -----------------------------------------------------
    # OUTPUT
    # -----------------------------------------------------

    "output_dir": "outputs",


    # -----------------------------------------------------
    # MAP MATCHING


    "max_dist": 30,
    "max_dist_init": 30,

    "obs_noise": 10,
    "obs_noise_ne": 30,

    "dist_noise": 15,

    "non_emitting_length_factor": 0.5,

    "max_lattice_width": 10,


    # -----------------------------------------------------
    # SAMPLING
   

    "random_state": 42,


    # -----------------------------------------------------
    # TRAJECTORY FILTERING


    "minimum_gpx_points": 5,
}


# =========================================================
# CREATE OUTPUT DIRECTORY
# =========================================================

OUTPUT_DIR = CONFIG["output_dir"]

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# =========================================================
# HELPER: OUTPUT PATH
# =========================================================

def output_path(filename):

    return os.path.join(
        OUTPUT_DIR,
        filename
    )


# =========================================================
# CITY
# =========================================================

city = LocationInfo(
    CONFIG["city_name"],                                                                                                                       
    CONFIG["country"],
    CONFIG["timezone"],
    CONFIG["latitude"],
    CONFIG["longitude"]
)


# =========================================================
# LOAD STREETLIGHTS
# =========================================================

def load_streetlights():

    streetlights_file = CONFIG["streetlights_file"]
    csv_file = CONFIG["streetlights_csv"]

    # -----------------------------------------------------
    # Already processed GeoPackage
    # -----------------------------------------------------

    if os.path.exists(streetlights_file):

        print(
            "Loading saved streetlights..."
        )

        streetlights = gpd.read_file(
            streetlights_file,
            layer=CONFIG["streetlights_layer"]
        )

        return streetlights


    # -----------------------------------------------------
    # Otherwise try CSV
    # -----------------------------------------------------

    if os.path.exists(csv_file):

        print(
            "Loading streetlights CSV..."
        )

        streetlights = pd.read_csv(
            csv_file,
            sep=CONFIG["streetlights_csv_separator"],
            encoding="utf-8"
        )

        lon_col = CONFIG["streetlights_lon_column"]
        lat_col = CONFIG["streetlights_lat_column"]

        if lon_col not in streetlights.columns:

            raise ValueError(
                f"Longitude column '{lon_col}' not found.\n"
                f"Available columns:\n"
                f"{streetlights.columns.tolist()}"
            )

        if lat_col not in streetlights.columns:

            raise ValueError(
                f"Latitude column '{lat_col}' not found.\n"
                f"Available columns:\n"
                f"{streetlights.columns.tolist()}"
            )

        streetlights = gpd.GeoDataFrame(

            streetlights,

            geometry=gpd.points_from_xy(
                streetlights[lon_col],
                streetlights[lat_col]
            ),

            crs=CONFIG["streetlights_csv_crs"]
        )

        # -------------------------------------------------
        # Save converted streetlights
        # -------------------------------------------------

        streetlights.to_file(

            streetlights_file,

            layer=CONFIG["streetlights_layer"],

            driver="GPKG"
        )

        print(
            f"Streetlights saved to "
            f"{streetlights_file}"
        )

        return streetlights


    # -----------------------------------------------------
    # NO STREETLIGHT DATA
    # -----------------------------------------------------

    print(
        "\nWARNING: No streetlight data found."
    )

    print(
        f"  Checked: {streetlights_file}"
    )

    print(
        f"  Checked: {csv_file}"
    )

    print(
        "Continuing without streetlight data."
    )

    # Empty GeoDataFrame
    return gpd.GeoDataFrame(
        geometry=[],
        crs=None
    )


streetlights = load_streetlights()


print(
    f"Streetlights: "
    f"{len(streetlights):,}"
)


# =========================================================
# LOAD WALKING GRAPH
# =========================================================

print(
    "\nLoading walking graph..."
)

G = ox.load_graphml(
    CONFIG["graph_file"]
)


print(
    f"Nodes: {len(G.nodes):,}"
)

print(
    f"Edges: {len(G.edges):,}"
)


# =========================================================
# DETERMINE GRAPH CRS


graph_crs = G.graph.get(
    "crs",
    "EPSG:4326"
)

print(
    f"Graph CRS: {graph_crs}"
)


# =========================================================
# ROAD EDGES


print(
    "\nPreparing road edges..."
)

roads = ox.graph_to_gdfs(
    G,
    nodes=False
)


# ---------------------------------------------------------
# Make sure roads have projected CRS

if roads.crs is None:

    roads = roads.set_crs(
        "EPSG:4326"
    )


# Convert graph edges to GeoDataFrame
roads = ox.graph_to_gdfs(
    G,
    nodes=False,
    edges=True
)

# London metric CRS: British National Grid
metric_crs = "EPSG:27700"

# Reproject roads from EPSG:4326 to EPSG:27700
roads = roads.to_crs(metric_crs)

# Reset index to get u, v, key as columns
roads = roads.reset_index()

# Create unique edge identifier
roads["edge_id"] = list(
    zip(
        roads["u"],
        roads["v"],
        roads["key"]
    )
)

print(f"Road CRS: {roads.crs}")
print(f"Road edges: {len(roads):,}")


print(
    f"Road CRS: {metric_crs}"
)


# =========================================================
# LOAD BUILDINGS
# =========================================================

def load_buildings():

    buildings_file = CONFIG["buildings_file"]
    buildings_layer = CONFIG["buildings_layer"]

    print("Loading buildings...")

    buildings = gpd.read_file(
        buildings_file,
        layer=buildings_layer
    )

    print(f"Buildings: {len(buildings):,}")
    print(f"Building columns: {list(buildings.columns)}")

    # -----------------------------------------------------
    # Normalize building height column
    # -----------------------------------------------------

    configured_height = CONFIG["building_height_column"]

    if configured_height in buildings.columns:
        height_col = configured_height

    elif "height_m" in buildings.columns:
        print(
            f"Using 'height_m' as building height column "
            f"(configured column was '{configured_height}')."
        )
        height_col = "height_m"

    elif "height" in buildings.columns:
        print("Using 'height' as building height column.")
        height_col = "height"

    else:
        raise ValueError(
            "No building height column found.\n"
            f"Available columns: {list(buildings.columns)}"
        )

    # Rename internally so the rest of the pipeline
    # always works with the same column name.
    if height_col != "height":
        buildings = buildings.rename(
            columns={height_col: "height"}
        )

    print(f"Building height column: 'height'")

    # -----------------------------------------------------
    # Reproject to metric CRS
    # -----------------------------------------------------

    buildings = buildings.to_crs(metric_crs)

    return buildings



#buildings = load_buildings()


# =========================================================
# HMM MAP


print(
    "\nBuilding HMM map..."
)

map_con = InMemMap(

    CONFIG["city_name"],

    use_latlon=True,

    use_rtree=False,

    index_edges=True
)


# ---------------------------------------------------------
# Add nodes
# ---------------------------------------------------------

for node, data in G.nodes(
    data=True
):

    map_con.add_node(

        node,

        (
            data["y"],
            data["x"]
        )

    )


# ---------------------------------------------------------
# Add edges


for u, v in G.edges():

    map_con.add_edge(
        u,
        v
    )


print(
    "HMM map ready."
)


# =========================================================
# MATCHER
# =========================================================

matcher = DistanceMatcher(

    map_con,

    max_dist=CONFIG[
        "max_dist"
    ],

    max_dist_init=CONFIG[
        "max_dist_init"
    ],

    obs_noise=CONFIG[
        "obs_noise"
    ],

    obs_noise_ne=CONFIG[
        "obs_noise_ne"
    ],

    dist_noise=CONFIG[
        "dist_noise"
    ],

    non_emitting_length_factor=CONFIG[
        "non_emitting_length_factor"
    ],

    max_lattice_width=CONFIG[
        "max_lattice_width"
    ]
)


# =========================================================
# GPX XML NAMESPACE
# =========================================================

NS = {

    "gpx":
    "http://www.topografix.com/GPX/1/0"

}


# =========================================================
# LOAD GPX
# =========================================================

def load_gpx(path):

    tree = ET.parse(
        path
    )

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


    return pd.DataFrame(
        pts
    )


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
# STATES -> EDGES
# =========================================================

def states_to_edges(
    states
):

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


        # -------------------------------------------------
        # If multiple parallel edges exist,
        # choose shortest one.
        # -------------------------------------------------

        key, data = min(

            edge_data.items(),

            key=lambda x:
                x[1].get(
                    "length",
                    np.inf
                )

        )


        edges.append(
            (
                u,
                v,
                key
            )
        )


    return edges


# =========================================================
# TRAJECTORY PERIOD
# =========================================================

def trajectory_period(
    df
):

    times = pd.to_datetime(

        df["datetime"],

        errors="coerce"

    ).dropna()


    if len(times) == 0:

        return "unknown"


    timestamp = times.iloc[0]


    # -----------------------------------------------------
    # GPX timestamps are normally UTC
    # -----------------------------------------------------

    if timestamp.tzinfo is None:

        timestamp = timestamp.tz_localize(
            "UTC"
        )


    timestamp = timestamp.tz_convert(
        CONFIG["timezone"]
    )


    # -----------------------------------------------------
    # Nautical twilight
    # depression = 12 degrees
    # -----------------------------------------------------

    twilight = sun(

        city.observer,

        date=timestamp.date(),

        tzinfo=CONFIG[
            "timezone"
        ],

        dawn_dusk_depression=12
    )


    if (

        timestamp < twilight["dawn"]

        or

        timestamp > twilight["dusk"]

    ):

        return "night"


    return "day"


# =========================================================
# SAMPLE POINTS ON EDGES
# =========================================================

def sample_points_on_edges(

    edge_sequence,

    roads,

    trace_id,

    period,

    random_state=42

):

    """
    For every occurrence of a matched edge,
    generate one random point on that edge.

    Therefore:

        number of sampled points
        =
        number of matched edge occurrences
    """


    rng = np.random.default_rng(
        random_state
    )


    # -----------------------------------------------------
    # Count edge occurrences
    # -----------------------------------------------------

    edge_counts = {}


    for edge_id in edge_sequence:

        edge_counts[edge_id] = (

            edge_counts.get(
                edge_id,
                0
            ) + 1

        )


    # -----------------------------------------------------
    # Create dictionary:
    #
    # (u,v,key) -> geometry
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

            roads_lookup[
                "edge_id"
            ],

            roads_lookup[
                "geometry"
            ]

        )

    )


    sampled = []


    # -----------------------------------------------------
    # Generate points
    # -----------------------------------------------------

    for edge_id, n in edge_counts.items():

        geometry = roads_lookup.get(
            edge_id
        )


        if geometry is None:
            continue


        if geometry.is_empty:
            continue


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
    # Empty result
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


    # -----------------------------------------------------
    # GeoDataFrame
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # Ignore very short traces
    # -----------------------------------------------------

    if len(df) < CONFIG[
        "minimum_gpx_points"
    ]:

        return None


    trace_id = os.path.basename(
        gpx_path
    )


    # =====================================================
    # DAY / NIGHT
    # =====================================================

    period = trajectory_period(
        df
    )


    # =====================================================
    # GPS POINTS
    # =====================================================

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
            f"Forward error "
            f"({trace_id}):",
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
            f"Backward error "
            f"({trace_id}):",
            e
        )

        backward_states = []


    # =====================================================
    # COVERAGE
    # =====================================================

    gps_count = len(df)


    forward_ratio = (

        len(forward_states)
        /
        gps_count

        if gps_count > 0

        else 0

    )


    backward_ratio = (

        len(backward_states)
        /
        gps_count

        if gps_count > 0

        else 0

    )


    # =====================================================
    # SELECT BEST DIRECTION
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

            trace_id,

            period,

            random_state=CONFIG[
                "random_state"
            ]

        )

    )


    # =====================================================
    # RESULT
    # =====================================================

    return {

        "trace":
            trace_id,

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

print(
    "\n" + "=" * 60
)

print(
    "PROCESSING GPX TRACES"
)

print(
    "=" * 60
)


results = []

feature_points_all = []


gpx_folder = CONFIG[
    "gpx_folder"
]


if not os.path.exists(
    gpx_folder
):

    raise FileNotFoundError(
        f"GPX folder not found:\n"
        f"{gpx_folder}"
    )


files = sorted([

    f

    for f in os.listdir(
        gpx_folder
    )

    if f.lower().endswith(
        ".gpx"
    )

])


print(
    f"GPX files found: "
    f"{len(files):,}"
)


for idx, file in enumerate(
    files,
    start=1
):

    path = os.path.join(
        gpx_folder,
        file
    )


    result = process_trace(
        path
    )


    if result is None:

        continue


    print(

        f"[{idx}/{len(files)}] "

        f"{file} | "

        f"Period="
        f"{result['period']} | "

        f"Forward="
        f"{result['forward_ratio']:.3f} | "

        f"Backward="
        f"{result['backward_ratio']:.3f} | "

        f"Winner="
        f"{result['best_direction']} | "

        f"Edges="
        f"{len(result['best_edges'])} | "

        f"Feature points="
        f"{len(result['feature_points'])}"

    )


    results.append(
        result
    )


    if len(
        result["feature_points"]
    ) > 0:

        feature_points_all.append(

            result[
                "feature_points"
            ]

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

FEATURE_POINTS_FILE = output_path(
    "trajectory_feature_points.gpkg"
)


feature_points.to_file(

    FEATURE_POINTS_FILE,

    layer="feature_points",

    driver="GPKG"

)


print(
    f"Feature points saved to:\n"
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


# =========================================================
# SAVE SUMMARY
# =========================================================

summary_file = output_path(
    "matching_summary.csv"
)


summary.to_csv(

    summary_file,

    index=False

)


print(
    "\nMatching summary:"
)

print(
    summary.head()
)


# =========================================================
# COVERAGE STATISTICS
# =========================================================

if len(summary) > 0:

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

    roads[
        "edge_id"
    ].isin(
        unique_edges
    )

].copy()


print(

    f"Road segments retained: "
    f"{len(roads_used):,}"

)


roads_used.to_file(

    output_path(
        "roads_used.gpkg"
    ),

    layer="roads_used",

    driver="GPKG"

)


# =========================================================
# UNIQUE EDGES CSV
# =========================================================

unique_edges_df = pd.DataFrame({

    "edge_id":
        list(unique_edges)

})


unique_edges_df.to_csv(

    output_path(
        "unique_edges.csv"
    ),

    index=False

)




# =========================================================
# SAVE PROCESSED STREETLIGHTS
# =========================================================

streetlights_output = output_path(

    f"{CONFIG['city_name'].lower()}_streetlights.gpkg"

)


if not os.path.exists(
    streetlights_output
):

    streetlights.to_file(

        streetlights_output,

        layer="streetlights",

        driver="GPKG"

    )


# =========================================================
# FINAL OUTPUT
# =========================================================

print(
    "\n" + "=" * 60
)

print(
    "OUTPUT FILES"
)

print(
    "=" * 60
)


print(
    "1. trajectory_feature_points.gpkg"
)

print(
    "   -> sampled points on matched trajectories"
)


print(
    "2. "
    f"{CONFIG['city_name'].lower()}_buildings.gpkg"
)

print(
    "   -> building geometries + height"
)


print(
    "3. "
    f"{CONFIG['city_name'].lower()}_streetlights.gpkg"
)

print(
    "   -> streetlight points"
)


print(
    "4. roads_used.gpkg"
)

print(
    "   -> road edges traversed by trajectories"
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


print(
    "=" * 60
)

print(
    "\nProcessing complete."
)