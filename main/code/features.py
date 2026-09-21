import os

import geopandas as gpd
import pandas as pd
import numpy as np

from geopandas import sjoin

from t4gpd.commons.encoding.EncodingIndices import EncodingIndices
from t4gpd.commons.encoding.IsovistBuilder import IsovistBuilder
from t4gpd.commons.encoding.SensorBasedEncodingLib import (
    SensorBasedEncodingLib
)


# =========================================================
# CONFIGURATION
# =========================================================
#
# Change ONLY this section when switching cities.
#
# =========================================================

CONFIG = {

    # -----------------------------------------------------
    # CITY
    # -----------------------------------------------------

    "city_name": "London",

    # London:
    # EPSG:27700 = British National Grid
    #
    # Paris:
    # EPSG:2154 = Lambert-93

    "metric_crs": 27700,


    # -----------------------------------------------------
    # TRAJECTORY FEATURE POINTS
    # -----------------------------------------------------

    "feature_points_file":
        "C:/Users/oussama.nair/Downloads/london_outputs/trajectory_feature_points.gpkg",

    "feature_points_layer":
        "feature_points",


    # -----------------------------------------------------
    # BUILDINGS
    # -----------------------------------------------------

    "buildings_file":
        "london_buildings.gpkg",

    "buildings_layer":
        "buildings",

    # London GBA:
    #     height_m
    #
    # Paris:
    #     hauteur
    #
    # The script also automatically checks
    # "height" if necessary.

    "building_height_column":
        "height_m",


    # -----------------------------------------------------
    # STREETLIGHTS
    # -----------------------------------------------------
    #
    # London:
    #
    #     None
    #
    # Paris:
    #
    #     "paris_streetlights.gpkg"
    #
    # -----------------------------------------------------

    "streetlights_file":
        None,

    "streetlights_layer":
        "streetlights",


    # -----------------------------------------------------
    # OUTPUT DIRECTORY
    # -----------------------------------------------------

    "output_dir":
        "outputs",


    # -----------------------------------------------------
    # MORPHOLOGICAL PARAMETERS
    # -----------------------------------------------------

    "h0":
        1.6,

    "rayLength":
        100,

    "nRays":
        64,
}


# =========================================================
# DERIVED OUTPUT PATHS
# =========================================================

CITY = CONFIG["city_name"].lower()

OUTPUT_DIR = CONFIG["output_dir"]


os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    f"{CITY}_morphological_features.gpkg"
)


CSV_FILE = os.path.join(
    OUTPUT_DIR,
    f"{CITY}_morphological_features.csv"
)


ISOVIST_FILE = os.path.join(
    OUTPUT_DIR,
    f"{CITY}_isovists.gpkg"
)


# =========================================================
# HELPER
# =========================================================

def check_file(
    filepath,
    description
):

    if not os.path.exists(filepath):

        raise FileNotFoundError(
            f"\n{description} not found:\n"
            f"{filepath}\n"
        )


# =========================================================
# START
# =========================================================

print()
print("=" * 70)
print("MORPHOLOGICAL FEATURE EXTRACTION")
print("=" * 70)

print()
print("City:", CONFIG["city_name"])
print("Metric CRS:", CONFIG["metric_crs"])

print()


# =========================================================
# LOAD TRAJECTORY FEATURE POINTS
# =========================================================

print("=" * 70)
print("LOADING TRAJECTORY FEATURE POINTS")
print("=" * 70)

print()


FEATURE_POINTS_FILE = (
    CONFIG["feature_points_file"]
)

FEATURE_POINTS_LAYER = (
    CONFIG["feature_points_layer"]
)


check_file(
    FEATURE_POINTS_FILE,
    "Trajectory feature points file"
)


print(
    "Loading trajectory feature points..."
)


sensors = gpd.read_file(

    FEATURE_POINTS_FILE,

    layer=FEATURE_POINTS_LAYER
)


print(
    f"Sensors: {len(sensors):,}"
)


print(
    "CRS:",
    sensors.crs
)


if sensors.crs is None:

    raise ValueError(
        "Trajectory feature points have no CRS."
    )


# =========================================================
# LOAD BUILDINGS
# =========================================================

print()
print("=" * 70)
print("LOADING BUILDINGS")
print("=" * 70)

print()


BUILDINGS_FILE = (
    CONFIG["buildings_file"]
)

BUILDINGS_LAYER = (
    CONFIG["buildings_layer"]
)


check_file(
    BUILDINGS_FILE,
    "Buildings file"
)


print(
    "Loading buildings..."
)


buildings = gpd.read_file(

    BUILDINGS_FILE,

    layer=BUILDINGS_LAYER
)


print(
    f"Buildings: {len(buildings):,}"
)


