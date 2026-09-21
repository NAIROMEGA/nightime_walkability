"""
GlobalBuildingAtlas -> London buildings

This script:
    1. Downloads the required London GBA tile only
    2. Downloads the official produce_lod1.py
    3. Runs the official GBA enrichment
    4. Reads the resulting LoD1 GeoJSON
    5. Converts to EPSG:27700
    6. Clips to the London study area
    7. Saves london_buildings.gpkg

IMPORTANT:
    Do NOT download the entire GBA repository.
    The London tile is:

        w005_n55_e000_n50

Approximate London bbox:
    west  = -0.55
    south = 51.28
    east  =  0.35
    north = 51.70
"""

from pathlib import Path
import shutil
import subprocess
import sys
import os

# ============================================================
# CONFIGURATION
# ============================================================
ROOT = Path(__file__).resolve().parent / "GBA_London"

# London study area in WGS84
LONDON_WEST = -0.55
LONDON_SOUTH = 51.28
LONDON_EAST = 0.35
LONDON_NORTH = 51.70

# GBA tile covering London
TILE = "w005_n55_e000_n50"

# Hugging Face repositories
LOD1_REPO = "zhu-xlab/GBA.LoD1"
ODBL_REPO = "zhu-xlab/GBA.ODbLPolygon"

# Input folders
LOD1_DIR = ROOT / "LoD1"
POLYGON_DIR = ROOT / "Polygon"
ODBL_DIR = ROOT / "ODbLPolygon"

# Output folders
LOD1_OUTPUT = ROOT / "LoD1_GeoJSON"

# Final file
FINAL_GPKG = Path("london_buildings.gpkg")

# CRS
SOURCE_CRS = "EPSG:3857"
TARGET_CRS = "EPSG:27700"


# ============================================================
# PRINT HEADER
# ============================================================

def header(text):
    print()
    print("=" * 70)
    print(text)
    print("=" * 70)


# ============================================================
# CHECK PACKAGES
# ============================================================

def check_packages():

    required = {
        "huggingface_hub": "huggingface_hub",
        "geopandas": "geopandas",
        "shapely": "shapely",
        "fiona": "fiona",
        "ijson": "ijson",
        "pandas": "pandas",
    }

    missing = []

    for import_name, package_name in required.items():

        try:
            __import__(import_name)

        except ImportError:
            missing.append(package_name)

    if missing:

        print()
        print("Missing packages:")
        for package in missing:
            print("   ", package)

        print()
        print("Install them with:")
        print()
        print(
            f"{sys.executable} -m pip install "
            + " ".join(missing)
        )

        sys.exit(1)


# ============================================================
# IMPORTS AFTER PACKAGE CHECK
# ============================================================

check_packages()

from huggingface_hub import hf_hub_download
import geopandas as gpd
import pandas as pd
from shapely.geometry import box


# ============================================================
# DISK SPACE
# ============================================================

def disk_space():
    """
    Check free disk space on the drive where the script/data directory lives.
    Windows-safe for relative paths.
    """

    # Resolve ROOT to an absolute path first
    check_path = ROOT.resolve()

    # ROOT may not exist yet, so use its parent
    if not check_path.exists():
        check_path = check_path.parent

    total, used, free = shutil.disk_usage(str(check_path))

    free_gb = free / (1024 ** 3)
    total_gb = total / (1024 ** 3)

    print()
    print(f"Disk: {check_path.drive}")
    print(f"Total disk space: {total_gb:.2f} GB")
    print(f"Free disk space : {free_gb:.2f} GB")

    if free_gb < 15:
        print()
        print("WARNING:")
        print("Less than 15 GB of free space is available.")
        print("GBA processing may require additional temporary space.")
        print()

    return free_gb


# ============================================================
# DOWNLOAD FILE
# ============================================================

def download_hf_file(repo_id, repo_type, filename, local_dir):

    print()
    print("-" * 70)
    print("Downloading")
    print("-" * 70)

    print("Repository :", repo_id)
    print("File       :", filename)
    print("Local dir  :", local_dir)

    local_dir = Path(local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)

    # IMPORTANT:
    # local_dir is the repository root.
    #
    # This preserves the original relative path.
    #
    # Example:
    #
    # filename =
    #   LoD1/europe/file.json
    #
    # becomes:
    #
    # GBA_London/LoD1/europe/file.json

    downloaded = hf_hub_download(
        repo_id=repo_id,
        repo_type=repo_type,
        filename=filename,
        local_dir=str(local_dir),
    )

    print()
    print("Downloaded:")
    print(downloaded)

    return Path(downloaded)


# ============================================================
# DOWNLOAD GBA DATA
# ============================================================

