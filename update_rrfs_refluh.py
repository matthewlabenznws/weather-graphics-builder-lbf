# ============================================================
# RRFS COMPOSITE REFLECTIVITY + 2-5 KM UH >= 75
#
# RRFS input from NOAA/NCEP NOMADS parallel feed
# Progressive publishing to AWS S3
#
# Output:
#
# s3://mtl-nwslbf-model-data/
# weather-graphics/rrfs/reflUH/latest/
#
#     manifest.json
#     f000.png
#     f001.png
#     ...
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import gzip
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import warnings

from datetime import (
    datetime,
    timedelta,
    timezone
)

from pathlib import Path

import boto3
import numpy as np
import requests
import xarray as xr

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import cartopy.crs as ccrs

from matplotlib.colors import (
    LinearSegmentedColormap,
    Normalize
)

from scipy.ndimage import (
    zoom,
    gaussian_filter
)
from scipy.spatial import cKDTree


warnings.filterwarnings("ignore")


# ============================================================
# AWS OUTPUT SETTINGS
# ============================================================

OUTPUT_AWS_REGION = "us-east-2"

OUTPUT_BUCKET = (
    "mtl-nwslbf-model-data"
)

OUTPUT_PREFIX = (
    "weather-graphics/"
    "rrfs/"
    "reflUH/"
    "latest"
)


output_s3 = boto3.client(
    "s3",
    region_name=OUTPUT_AWS_REGION
)


# ============================================================
# NOAA/NCEP RRFS PARALLEL NOMADS INPUT
#
# Current deterministic CONUS files are published as:
#
# rrfs.YYYYMMDD/CC/
# rrfs.tCCz.2dfld.3km.fFFF.conus.grib2
# ============================================================

RRFS_NOMADS_BASE = (
    "https://nomads.ncep.noaa.gov/"
    "pub/data/nccf/com/rrfs/para"
)


RRFS_SESSION = requests.Session()

RRFS_SESSION.headers.update({
    "User-Agent":
        "NWS-LBF-RRFS-Graphics/1.0"
})


HTTP_CONNECT_TIMEOUT = 20
HTTP_READ_TIMEOUT = 180


# ============================================================
# MAP DOMAIN
#
# Same geographic bounds as HRRR PNG so switching models
# does not move/resize the image overlay in Mapbox.
# ============================================================

WEST = -105.5
EAST = -96.0
SOUTH = 38.5
NORTH = 44.5



# ============================================================
# SAMPLING GRID SETTINGS
#
# The browser samples a lightweight regular lat/lon grid
# generated from the native model fields.
#
# 0.03 degree spacing is roughly 2-3 km across this domain.
# ============================================================

SAMPLE_DX = 0.03
SAMPLE_DY = 0.03
SAMPLE_BUFFER_DEG = 0.25

# Cache the nearest-native-point mapping because the RRFS grid
# geometry is unchanged from one forecast hour to the next.
SAMPLE_MAPPING_CACHE = None

# ============================================================
# REFLECTIVITY
# ============================================================

MIN_REFL = 10.0

UPSCALE = 4

SMOOTH_SIGMA = 0.4


# ============================================================
# UH
# ============================================================

UH_THRESHOLD = 75.0

UH_FILL_ALPHA = 0.45


# ============================================================
# IMAGE
# ============================================================

FIG_WIDTH = 16

FIG_HEIGHT = 10

DPI = 150


# ============================================================
# RUN SETTINGS
# ============================================================

# Search backward this many hours for a valid RRFS CONUS run.
MAX_RUN_LOOKBACK = 12

# Retries per forecast hour.
DOWNLOAD_ATTEMPTS = 3
RETRY_SLEEP_SECONDS = 10


# ============================================================
# LOCAL OUTPUT
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)


OUTPUT_DIR = (

    BASE_DIR

    / "output"

    / "rrfs"

    / "reflUH"

    / "latest"

)


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


TEMP_DIR = (

    BASE_DIR

    / "output"

    / "rrfs"

    / "temp"

)


TEMP_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# RADARSCOPE-STYLE REFLECTIVITY COLOR TABLE
# ============================================================

REFL_POINTS = [

    (-15.00, (0, 0, 0)),

    (5.00, (29, 37, 60)),

    (17.50, (89, 155, 171)),

    (22.50, (33, 186, 72)),

    (32.50, (5, 101, 1)),


    # Yellow

    (37.49, (251, 252, 0)),

    (37.50, (199, 176, 0)),


    # Orange

    (42.49, (253, 149, 2)),

    (42.50, (172, 92, 2)),


    # Red

    (49.99, (253, 38, 0)),

    (50.00, (135, 43, 22)),


    # Pink

    (59.99, (193, 148, 179)),

    (60.00, (200, 23, 119)),


    # Purple

    (69.99, (165, 2, 215)),

    (70.00, (64, 0, 146)),


    # Cyan

    (74.99, (135, 255, 253)),

    (75.00, (54, 120, 142)),


    # Extreme

    (80.00, (173, 99, 64)),

    (85.00, (105, 0, 4)),

    (95.00, (0, 0, 0))

]


