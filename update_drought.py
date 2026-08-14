#!/usr/bin/env python3

# ============================================================
# NWS NORTH PLATTE WEATHER GRAPHICS BUILDER
# U.S. DROUGHT MONITOR UPDATER
#
# Downloads the current official U.S. Drought Monitor
# shapefile, converts it to WGS84 GeoJSON, simplifies the
# geometry for web display, and writes a small manifest.
#
# Outputs:
#
#   data/drought/current.geojson
#   data/drought/latest.json
#
# Required packages:
#
#   requests
#   geopandas
#   shapely
#   pyproj
#   fiona / pyogrio
#
# ============================================================


from __future__ import annotations


import json
import os
import re
import shutil
import sys
import tempfile
import time
import zipfile

from datetime import datetime, timezone
from pathlib import Path


import geopandas as gpd
import requests


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR = Path(
    "data/drought"
)


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


GEOJSON_OUTPUT = (
    OUTPUT_DIR
    /
    "current.geojson"
)


MANIFEST_OUTPUT = (
    OUTPUT_DIR
    /
    "latest.json"
)


# ============================================================
# OFFICIAL U.S. DROUGHT MONITOR SOURCE
#
# Current merged shapefile.
# ============================================================

USDM_CURRENT_URL = (

    "https://droughtmonitor.unl.edu/"
    "data/shapefiles_m/"
    "USDM_current_M.zip"

)


# ============================================================
# DOWNLOAD SETTINGS
# ============================================================

REQUEST_TIMEOUT_SECONDS = 120

MAX_DOWNLOAD_ATTEMPTS = 4

RETRY_WAIT_SECONDS = 10


REQUEST_HEADERS = {

    "User-Agent":

        "NWS-LBF-Weather-Graphics-Builder/1.0",

    "Accept":

        "*/*"

}


# ============================================================
# GEOMETRY SIMPLIFICATION
#
# Simplification occurs after temporarily projecting into
# Web Mercator so the tolerance is measured in meters.
#
# 1000 m gives a much smaller GeoJSON while retaining more
# than enough detail for the weather graphics map.
# ============================================================

SIMPLIFY_TOLERANCE_METERS = 1000.0


# ============================================================
# OFFICIAL U.S. DROUGHT MONITOR COLORS
# ============================================================

DROUGHT_COLORS = {

    0:
        "#FFFF00",

    1:
        "#FCD37F",

    2:
        "#FFAA00",

    3:
        "#E60000",

    4:
        "#730000"

}


# ============================================================
# DROUGHT CATEGORY NAMES
# ============================================================

DROUGHT_NAMES = {

    0:
        "Abnormally Dry",

    1:
        "Moderate Drought",

    2:
        "Severe Drought",

    3:
        "Extreme Drought",

    4:
        "Exceptional Drought"

}


# ============================================================
# DOWNLOAD CURRENT USDM ZIP
# ============================================================

def download_current_usdm() -> bytes:

    last_error = None


    for attempt in range(

        1,
        MAX_DOWNLOAD_ATTEMPTS + 1

    ):

        print()
        print("=" * 70)
        print("DOWNLOADING U.S. DROUGHT MONITOR")
        print("=" * 70)

        print(
            f"Attempt "
            f"{attempt}/"
            f"{MAX_DOWNLOAD_ATTEMPTS}"
        )

        print(
            USDM_CURRENT_URL
        )


        try:

            response = requests.get(

                USDM_CURRENT_URL,

                headers=
                    REQUEST_HEADERS,

                timeout=
                    REQUEST_TIMEOUT_SECONDS

            )


            response.raise_for_status()


            content = (
                response.content
            )


            if (
                not content
            ):

                raise RuntimeError(
                    "Downloaded drought file was empty."
                )


            # =================================================
            # ZIP FILE SIGNATURE
            # =================================================

            if (
                not content.startswith(
                    b"PK"
                )
            ):

                raise RuntimeError(

                    "Downloaded file does not appear "
                    "to be a valid ZIP archive."

                )


            print(
                f"Downloaded "
                f"{len(content):,} bytes."
            )


            return content


        except Exception as error:

            last_error = (
                error
            )


            print(
                f"Attempt failed: "
                f"{error}"
            )


            if (
                attempt
                <
                MAX_DOWNLOAD_ATTEMPTS
            ):

                print(
                    f"Waiting "
                    f"{RETRY_WAIT_SECONDS} seconds..."
                )


                time.sleep(
                    RETRY_WAIT_SECONDS
                )


    raise RuntimeError(

        "Unable to download the current "
        "U.S. Drought Monitor dataset.\n"
        f"Last error: {last_error}"

    )


