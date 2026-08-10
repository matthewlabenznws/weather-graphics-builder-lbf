import json
import os
import sys
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import requests


# ============================================================
# CONFIGURATION
# ============================================================

SPC_URL = (
    "https://www.spc.noaa.gov/products/outlook/"
    "day1otlk-shp.zip"
)

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"

OUTPUT_FILE = DATA_DIR / "spc_day1_cat.geojson"

TIMEOUT = 60


# ============================================================
# LOGGING
# ============================================================

def log(message):
    """
    Print a UTC timestamp with every message.
    Useful when the script runs from cron.
    """

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )

    print(
        f"[{timestamp}] {message}",
        flush=True
    )


# ============================================================
# DOWNLOAD SPC ZIP
# ============================================================

def download_spc_zip(destination):

    log("Downloading current SPC Day 1 outlook...")

    response = requests.get(
        SPC_URL,
        timeout=TIMEOUT,
        headers={
            "User-Agent":
                "NWS-LBF-Weather-Graphics/1.0"
        }
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "Content-Type",
        ""
    )

    log(
        f"HTTP {response.status_code} | "
        f"{len(response.content) / 1024:.1f} KB | "
        f"{content_type}"
    )


    # --------------------------------------------------------
    # Basic validation
    # --------------------------------------------------------

    if len(response.content) < 1000:

        raise RuntimeError(
            "Downloaded SPC ZIP is unexpectedly small."
        )


    destination.write_bytes(
        response.content
    )


    # --------------------------------------------------------
    # Make sure the file really is a ZIP
    # --------------------------------------------------------

    if not zipfile.is_zipfile(destination):

        raise RuntimeError(
            "SPC response is not a valid ZIP file."
        )


# ============================================================
# EXTRACT ZIP
# ============================================================

def extract_zip(zip_file, destination):

    log("Extracting SPC outlook ZIP...")

    destination.mkdir(
        parents=True,
        exist_ok=True
    )

    with zipfile.ZipFile(
        zip_file,
        "r"
    ) as z:

        z.extractall(
            destination
        )


# ============================================================
# FIND CATEGORICAL SHAPEFILE
# ============================================================

def find_categorical_shapefile(folder):

    shapefiles = sorted(
        folder.rglob("*.shp")
    )

    if not shapefiles:

        raise FileNotFoundError(
            "No shapefiles were found in the SPC ZIP."
        )


    log("Shapefiles found:")

    for shp in shapefiles:
        log(f"  {shp.name}")


    # --------------------------------------------------------
    # BEST CHOICE:
    #
    # day1otlk_YYYYMMDD_HHMM_cat.shp
    #
    # This is the timestamped categorical outlook and avoids
    # the .lyr and .nolyr variants.
    # --------------------------------------------------------

    timestamped_cat = [
        shp
        for shp in shapefiles
        if "_cat" in shp.stem.lower()
        and ".lyr" not in shp.stem.lower()
        and ".nolyr" not in shp.stem.lower()
        and any(
            char.isdigit()
            for char in shp.stem
        )
    ]


    if timestamped_cat:

        chosen = timestamped_cat[0]

        log(
            "Using timestamped categorical shapefile: "
            f"{chosen.name}"
        )

        return chosen


    # --------------------------------------------------------
    # FALLBACK:
    #
    # day1otlk_cat.shp
    # --------------------------------------------------------

    plain_cat = [
        shp
        for shp in shapefiles
        if shp.name.lower()
        == "day1otlk_cat.shp"
    ]


    if plain_cat:

        chosen = plain_cat[0]

        log(
            "Using categorical shapefile: "
            f"{chosen.name}"
        )

        return chosen


    # --------------------------------------------------------
    # LAST RESORT
    # --------------------------------------------------------

    generic_cat = [
        shp
        for shp in shapefiles
        if "cat" in shp.stem.lower()
        and ".lyr" not in shp.stem.lower()
        and ".nolyr" not in shp.stem.lower()
    ]


    if generic_cat:

        chosen = generic_cat[0]

        log(
            "Using fallback categorical shapefile: "
            f"{chosen.name}"
        )

        return chosen


    raise FileNotFoundError(
        "Could not identify SPC Day 1 categorical shapefile."
    )


# ============================================================
# READ + CLEAN SPC DATA
# ============================================================