COLOR_MIN = -15.0

COLOR_MAX = 95.0


# ============================================================
# BUILD REFLECTIVITY COLORMAP
# ============================================================

def build_refl_colormap():

    cmap_points = []


    for value, rgb in REFL_POINTS:

        position = (

            (value - COLOR_MIN)

            /

            (COLOR_MAX - COLOR_MIN)

        )


        color = (

            rgb[0] / 255.0,

            rgb[1] / 255.0,

            rgb[2] / 255.0

        )


        cmap_points.append(
            (
                position,
                color
            )
        )


    cmap = (
        LinearSegmentedColormap
        .from_list(
            "radarscope_br",
            cmap_points,
            N=2048
        )
    )


    norm = Normalize(

        vmin=COLOR_MIN,

        vmax=COLOR_MAX

    )


    levels = np.arange(

        MIN_REFL,

        96,

        1.0

    )


    return (
        cmap,
        norm,
        levels
    )


(
    REFL_CMAP,
    REFL_NORM,
    REFL_LEVELS

) = build_refl_colormap()


# ============================================================
# BUILD RRFS RUN DIRECTORY URL
#
# Example:
# https://nomads.ncep.noaa.gov/pub/data/nccf/com/rrfs/para/
# rrfs.20260817/15/
# ============================================================

def make_run_url(
    run_time
):

    date_string = (
        run_time.strftime(
            "%Y%m%d"
        )
    )


    cycle = (
        run_time.strftime(
            "%H"
        )
    )


    return (
        f"{RRFS_NOMADS_BASE}/"
        f"rrfs.{date_string}/"
        f"{cycle}/"
    )


# ============================================================
# BUILD RRFS CONUS 2-D FILENAME
#
# Current NOMADS parallel naming:
# rrfs.tCCz.2dfld.3km.fFFF.conus.grib2
# ============================================================

def make_2dfld_filename(
    run_time,
    fhr
):

    cycle = (
        run_time.strftime(
            "%H"
        )
    )


    return (
        f"rrfs.t{cycle}z."
        f"2dfld.3km."
        f"f{fhr:03d}."
        f"conus.grib2"
    )


# ============================================================
# BUILD RRFS GRIB URL
# ============================================================

def make_grib_url(
    run_time,
    fhr
):

    return (
        make_run_url(
            run_time
        )
        +
        make_2dfld_filename(
            run_time,
            fhr
        )
    )


# ============================================================
# HTTP GET
# ============================================================

def http_get(
    url,
    headers=None
):

    response = RRFS_SESSION.get(
        url,
        headers=headers,
        timeout=(
            HTTP_CONNECT_TIMEOUT,
            HTTP_READ_TIMEOUT
        )
    )


    response.raise_for_status()


    return response


# ============================================================
# CHECK URL EXISTS
#
# Use a one-byte range GET rather than HEAD because NOMADS
# HTTP behavior is more consistent for GET requests.
# ============================================================

def url_exists(
    url
):

    try:

        response = RRFS_SESSION.get(
            url,
            headers={
                "Range":
                    "bytes=0-0"
            },
            timeout=(
                HTTP_CONNECT_TIMEOUT,
                30
            )
        )


        return (
            response.status_code
            in
            (
                200,
                206
            )
        )


    except requests.RequestException:

        return False


# ============================================================
# FIND LATEST RRFS CONUS RUN
# ============================================================

def find_latest_rrfs():

    now = (
        datetime
        .now(
            timezone.utc
        )
    )


    start = (
        now.replace(
            minute=0,
            second=0,
            microsecond=0
        )
    )


    print("=" * 70)

    print(
        "SEARCHING FOR LATEST RRFS PARALLEL CONUS CYCLE"
    )

    print("=" * 70)


    for back in range(
        MAX_RUN_LOOKBACK + 1
    ):

        run_time = (
            start
            -
            timedelta(
                hours=back
            )
        )


        grib_url = (
            make_grib_url(
                run_time,
                0
            )
        )


        idx_url = (
            grib_url
            +
            ".idx"
        )


        print(
            f"Checking RRFS "
            f"{run_time:%Y%m%d %HZ}...",
            flush=True
        )


        if not url_exists(
            idx_url
        ):

            continue


        print()

        print(
            "FOUND RRFS CONUS RUN:"
        )

        print(
            f"Run:  "
            f"{run_time:%Y-%m-%d %HZ}"
        )

        print(
            f"URL:  "
            f"{make_run_url(run_time)}"
        )


        return run_time


    raise RuntimeError(
        "Could not find a recent RRFS CONUS run on NOMADS."
    )