def download_gba():

    header("1/4 — DOWNLOAD GBA DATA")

    # --------------------------------------------------------
    # Create root
    # --------------------------------------------------------

    ROOT.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # 1. LoD1 JSON
    # --------------------------------------------------------

    lod1_file = (
        f"LoD1/europe/{TILE}.json"
    )

    download_hf_file(
        repo_id=LOD1_REPO,
        repo_type="dataset",
        filename=lod1_file,
        local_dir=ROOT,
    )

    # --------------------------------------------------------
    # 2. GBA Polygon
    # --------------------------------------------------------

    polygon_file = (
        f"Polygon/europe/{TILE}.geojson"
    )

    download_hf_file(
        repo_id=LOD1_REPO,
        repo_type="dataset",
        filename=polygon_file,
        local_dir=ROOT,
    )

    # --------------------------------------------------------
    # 3. ODbL Polygon
    # --------------------------------------------------------

    odbl_file = (
        f"europe/{TILE}.geojson"
    )

    download_hf_file(
        repo_id=ODBL_REPO,
        repo_type="dataset",
        filename=odbl_file,
        local_dir=ODBL_DIR,
    )

    # --------------------------------------------------------
    # 4. Official GBA processing script
    # --------------------------------------------------------

    header("Downloading official produce_lod1.py")

    download_hf_file(
        repo_id=LOD1_REPO,
        repo_type="dataset",
        filename="produce_lod1.py",
        local_dir=ROOT,
    )


# ============================================================
# VERIFY FILE STRUCTURE
# ============================================================

def verify_files():

    header("2/4 — VERIFY FILE STRUCTURE")

    expected = [

        ROOT / "LoD1" / "europe" / f"{TILE}.json",

        ROOT / "Polygon" / "europe" / f"{TILE}.geojson",

        ROOT / "ODbLPolygon" / "europe" / f"{TILE}.geojson",

        ROOT / "produce_lod1.py",
    ]

    everything_ok = True

    for path in expected:

        if path.exists():

            size_gb = path.stat().st_size / (1024 ** 3)

            print(
                f"[OK] {path}"
                f"  ({size_gb:.2f} GB)"
            )

        else:

            print(
                f"[MISSING] {path}"
            )

            everything_ok = False

    if not everything_ok:

        raise FileNotFoundError(
            "One or more required GBA files are missing."
        )

    print()
    print("Directory structure is correct.")


# ============================================================
# RUN OFFICIAL GBA SCRIPT
# ============================================================

def run_produce_lod1():
    print()
    print("=" * 70)
    print("3/4 — RUN GBA LoD1 ENRICHMENT")
    print("=" * 70)

    script = (ROOT / "produce_lod1.py").resolve()

    odbl_root = (ROOT / "ODbLPolygon").resolve()
    polygon_root = (ROOT / "Polygon").resolve()
    json_root = (ROOT / "LoD1").resolve()
    output_root = (ROOT / "LoD1_GeoJSON").resolve()
    sqlite_root = (ROOT / "sqlite_tmp").resolve()

    # Safety checks
    required = [
        ("produce_lod1.py", script),
        ("ODbLPolygon", odbl_root),
        ("Polygon", polygon_root),
        ("LoD1", json_root),
    ]

    for name, path in required:
        if not path.exists():
            raise FileNotFoundError(
                f"Required GBA component not found:\n{name}: {path}"
            )

    output_root.mkdir(parents=True, exist_ok=True)
    sqlite_root.mkdir(parents=True, exist_ok=True)

    # IMPORTANT:
    # Run from the Downloads directory, NOT from GBA_London.
    workdir = ROOT.parent.resolve()

    cmd = [
        sys.executable,
        str(script),
        "--odbl_root",
        str(odbl_root),
        "--polygon_root",
        str(polygon_root),
        "--json_root",
        str(json_root),
        "--output_root",
        str(output_root),
        "--sqlite_root",
        str(sqlite_root),
    ]

    print()
    print("Command:")
    print()

    print(" ".join(f'"{x}"' for x in cmd))

    print()
    print(f"Working directory:")
    print(workdir)

    print()
    print("This step may take a LONG time.")
    print("The ODbL London tile is approximately 8 GB.")
    print()
    print("Starting official GBA enrichment...")
    print()

    result = subprocess.run(
        cmd,
        cwd=str(workdir),
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"\nproduce_lod1.py failed with exit code {result.returncode}"
        )

    print()
    print("=" * 70)
    print("GBA LoD1 enrichment completed successfully.")
    print("=" * 70)


# ============================================================
# FIND OUTPUT FILES
# ============================================================