print(
    "CRS:",
    buildings.crs
)


if buildings.crs is None:

    raise ValueError(
        "Buildings have no CRS."
    )


print()
print(
    "Building columns:"
)

print(
    buildings.columns.tolist()
)


# =========================================================
# BUILDING HEIGHT
# =========================================================

print()
print("=" * 70)
print("CHECKING BUILDING HEIGHTS")
print("=" * 70)

print()


configured_height = (
    CONFIG["building_height_column"]
)


# Possible column names.

height_candidates = [

    configured_height,

    "height_m",

    "hauteur",

    "height",

]


height_column = None


for column in height_candidates:

    if column in buildings.columns:

        height_column = column

        break


if height_column is None:

    raise ValueError(

        "\nBuilding height column not found.\n\n"

        f"Configured column: "
        f"{configured_height}\n\n"

        "Available columns:\n"

        f"{buildings.columns.tolist()}"
    )


print(
    "Using building height column:",
    height_column
)


# ---------------------------------------------------------
# Normalize to "hauteur"
# ---------------------------------------------------------

if height_column != "hauteur":

    buildings = buildings.rename(

        columns={
            height_column:
                "hauteur"
        }
    )


# ---------------------------------------------------------
# Convert to numeric
# ---------------------------------------------------------

buildings["hauteur"] = pd.to_numeric(

    buildings["hauteur"],

    errors="coerce"
)


print()
print(
    "Building height statistics:"
)

print(
    buildings["hauteur"].describe()
)


# ---------------------------------------------------------
# Keep only positive heights
# ---------------------------------------------------------

buildings = buildings[
    buildings["hauteur"] > 0
].copy()


print()
print(
    f"Buildings with positive height: "
    f"{len(buildings):,}"
)


# =========================================================
# LOAD STREETLIGHTS
# =========================================================

print()
print("=" * 70)
print("LOADING STREETLIGHTS")
print("=" * 70)

print()


STREETLIGHTS_FILE = (
    CONFIG["streetlights_file"]
)


if STREETLIGHTS_FILE is None:

    # -----------------------------------------------------
    # No lighting dataset configured
    # -----------------------------------------------------

    print(
        "No streetlight dataset configured."
    )

    print(
        "Streetlight analysis will be skipped."
    )

    streetlights = None

    LIGHTING_AVAILABLE = False


else:

    # -----------------------------------------------------
    # Lighting dataset configured
    # -----------------------------------------------------

    if not os.path.exists(
        STREETLIGHTS_FILE
    ):

        print(
            "WARNING:"
        )

        print(
            f"Streetlight file not found: "
            f"{STREETLIGHTS_FILE}"
        )

        print(
            "Streetlight analysis will be skipped."
        )

        streetlights = None

        LIGHTING_AVAILABLE = False

    else:

        print(
            "Loading streetlights..."
        )


        streetlights = gpd.read_file(

            STREETLIGHTS_FILE,

            layer=CONFIG[
                "streetlights_layer"
            ]
        )


        print(
            f"Streetlights: "
            f"{len(streetlights):,}"
        )


        print(
            "CRS:",
            streetlights.crs
        )


        if streetlights.crs is None:

            raise ValueError(
                "Streetlights have no CRS."
            )


        LIGHTING_AVAILABLE = True


# =========================================================
# CRS
# =========================================================

print()
print("=" * 70)
print("REPROJECTING DATA")
print("=" * 70)

print()


METRIC_CRS = CONFIG["metric_crs"]


print(
    "Target CRS:",
    METRIC_CRS
)


# ---------------------------------------------------------
# Sensors
# ---------------------------------------------------------

sensors = sensors.to_crs(
    METRIC_CRS
)


# ---------------------------------------------------------
# Buildings
# ---------------------------------------------------------

buildings = buildings.to_crs(
    METRIC_CRS
)


# ---------------------------------------------------------
# Streetlights
# ---------------------------------------------------------

if LIGHTING_AVAILABLE:

    streetlights = streetlights.to_crs(
        METRIC_CRS
    )


print(
    "Reprojection complete."
)


# =========================================================
# PARAMETERS
# =========================================================

print()
print("=" * 70)
print("MORPHOLOGICAL PARAMETERS")
print("=" * 70)

print()


h0 = CONFIG["h0"]

rayLength = CONFIG["rayLength"]

nRays = CONFIG["nRays"]


print(
    "h0       =",
    h0
)

print(
    "rayLength =",
    rayLength
)

print(
    "nRays     =",
    nRays
)


# =========================================================
# MORPHOLOGICAL ENCODING
# =========================================================

print()
print("=" * 70)
print("COMPUTING MORPHOLOGICAL INDICATORS")
print("=" * 70)

print()


