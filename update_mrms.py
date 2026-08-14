#!/usr/bin/env python3

# ============================================================
# NWS LBF WEATHER GRAPHICS BUILDER
# MRMS MULTISENSOR QPE PASS 2
#
# Products:
#   24-hour QPE
#   48-hour QPE
#   72-hour QPE
#
# Output:
#   data/mrms/qpe_24h.png
#   data/mrms/qpe_48h.png
#   data/mrms/qpe_72h.png
#   data/mrms/latest.json
#
# Source:
#   NOAA / NCEP MRMS
#
# Units:
#   Source = millimeters
#   Output/display = inches
# ============================================================

from __future__ import annotations

import gzip
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import requests
import rasterio
from matplotlib.colors import ListedColormap, BoundaryNorm
from rasterio.windows import from_bounds


# ============================================================
# OUTPUT
# ============================================================

OUTPUT_DIR = Path("data/mrms")

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# DOMAIN
#
# Same broad Central Plains region you've been using.
# ============================================================

WEST = -106.0
EAST = -95.0

SOUTH = 36.5
NORTH = 46.5


# ============================================================
# MRMS PRODUCTS
# ============================================================

MRMS_BASE_URL = (
    "https://mrms.ncep.noaa.gov/2D"
)


PRODUCTS = {

    "24h": {

        "directory":
            "MultiSensor_QPE_24H_Pass2",

        "filename":
            "MRMS_MultiSensor_QPE_24H_Pass2.latest.grib2.gz",

        "output":
            OUTPUT_DIR / "qpe_24h.png",

        "label":
            "24-Hour MRMS QPE"

    },


    "48h": {

        "directory":
            "MultiSensor_QPE_48H_Pass2",

        "filename":
            "MRMS_MultiSensor_QPE_48H_Pass2.latest.grib2.gz",

        "output":
            OUTPUT_DIR / "qpe_48h.png",

        "label":
            "48-Hour MRMS QPE"

    },


    "72h": {

        "directory":
            "MultiSensor_QPE_72H_Pass2",

        "filename":
            "MRMS_MultiSensor_QPE_72H_Pass2.latest.grib2.gz",

        "output":
            OUTPUT_DIR / "qpe_72h.png",

        "label":
            "72-Hour MRMS QPE"

    }

}


# ============================================================
# NETWORK SETTINGS
# ============================================================

REQUEST_TIMEOUT_SECONDS = 120

MAX_ATTEMPTS = 4

RETRY_WAIT_SECONDS = 10


HEADERS = {

    "User-Agent":
        "NWS-LBF-Weather-Graphics-Builder/1.0",

    "Accept":
        "*/*"

}


# ============================================================
# PRECIPITATION COLORMAP
#
# First bin is transparent.
#
# Everything below 0.01 inch is masked entirely.
# ============================================================

colors = [

    (1.0, 1.0, 1.0, 0.0),

    "#dcdcdc",
    "#bebebe",
    "#a0a0a0",
    "#828282",

    "#b7f0be",
    "#9fdbb3",
    "#87c7a7",
    "#6fb29c",
    "#579d90",
    "#3f8885",
    "#277479",
    "#146473",

    "#1450b4",
    "#2a61bb",
    "#3f73c2",
    "#5584c9",
    "#6b96d0",
    "#80a7d6",
    "#96b9dd",
    "#accae4",
    "#c1dceb",
    "#d7edf2",

    "#cebce0",
    "#c9addb",
    "#c49ed5",
    "#bf90d0",
    "#ba81ca",
    "#b472c5",
    "#af63bf",
    "#aa55ba",
    "#a546b4",
    "#a037af",

    "#a53a34",
    "#ad4842",
    "#b5554f",
    "#bd635d",
    "#c6716b",
    "#ce7f79",
    "#d68c86",
    "#de9a94",

    "#f8eea2",
    "#eed68c",
    "#e5bd76",
    "#dba560",
    "#d28c4a",
    "#c87434",
    "#ac632d",
    "#965727",
    "#814a21",
    "#6b3e1b",
    "#553115"

]