def prepare_geojson(shapefile):

    log(
        f"Reading {shapefile.name}..."
    )

    gdf = gpd.read_file(
        shapefile
    )


    if gdf.empty:

        raise RuntimeError(
            "SPC categorical shapefile contains no features."
        )


    log(
        f"Found {len(gdf)} outlook features."
    )


    log(
        "Columns: "
        + ", ".join(gdf.columns)
    )


    # --------------------------------------------------------
    # Validate important fields
    # --------------------------------------------------------

    required_fields = {
        "LABEL",
        "geometry"
    }

    missing = (
        required_fields
        - set(gdf.columns)
    )


    if missing:

        raise RuntimeError(
            "Missing required SPC fields: "
            + ", ".join(sorted(missing))
        )


    # --------------------------------------------------------
    # Remove bad geometries
    # --------------------------------------------------------

    gdf = gdf[
        gdf.geometry.notnull()
    ].copy()

    gdf = gdf[
        ~gdf.geometry.is_empty
    ].copy()


    if gdf.empty:

        raise RuntimeError(
            "No valid SPC geometries remain."
        )


    # --------------------------------------------------------
    # CRS
    # --------------------------------------------------------

    if gdf.crs is None:

        raise RuntimeError(
            "SPC shapefile has no CRS."
        )


    if str(gdf.crs) != "EPSG:4326":

        log(
            f"Converting CRS from "
            f"{gdf.crs} to EPSG:4326..."
        )

        gdf = gdf.to_crs(
            "EPSG:4326"
        )


    # --------------------------------------------------------
    # Keep only the fields we need on the website
    # --------------------------------------------------------

    desired_fields = [
        "DN",
        "VALID",
        "EXPIRE",
        "ISSUE",
        "VALID_ISO",
        "EXPIRE_ISO",
        "ISSUE_ISO",
        "FORECASTER",
        "LABEL",
        "LABEL2",
        "stroke",
        "fill",
        "geometry"
    ]


    keep_fields = [
        field
        for field in desired_fields
        if field in gdf.columns
    ]


    gdf = gdf[
        keep_fields
    ].copy()


    # --------------------------------------------------------
    # Normalize text values
    # --------------------------------------------------------

    gdf["LABEL"] = (
        gdf["LABEL"]
        .astype(str)
        .str.strip()
        .str.upper()
    )


    log(
        "Categories: "
        + ", ".join(
            gdf["LABEL"].tolist()
        )
    )


    return gdf


# ============================================================
# GET ISSUE IDENTIFIER
# ============================================================

def get_issue_id(gdf):

    """
    Use ISSUE_ISO when available.
    Falls back to ISSUE.
    """

    if (
        "ISSUE_ISO" in gdf.columns
        and not gdf["ISSUE_ISO"].empty
    ):

        values = (
            gdf["ISSUE_ISO"]
            .dropna()
            .astype(str)
            .unique()
        )

        if len(values) > 0:
            return values[0]


    if (
        "ISSUE" in gdf.columns
        and not gdf["ISSUE"].empty
    ):

        values = (
            gdf["ISSUE"]
            .dropna()
            .astype(str)
            .unique()
        )

        if len(values) > 0:
            return values[0]


    return None


# ============================================================
# READ CURRENT GEOJSON ISSUE
# ============================================================

def get_existing_issue():

    if not OUTPUT_FILE.exists():
        return None


    try:

        with OUTPUT_FILE.open(
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)


        features = data.get(
            "features",
            []
        )


        if not features:
            return None


        props = features[0].get(
            "properties",
            {}
        )


        return (
            props.get("ISSUE_ISO")
            or props.get("ISSUE")
        )


    except Exception as e:

        log(
            "Could not read existing GeoJSON issue: "
            f"{e}"
        )

        return None


# ============================================================
# WRITE GEOJSON ATOMICALLY
# ============================================================

def write_geojson(gdf):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


    temp_output = (
        DATA_DIR
        / "spc_day1_cat.tmp.geojson"
    )


    log(
        "Writing temporary GeoJSON..."
    )


    gdf.to_file(
        temp_output,
        driver="GeoJSON"
    )


    # --------------------------------------------------------
    # Validate written file
    # --------------------------------------------------------

    if not temp_output.exists():

        raise RuntimeError(
            "Temporary GeoJSON was not created."
        )


    if temp_output.stat().st_size < 100:

        raise RuntimeError(
            "Temporary GeoJSON is unexpectedly small."
        )


    # --------------------------------------------------------
    # Atomic replacement
    # --------------------------------------------------------

    os.replace(
        temp_output,
        OUTPUT_FILE
    )


    log(
        f"Updated {OUTPUT_FILE}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    log(
        "=" * 60
    )

    log(
        "SPC Day 1 categorical update starting"
    )

    log(
        "=" * 60
    )


    with tempfile.TemporaryDirectory() as temp:

        temp_dir = Path(temp)

        zip_file = (
            temp_dir
            / "day1otlk-shp.zip"
        )

        extract_dir = (
            temp_dir
            / "spc"
        )


        # ----------------------------------------------------
        # DOWNLOAD
        # ----------------------------------------------------

        download_spc_zip(
            zip_file
        )


        # ----------------------------------------------------
        # EXTRACT
        # ----------------------------------------------------

        extract_zip(
            zip_file,
            extract_dir
        )


        # ----------------------------------------------------
        # FIND CATEGORICAL SHAPEFILE
        # ----------------------------------------------------

        shapefile = (
            find_categorical_shapefile(
                extract_dir
            )
        )


        # ----------------------------------------------------
        # PREPARE DATA
        # ----------------------------------------------------

        gdf = prepare_geojson(
            shapefile
        )


        # ----------------------------------------------------
        # CHECK IF SPC ISSUANCE CHANGED
        # ----------------------------------------------------

        new_issue = get_issue_id(
            gdf
        )

        existing_issue = (
            get_existing_issue()
        )


        log(
            f"Existing issue: {existing_issue}"
        )

        log(
            f"Downloaded issue: {new_issue}"
        )


        if (
            new_issue
            and existing_issue
            and new_issue == existing_issue
        ):

            log(
                "SPC outlook has not changed. "
                "No file update needed."
            )

            return


        # ----------------------------------------------------
        # WRITE NEW DATA
        # ----------------------------------------------------

        write_geojson(
            gdf
        )


        log(
            "SPC Day 1 outlook successfully updated."
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except Exception as e:

        log(
            "SPC UPDATE FAILED"
        )

        log(
            f"{type(e).__name__}: {e}"
        )

        sys.exit(1)