# ============================================================
# EXTRACT ZIP
# ============================================================

def extract_usdm_zip(
    zip_bytes: bytes,
    destination: Path
):

    zip_path = (
        destination
        /
        "usdm_current.zip"
    )


    with open(
        zip_path,
        "wb"
    ) as file:

        file.write(
            zip_bytes
        )


    print()
    print("=" * 70)
    print("EXTRACTING DROUGHT MONITOR")
    print("=" * 70)


    with zipfile.ZipFile(
        zip_path,
        "r"
    ) as archive:

        archive.extractall(
            destination
        )


        names = (
            archive.namelist()
        )


    print(
        f"Extracted "
        f"{len(names)} files."
    )


    return names


# ============================================================
# FIND SHAPEFILE
# ============================================================

def find_shapefile(
    directory: Path
) -> Path:

    shapefiles = list(

        directory.rglob(
            "*.shp"
        )

    )


    if (
        not shapefiles
    ):

        raise RuntimeError(

            "No shapefile was found "
            "inside the U.S. Drought Monitor ZIP."

        )


    print()
    print(
        "Shapefile candidates:"
    )


    for shapefile in shapefiles:

        print(
            f"  {shapefile.name}"
        )


    # ========================================================
    # Prefer the merged "_M" shapefile if multiple exist.
    # ========================================================

    for shapefile in shapefiles:

        name = (
            shapefile
            .stem
            .upper()
        )


        if (
            name.endswith(
                "_M"
            )
        ):

            print()
            print(
                f"Using shapefile: "
                f"{shapefile.name}"
            )


            return shapefile


    # ========================================================
    # Otherwise use first available shapefile.
    # ========================================================

    shapefile = (
        shapefiles[0]
    )


    print()
    print(
        f"Using shapefile: "
        f"{shapefile.name}"
    )


    return shapefile


# ============================================================
# DETECT VALID DATE FROM FILE NAMES
# ============================================================

def detect_valid_date(
    filenames
):

    # ========================================================
    # Look for YYYYMMDD anywhere in archive names.
    # ========================================================

    date_pattern = re.compile(

        r"(?<!\d)"
        r"(20\d{6})"
        r"(?!\d)"

    )


    for filename in filenames:

        match = date_pattern.search(
            filename
        )


        if (
            not match
        ):

            continue


        raw_date = (
            match.group(1)
        )


        try:

            parsed = datetime.strptime(

                raw_date,

                "%Y%m%d"

            )


            return (
                parsed
                .date()
                .isoformat()
            )


        except ValueError:

            continue


    return None


# ============================================================
# NORMALIZE DROUGHT CATEGORY
#
# USDM files normally use the field "DM".
#
# Handles:
#
#   0
#   1
#   2
#   3
#   4
#
# or:
#
#   D0
#   D1
#   D2
#   D3
#   D4
# ============================================================

def normalize_dm_value(
    value
):

    if (
        value
        is None
    ):

        return None


    # ========================================================
    # NUMERIC
    # ========================================================

    try:

        numeric = int(
            float(
                value
            )
        )


        if (
            0
            <=
            numeric
            <=
            4
        ):

            return numeric


    except (
        ValueError,
        TypeError
    ):

        pass


    # ========================================================
    # STRING D0-D4
    # ========================================================

    text = (
        str(
            value
        )
        .strip()
        .upper()
    )


    match = re.search(

        r"D?([0-4])",

        text

    )


    if (
        match
    ):

        return int(
            match.group(1)
        )


    return None


# ============================================================
# FIND DROUGHT CATEGORY FIELD
# ============================================================