bounds = np.concatenate([

    np.arange(
        0.00,
        0.01,
        0.01
    ),

    np.arange(
        0.01,
        0.05,
        0.02
    ),

    np.arange(
        0.05,
        0.10,
        0.025
    ),

    np.arange(
        0.10,
        1.00,
        0.05
    ),

    np.arange(
        1.00,
        2.00,
        0.10
    ),

    np.arange(
        2.00,
        4.00,
        0.25
    ),

    np.arange(
        4.00,
        6.00,
        0.50
    ),

    np.arange(
        6.00,
        10.00,
        1.00
    ),

    np.arange(
        10.00,
        17.50,
        2.50
    )

])


if bounds[-1] < 17.5:

    bounds = np.append(
        bounds,
        17.5
    )


# ============================================================
# MAKE SURE NUMBER OF COLORS MATCHES NUMBER OF INTERVALS
# ============================================================

required_colors = (
    len(bounds)
    -
    1
)


if len(colors) < required_colors:

    raise RuntimeError(

        "Not enough colors for precipitation bounds.\n"
        f"Colors: {len(colors)}\n"
        f"Intervals: {required_colors}"

    )


if len(colors) > required_colors:

    colors = colors[
        :required_colors
    ]


cmap = ListedColormap(

    colors,

    name="precip_bins"

)


cmap.set_bad(
    (0, 0, 0, 0)
)


norm = BoundaryNorm(

    bounds,

    cmap.N,

    clip=True

)


# ============================================================
# DOWNLOAD FILE
# ============================================================

def download_file(
    url
):

    last_error = None


    for attempt in range(
        1,
        MAX_ATTEMPTS + 1
    ):

        print()
        print(
            f"Downloading:"
        )

        print(
            f"  {url}"
        )

        print(
            f"Attempt {attempt}/{MAX_ATTEMPTS}"
        )


        try:

            response = requests.get(

                url,

                headers=HEADERS,

                timeout=REQUEST_TIMEOUT_SECONDS

            )


            response.raise_for_status()


            if not response.content:

                raise RuntimeError(
                    "Downloaded file was empty."
                )


            print(

                "Downloaded "
                f"{len(response.content):,} bytes."

            )


            return response.content


        except Exception as exc:

            last_error = exc


            print(
                f"Download failed: {exc}"
            )


            if attempt < MAX_ATTEMPTS:

                print(
                    f"Waiting {RETRY_WAIT_SECONDS} seconds..."
                )

                time.sleep(
                    RETRY_WAIT_SECONDS
                )


    raise RuntimeError(

        "MRMS download failed after "
        f"{MAX_ATTEMPTS} attempts.\n"
        f"Last error: {last_error}"

    )


# ============================================================
# DECOMPRESS GZIP
# ============================================================

def decompress_gzip(
    compressed_bytes
):

    try:

        return gzip.decompress(
            compressed_bytes
        )


    except Exception as exc:

        raise RuntimeError(

            f"Could not decompress MRMS gzip file: {exc}"

        ) from exc


# ============================================================
# READ / CROP MRMS GRIB
# ============================================================