# ============================================================
# DISCOVER AVAILABLE FORECAST HOURS
#
# Read the NOMADS directory listing instead of hard-coding
# F018/F060/F084. This lets the script work while a cycle is
# still being published.
# ============================================================

def discover_forecast_hours(
    run_time
):

    run_url = (
        make_run_url(
            run_time
        )
    )


    print()

    print(
        "Discovering available RRFS CONUS forecast hours..."
    )


    response = http_get(
        run_url
    )


    html = (
        response.text
    )


    cycle = (
        run_time.strftime(
            "%H"
        )
    )


    pattern = re.compile(
        rf"rrfs\.t{cycle}z\."
        rf"2dfld\.3km\."
        rf"f(\d{{3}})\."
        rf"conus\.grib2"
    )


    hours = sorted({
        int(match)
        for match in pattern.findall(
            html
        )
    })


    if not hours:

        raise RuntimeError(
            "No RRFS CONUS 2-D forecast hours found in NOMADS directory."
        )


    print(
        f"Available CONUS forecast hours: "
        f"F{hours[0]:03d}-F{hours[-1]:03d}"
    )

    print(
        f"Total available hours: "
        f"{len(hours)}"
    )


    return hours


# ============================================================
# DOWNLOAD TEXT
# ============================================================

def download_text(
    url
):

    response = http_get(
        url
    )


    return response.text


# ============================================================
# READ GRIB INDEX
# ============================================================

def get_idx_text(
    grib_url
):

    idx_url = (
        grib_url
        +
        ".idx"
    )


    print(
        "Index:",
        idx_url
    )


    return (
        download_text(
            idx_url
        )
    )


# ============================================================
# PARSE .IDX FILE
# ============================================================

def parse_idx(
    idx_text
):

    records = []


    for line in (
        idx_text
        .splitlines()
    ):

        line = (
            line.strip()
        )


        if not line:

            continue


        pieces = (
            line.split(
                ":"
            )
        )


        if (
            len(pieces) < 5
        ):

            continue


        try:

            message_number = (
                int(
                    pieces[0]
                )
            )


            start_byte = (
                int(
                    pieces[1]
                )
            )


        except ValueError:

            continue


        records.append({

            "message":
                message_number,

            "start":
                start_byte,

            "line":
                line

        })


    # Add ending byte

    for index in range(
        len(records)
    ):

        if (
            index + 1
            <
            len(records)
        ):

            records[index][
                "end"
            ] = (

                records[
                    index + 1
                ][
                    "start"
                ]

                -

                1

            )


        else:

            records[index][
                "end"
            ] = None


    return records


# ============================================================
# FIND REFLECTIVITY RECORD
# ============================================================

def find_reflectivity_record(
    records
):

    candidates = []


    for record in records:

        text = (
            record[
                "line"
            ]
            .upper()
        )


        # Composite reflectivity

        if (
            ":REFC:"
            in text
        ):

            candidates.append(
                record
            )


    if candidates:

        return (
            candidates[0]
        )


    raise RuntimeError(
        "REFC not found in RRFS index."
    )


# ============================================================
# FIND 2-5 KM MAX UH
# ============================================================

def find_uh_record(
    records
):

    candidates = []


    for record in records:

        text = (
            record[
                "line"
            ]
            .upper()
        )


        if (
            ":MXUPHL:"
            not in text
        ):

            continue


        # Explicit 5-2 km layer

        if (
            "5000-2000 M"
            in text
            or
            "5000-2000 M ABOVE GROUND"
            in text
        ):

            return record


        candidates.append(
            record
        )


    # If format changed but only one max-UH exists,
    # use first MXUPHL candidate.

    if candidates:

        print(
            "WARNING: exact 2-5 km text "
            "not found; using first MXUPHL."
        )

        return (
            candidates[0]
        )


    raise RuntimeError(
        "MXUPHL not found in RRFS index."
    )


# ============================================================
# DOWNLOAD BYTE RANGE FROM NOMADS
# ============================================================

def download_range(
    grib_url,
    record
):

    start_byte = (
        record[
            "start"
        ]
    )


    end_byte = (
        record[
            "end"
        ]
    )


    if end_byte is None:

        range_header = (
            f"bytes={start_byte}-"
        )

    else:

        range_header = (
            f"bytes="
            f"{start_byte}-"
            f"{end_byte}"
        )


    print(
        "Range:",
        range_header
    )


    response = http_get(
        grib_url,
        headers={
            "Range":
                range_header
        }
    )


    data = (
        response.content
    )


    if not data:

        raise RuntimeError(
            "NOMADS returned an empty GRIB byte range."
        )


    # Every selected GRIB message should begin with GRIB.
    if data[:4] != b"GRIB":

        raise RuntimeError(
            "Downloaded byte range does not begin with GRIB."
        )


    return data


# ============================================================
# WRITE FIELD GRIB
# ============================================================