print(
    "Running SensorBasedEncodingLib.encode2D25D..."
)


osensors = SensorBasedEncodingLib.encode2D25D(

    sensors,

    buildings,

    "hauteur",

    h0,

    rayLength,

    nRays
)


print()
print(
    "Morphological encoding complete."
)


print(
    f"Output sensors: {len(osensors):,}"
)


# =========================================================
# INSPECT GENERATED COLUMNS
# =========================================================

print()
print("=" * 70)
print("GENERATED COLUMNS")
print("=" * 70)

print()


print(
    osensors.columns.tolist()
)


# =========================================================
# INSPECT RAW RAY VALUES
# =========================================================

print()
print("=" * 70)
print("INSPECTING RAY LENGTHS")
print("=" * 70)

print()


for col in [

    "raylen2D",

    "raylen25D",

    "angles"

]:

    if col not in osensors.columns:

        print(
            f"{col}: NOT FOUND"
        )

        continue


    print()
    print(
        f"--- {col} ---"
    )


    for idx, values in (

        osensors[col]
        .head(3)
        .items()

    ):

        try:

            arr = np.asarray(

                values,

                dtype=float
            )


            print(
                f"index={idx}"
            )


            print(
                "  min:",
                np.nanmin(arr)
            )


            print(
                "  max:",
                np.nanmax(arr)
            )


            print(
                "  finite:",
                np.sum(
                    np.isfinite(arr)
                ),
                "/",
                len(arr)
            )


            print(
                "  infinite:",
                np.sum(
                    np.isinf(arr)
                )
            )


        except Exception as e:

            print(
                "  Could not inspect:",
                e
            )


# =========================================================
# CLEAN INFINITE RAY LENGTHS
# =========================================================

print()
print("=" * 70)
print("CLEANING RAY LENGTHS")
print("=" * 70)

print()


def clean_ray_values(values):

    arr = np.asarray(

        values,

        dtype=float
    )


    # t4gpd uses infinity when a ray
    # does not encounter a building
    # within rayLength.
    #
    # We interpret this as maximum
    # visibility distance.

    arr = np.where(

        np.isfinite(arr),

        arr,

        rayLength
    )


    return arr


for col in [

    "raylen2D",

    "raylen25D"

]:

    if col not in osensors.columns:

        continue


    osensors[col] = (

        osensors[col]

        .apply(
            clean_ray_values
        )
    )


print(
    "Infinite ray lengths replaced by",
    rayLength,
    "m."
)


# =========================================================
# RAY-LENGTH INDICES
# =========================================================

print()
print("=" * 70)
print("COMPUTING RAY-LENGTH INDICES")
print("=" * 70)

print()


if "raylen2D" in osensors.columns:

    osensors = EncodingIndices.raylen_indices(

        osensors,

        raylen="raylen2D"
    )


    print(
        "raylen2D indices computed."
    )


if "raylen25D" in osensors.columns:

    osensors = EncodingIndices.raylen_indices(

        osensors,

        raylen="raylen25D"
    )


    print(
        "raylen25D indices computed."
    )


# =========================================================
# SKY VIEW FACTOR
# =========================================================

print()
print("=" * 70)
print("COMPUTING SKY VIEW FACTOR")
print("=" * 70)

print()


if "angles" in osensors.columns:

    osensors = EncodingIndices.svf_indices(

        osensors,

        angles="angles"
    )


    print(
        "SVF computation complete."
    )


else:

    print(
        "WARNING: 'angles' column not found."
    )


# =========================================================
# SVF CHECK
# =========================================================

print()
print(
    "Checking SVF..."
)


if "svf_geom" in osensors.columns:

    print()

    print(
        osensors[
            "svf_geom"
        ].describe()
    )


else:

    print(
        "WARNING: svf_geom not found."
    )


# =========================================================
# BUILD ISOVISTS
# =========================================================

print()
print("=" * 70)
print("BUILDING ISOVISTS")
print("=" * 70)

print()


isovists = IsovistBuilder.build(

    osensors,

    "raylen2D",

    copy=True
)


print(
    f"Isovists: {len(isovists):,}"
)


# =========================================================
# ISOVIST AREA / PERIMETER
# =========================================================

print()
print("=" * 70)
print("COMPUTING ISOVIST GEOMETRY")
print("=" * 70)

print()


osensors["isovist_area"] = (

    isovists.geometry.area
)


osensors["isovist_perimeter"] = (

    isovists.geometry.length
)


print(
    "Isovist geometry computed."
)


# =========================================================
# STREETLIGHT COUNT
# =========================================================

print()
print("=" * 70)
print("STREETLIGHT ANALYSIS")
print("=" * 70)

print()