def read_mrms_grib(
    grib_bytes
):

    temporary_path = None


    try:

        with tempfile.NamedTemporaryFile(

            suffix=".grib2",

            delete=False

        ) as temp_file:

            temp_file.write(
                grib_bytes
            )

            temporary_path = (
                temp_file.name
            )


        # ====================================================
        # OPEN GRIB
        # ====================================================

        with rasterio.open(
            temporary_path
        ) as src:

            print()
            print(
                "MRMS GRIB metadata:"
            )

            print(
                f"  CRS: {src.crs}"
            )

            print(
                f"  Width: {src.width}"
            )

            print(
                f"  Height: {src.height}"
            )

            print(
                f"  Bounds: {src.bounds}"
            )

            print(
                f"  Transform: {src.transform}"
            )


            # =================================================
            # EXPECT GEOGRAPHIC LAT/LON GRID
            # =================================================

            if src.crs is None:

                print(
                    "Warning: GRIB CRS missing. "
                    "Assuming geographic lat/lon."
                )


            # =================================================
            # CREATE CROP WINDOW
            # =================================================

            window = from_bounds(

                WEST,
                SOUTH,
                EAST,
                NORTH,

                transform=src.transform

            )


            window = window.round_offsets().round_lengths()


            # =================================================
            # READ DATA
            # =================================================

            data = src.read(

                1,

                window=window,

                boundless=False

            ).astype(
                np.float32
            )


            cropped_transform = (
                src.window_transform(
                    window
                )
            )


            # =================================================
            # ACTUAL CROP BOUNDS
            # =================================================

            left =
                cropped_transform.c


            top =
                cropped_transform.f


            right = (
                left
                +
                cropped_transform.a
                *
                data.shape[1]
            )


            bottom = (
                top
                +
                cropped_transform.e
                *
                data.shape[0]
            )


            extent = {

                "west":
                    min(
                        left,
                        right
                    ),

                "east":
                    max(
                        left,
                        right
                    ),

                "south":
                    min(
                        bottom,
                        top
                    ),

                "north":
                    max(
                        bottom,
                        top
                    )

            }


            # =================================================
            # REMOVE FILL / INVALID VALUES
            #
            # MRMS uses negative values for missing / coverage
            # flags. Precipitation itself cannot be negative.
            # =================================================

            data[

                ~np.isfinite(
                    data
                )

            ] = np.nan


            data[

                data < 0

            ] = np.nan


            return (
                data,
                extent
            )


    finally:

        if (
            temporary_path
            and
            os.path.exists(
                temporary_path
            )
        ):

            os.remove(
                temporary_path
            )


# ============================================================
# MM -> INCHES
# ============================================================

def mm_to_inches(
    precip_mm
):

    return (
        precip_mm
        /
        25.4
    )


# ============================================================
# RENDER TRANSPARENT PNG
# ============================================================

def render_precip_png(
    precip_inches,
    output_path
):

    print()
    print(
        f"Rendering {output_path}"
    )


    # ========================================================
    # MASK TRACE / ZERO VALUES
    # ========================================================

    plot_data = np.ma.masked_where(

        (
            ~np.isfinite(
                precip_inches
            )
        )

        |

        (
            precip_inches
            <
            0.01
        ),

        precip_inches

    )


    # ========================================================
    # CREATE EXACT-SIZE IMAGE
    #
    # No axes.
    # No borders.
    # Transparent background.
    # ========================================================

    height,
    width = plot_data.shape


    dpi =
        100


    figure_width =
        width / dpi


    figure_height =
        height / dpi


    fig = plt.figure(

        figsize=(
            figure_width,
            figure_height
        ),

        dpi=dpi,

        frameon=False

    )


    ax = fig.add_axes(
        [
            0,
            0,
            1,
            1
        ]
    )


    ax.set_axis_off()


    ax.imshow(

        plot_data,

        cmap=cmap,

        norm=norm,

        interpolation="nearest",

        origin="upper",

        aspect="auto"

    )


    fig.savefig(

        output_path,

        dpi=dpi,

        transparent=True,

        bbox_inches=None,

        pad_inches=0

    )


    plt.close(
        fig
    )


    print(
        f"Saved {output_path}"
    )


# ============================================================
# PROCESS ONE PRODUCT
# ============================================================