def find_dm_field(
    frame: gpd.GeoDataFrame
) -> str:

    print()
    print("=" * 70)
    print("SHAPEFILE FIELDS")
    print("=" * 70)


    for column in frame.columns:

        print(
            f"  {column}"
        )


    candidates = [

        "DM",
        "dm",
        "DROUGHT",
        "Drought",
        "drought",
        "CATEGORY",
        "Category",
        "category"

    ]


    for candidate in candidates:

        if (
            candidate
            in
            frame.columns
        ):

            print()
            print(
                f"Using drought field: "
                f"{candidate}"
            )


            return candidate


    # ========================================================
    # CASE-INSENSITIVE FALLBACK
    # ========================================================

    lookup = {

        column.lower():
            column

        for column in frame.columns

    }


    if (
        "dm"
        in
        lookup
    ):

        field = (
            lookup[
                "dm"
            ]
        )


        print()
        print(
            f"Using drought field: "
            f"{field}"
        )


        return field


    raise RuntimeError(

        "Could not identify the drought category field "
        "in the U.S. Drought Monitor shapefile."

    )


# ============================================================
# PREPARE GEOJSON
# ============================================================

def prepare_drought_data(
    shapefile: Path
) -> gpd.GeoDataFrame:

    print()
    print("=" * 70)
    print("READING U.S. DROUGHT MONITOR")
    print("=" * 70)


    frame = gpd.read_file(
        shapefile
    )


    print(
        f"Features read: "
        f"{len(frame)}"
    )


    print(
        f"Source CRS: "
        f"{frame.crs}"
    )


    if (
        frame.empty
    ):

        raise RuntimeError(

            "U.S. Drought Monitor shapefile "
            "contains no features."

        )


    if (
        frame.crs
        is None
    ):

        raise RuntimeError(

            "U.S. Drought Monitor shapefile "
            "does not contain a usable CRS."

        )


    # ========================================================
    # DROUGHT CATEGORY FIELD
    # ========================================================

    dm_field = (
        find_dm_field(
            frame
        )
    )


    # ========================================================
    # NORMALIZE CATEGORY
    # ========================================================

    frame[
        "dm_int"
    ] = frame[
        dm_field
    ].apply(
        normalize_dm_value
    )


    frame = frame[

        frame[
            "dm_int"
        ].notna()

    ].copy()


    frame[
        "dm_int"
    ] = frame[
        "dm_int"
    ].astype(
        int
    )


    if (
        frame.empty
    ):

        raise RuntimeError(

            "No valid D0-D4 polygons "
            "were found in the drought dataset."

        )


    print()
    print(
        "Drought categories found:"
    )


    for category in sorted(

        frame[
            "dm_int"
        ].unique()

    ):

        count = int(

            (
                frame[
                    "dm_int"
                ]
                ==
                category
            ).sum()

        )


        print(
            f"  D{category}: "
            f"{count} feature(s)"
        )


    # ========================================================
    # REMOVE INVALID GEOMETRY
    # ========================================================

    frame = frame[

        frame.geometry.notna()

        &

        ~frame.geometry.is_empty

    ].copy()


    # ========================================================
    # REPAIR INVALID GEOMETRIES
    # ========================================================

    invalid_count = int(

        (
            ~frame.geometry.is_valid
        ).sum()

    )


    if (
        invalid_count
        >
        0
    ):

        print()
        print(
            f"Repairing "
            f"{invalid_count} invalid geometries..."
        )


        frame.geometry = (
            frame.geometry.buffer(
                0
            )
        )


    # ========================================================
    # WEB-MERCATOR SIMPLIFICATION
    # ========================================================

    print()
    print(
        f"Simplifying geometry at "
        f"{SIMPLIFY_TOLERANCE_METERS:.0f} meters..."
    )


    web_mercator = (
        frame.to_crs(
            epsg=3857
        )
    )


    web_mercator.geometry = (

        web_mercator.geometry.simplify(

            SIMPLIFY_TOLERANCE_METERS,

            preserve_topology=True

        )

    )


    # ========================================================
    # MAPBOX / GEOJSON NEEDS WGS84
    # ========================================================

    frame = (
        web_mercator.to_crs(
            epsg=4326
        )
    )


    # ========================================================
    # MAPBOX DISPLAY PROPERTIES
    # ========================================================

    frame[
        "category"
    ] = frame[
        "dm_int"
    ].apply(

        lambda value:
            f"D{value}"

    )


    frame[
        "name"
    ] = frame[
        "dm_int"
    ].map(
        DROUGHT_NAMES
    )


    frame[
        "label"
    ] = frame.apply(

        lambda row:

            (
                f"{row['category']} - "
                f"{row['name']}"
            ),

        axis=1

    )


    frame[
        "fill"
    ] = frame[
        "dm_int"
    ].map(
        DROUGHT_COLORS
    )


    # ========================================================
    # DARK OUTLINE
    # ========================================================

    frame[
        "stroke"
    ] = "#4A2A00"


    # ========================================================
    # RETAIN ONLY WEB-NEEDED PROPERTIES
    # ========================================================

    frame = frame[

        [

            "dm_int",
            "category",
            "name",
            "label",
            "fill",
            "stroke",
            "geometry"

        ]

    ].copy()


    # ========================================================
    # SORT LOWEST -> HIGHEST CATEGORY
    #
    # If polygons overlap, higher drought categories get
    # serialized later.
    # ========================================================

    frame = frame.sort_values(

        by=
            "dm_int",

        ascending=
            True

    ).reset_index(
        drop=True
    )


    return frame