if not LIGHTING_AVAILABLE:

    print(
        "No streetlight data available."
    )

    print(
        "Skipping spatial join."
    )

    print(
        "No streetlight_count column "
        "will be created."
    )


else:

    print(
        "Counting streetlights "
        "inside isovists..."
    )


    # -----------------------------------------------------
    # Reset indices to ensure index_right corresponds
    # directly to the isovist row.
    # -----------------------------------------------------

    isovists = isovists.reset_index(
        drop=True
    )


    osensors = osensors.reset_index(
        drop=True
    )


    # -----------------------------------------------------
    # Spatial join
    # -----------------------------------------------------

    streetlight_join = sjoin(

        streetlights,

        isovists,

        how="inner",

        predicate="within"
    )


    print(
        f"Streetlight-isovist matches: "
        f"{len(streetlight_join):,}"
    )


    # -----------------------------------------------------
    # Count lights per isovist
    # -----------------------------------------------------

    streetlight_counts = (

        streetlight_join

        .groupby(
            "index_right"
        )

        .size()
    )


    # -----------------------------------------------------
    # Initialize all isovists with zero.
    #
    # This is appropriate HERE because the lighting
    # dataset actually exists.
    #
    # If an isovist has no matched streetlight,
    # it genuinely has zero according to the dataset.
    # -----------------------------------------------------

    osensors[
        "streetlight_count"
    ] = 0


    # -----------------------------------------------------
    # Assign counts
    # -----------------------------------------------------

    for idx, count in (

        streetlight_counts.items()

    ):

        if idx in osensors.index:

            osensors.loc[

                idx,

                "streetlight_count"

            ] = int(count)


    print(
        "Streetlight counting complete."
    )


# =========================================================
# FEATURE STATISTICS
# =========================================================

print()
print("=" * 70)
print("FEATURE STATISTICS")
print("=" * 70)

print()


feature_columns = [

    "svf_geom",

    "raylen2D",

    "raylen25D",

    "isovist_area",

    "isovist_perimeter",

]


# Add lighting only when available.

if LIGHTING_AVAILABLE:

    feature_columns.append(
        "streetlight_count"
    )


for column in feature_columns:

    if column not in osensors.columns:

        print()
        print(
            f"{column}: NOT AVAILABLE"
        )

        continue


    print()
    print(
        f"--- {column} ---"
    )


    try:

        print(
            osensors[
                column
            ].describe()
        )


    except Exception as e:

        print(
            "Could not calculate statistics:",
            e
        )


# =========================================================
# SAVE ISOVISTS
# =========================================================

print()
print("=" * 70)
print("SAVING ISOVISTS")
print("=" * 70)

print()


isovists.to_file(

    ISOVIST_FILE,

    layer="isovists",

    driver="GPKG"
)


print(
    f"Saved: {ISOVIST_FILE}"
)


# =========================================================
# SAVE MORPHOLOGICAL FEATURES
# =========================================================

print()
print("=" * 70)
print("SAVING MORPHOLOGICAL FEATURES")
print("=" * 70)

print()


osensors.to_file(

    OUTPUT_FILE,

    layer="morphological_features",

    driver="GPKG"
)


print(
    f"Saved: {OUTPUT_FILE}"
)


# =========================================================
# SAVE CSV
# =========================================================

print()
print("=" * 70)
print("SAVING CSV")
print("=" * 70)

print()


df = pd.DataFrame(

    osensors.drop(
        columns="geometry"
    )
)


df.to_csv(

    CSV_FILE,

    index=False
)


print(
    f"Saved: {CSV_FILE}"
)


# =========================================================
# FINAL SUMMARY
# =========================================================

print()
print("=" * 70)
print("MORPHOLOGICAL FEATURE EXTRACTION COMPLETE")
print("=" * 70)

print()


print(
    "City:",
    CONFIG["city_name"]
)


print(
    "CRS:",
    CONFIG["metric_crs"]
)


print(
    f"Sensors: {len(osensors):,}"
)


print(
    f"Isovists: {len(isovists):,}"
)


print(
    f"Buildings: {len(buildings):,}"
)


if LIGHTING_AVAILABLE:

    print(
        f"Streetlights: "
        f"{len(streetlights):,}"
    )

    print(
        "Lighting analysis: ENABLED"
    )

else:

    print(
        "Streetlights: unavailable"
    )

    print(
        "Lighting analysis: DISABLED"
    )


print()
print(
    "Features available:"
)


for column in feature_columns:

    if column in osensors.columns:

        print(
            " -",
            column
        )


print()
print(
    "Output files:"
)


print(
    "1.",
    OUTPUT_FILE
)


print(
    "2.",
    CSV_FILE
)


print(
    "3.",
    ISOVIST_FILE
)


print()
print("=" * 70)
print("DONE")
print("=" * 70)