def download_field_grib(
    grib_url,
    record,
    destination
):

    data = (
        download_range(
            grib_url,
            record
        )
    )


    with open(
        destination,
        "wb"
    ) as file:

        file.write(
            data
        )


# ============================================================
# OPEN SINGLE GRIB FIELD
# ============================================================

def open_grib_field(
    filename
):

    # Each temporary file contains just one GRIB message,
    # which avoids cfgrib conflicts.

    ds = xr.open_dataset(

        filename,

        engine="cfgrib",

        backend_kwargs={

            "indexpath":
                "",

            "errors":
                "ignore"

        }

    )


    return ds


# ============================================================
# GET FIRST 2-D VARIABLE
# ============================================================

def get_2d_variable(
    ds
):

    for name in (
        ds.data_vars
    ):

        field = (
            ds[name]
        )


        if (
            field.ndim >= 2
        ):

            return field


    raise RuntimeError(
        "No 2-D variable found."
    )


# ============================================================
# GET LAT / LON
# ============================================================

def get_lat_lon(
    ds
):

    # Common names

    possible_lat = [

        "latitude",

        "lat"

    ]


    possible_lon = [

        "longitude",

        "lon"

    ]


    lat = None

    lon = None


    for name in possible_lat:

        if name in ds:

            lat = (
                ds[name]
                .values
            )

            break


    for name in possible_lon:

        if name in ds:

            lon = (
                ds[name]
                .values
            )

            break


    if (
        lat is None
        or
        lon is None
    ):

        raise RuntimeError(
            "Could not find RRFS lat/lon coordinates."
        )


    # Some GRIB decoders return longitude 0-360.

    lon = np.where(

        lon > 180,

        lon - 360,

        lon

    )


    return (
        lon,
        lat
    )


# ============================================================
# LOAD ONE RRFS FORECAST HOUR
# ============================================================

def load_hour(
    run_time,
    fhr
):

    print()

    print("=" * 70)

    print(
        f"RRFS "
        f"{run_time:%Y%m%d %HZ} "
        f"F{fhr:03d}"
    )

    print("=" * 70)


    grib_url = (
        make_grib_url(
            run_time,
            fhr
        )
    )


    last_error = None


    for attempt in range(
        1,
        DOWNLOAD_ATTEMPTS + 1
    ):

        ds_refl = None
        ds_uh = None

        try:

            print(
                f"Attempt "
                f"{attempt}/"
                f"{DOWNLOAD_ATTEMPTS}"
            )

            print(
                "GRIB:",
                grib_url
            )


            # =================================================
            # INVENTORY
            # =================================================

            idx_text = (
                get_idx_text(
                    grib_url
                )
            )


            records = (
                parse_idx(
                    idx_text
                )
            )


            if not records:

                raise RuntimeError(
                    "RRFS index contains no readable records."
                )


            refl_record = (
                find_reflectivity_record(
                    records
                )
            )


            print(
                "REFC:",
                refl_record["line"]
            )


            # =================================================
            # REFLECTIVITY TEMP FILE
            # =================================================

            refl_file = (
                TEMP_DIR
                /
                f"rrfs_refl_"
                f"f{fhr:03d}.grib2"
            )


            download_field_grib(
                grib_url,
                refl_record,
                refl_file
            )


            ds_refl = (
                open_grib_field(
                    refl_file
                )
            )


            refl_da = (
                get_2d_variable(
                    ds_refl
                )
            )


            refl = np.squeeze(
                refl_da.values
            ).astype(
                float
            )


            (
                lon,
                lat
            ) = get_lat_lon(
                ds_refl
            )


            # =================================================
            # UH
            # =================================================

            try:

                uh_record = (
                    find_uh_record(
                        records
                    )
                )


                print(
                    "UH:",
                    uh_record["line"]
                )


                uh_file = (
                    TEMP_DIR
                    /
                    f"rrfs_uh_"
                    f"f{fhr:03d}.grib2"
                )


                download_field_grib(
                    grib_url,
                    uh_record,
                    uh_file
                )


                ds_uh = (
                    open_grib_field(
                        uh_file
                    )
                )


                uh_da = (
                    get_2d_variable(
                        ds_uh
                    )
                )


                uh = np.squeeze(
                    uh_da.values
                ).astype(
                    float
                )


            except Exception as uh_error:

                print(
                    "UH unavailable:"
                )

                print(
                    uh_error
                )


                uh = np.zeros_like(
                    refl
                )


            print(
                f"Reflectivity max: "
                f"{np.nanmax(refl):.1f} dBZ"
            )

            print(
                f"UH max: "
                f"{np.nanmax(uh):.1f}"
            )


            # =================================================
            # CLOSE DATASETS BEFORE CLEANING FILES
            # =================================================

            try:

                if ds_refl is not None:
                    ds_refl.close()

            except Exception:

                pass


            try:

                if ds_uh is not None:
                    ds_uh.close()

            except Exception:

                pass


            # =================================================
            # CLEAN TEMP FILES
            # =================================================

            for temp_file in (
                TEMP_DIR.glob(
                    f"*f{fhr:03d}.grib2*"
                )
            ):

                try:

                    temp_file.unlink()

                except Exception:

                    pass


            return (
                lon,
                lat,
                refl,
                uh
            )


        except Exception as error:

            last_error = error


            print(
                f"Attempt failed: "
                f"{error}"
            )


            try:

                if ds_refl is not None:
                    ds_refl.close()

            except Exception:

                pass


            try:

                if ds_uh is not None:
                    ds_uh.close()

            except Exception:

                pass


            for temp_file in (
                TEMP_DIR.glob(
                    f"*f{fhr:03d}.grib2*"
                )
            ):

                try:

                    temp_file.unlink()

                except Exception:

                    pass


            if (
                attempt
                <
                DOWNLOAD_ATTEMPTS
            ):

                time.sleep(
                    RETRY_SLEEP_SECONDS
                )


    raise RuntimeError(
        f"F{fhr:03d} failed: "
        f"{last_error}"
    )