def find_output_files():

    header("SEARCHING FOR GENERATED LoD1 GEOJSON")

    if not LOD1_OUTPUT.exists():

        raise FileNotFoundError(
            f"Output directory does not exist: {LOD1_OUTPUT}"
        )

    files = list(
        LOD1_OUTPUT.rglob("*.geojson")
    )

    print()
    print(f"Found {len(files)} GeoJSON files.")

    for f in files:

        size_mb = f.stat().st_size / (1024 ** 2)

        print(
            f"  {f} "
            f"({size_mb:.1f} MB)"
        )

    if not files:

        raise FileNotFoundError(
            "No LoD1 GeoJSON files were generated."
        )

    return files


# ============================================================
# FIND HEIGHT COLUMN
# ============================================================

def find_height_column(columns):

    print()
    print("Available columns:")

    for c in columns:

        print("   ", c)

    # Exact names first
    preferred = [

        "height",
        "Height",
        "height_m",
        "building_height",
        "buildingHeight",
        "HEIGHT",
        "h",
        "H",
    ]

    for col in preferred:

        if col in columns:

            print()
            print(
                f"Using height column: {col}"
            )

            return col

    # Search by substring
    for col in columns:

        name = str(col).lower()

        if "height" in name:

            print()
            print(
                f"Using detected height column: {col}"
            )

            return col

    print()
    print(
        "WARNING: No height column detected."
    )

    return None


# ============================================================
# PROCESS ONE GEOJSON
# ============================================================

def process_geojson(path):

    print()
    print("=" * 70)
    print("READING")
    print(path)
    print("=" * 70)

    gdf = gpd.read_file(path)

    print(
        f"Buildings loaded: {len(gdf):,}"
    )

    print(
        f"CRS: {gdf.crs}"
    )

    # --------------------------------------------------------
    # Ensure CRS
    # --------------------------------------------------------

    if gdf.crs is None:

        print(
            "CRS missing. Assuming EPSG:3857 "
            "according to GBA documentation."
        )

        gdf = gdf.set_crs(
            SOURCE_CRS,
            allow_override=True
        )

    # --------------------------------------------------------
    # Height
    # --------------------------------------------------------

    height_col = find_height_column(
        gdf.columns
    )

    if height_col is not None:

        gdf["height_m"] = pd.to_numeric(
            gdf[height_col],
            errors="coerce"
        )

    else:

        gdf["height_m"] = None

    # --------------------------------------------------------
    # Building ID
    # --------------------------------------------------------

    possible_ids = [

        "id",
        "ID",
        "building_id",
        "buildingId",
        "fid",
        "FID",
    ]

    id_col = None

    for col in possible_ids:

        if col in gdf.columns:

            id_col = col
            break

    if id_col is not None:

        gdf["building_id"] = (
            gdf[id_col]
            .astype(str)
        )

    else:

        gdf["building_id"] = [
            f"gba_{i}"
            for i in range(len(gdf))
        ]

    # --------------------------------------------------------
    # Keep only useful columns
    # --------------------------------------------------------

    gdf = gdf[
        [
            "building_id",
            "height_m",
            "geometry",
        ]
    ].copy()

    # --------------------------------------------------------
    # Remove empty geometry
    # --------------------------------------------------------

    gdf = gdf[
        gdf.geometry.notna()
    ].copy()

    gdf = gdf[
        ~gdf.geometry.is_empty
    ].copy()

    # --------------------------------------------------------
    # Fix invalid geometry
    # --------------------------------------------------------

    print(
        "Checking invalid geometries..."
    )

    invalid = (
        ~gdf.geometry.is_valid
    ).sum()

    print(
        f"Invalid geometries: {invalid:,}"
    )

    if invalid > 0:

        print(
            "Repairing invalid geometries..."
        )

        gdf["geometry"] = (
            gdf.geometry
            .make_valid()
        )

    # --------------------------------------------------------
    # Explode multipart geometries
    # --------------------------------------------------------

    gdf = gdf.explode(
        index_parts=False
    ).reset_index(drop=True)

    return gdf


# ============================================================
# BUILD FINAL BUILDING DATASET
# ============================================================