def process_product(
    key,
    config
):

    print()
    print("=" * 70)

    print(
        f"PROCESSING MRMS {key.upper()} QPE"
    )

    print("=" * 70)


    url = (

        f"{MRMS_BASE_URL}/"
        f"{config['directory']}/"
        f"{config['filename']}"

    )


    # ========================================================
    # DOWNLOAD
    # ========================================================

    compressed_data = (
        download_file(
            url
        )
    )


    # ========================================================
    # UNZIP
    # ========================================================

    grib_data = (
        decompress_gzip(
            compressed_data
        )
    )


    print(
        f"Decompressed size: "
        f"{len(grib_data):,} bytes"
    )


    # ========================================================
    # READ
    # ========================================================

    precip_mm, extent = (
        read_mrms_grib(
            grib_data
        )
    )


    # ========================================================
    # CONVERT
    # ========================================================

    precip_inches = (
        mm_to_inches(
            precip_mm
        )
    )


    # ========================================================
    # STATS
    # ========================================================

    valid = precip_inches[

        np.isfinite(
            precip_inches
        )

    ]


    if valid.size > 0:

        minimum =
            float(
                np.nanmin(
                    valid
                )
            )


        maximum =
            float(
                np.nanmax(
                    valid
                )
            )


        print(
            f"Minimum precip: {minimum:.3f} in"
        )

        print(
            f"Maximum precip: {maximum:.3f} in"
        )


    else:

        minimum =
            None


        maximum =
            None


    # ========================================================
    # RENDER
    # ========================================================

    render_precip_png(

        precip_inches,

        config[
            "output"
        ]

    )


    return {

        "key":
            key,

        "label":
            config[
                "label"
            ],

        "image":
            str(
                config[
                    "output"
                ]
            ).replace(
                "\\",
                "/"
            ),

        "extent":
            extent,

        "minimum_inches":
            minimum,

        "maximum_inches":
            maximum,

        "source_url":
            url

    }


# ============================================================
# WRITE MANIFEST
# ============================================================

def write_manifest(
    products
):

    manifest = {

        "generated":
            datetime.now(
                timezone.utc
            )
            .isoformat()
            .replace(
                "+00:00",
                "Z"
            ),

        "source":
            "NOAA/NCEP MRMS MultiSensor QPE Pass 2",

        "units":
            "inches",

        "minimum_display_inches":
            0.01,

        "products":
            products

    }


    output_path = (
        OUTPUT_DIR
        /
        "latest.json"
    )


    temporary_path = (
        OUTPUT_DIR
        /
        "latest.json.tmp"
    )


    with open(

        temporary_path,

        "w",

        encoding="utf-8"

    ) as file:

        json.dump(

            manifest,

            file,

            indent=2,

            allow_nan=False

        )


    os.replace(

        temporary_path,

        output_path

    )


    print()
    print(
        f"Saved manifest: {output_path}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("NWS LBF MRMS QPE UPDATE")
    print("=" * 70)

    print(
        "Domain:"
    )

    print(
        f"  West:  {WEST}"
    )

    print(
        f"  East:  {EAST}"
    )

    print(
        f"  South: {SOUTH}"
    )

    print(
        f"  North: {NORTH}"
    )


    completed_products = {}


    for key, config in PRODUCTS.items():

        try:

            result = process_product(

                key,
                config

            )


            completed_products[
                key
            ] = result


        except Exception as exc:

            print()
            print(
                f"FAILED MRMS {key}: {exc}"
            )

            raise


    # ========================================================
    # MANIFEST
    # ========================================================

    write_manifest(
        completed_products
    )


    print()
    print("=" * 70)
    print("MRMS UPDATE COMPLETE")
    print("=" * 70)

    print(
        f"24-hour: {PRODUCTS['24h']['output']}"
    )

    print(
        f"48-hour: {PRODUCTS['48h']['output']}"
    )

    print(
        f"72-hour: {PRODUCTS['72h']['output']}"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except Exception as exc:

        print()
        print("=" * 70)
        print("MRMS UPDATE FAILED")
        print("=" * 70)

        print(
            str(exc)
        )

        sys.exit(
            1
        )