# ============================================================
# PROCESS REFLECTIVITY
# ============================================================

def process_reflectivity(
    lon,
    lat,
    refl
):

    original_min = (
        np.nanmin(
            refl
        )
    )


    original_max = (
        np.nanmax(
            refl
        )
    )


    refl_clean = np.where(

        np.isfinite(
            refl
        ),

        refl,

        -20.0

    )


    # ========================================================
    # 4X CUBIC INTERPOLATION
    # ========================================================

    refl_fine = zoom(

        refl_clean,

        UPSCALE,

        order=3

    )


    lon_fine = zoom(

        lon,

        UPSCALE,

        order=3

    )


    lat_fine = zoom(

        lat,

        UPSCALE,

        order=3

    )


    # Prevent cubic overshoot

    refl_fine = np.clip(

        refl_fine,

        original_min,

        original_max

    )


    # ========================================================
    # LIGHT SMOOTHING
    # ========================================================

    refl_fine = gaussian_filter(

        refl_fine,

        sigma=
            SMOOTH_SIGMA

    )


    refl_fine = np.clip(

        refl_fine,

        original_min,

        original_max

    )


    # ========================================================
    # MASK BELOW 10 DBZ
    # ========================================================

    refl_plot = (
        np.ma.masked_where(

            refl_fine
            <
            MIN_REFL,

            refl_fine

        )
    )


    return (
        lon_fine,
        lat_fine,
        refl_plot
    )


# ============================================================
# PROCESS UH
# ============================================================

def process_uh(
    lon,
    lat,
    uh
):

    uh_clean = np.where(

        np.isfinite(
            uh
        ),

        uh,

        0.0

    )


    # Linear interpolation avoids cubic overshoot
    # around the 75 threshold.

    uh_fine = zoom(

        uh_clean,

        UPSCALE,

        order=1

    )


    lon_fine = zoom(

        lon,

        UPSCALE,

        order=1

    )


    lat_fine = zoom(

        lat,

        UPSCALE,

        order=1

    )


    return (
        lon_fine,
        lat_fine,
        uh_fine
    )


# ============================================================
# PLOT ONE FORECAST HOUR
# ============================================================

