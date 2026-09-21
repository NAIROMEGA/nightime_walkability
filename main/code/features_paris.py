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
# FILES
# =========================================================

FEATURE_POINTS_FILE = "trajectory_feature_points.gpkg"
BUILDINGS_FILE = "paris_buildings.gpkg"
STREETLIGHTS_FILE = "paris_streetlights.gpkg"

OUTPUT_FILE = "paris_morphological_features.gpkg"
CSV_FILE = "paris_morphological_features.csv"
ISOVIST_FILE = "paris_isovists.gpkg"


# =========================================================
# LOAD TRAJECTORY FEATURE POINTS
# =========================================================

print("Loading trajectory feature points...")

sensors = gpd.read_file(
    FEATURE_POINTS_FILE,
    layer="feature_points"
)

print(
    f"Sensors: {len(sensors):,}"
)


# =========================================================
# LOAD BUILDINGS
# =========================================================

print("Loading buildings...")

buildings = gpd.read_file(
    BUILDINGS_FILE,
    layer="buildings"
)

print(
    f"Buildings: {len(buildings):,}"
)


# =========================================================
# LOAD STREETLIGHTS
# =========================================================

print("Loading streetlights...")

streetlights = gpd.read_file(
    STREETLIGHTS_FILE,
    layer="streetlights"
)

print(
    f"Streetlights: {len(streetlights):,}"
)


# =========================================================
# CRS
# =========================================================

print("\nCRS:")

print(
    "Sensors:",
    sensors.crs
)

print(
    "Buildings:",
    buildings.crs
)

print(
    "Streetlights:",
    streetlights.crs
)


# Everything in Lambert-93

sensors = sensors.to_crs(2154)

buildings = buildings.to_crs(2154)

streetlights = streetlights.to_crs(2154)


# =========================================================
# BUILDING HEIGHT
# =========================================================

print(
    "\nChecking building heights..."
)

buildings["hauteur"] = pd.to_numeric(
    buildings["hauteur"],
    errors="coerce"
)

print(
    buildings["hauteur"].describe()
)


# Keep only buildings with a positive height

buildings = buildings[
    buildings["hauteur"] > 0
].copy()


print(
    f"Buildings with positive height: "
    f"{len(buildings):,}"
)


# =========================================================
# PARAMETERS
# =========================================================

h0 = 1.6
rayLength = 100
nRays = 64


print("\nParameters:")
print("h0 =", h0)
print("rayLength =", rayLength)
print("nRays =", nRays)


# =========================================================
# MORPHOLOGICAL ENCODING
# =========================================================

print(
    "\nComputing morphological indicators..."
)

osensors = SensorBasedEncodingLib.encode2D25D(

    sensors,

    buildings,

    "hauteur",

    h0,

    rayLength,

    nRays
)


print(
    "Morphological encoding complete."
)


# =========================================================
# INSPECT GENERATED COLUMNS
# =========================================================

print(
    "\nGenerated columns:"
)

print(
    osensors.columns.tolist()
)


# =========================================================
# INSPECT RAW RAY VALUES
# =========================================================

print(
    "\nInspecting ray lengths..."
)


for col in ["raylen2D", "raylen25D", "angles"]:

    if col not in osensors.columns:

        print(
            f"{col}: NOT FOUND"
        )

        continue

    print(
        f"\n--- {col} ---"
    )

    for idx, values in osensors[col].head(3).items():

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
                np.sum(np.isfinite(arr)),
                "/",
                len(arr)
            )

            print(
                "  infinite:",
                np.sum(np.isinf(arr))
            )

        except Exception as e:

            print(
                "  Could not inspect:",
                e
            )


# =========================================================
# CLEAN INFINITE RAY LENGTHS
# =========================================================

print(
    "\nCleaning infinite ray lengths..."
)


for col in ["raylen2D", "raylen25D"]:

    if col not in osensors.columns:

        continue

    def clean_ray_values(values):

        arr = np.asarray(
            values,
            dtype=float
        )

        # Rays that do not hit a building
        # within rayLength are represented by inf.
        #
        # We interpret them as having the
        # maximum visibility distance.

        arr = np.where(
            np.isfinite(arr),
            arr,
            rayLength
        )

        return arr


    osensors[col] = (
        osensors[col]
        .apply(clean_ray_values)
    )


print(
    "Infinite ray lengths replaced by",
    rayLength,
    "m."
)


# =========================================================
# RAY-LENGTH INDICES
# =========================================================

print(
    "\nComputing ray-length indices..."
)


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
# SVF
# =========================================================

print(
    "\nComputing SVF..."
)


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
# CHECK SVF
# =========================================================

print(
    "\nChecking SVF..."
)

if "svf_geom" in osensors.columns:

    print(
        osensors["svf_geom"].describe()
    )

else:

    print(
        "WARNING: svf_geom not found."
    )


# =========================================================
# BUILD ISOVISTS
# =========================================================

print(
    "\nBuilding isovists..."
)


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

print(
    "\nComputing isovist geometry..."
)


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
# STREETLIGHTS PER ISOVIST
# =========================================================

print(
    "\nCounting streetlights inside isovists..."
)


streetlight_join = sjoin(

    streetlights,

    isovists,

    how="inner",

    predicate="within"
)


streetlight_counts = (

    streetlight_join

    .groupby(
        "index_right"
    )

    .size()

)


# Initialize all sensors with zero

osensors["streetlight_count"] = 0


# Assign counts

for idx, count in streetlight_counts.items():

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

print(
    "\n"
    + "=" * 60
)

print(
    "FEATURE STATISTICS"
)

print(
    "=" * 60
)


feature_columns = [

    "svf_geom",

    "raylen2D",

    "raylen25D",

    "isovist_area",

    "isovist_perimeter",

    "streetlight_count"

]


for column in feature_columns:

    if column in osensors.columns:

        print(
            f"\n{column}:"
        )

        try:

            print(
                osensors[column].describe()
            )

        except Exception as e:

            print(
                "Could not calculate statistics:",
                e
            )


# =========================================================
# SAVE ISOVISTS
# =========================================================

print(
    "\nSaving isovists..."
)


isovists.to_file(

    ISOVIST_FILE,

    layer="isovists",

    driver="GPKG"
)


print(
    f"Saved: {ISOVIST_FILE}"
)


# =========================================================
# SAVE GEO PACKAGE
# =========================================================

print(
    "\nSaving morphological features..."
)


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

print(
    "\nSaving CSV..."
)


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

print(
    "\n"
    + "=" * 60
)

print(
    "MORPHOLOGICAL FEATURE EXTRACTION COMPLETE"
)

print(
    "=" * 60
)

print(
    f"Sensors: {len(osensors):,}"
)

print(
    f"Isovists: {len(isovists):,}"
)

print(
    "\nFeatures available:"
)

for column in feature_columns:

    if column in osensors.columns:

        print(
            " -",
            column
        )

print(
    "\nOutput files:"
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

print(
    "=" * 60
)