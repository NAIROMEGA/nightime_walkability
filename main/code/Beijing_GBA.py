"""
GlobalBuildingAtlas -> Beijing buildings

This script:
    1. Downloads the required Beijing GBA tiles only
    2. Downloads the official produce_lod1.py
    3. Runs the official GBA enrichment
    4. Reads the resulting LoD1 GeoJSON files
    5. Converts to EPSG:32650
    6. Filters to the Beijing study area
    7. Saves beijing_buildings.gpkg

IMPORTANT:
    Beijing crosses the 40°N tile boundary, so two GBA tiles
    are required:

        e115_n45_e120_n40
        e115_n40_e120_n35
"""

from pathlib import Path
import shutil
import subprocess
import sys


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parent / "GBA_Beijing"


# ------------------------------------------------------------
# Beijing study area in WGS84
# ------------------------------------------------------------

BEIJING_WEST = 115.42
BEIJING_SOUTH = 39.65
BEIJING_EAST = 117.50
BEIJING_NORTH = 40.25


# ------------------------------------------------------------
# GBA tiles
# ------------------------------------------------------------

TILES = [
    {
        "region": "asiaeast",
        "tile": "e115_n45_e120_n40",
    },
    {
        "region": "asiaeast",
        "tile": "e115_n40_e120_n35",
    },
]


# ------------------------------------------------------------
# Hugging Face repositories
# ------------------------------------------------------------

# IMPORTANT:
#
# Both LoD1 AND Polygon are in GBA.LoD1.
#
# Do NOT use "zhu-xlab/GBA.Polygon" here.
#
LOD1_REPO = "zhu-xlab/GBA.LoD1"
ODBL_REPO = "zhu-xlab/GBA.ODbLPolygon"


# ------------------------------------------------------------
# Input folders
# ------------------------------------------------------------

LOD1_DIR = ROOT / "LoD1"
POLYGON_DIR = ROOT / "Polygon"
ODBL_DIR = ROOT / "ODbLPolygon"


# ------------------------------------------------------------
# Output folders
# ------------------------------------------------------------

LOD1_OUTPUT = ROOT / "LoD1_GeoJSON"


# ------------------------------------------------------------
# Final file
# ------------------------------------------------------------

FINAL_GPKG = Path("beijing_buildings.gpkg")


# ------------------------------------------------------------
# CRS
# ------------------------------------------------------------

SOURCE_CRS = "EPSG:3857"
TARGET_CRS = "EPSG:32650"


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

    check_path = ROOT.resolve()

    if not check_path.exists():
        check_path = check_path.parent

    total, used, free = shutil.disk_usage(
        str(check_path)
    )

    free_gb = free / (1024 ** 3)
    total_gb = total / (1024 ** 3)

    print()
    print(f"Disk: {check_path.drive}")
    print(
        f"Total disk space: "
        f"{total_gb:.2f} GB"
    )
    print(
        f"Free disk space : "
        f"{free_gb:.2f} GB"
    )

    if free_gb < 30:

        print()
        print("WARNING:")
        print(
            "Less than 30 GB of free space is available."
        )
        print(
            "Beijing GBA processing requires substantial "
            "temporary disk space."
        )
        print()

    return free_gb


# ============================================================
# DOWNLOAD FILE
# ============================================================

def download_hf_file(
    repo_id,
    repo_type,
    filename,
    local_dir,
):

    print()
    print("-" * 70)
    print("Downloading")
    print("-" * 70)

    print("Repository :", repo_id)
    print("File       :", filename)
    print("Local dir  :", local_dir)

    local_dir = Path(local_dir)

    local_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    try:

        downloaded = hf_hub_download(
            repo_id=repo_id,
            repo_type=repo_type,
            filename=filename,
            local_dir=str(local_dir),
        )

    except Exception as e:

        print()
        print("DOWNLOAD FAILED")
        print()
        print(
            f"Repository: {repo_id}"
        )
        print(
            f"File      : {filename}"
        )
        print()
        print(
            f"Error: {type(e).__name__}: {e}"
        )

        raise

    print()
    print("Downloaded:")
    print(downloaded)

    return Path(downloaded)


# ============================================================
# DOWNLOAD GBA DATA
# ============================================================