def plot_hour(
    run_time,
    fhr,
    lon,
    lat,
    refl,
    uh
):

    output_file = (

        OUTPUT_DIR

        /

        f"f{fhr:03d}.png"

    )


    (
        lon_refl,
        lat_refl,
        refl_plot

    ) = process_reflectivity(

        lon,
        lat,
        refl

    )


    (
        lon_uh,
        lat_uh,
        uh_fine

    ) = process_uh(

        lon,
        lat,
        uh

    )


    # ========================================================
    # FIGURE
    # ========================================================

    fig = plt.figure(

        figsize=(

            FIG_WIDTH,

            FIG_HEIGHT

        ),

        dpi=DPI,

        facecolor="none"

    )


    ax = fig.add_axes(

        [
            0,
            0,
            1,
            1
        ],

        projection=
            ccrs.PlateCarree()

    )


    fig.patch.set_alpha(
        0
    )


    ax.patch.set_alpha(
        0
    )


    ax.set_extent(

        [
            WEST,
            EAST,
            SOUTH,
            NORTH
        ],

        crs=
            ccrs.PlateCarree()

    )


    # ========================================================
    # REFLECTIVITY
    # ========================================================

    ax.contourf(

        lon_refl,

        lat_refl,

        refl_plot,

        levels=
            REFL_LEVELS,

        cmap=
            REFL_CMAP,

        norm=
            REFL_NORM,

        extend=
            "max",

        transform=
            ccrs.PlateCarree(),

        antialiased=
            True,

        zorder=
            1

    )


    # ========================================================
    # 2-5 KM UH >= 75
    # ========================================================

    uh_max = (
        np.nanmax(
            uh_fine
        )
    )


    if (
        uh_max
        >=
        UH_THRESHOLD
    ):

        # ----------------------------------------------------
        # SEMI-TRANSPARENT BLACK FILL
        # ----------------------------------------------------

        ax.contourf(

            lon_uh,

            lat_uh,

            uh_fine,

            levels=[

                UH_THRESHOLD,

                max(
                    1000.0,
                    uh_max + 1.0
                )

            ],

            colors=[
                "#000000"
            ],

            alpha=
                UH_FILL_ALPHA,

            transform=
                ccrs.PlateCarree(),

            antialiased=
                True,

            zorder=
                5

        )


        # ----------------------------------------------------
        # BLACK OUTLINE
        # ----------------------------------------------------

        ax.contour(

            lon_uh,

            lat_uh,

            uh_fine,

            levels=[
                UH_THRESHOLD
            ],

            colors=[
                "#000000"
            ],

            linewidths=
                1.5,

            transform=
                ccrs.PlateCarree(),

            zorder=
                6

        )


    ax.set_axis_off()


    # ========================================================
    # SAVE TRANSPARENT PNG
    # ========================================================

    plt.savefig(

        output_file,

        dpi=DPI,

        transparent=True,

        facecolor="none",

        edgecolor="none",

        bbox_inches=None,

        pad_inches=0

    )


    plt.close(
        fig
    )


    valid_time = (

        run_time

        +

        timedelta(
            hours=fhr
        )

    )


    frame_info = {

        "fhr":
            fhr,

        "file":
            f"f{fhr:03d}.png",

        "valid":
            valid_time.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

    }


    print(
        f"Created "
        f"{output_file.name}"
    )


    return (
        output_file,
        frame_info
    )


# ============================================================
# UPLOAD FRAME TO YOUR S3
# ============================================================

def upload_frame(
    output_file,
    fhr
):

    key = (

        f"{OUTPUT_PREFIX}/"

        f"f{fhr:03d}.png"

    )


    output_s3.upload_file(

        str(
            output_file
        ),

        OUTPUT_BUCKET,

        key,

        ExtraArgs={

            "ContentType":
                "image/png",

            "CacheControl":
                "no-cache, no-store, must-revalidate"

        }

    )


    print(

        f"Uploaded "
        f"F{fhr:03d} to S3."

    )




# ============================================================
# BUILD / CACHE SAMPLING MAPPING
# ============================================================

def get_sample_mapping(lon, lat):
    global SAMPLE_MAPPING_CACHE

    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)

    # Normalize longitudes to -180..180.
    lon = np.where(lon > 180.0, lon - 360.0, lon)

    # Reuse the mapping after the first hour because the model
    # grid geometry is fixed within a run.
    if SAMPLE_MAPPING_CACHE is not None:
        if SAMPLE_MAPPING_CACHE["native_shape"] == lon.shape:
            return SAMPLE_MAPPING_CACHE

    native_mask = (
        np.isfinite(lon)
        & np.isfinite(lat)
        & (lon >= WEST - SAMPLE_BUFFER_DEG)
        & (lon <= EAST + SAMPLE_BUFFER_DEG)
        & (lat >= SOUTH - SAMPLE_BUFFER_DEG)
        & (lat <= NORTH + SAMPLE_BUFFER_DEG)
    )

    flat_mask = native_mask.ravel()

    native_lon = lon.ravel()[flat_mask]
    native_lat = lat.ravel()[flat_mask]

    if native_lon.size == 0:
        raise RuntimeError(
            "No native model points found inside sampling domain."
        )

    sample_lons = np.arange(
        WEST,
        EAST + SAMPLE_DX / 2.0,
        SAMPLE_DX,
        dtype=float
    )

    sample_lats = np.arange(
        SOUTH,
        NORTH + SAMPLE_DY / 2.0,
        SAMPLE_DY,
        dtype=float
    )

    sample_lon_2d, sample_lat_2d = np.meshgrid(
        sample_lons,
        sample_lats
    )

    native_points = np.column_stack(
        (native_lon, native_lat)
    )

    sample_points = np.column_stack(
        (
            sample_lon_2d.ravel(),
            sample_lat_2d.ravel()
        )
    )

    print(
        "Building sampling nearest-neighbor mapping..."
    )

    tree = cKDTree(native_points)

    _, nearest_index = tree.query(
        sample_points,
        k=1
    )

    SAMPLE_MAPPING_CACHE = {
        "native_shape": lon.shape,
        "flat_mask": flat_mask,
        "nearest_index": nearest_index,
        "sample_lons": sample_lons,
        "sample_lats": sample_lats
    }

    return SAMPLE_MAPPING_CACHE


# ============================================================
# BUILD SAMPLING DATA
# ============================================================