# ============================================================
# WRITE GEOJSON ATOMICALLY
# ============================================================

def write_geojson(
    frame: gpd.GeoDataFrame
):

    temporary_output = (

        OUTPUT_DIR
        /
        "current.geojson.tmp"

    )


    print()
    print("=" * 70)
    print("WRITING DROUGHT GEOJSON")
    print("=" * 70)


    geojson_text = (
        frame.to_json(

            drop_id=True,

            to_wgs84=True

        )
    )


    # ========================================================
    # VALIDATE BEFORE WRITING FINAL FILE
    # ========================================================

    parsed = json.loads(
        geojson_text
    )


    if (
        parsed.get(
            "type"
        )
        !=
        "FeatureCollection"
    ):

        raise RuntimeError(

            "Generated drought GeoJSON "
            "is not a FeatureCollection."

        )


    features = (
        parsed.get(
            "features",
            []
        )
    )


    if (
        not features
    ):

        raise RuntimeError(

            "Generated drought GeoJSON "
            "contains no features."

        )


    with open(

        temporary_output,

        "w",

        encoding=
            "utf-8"

    ) as file:

        json.dump(

            parsed,

            file,

            separators=(
                ",",
                ":"
            ),

            ensure_ascii=False,

            allow_nan=False

        )


    os.replace(

        temporary_output,

        GEOJSON_OUTPUT

    )


    print(
        f"Saved: "
        f"{GEOJSON_OUTPUT}"
    )


    print(
        f"Features: "
        f"{len(features)}"
    )


    print(
        f"File size: "
        f"{GEOJSON_OUTPUT.stat().st_size / 1024:.1f} KB"
    )


# ============================================================
# WRITE MANIFEST
# ============================================================