def build_final_gpkg(files):

    header("4/4 — BUILD LONDON BUILDINGS GPKG")

    all_parts = []

    for i, path in enumerate(files, 1):

        print()
        print(
            f"Processing file "
            f"{i}/{len(files)}"
        )

        gdf = process_geojson(path)

        all_parts.append(gdf)

        # Free memory
        del gdf

    print()
    print(
        "Combining GeoJSON files..."
    )

    buildings = gpd.GeoDataFrame(
        pd.concat(
            all_parts,
            ignore_index=True
        ),
        geometry="geometry",
        crs=SOURCE_CRS,
    )

    del all_parts

    print()
    print(
        f"Total buildings before clipping: "
        f"{len(buildings):,}"
    )

    # ========================================================
    # CLIP TO LONDON
    # ========================================================

    print()
    print(
        "Clipping to London bbox..."
    )

    london_bbox = box(
        LONDON_WEST,
        LONDON_SOUTH,
        LONDON_EAST,
        LONDON_NORTH,
    )

    bbox_gdf = gpd.GeoDataFrame(
        {"geometry": [london_bbox]},
        crs="EPSG:4326",
    )

    # Convert bbox to GBA CRS
    bbox_gdf = bbox_gdf.to_crs(
        SOURCE_CRS
    )

    bbox_geom = bbox_gdf.geometry.iloc[0]

    # Spatial filter first
    buildings = buildings[
        buildings.geometry.intersects(
            bbox_geom
        )
    ].copy()

    print(
        f"Buildings after London clip: "
        f"{len(buildings):,}"
    )

    # ========================================================
    # REPROJECT TO BRITISH NATIONAL GRID
    # ========================================================

    print()
    print(
        f"Reprojecting "
        f"{SOURCE_CRS} -> {TARGET_CRS}"
    )

    buildings = buildings.to_crs(
        TARGET_CRS
    )

    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    before = len(buildings)

    buildings = buildings.drop_duplicates(
        subset=["building_id"]
    )

    after = len(buildings)

    print()
    print(
        f"Duplicate buildings removed: "
        f"{before - after:,}"
    )

    # ========================================================
    # RESET ID
    # ========================================================

    buildings = buildings.reset_index(
        drop=True
    )

    # ========================================================
    # HEIGHT STATISTICS
    # ========================================================

    buildings["height_m"] = pd.to_numeric(
        buildings["height_m"],
        errors="coerce"
    )

    print()
    print("HEIGHT STATISTICS")
    print("-" * 50)

    print(
        buildings["height_m"]
        .describe()
    )

    # ========================================================
    # SAVE
    # ========================================================

    print()
    print(
        f"Saving:"
    )

    print(
        FINAL_GPKG.resolve()
    )

    # Remove old file if it exists
    if FINAL_GPKG.exists():

        FINAL_GPKG.unlink()

    buildings.to_file(
        FINAL_GPKG,
        layer="buildings",
        driver="GPKG",
    )

    print()
    print(
        "SUCCESS!"
    )

    print()
    print(
        f"Final buildings: "
        f"{len(buildings):,}"
    )

    print(
        f"CRS: "
        f"{buildings.crs}"
    )

    print(
        f"Output: "
        f"{FINAL_GPKG.resolve()}"
    )

    # ========================================================
    # FINAL COLUMN CHECK
    # ========================================================

    print()
    print("FINAL COLUMNS")

    for c in buildings.columns:

        print(
            "   ",
            c
        )

    return buildings


# ============================================================
# MAIN
# ============================================================

def main():

    header(
        "GLOBAL BUILDING ATLAS — LONDON"
    )

    print()
    print(
        "This script downloads ONLY the London tile."
    )

    print()
    print(
        f"Tile: {TILE}"
    )

    print(
        f"London bbox: "
        f"{LONDON_WEST}, "
        f"{LONDON_SOUTH}, "
        f"{LONDON_EAST}, "
        f"{LONDON_NORTH}"
    )

    print(
        f"Target CRS: {TARGET_CRS}"
    )

    print()

    disk_space()

    # --------------------------------------------------------
    # Download
    # --------------------------------------------------------

    download_gba()

    # --------------------------------------------------------
    # Verify
    # --------------------------------------------------------

    verify_files()

    # --------------------------------------------------------
    # Process
    # --------------------------------------------------------

    run_produce_lod1()

    # --------------------------------------------------------
    # Find outputs
    # --------------------------------------------------------

    files = find_output_files()

    # --------------------------------------------------------
    # Build GPKG
    # --------------------------------------------------------

    buildings = build_final_gpkg(
        files
    )

    # --------------------------------------------------------
    # DONE
    # --------------------------------------------------------

    header(
        "COMPLETE"
    )

    print()
    print(
        "London building dataset is ready."
    )

    print()
    print(
        f"FILE:"
    )

    print(
        FINAL_GPKG.resolve()
    )

    print()
    print(
        "Schema:"
    )

    print(
        "    building_id"
    )

    print(
        "    height_m"
    )

    print(
        "    geometry"
    )

    print()
    print(
        f"CRS: {TARGET_CRS}"
    )


if __name__ == "__main__":

    main()