def build_sample_grid(lon, lat, refl, uh):
    mapping = get_sample_mapping(
        lon,
        lat
    )

    refl = np.asarray(refl, dtype=float)
    uh = np.asarray(uh, dtype=float)

    if refl.shape != mapping["native_shape"]:
        raise RuntimeError(
            "Reflectivity shape does not match sampling grid."
        )

    if uh.shape != mapping["native_shape"]:
        raise RuntimeError(
            "UH shape does not match sampling grid."
        )

    flat_mask = mapping["flat_mask"]
    nearest_index = mapping["nearest_index"]

    native_refl = refl.ravel()[flat_mask]
    native_uh = uh.ravel()[flat_mask]

    sample_refl = native_refl[nearest_index]
    sample_uh = native_uh[nearest_index]

    sample_refl = np.where(
        np.isfinite(sample_refl),
        sample_refl,
        -9999.0
    )

    sample_uh = np.where(
        np.isfinite(sample_uh),
        sample_uh,
        -9999.0
    )

    sample_refl = np.round(
        sample_refl,
        1
    )

    sample_uh = np.round(
        sample_uh,
        1
    )

    sample_lons = mapping["sample_lons"]
    sample_lats = mapping["sample_lats"]

    return {
        "west": float(sample_lons[0]),
        "east": float(sample_lons[-1]),
        "south": float(sample_lats[0]),
        "north": float(sample_lats[-1]),
        "dx": float(SAMPLE_DX),
        "dy": float(SAMPLE_DY),
        "nx": int(sample_lons.size),
        "ny": int(sample_lats.size),
        "missing": -9999.0,
        "refl": sample_refl.astype(np.float32).tolist(),
        "uh": sample_uh.astype(np.float32).tolist()
    }


# ============================================================
# WRITE + UPLOAD SAMPLING DATA
# ============================================================

def publish_sample_grid(
    fhr,
    lon,
    lat,
    refl,
    uh
):
    print(
        f"Building sampling data for F{fhr:03d}..."
    )

    sample_data = build_sample_grid(
        lon,
        lat,
        refl,
        uh
    )

    filename = (
        f"f{fhr:03d}_sample.json.gz"
    )

    local_file = (
        OUTPUT_DIR
        / filename
    )

    with gzip.open(
        local_file,
        "wt",
        encoding="utf-8",
        compresslevel=6
    ) as f:
        json.dump(
            sample_data,
            f,
            separators=(",", ":")
        )

    key = (
        f"{OUTPUT_PREFIX}/"
        f"{filename}"
    )

    output_s3.upload_file(
        str(local_file),
        OUTPUT_BUCKET,
        key,
        ExtraArgs={
            "ContentType": "application/json",
            "ContentEncoding": "gzip",
            "CacheControl":
                "no-cache, no-store, must-revalidate"
        }
    )

    print(
        f"Uploaded sampling data: "
        f"s3://{OUTPUT_BUCKET}/{key}"
    )

    return filename

# ============================================================
# MANIFEST
# ============================================================

def build_manifest(
    run_time,
    max_fhr,
    hours,
    status
):

    return {

        "model":
            "RRFS",

        "product":
            "reflUH",

        "description":
            (
                "Composite Reflectivity + "
                "2-5 km UH >= 75"
            ),

        "run":
            run_time.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),

        "cycle":
            run_time.strftime(
                "%HZ"
            ),

        "max_fhr":
            max_fhr,

        "reflectivity_min_dbz":
            MIN_REFL,

        "uh_threshold":
            UH_THRESHOLD,

        "status":
            status,

        "bounds": {

            "west":
                WEST,

            "east":
                EAST,

            "south":
                SOUTH,

            "north":
                NORTH

        },

        "hours":
            hours

    }


# ============================================================
# PUBLISH MANIFEST
# ============================================================

def publish_manifest(
    run_time,
    max_fhr,
    hours,
    status
):

    manifest = (
        build_manifest(

            run_time,

            max_fhr,

            hours,

            status

        )
    )


    manifest_file = (

        OUTPUT_DIR

        /

        "manifest.json"

    )


    with manifest_file.open(

        "w",

        encoding=
            "utf-8"

    ) as file:

        json.dump(

            manifest,

            file,

            indent=2

        )


    output_s3.upload_file(

        str(
            manifest_file
        ),

        OUTPUT_BUCKET,

        (
            f"{OUTPUT_PREFIX}/"
            f"manifest.json"
        ),

        ExtraArgs={

            "ContentType":
                "application/json",

            "CacheControl":
                "no-cache, no-store, must-revalidate"

        }

    )


    print(

        f"Manifest published: "
        f"{len(hours)} hours, "
        f"status={status}"

    )


# ============================================================
# CLEAN LOCAL OUTPUT
# ============================================================