def write_manifest(
    frame: gpd.GeoDataFrame,
    valid_date
):

    generated = (

        datetime.now(
            timezone.utc
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z"
        )

    )


    category_counts = {}


    for category in range(
        5
    ):

        category_counts[
            f"D{category}"
        ] = int(

            (
                frame[
                    "dm_int"
                ]
                ==
                category
            ).sum()

        )


    bounds = (
        frame.total_bounds
    )


    manifest = {

        "generated":
            generated,

        "valid_date":
            valid_date,

        "source":
            "U.S. Drought Monitor",

        "source_url":
            USDM_CURRENT_URL,

        "attribution":

            (
                "National Drought Mitigation Center (NDMC), "
                "U.S. Department of Agriculture (USDA), "
                "National Oceanic and Atmospheric Administration (NOAA)"
            ),

        "geojson":
            str(
                GEOJSON_OUTPUT
            ).replace(
                "\\",
                "/"
            ),

        "feature_count":
            int(
                len(
                    frame
                )
            ),

        "categories":
            category_counts,

        "colors": {

            f"D{category}":
                color

            for (
                category,
                color
            ) in DROUGHT_COLORS.items()

        },

        "category_names": {

            f"D{category}":
                name

            for (
                category,
                name
            ) in DROUGHT_NAMES.items()

        },

        "extent": {

            "west":
                float(
                    bounds[0]
                ),

            "south":
                float(
                    bounds[1]
                ),

            "east":
                float(
                    bounds[2]
                ),

            "north":
                float(
                    bounds[3]
                )

        }

    }


    temporary_output = (

        OUTPUT_DIR
        /
        "latest.json.tmp"

    )


    with open(

        temporary_output,

        "w",

        encoding=
            "utf-8"

    ) as file:

        json.dump(

            manifest,

            file,

            indent=
                2,

            ensure_ascii=False,

            allow_nan=False

        )


    os.replace(

        temporary_output,

        MANIFEST_OUTPUT

    )


    print()
    print("=" * 70)
    print("DROUGHT MANIFEST SAVED")
    print("=" * 70)


    print(
        MANIFEST_OUTPUT
    )


# ============================================================
# PRINT SUMMARY
# ============================================================

def print_summary(
    frame,
    valid_date
):

    print()
    print("=" * 70)
    print("U.S. DROUGHT MONITOR SUMMARY")
    print("=" * 70)


    if (
        valid_date
    ):

        print(
            f"Valid date: "
            f"{valid_date}"
        )


    else:

        print(
            "Valid date: "
            "not detected from archive filename"
        )


    print()


    for category in range(
        5
    ):

        count = int(

            (
                frame[
                    "dm_int"
                ]
                ==
                category
            ).sum()

        )


        print(

            f"D{category} "
            f"{DROUGHT_NAMES[category]}: "
            f"{count} feature(s)"

        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("NWS NORTH PLATTE")
    print("U.S. DROUGHT MONITOR UPDATE")
    print("=" * 70)


    # ========================================================
    # DOWNLOAD
    # ========================================================

    zip_bytes = (
        download_current_usdm()
    )


    # ========================================================
    # TEMP DIRECTORY
    # ========================================================

    with tempfile.TemporaryDirectory() as temp_directory:

        temp_path = Path(
            temp_directory
        )


        # ====================================================
        # EXTRACT
        # ====================================================

        filenames = extract_usdm_zip(

            zip_bytes,
            temp_path

        )


        # ====================================================
        # VALID DATE
        # ====================================================

        valid_date = (
            detect_valid_date(
                filenames
            )
        )


        if (
            valid_date
        ):

            print()
            print(
                f"Detected valid date: "
                f"{valid_date}"
            )


        # ====================================================
        # FIND SHAPEFILE
        # ====================================================

        shapefile = (
            find_shapefile(
                temp_path
            )
        )


        # ====================================================
        # PROCESS
        # ====================================================

        frame = (
            prepare_drought_data(
                shapefile
            )
        )


        # ====================================================
        # WRITE GEOJSON
        # ====================================================

        write_geojson(
            frame
        )


        # ====================================================
        # WRITE MANIFEST
        # ====================================================

        write_manifest(

            frame,
            valid_date

        )


        # ====================================================
        # SUMMARY
        # ====================================================

        print_summary(

            frame,
            valid_date

        )


    print()
    print("=" * 70)
    print("DROUGHT UPDATE COMPLETE")
    print("=" * 70)


    print()
    print(
        "Generated files:"
    )

    print(
        f"  {GEOJSON_OUTPUT}"
    )

    print(
        f"  {MANIFEST_OUTPUT}"
    )


# ============================================================
# RUN
# ============================================================

if (
    __name__
    ==
    "__main__"
):

    try:

        main()


    except Exception as error:

        print()
        print("=" * 70)
        print("DROUGHT UPDATE FAILED")
        print("=" * 70)

        print(
            error
        )


        sys.exit(
            1
        )