def download_gba():

    header("1/4 — DOWNLOAD GBA DATA")

    ROOT.mkdir(
        parents=True,
        exist_ok=True
    )


    # ========================================================
    # DOWNLOAD EACH TILE
    # ========================================================

    for item in TILES:

        region = item["region"]
        tile = item["tile"]

        print()
        print("#" * 70)
        print(
            f"TILE: {region}/{tile}"
        )
        print("#" * 70)


        # ----------------------------------------------------
        # 1. LoD1 JSON
        # ----------------------------------------------------

        lod1_file = (
            f"LoD1/"
            f"{region}/"
            f"{tile}.json"
        )

        download_hf_file(
            repo_id=LOD1_REPO,
            repo_type="dataset",
            filename=lod1_file,
            local_dir=ROOT,
        )


        # ----------------------------------------------------
        # 2. GBA Polygon
        #
        # IMPORTANT:
        # Polygon is ALSO inside GBA.LoD1.
        # ----------------------------------------------------

        polygon_file = (
            f"Polygon/"
            f"{region}/"
            f"{tile}.geojson"
        )

        download_hf_file(
            repo_id=LOD1_REPO,
            repo_type="dataset",
            filename=polygon_file,
            local_dir=ROOT,
        )


        # ----------------------------------------------------
        # 3. ODbL Polygon
        #
        # This one comes from GBA.ODbLPolygon.
        # ----------------------------------------------------

        odbl_file = (
            f"{region}/"
            f"{tile}.geojson"
        )

        download_hf_file(
            repo_id=ODBL_REPO,
            repo_type="dataset",
            filename=odbl_file,
            local_dir=ODBL_DIR,
        )


    # ========================================================
    # OFFICIAL PROCESSING SCRIPT
    # ========================================================

    header(
        "Downloading official produce_lod1.py"
    )

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

    header(
        "2/4 — VERIFY FILE STRUCTURE"
    )

    expected = []

    for item in TILES:

        region = item["region"]
        tile = item["tile"]

        expected.append(
            ROOT
            / "LoD1"
            / region
            / f"{tile}.json"
        )

        expected.append(
            ROOT
            / "Polygon"
            / region
            / f"{tile}.geojson"
        )

        expected.append(
            ROOT
            / "ODbLPolygon"
            / region
            / f"{tile}.geojson"
        )

    expected.append(
        ROOT / "produce_lod1.py"
    )


    everything_ok = True

    for path in expected:

        if path.exists():

            size_gb = (
                path.stat().st_size
                / (1024 ** 3)
            )

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
    print(
        "Directory structure is correct."
    )


# ============================================================
# RUN OFFICIAL GBA SCRIPT
# ============================================================

def run_produce_lod1():

    print()
    print("=" * 70)
    print("3/4 — RUN GBA LoD1 ENRICHMENT")
    print("=" * 70)


    script = (
        ROOT / "produce_lod1.py"
    ).resolve()

    odbl_root = (
        ROOT / "ODbLPolygon"
    ).resolve()

    polygon_root = (
        ROOT / "Polygon"
    ).resolve()

    json_root = (
        ROOT / "LoD1"
    ).resolve()

    output_root = (
        ROOT / "LoD1_GeoJSON"
    ).resolve()

    sqlite_root = (
        ROOT / "sqlite_tmp"
    ).resolve()


    # --------------------------------------------------------
    # Safety checks
    # --------------------------------------------------------

    required = [

        (
            "produce_lod1.py",
            script
        ),

        (
            "ODbLPolygon",
            odbl_root
        ),

        (
            "Polygon",
            polygon_root
        ),

        (
            "LoD1",
            json_root
        ),
    ]


    for name, path in required:

        if not path.exists():

            raise FileNotFoundError(
                f"Required GBA component not found:\n"
                f"{name}: {path}"
            )


    output_root.mkdir(
        parents=True,
        exist_ok=True
    )

    sqlite_root.mkdir(
        parents=True,
        exist_ok=True
    )


    # --------------------------------------------------------
    # Command
    # --------------------------------------------------------

    workdir = (
        ROOT.parent.resolve()
    )


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

    print(
        " ".join(
            f'"{x}"'
            for x in cmd
        )
    )


    print()
    print(
        "Working directory:"
    )

    print(workdir)


    print()
    print(
        "The Beijing tiles are large."
    )

    print(
        "The official GBA enrichment may take "
        "a LONG time."
    )

    print()
    print(
        "Starting official GBA enrichment..."
    )

    print()


    result = subprocess.run(
        cmd,
        cwd=str(workdir),
        check=False,
    )


    if result.returncode != 0:

        raise RuntimeError(
            f"\nproduce_lod1.py failed "
            f"with exit code "
            f"{result.returncode}"
        )


    print()
    print("=" * 70)
    print(
        "GBA LoD1 enrichment completed successfully."
    )
    print("=" * 70)


# ============================================================
# FIND OUTPUT FILES
# ============================================================