def clean_local_output():

    for file in OUTPUT_DIR.glob(
        "f*.png"
    ):

        try:

            file.unlink()

        except Exception:

            pass


    for file in OUTPUT_DIR.glob(
        "f*_sample.json.gz"
    ):

        try:

            file.unlink()

        except Exception:

            pass


    manifest = (

        OUTPUT_DIR

        /

        "manifest.json"

    )


    if manifest.exists():

        manifest.unlink()


    if TEMP_DIR.exists():

        shutil.rmtree(
            TEMP_DIR
        )


    TEMP_DIR.mkdir(

        parents=True,

        exist_ok=True

    )


# ============================================================
# CLEAR PREVIOUS RRFS LATEST S3 DATA
# ============================================================

def clear_old_s3_frames():

    print()

    print(
        "Clearing previous RRFS latest frames..."
    )


    paginator = (
        output_s3
        .get_paginator(
            "list_objects_v2"
        )
    )


    objects = []


    for page in paginator.paginate(

        Bucket=
            OUTPUT_BUCKET,

        Prefix=
            f"{OUTPUT_PREFIX}/"

    ):

        for obj in page.get(
            "Contents",
            []
        ):

            key = (
                obj["Key"]
            )


            if (

                key.endswith(
                    ".png"
                )

                or

                key.endswith(
                    "_sample.json.gz"
                )

                or

                key.endswith(
                    "manifest.json"
                )

            ):

                objects.append({

                    "Key":
                        key

                })


                if (
                    len(objects)
                    ==
                    1000
                ):

                    output_s3.delete_objects(

                        Bucket=
                            OUTPUT_BUCKET,

                        Delete={

                            "Objects":
                                objects

                        }

                    )


                    objects = []


    if objects:

        output_s3.delete_objects(

            Bucket=
                OUTPUT_BUCKET,

            Delete={

                "Objects":
                    objects

            }

        )


    print(
        "Previous RRFS frames cleared."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)

    print(
        "RRFS REFL + UH NOMADS PROGRESSIVE UPDATE"
    )

    print("=" * 70)


    # ========================================================
    # FIND LATEST RUN
    # ========================================================

    run_time = (
        find_latest_rrfs()
    )


    available_hours = (
        discover_forecast_hours(
            run_time
        )
    )


    max_fhr = (
        max(
            available_hours
        )
    )


    print()

    print(
        f"RRFS run: "
        f"{run_time:%Y-%m-%d %HZ}"
    )

    print(
        f"Forecast range currently available: "
        f"F{available_hours[0]:03d}-"
        f"F{available_hours[-1]:03d}"
    )


    # ========================================================
    # CLEAN CURRENT LATEST PRODUCT
    # ========================================================

    clean_local_output()

    clear_old_s3_frames()


    hours_written = []


    # ========================================================
    # EMPTY BUILDING MANIFEST
    # ========================================================

    publish_manifest(
        run_time,
        max_fhr,
        hours_written,
        status=
            "building"
    )


    # ========================================================
    # PROCESS FORECAST HOURS
    # ========================================================

    for fhr in available_hours:

        try:

            (
                lon,
                lat,
                refl,
                uh
            ) = load_hour(
                run_time,
                fhr
            )


            (
                output_file,
                frame_info
            ) = plot_hour(
                run_time,
                fhr,
                lon,
                lat,
                refl,
                uh
            )


            # =================================================
            # IMMEDIATE S3 UPLOAD
            # =================================================

            upload_frame(
                output_file,
                fhr
            )


            # =================================================
            # BUILD + UPLOAD SAMPLING DATA
            # =================================================

            sample_file = publish_sample_grid(
                fhr,
                lon,
                lat,
                refl,
                uh
            )


            frame_info[
                "sample_file"
            ] = sample_file


            # =================================================
            # ADD HOUR
            # =================================================

            hours_written.append(
                frame_info
            )


            # =================================================
            # IMMEDIATELY UPDATE MANIFEST
            # =================================================

            publish_manifest(
                run_time,
                max_fhr,
                hours_written,
                status=
                    "building"
            )


            print()

            print(
                f"F{fhr:03d} "
                f"is now available."
            )


        except Exception as error:

            print()

            print(
                f"Skipping "
                f"F{fhr:03d}: "
                f"{error}"
            )


    # ========================================================
    # FINAL MANIFEST
    # ========================================================

    publish_manifest(
        run_time,
        max_fhr,
        hours_written,
        status=
            "complete"
    )


    print()

    print("=" * 70)

    print(
        "RRFS UPDATE COMPLETE"
    )

    print(
        f"Frames published: "
        f"{len(hours_written)}"
    )

    print("=" * 70)


    # A successful GitHub Actions run with zero frames is not useful.
    # Fail explicitly so the workflow cannot appear green when the
    # data-download/field-processing side did not actually work.
    if not hours_written:

        raise RuntimeError(
            "RRFS update completed with ZERO published frames."
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
