# ============================================================
# RRFS COMPOSITE REFLECTIVITY + 2-5 KM UH >= 75
#
# RRFS INPUT:
# NOAA/NCEP RRFS Parallel NOMADS
#
# OUTPUT:
# Your existing AWS S3 bucket
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
#
# THIS IS YOUR OUTPUT BUCKET.
# KEEP THIS.
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
# NOAA RRFS PARALLEL NOMADS INPUT
# ============================================================

RRFS_NOMADS_BASE = (
    "https://nomads.ncep.noaa.gov/"
    "pub/data/nccf/com/rrfs/para"
)


# ============================================================
# HTTP SESSION
# ============================================================

RRFS_SESSION = requests.Session()

RRFS_SESSION.headers.update({

    "User-Agent":
        "NWS-LBF-RRFS-Graphics/1.0"

})


# ============================================================
# MAP DOMAIN
# ============================================================

WEST = -105.5
EAST = -96.0
SOUTH = 38.5
NORTH = 44.5


# ============================================================
# SAMPLING GRID SETTINGS
# ============================================================

SAMPLE_DX = 0.03
SAMPLE_DY = 0.03
SAMPLE_BUFFER_DEG = 0.25

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

MAX_RUN_LOOKBACK = 12

DOWNLOAD_ATTEMPTS = 3

RETRY_SLEEP_SECONDS = 10


# ============================================================
# NOMADS REQUEST SETTINGS
#
# NCEP asks automated users to pause between repeated requests.
# ============================================================

NOMADS_REQUEST_SLEEP_SECONDS = 1.0

HTTP_CONNECT_TIMEOUT = 20

HTTP_READ_TIMEOUT = 120


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
#
# .../para/rrfs.20260817/12/
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
# RRFS 2-D FILENAME
#
# Current parallel naming:
#
# rrfs.t12z.2dfld.2p5km.f000.pr.grib2
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

        f"2dfld.2p5km."

        f"f{fhr:03d}."

        f"pr.grib2"

    )


# ============================================================
# RRFS GRIB URL
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
# HTTP REQUEST
# ============================================================

def http_get(
    url,
    *,
    headers=None,
    stream=False
):

    response = RRFS_SESSION.get(

        url,

        headers=headers,

        stream=stream,

        timeout=(
            HTTP_CONNECT_TIMEOUT,
            HTTP_READ_TIMEOUT
        )

    )


    response.raise_for_status()


    return response


# ============================================================
# CHECK URL
# ============================================================

def url_exists(
    url
):

    try:

        response = RRFS_SESSION.head(

            url,

            allow_redirects=True,

            timeout=(
                HTTP_CONNECT_TIMEOUT,
                30
            )

        )


        if response.status_code == 200:

            return True


        # ----------------------------------------------------
        # Some HTTP servers do not handle HEAD exactly like GET.
        # Fall back to a one-byte GET.
        # ----------------------------------------------------

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
# FIND LATEST RRFS RUN
#
# We require F000 + F000.idx to exist.
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
        "SEARCHING FOR LATEST RRFS PARALLEL CYCLE"
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

            f"{run_time:%Y%m%d %HZ}..."

        )


        if not url_exists(
            idx_url
        ):

            continue


        if not url_exists(
            grib_url
        ):

            continue


        print()

        print(
            "FOUND RRFS:"
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

        "Could not find a recent RRFS "
        "parallel run on NOMADS."

    )


# ============================================================
# DISCOVER AVAILABLE FORECAST HOURS
#
# Instead of assuming F018/F060/etc., inspect the directory
# listing and use what NOMADS actually has.
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
        "Discovering available RRFS forecast hours..."
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
        rf"2dfld\.2p5km\."
        rf"f(\d{{3}})\."
        rf"pr\.grib2"

    )


    hours = sorted({

        int(
            match
        )

        for match in pattern.findall(
            html
        )

    })


    if not hours:

        raise RuntimeError(

            "No RRFS 2-D forecast hours "
            "found in NOMADS directory."

        )


    print(

        f"Available forecast hours: "
        f"F{hours[0]:03d}-F{hours[-1]:03d}"

    )


    print(

        f"Total available: "
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


    return (
        response.text
    )


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


    # --------------------------------------------------------
    # Calculate ending byte from the beginning of the next
    # GRIB message.
    # --------------------------------------------------------

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
# FIND COMPOSITE REFLECTIVITY
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


        # ----------------------------------------------------
        # Prefer explicitly identified 2-5 km UH.
        # Handle likely wording variations.
        # ----------------------------------------------------

        if (

            "5000-2000 M"
            in text

            or

            "5000-2000 M ABOVE GROUND"
            in text

            or

            "2000-5000 M"
            in text

            or

            "2000-5000 M ABOVE GROUND"
            in text

        ):

            return record


        candidates.append(
            record
        )


    if candidates:

        print(

            "WARNING: exact 2-5 km UH layer "
            "text not found; using first MXUPHL."

        )


        print(
            candidates[0]["line"]
        )


        return (
            candidates[0]
        )


    raise RuntimeError(

        "MXUPHL not found in RRFS index."

    )


# ============================================================
# DOWNLOAD HTTP BYTE RANGE
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


    # --------------------------------------------------------
    # NOMADS should return HTTP 206 for a byte-range request.
    #
    # A 200 can occur if a server ignores Range. We do not
    # silently accept a gigantic full file in that situation.
    # --------------------------------------------------------

    if (
        response.status_code
        not in
        (
            200,
            206
        )
    ):

        raise RuntimeError(

            f"Unexpected HTTP status "
            f"{response.status_code}"

        )


    data = (
        response.content
    )


    if not data:

        raise RuntimeError(

            "NOMADS returned an empty "
            "GRIB byte range."

        )


    # --------------------------------------------------------
    # Basic GRIB signature sanity check.
    # --------------------------------------------------------

    if (
        data[
            :4
        ]
        !=
        b"GRIB"
    ):

        raise RuntimeError(

            "Downloaded byte range does "
            "not begin with GRIB."

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

            "Could not find RRFS "
            "lat/lon coordinates."

        )


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

                    "RRFS index contains "
                    "no readable records."

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
            # REFLECTIVITY
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

            ds_uh = None


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
            # CLOSE DATASETS
            # =================================================

            try:

                ds_refl.close()

            except Exception:

                pass


            if ds_uh is not None:

                try:

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
                DOWNLOAD_ATTEMPTS
            ):

                print(

                    f"Waiting "
                    f"{RETRY_SLEEP_SECONDS} "
                    f"seconds before retry..."

                )


                time.sleep(
                    RETRY_SLEEP_SECONDS
                )


    raise RuntimeError(

        f"F{fhr:03d} failed: "
        f"{last_error}"

    )