def find_output_files():

    header(
        "SEARCHING FOR GENERATED LoD1 GEOJSON"
    )


    if not LOD1_OUTPUT.exists():

        raise FileNotFoundError(
            f"Output directory does not exist: "
            f"{LOD1_OUTPUT}"
        )


    files = list(
        LOD1_OUTPUT.rglob(
            "*.geojson"
        )
    )


    print()
    print(
        f"Found {len(files)} GeoJSON files."
    )


    for f in files:

        size_gb = (
            f.stat().st_size
            / (1024 ** 3)
        )

        print(
            f"  {f} "
            f"({size_gb:.2f} GB)"
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

def process_geojson(
    path,
    tile_index,
):

    print()
    print("=" * 70)
    print("READING")
    print(path)
    print("=" * 70)


    gdf = gpd.read_file(
        path
    )


    print(
        f"Buildings loaded: "
        f"{len(gdf):,}"
    )


    print(
        f"CRS: {gdf.crs}"
    )


    # --------------------------------------------------------
    # CRS
    # --------------------------------------------------------

    if gdf.crs is None:

        print(
            "CRS missing. Assuming EPSG:3857."
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

            f"gba_{tile_index}_{i}"

            for i in range(
                len(gdf)
            )
        ]


    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Qualify IDs by tile.
    #
    # This avoids accidentally deleting buildings from
    # different tiles that happen to have the same ID.
    # --------------------------------------------------------

    gdf["building_id"] = (

        f"tile{tile_index}_"

        + gdf["building_id"].astype(str)
    )


    # --------------------------------------------------------
    # Keep useful columns
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
        f"Invalid geometries: "
        f"{invalid:,}"
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
    ).reset_index(
        drop=True
    )


    return gdf


# ============================================================
# BUILD FINAL BUILDING DATASET
# ============================================================

def build_final_gpkg(files):

    header(
        "4/4 — BUILD BEIJING BUILDINGS GPKG"
    )


    all_parts = []


    for i, path in enumerate(
        files,
        1
    ):

        print()
        print(
            f"Processing file "
            f"{i}/{len(files)}"
        )


        gdf = process_geojson(
            path,
            i
        )


        all_parts.append(
            gdf
        )


        del gdf


    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

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
        f"Total buildings before "
        f"Beijing filtering: "
        f"{len(buildings):,}"
    )


    # ========================================================
    # BEIJING BBOX
    # ========================================================

    print()
    print(
        "Filtering to Beijing bbox..."
    )


    beijing_bbox = box(

        BEIJING_WEST,
        BEIJING_SOUTH,
        BEIJING_EAST,
        BEIJING_NORTH,
    )


    bbox_gdf = gpd.GeoDataFrame(

        {
            "geometry": [
                beijing_bbox
            ]
        },

        crs="EPSG:4326",
    )


    bbox_gdf = bbox_gdf.to_crs(
        SOURCE_CRS
    )


    bbox_geom = (
        bbox_gdf.geometry.iloc[0]
    )


    # --------------------------------------------------------
    # Spatial filter
    # --------------------------------------------------------

    buildings = buildings[
        buildings.geometry.intersects(
            bbox_geom
        )
    ].copy()


    print()
    print(
        f"Buildings after Beijing "
        f"filter: {len(buildings):,}"
    )


    # ========================================================
    # REPROJECT
    # ========================================================

    print()
    print(
        f"Reprojecting "
        f"{SOURCE_CRS} -> "
        f"{TARGET_CRS}"
    )


    buildings = buildings.to_crs(
        TARGET_CRS
    )


    # ========================================================
    # HEIGHT CLEANUP
    # ========================================================

    buildings["height_m"] = pd.to_numeric(
        buildings["height_m"],
        errors="coerce"
    )


    # --------------------------------------------------------
    # Remove buildings without usable positive height
    # --------------------------------------------------------

    before_height = len(
        buildings
    )


    buildings = buildings[
        buildings["height_m"].notna()
        &
        (buildings["height_m"] > 0)
    ].copy()


    print()
    print(
        "Buildings removed because of "
        "missing/non-positive height: "
        f"{before_height - len(buildings):,}"
    )


    # ========================================================
    # RESET INDEX
    # ========================================================

    buildings = buildings.reset_index(
        drop=True
    )


    # ========================================================
    # HEIGHT STATISTICS
    # ========================================================

    print()
    print(
        "HEIGHT STATISTICS"
    )

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
        "Saving:"
    )


    print(
        FINAL_GPKG.resolve()
    )


    if FINAL_GPKG.exists():

        print(
            "Removing existing GPKG..."
        )

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
    # FINAL COLUMNS
    # ========================================================

    print()
    print(
        "FINAL COLUMNS"
    )


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
        "GLOBAL BUILDING ATLAS — BEIJING"
    )


    print()
    print(
        "This script downloads ONLY the "
        "Beijing GBA tiles."
    )


    print()

    print(
        "Tiles:"
    )

    for item in TILES:

        print(
            f"    "
            f"{item['region']}/"
            f"{item['tile']}"
        )


    print()

    print(
        f"Beijing bbox: "
        f"{BEIJING_WEST}, "
        f"{BEIJING_SOUTH}, "
        f"{BEIJING_EAST}, "
        f"{BEIJING_NORTH}"
    )


    print(
        f"Source CRS: "
        f"{SOURCE_CRS}"
    )


    print(
        f"Target CRS: "
        f"{TARGET_CRS}"
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
    # Official processing
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
        "Beijing building dataset is ready."
    )


    print()
    print(
        "FILE:"
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


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()