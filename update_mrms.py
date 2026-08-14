#!/usr/bin/env python3

# ============================================================
# NWS NORTH PLATTE WEATHER GRAPHICS BUILDER
# MRMS MULTISENSOR QPE PASS 2
#
# Products:
#   24-hour precipitation
#   48-hour precipitation
#   72-hour precipitation
#
# MRMS source units:
#   millimeters
#
# Display / color scale units:
#   inches
#
# Rendering:
#   matplotlib contourf
#
# Outputs:
#   data/mrms/qpe_24h.png
#   data/mrms/qpe_48h.png
#   data/mrms/qpe_72h.png
#   data/mrms/latest.json
#
# City precipitation labels have been REMOVED.
#
# The vertical precipitation colorbar should be handled
# separately in index.html / graphics.js so it does not
# alter the geographic dimensions of the PNG.
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

matplotlib.use(
    "Agg"
)


import matplotlib.pyplot as plt
import numpy as np
import requests
import rasterio

from matplotlib.colors import (
    ListedColormap,
    BoundaryNorm
)

from rasterio.windows import from_bounds


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR = Path(
    "data/mrms"
)


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# MAP DOMAIN
#
# Broad Central Plains domain.
# ============================================================

WEST = -106.0

EAST = -95.0

SOUTH = 36.5

NORTH = 46.5


# ============================================================
# MRMS SERVER
# ============================================================

MRMS_BASE_URL = (
    "https://mrms.ncep.noaa.gov/2D"
)


# ============================================================
# MRMS PRODUCTS
# ============================================================

PRODUCTS = {

    "24h": {

        "directory":
            "MultiSensor_QPE_24H_Pass2",

        "filename":
            "MRMS_MultiSensor_QPE_24H_Pass2.latest.grib2.gz",

        "output":
            OUTPUT_DIR
            /
            "qpe_24h.png",

        "label":
            "24-Hour MRMS Precipitation"

    },


    "48h": {

        "directory":
            "MultiSensor_QPE_48H_Pass2",

        "filename":
            "MRMS_MultiSensor_QPE_48H_Pass2.latest.grib2.gz",

        "output":
            OUTPUT_DIR
            /
            "qpe_48h.png",

        "label":
            "48-Hour MRMS Precipitation"

    },


    "72h": {

        "directory":
            "MultiSensor_QPE_72H_Pass2",

        "filename":
            "MRMS_MultiSensor_QPE_72H_Pass2.latest.grib2.gz",

        "output":
            OUTPUT_DIR
            /
            "qpe_72h.png",

        "label":
            "72-Hour MRMS Precipitation"

    }

}


# ============================================================
# NETWORK SETTINGS
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
# PIVOTAL-STYLE PRECIPITATION COLORMAP
#
# Units = inches
#
# Keep this exact palette.
# ============================================================

COLORS = [

    # --------------------------------------------------------
    # 0.00 - 0.01
    #
    # Transparent / trace
    # --------------------------------------------------------

    (
        1.0,
        1.0,
        1.0,
        0.0
    ),


    # --------------------------------------------------------
    # GRAYS
    # --------------------------------------------------------

    "#dcdcdc",
    "#bebebe",
    "#a0a0a0",
    "#828282",


    # --------------------------------------------------------
    # GREENS
    # --------------------------------------------------------

    "#b7f0be",
    "#9fdbb3",
    "#87c7a7",
    "#6fb29c",
    "#579d90",
    "#3f8885",
    "#277479",
    "#146473",


    # --------------------------------------------------------
    # BLUES
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # PURPLES
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # REDS
    # --------------------------------------------------------

    "#a53a34",
    "#ad4842",
    "#b5554f",
    "#bd635d",
    "#c6716b",
    "#ce7f79",
    "#d68c86",
    "#de9a94",


    # --------------------------------------------------------
    # YELLOW / ORANGE / BROWN
    # --------------------------------------------------------

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


# ============================================================
# PIVOTAL-STYLE PRECIPITATION BOUNDS
#
# Units = inches
# ============================================================

BOUNDS = np.concatenate(

    [

        # ----------------------------------------------------
        # 0.00
        # ----------------------------------------------------

        np.arange(
            0.00,
            0.01,
            0.01
        ),


        # ----------------------------------------------------
        # 0.01, 0.03
        # ----------------------------------------------------

        np.arange(
            0.01,
            0.05,
            0.02
        ),


        # ----------------------------------------------------
        # 0.05, 0.075
        # ----------------------------------------------------

        np.arange(
            0.05,
            0.10,
            0.025
        ),


        # ----------------------------------------------------
        # 0.10 through 0.95 every 0.05
        # ----------------------------------------------------

        np.arange(
            0.10,
            1.00,
            0.05
        ),


        # ----------------------------------------------------
        # 1.00 through 1.90 every 0.10
        # ----------------------------------------------------

        np.arange(
            1.00,
            2.00,
            0.10
        ),


        # ----------------------------------------------------
        # 2.00 through 3.75 every 0.25
        # ----------------------------------------------------

        np.arange(
            2.00,
            4.00,
            0.25
        ),


        # ----------------------------------------------------
        # 4.00 through 5.50 every 0.50
        # ----------------------------------------------------

        np.arange(
            4.00,
            6.00,
            0.50
        ),


        # ----------------------------------------------------
        # 6 through 9 every 1 inch
        # ----------------------------------------------------

        np.arange(
            6.00,
            10.00,
            1.00
        ),


        # ----------------------------------------------------
        # 10, 12.5, 15
        # ----------------------------------------------------

        np.arange(
            10.00,
            17.50,
            2.50
        )

    ]

)


# ============================================================
# FINAL ENDPOINT
# ============================================================

if (
    BOUNDS[-1]
    <
    17.5
):

    BOUNDS = np.append(

        BOUNDS,

        17.5

    )


# ============================================================
# VERIFY COLOR COUNT
# ============================================================

NUMBER_OF_INTERVALS = (

    len(
        BOUNDS
    )

    -

    1

)


if (
    len(
        COLORS
    )
    !=
    NUMBER_OF_INTERVALS
):

    raise RuntimeError(

        "\n"
        "Precipitation color configuration mismatch.\n"
        "\n"
        f"Colors: {len(COLORS)}\n"
        f"Intervals: {NUMBER_OF_INTERVALS}\n"

    )


# ============================================================
# BUILD COLORMAP
# ============================================================

CMAP = ListedColormap(

    COLORS,

    name=
        "mrms_precip_bins"

)


# ============================================================
# MISSING DATA TRANSPARENT
# ============================================================

CMAP.set_bad(

    (
        0.0,
        0.0,
        0.0,
        0.0
    )

)


# ============================================================
# VALUES ABOVE 17.5 INCHES
#
# Use darkest brown.
# ============================================================

CMAP.set_over(
    "#553115"
)


# ============================================================
# NORMALIZATION
# ============================================================

NORM = BoundaryNorm(

    BOUNDS,

    CMAP.N,

    clip=False

)


# ============================================================
# DOWNLOAD MRMS FILE
# ============================================================

def download_file(
    url: str
) -> bytes:

    last_error = None


    for attempt in range(

        1,

        MAX_DOWNLOAD_ATTEMPTS
        +
        1

    ):

        print()
        print(
            "=" * 70
        )

        print(
            "DOWNLOADING MRMS DATA"
        )

        print(
            "=" * 70
        )

        print(
            f"Attempt "
            f"{attempt}/"
            f"{MAX_DOWNLOAD_ATTEMPTS}"
        )

        print(
            url
        )


        try:

            response = requests.get(

                url,

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
                    "Downloaded MRMS file was empty."
                )


            print(
                f"Downloaded: "
                f"{len(content):,} bytes"
            )


            return content


        except Exception as error:

            last_error = (
                error
            )


            print(
                f"Download failed: "
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

        "Unable to download MRMS data "
        f"after {MAX_DOWNLOAD_ATTEMPTS} attempts.\n"
        f"Last error: {last_error}"

    )


# ============================================================
# DECOMPRESS MRMS GZIP
# ============================================================

def decompress_mrms(
    compressed_data: bytes
) -> bytes:

    print()
    print(
        "Decompressing MRMS GRIB2..."
    )


    try:

        grib_data = gzip.decompress(
            compressed_data
        )


    except Exception as error:

        raise RuntimeError(

            "Unable to decompress MRMS file: "
            f"{error}"

        ) from error


    print(
        f"Decompressed size: "
        f"{len(grib_data):,} bytes"
    )


    return grib_data


# ============================================================
# READ AND CROP MRMS GRIB2
# ============================================================

def read_mrms_grib(
    grib_data: bytes
):

    temporary_path = None


    try:

        # ====================================================
        # TEMPORARY GRIB2 FILE
        # ====================================================

        with tempfile.NamedTemporaryFile(

            suffix=
                ".grib2",

            delete=
                False

        ) as temporary_file:

            temporary_file.write(
                grib_data
            )


            temporary_path = (
                temporary_file.name
            )


        # ====================================================
        # OPEN GRIB2
        # ====================================================

        with rasterio.open(
            temporary_path
        ) as source:

            print()
            print(
                "=" * 70
            )

            print(
                "MRMS GRID INFORMATION"
            )

            print(
                "=" * 70
            )

            print(
                f"CRS: "
                f"{source.crs}"
            )

            print(
                f"Grid size: "
                f"{source.width} x {source.height}"
            )

            print(
                f"Bounds: "
                f"{source.bounds}"
            )

            print(
                f"Transform: "
                f"{source.transform}"
            )


            # =================================================
            # CROP WINDOW
            # =================================================

            window = from_bounds(

                WEST,
                SOUTH,
                EAST,
                NORTH,

                transform=
                    source.transform

            )


            window = (

                window
                .round_offsets()
                .round_lengths()

            )


            # =================================================
            # READ PRECIPITATION
            # =================================================

            precipitation_mm = source.read(

                1,

                window=
                    window,

                boundless=
                    False

            ).astype(
                np.float32
            )


            # =================================================
            # TRANSFORM FOR CROPPED GRID
            # =================================================

            crop_transform = (

                source.window_transform(
                    window
                )

            )


            # =================================================
            # GEOGRAPHIC EXTENT
            # =================================================

            left = (
                crop_transform.c
            )


            top = (
                crop_transform.f
            )


            right = (

                left

                +

                crop_transform.a
                *
                precipitation_mm.shape[1]

            )


            bottom = (

                top

                +

                crop_transform.e
                *
                precipitation_mm.shape[0]

            )


            extent = {

                "west":
                    float(
                        min(
                            left,
                            right
                        )
                    ),

                "east":
                    float(
                        max(
                            left,
                            right
                        )
                    ),

                "south":
                    float(
                        min(
                            bottom,
                            top
                        )
                    ),

                "north":
                    float(
                        max(
                            bottom,
                            top
                        )
                    )

            }


            # =================================================
            # INVALID / MISSING MRMS VALUES
            #
            # Negative MRMS values are missing/coverage flags.
            # =================================================

            precipitation_mm[

                ~np.isfinite(
                    precipitation_mm
                )

            ] = np.nan


            precipitation_mm[

                precipitation_mm
                <
                0.0

            ] = np.nan


            print()
            print(
                "Cropped grid:"
            )

            print(
                f"Shape: "
                f"{precipitation_mm.shape}"
            )

            print(
                f"Extent: "
                f"{extent}"
            )


            return (

                precipitation_mm,
                extent,
                crop_transform

            )


    finally:

        # ====================================================
        # DELETE TEMPORARY GRIB
        # ====================================================

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
# MILLIMETERS TO INCHES
# ============================================================

def millimeters_to_inches(
    precipitation_mm
):

    return (

        precipitation_mm
        /
        25.4

    )


# ============================================================
# BUILD 1-D LATITUDE / LONGITUDE ARRAYS
#
# MRMS is on a regular geographic grid, so contourf can use
# 1-D x/y arrays instead of a large 2-D coordinate mesh.
#
# This reduces memory use significantly.
# ============================================================

def build_coordinate_arrays(
    shape,
    transform
):

    height, width = (
        shape
    )


    # ========================================================
    # PIXEL CENTER LONGITUDES
    # ========================================================

    columns = np.arange(

        width,

        dtype=
            np.float64

    )


    longitudes = (

        transform.c

        +

        (
            columns
            +
            0.5
        )
        *
        transform.a

    )


    # ========================================================
    # PIXEL CENTER LATITUDES
    # ========================================================

    rows = np.arange(

        height,

        dtype=
            np.float64

    )


    latitudes = (

        transform.f

        +

        (
            rows
            +
            0.5
        )
        *
        transform.e

    )


    return (

        longitudes,
        latitudes

    )


# ============================================================
# RENDER TRANSPARENT PRECIPITATION PNG
#
# Uses contourf rather than imshow.
#
# IMPORTANT:
# The PNG contains ONLY the precipitation raster.
# No city labels.
# No colorbar.
#
# The colorbar will be added separately in the website UI so
# Mapbox can preserve the exact geographic image extent.
# ============================================================

def render_precipitation_png(

    precipitation_inches,
    output_path,
    crop_transform

):

    print()
    print(
        "=" * 70
    )

    print(
        "RENDERING MRMS CONTOURF IMAGE"
    )

    print(
        "=" * 70
    )

    print(
        output_path
    )


    # ========================================================
    # MASK ZERO / TRACE PRECIPITATION
    #
    # Anything below 0.01 inch becomes transparent.
    # ========================================================

    plot_data = np.ma.masked_where(

        (

            ~np.isfinite(
                precipitation_inches
            )

            |

            (
                precipitation_inches
                <
                0.01
            )

        ),

        precipitation_inches

    )


    # ========================================================
    # GRID SIZE
    # ========================================================

    image_height = (
        plot_data.shape[0]
    )


    image_width = (
        plot_data.shape[1]
    )


    # ========================================================
    # LAT/LON ARRAYS
    # ========================================================

    (
        longitudes,
        latitudes

    ) = build_coordinate_arrays(

        plot_data.shape,

        crop_transform

    )


    # ========================================================
    # DIAGNOSTICS
    # ========================================================

    print(
        f"Longitude range: "
        f"{longitudes.min():.4f} to "
        f"{longitudes.max():.4f}"
    )

    print(
        f"Latitude range: "
        f"{latitudes.min():.4f} to "
        f"{latitudes.max():.4f}"
    )


    # ========================================================
    # FIGURE DIMENSIONS
    #
    # Keep approximately one output pixel per MRMS grid point.
    # ========================================================

    dpi = 100


    figure_width = (

        image_width
        /
        dpi

    )


    figure_height = (

        image_height
        /
        dpi

    )


    # ========================================================
    # CREATE FIGURE
    # ========================================================

    figure = plt.figure(

        figsize=(

            figure_width,
            figure_height

        ),

        dpi=
            dpi,

        frameon=
            False

    )


    # ========================================================
    # FULL-FIGURE AXIS
    # ========================================================

    axis = figure.add_axes(

        [
            0.0,
            0.0,
            1.0,
            1.0
        ]

    )


    axis.set_axis_off()


    # ========================================================
    # CONTOURF
    #
    # Exact Pivotal-style discrete levels.
    #
    # No interpolation is applied to the underlying data.
    # contourf determines polygons between grid points.
    # ========================================================

    axis.contourf(

        longitudes,

        latitudes,

        plot_data,

        levels=
            BOUNDS,

        cmap=
            CMAP,

        norm=
            NORM,

        extend=
            "max",

        antialiased=
            False

    )


    # ========================================================
    # EXACT GEOGRAPHIC VIEW
    # ========================================================

    longitude_min = float(
        np.nanmin(
            longitudes
        )
    )


    longitude_max = float(
        np.nanmax(
            longitudes
        )
    )


    latitude_min = float(
        np.nanmin(
            latitudes
        )
    )


    latitude_max = float(
        np.nanmax(
            latitudes
        )
    )


    axis.set_xlim(

        longitude_min,
        longitude_max

    )


    axis.set_ylim(

        latitude_min,
        latitude_max

    )


    # ========================================================
    # REMOVE ALL MARGINS
    # ========================================================

    axis.margins(
        0
    )


    # ========================================================
    # SAVE TRANSPARENT PNG
    # ========================================================

    figure.savefig(

        output_path,

        dpi=
            dpi,

        transparent=
            True,

        bbox_inches=
            None,

        pad_inches=
            0

    )


    plt.close(
        figure
    )


    print(
        "Saved contourf precipitation PNG."
    )


# ============================================================
# PROCESS ONE MRMS ACCUMULATION
# ============================================================

def process_product(
    product_key,
    configuration
):

    print()
    print()
    print(
        "#" * 70
    )

    print(
        f"MRMS "
        f"{product_key.upper()} "
        f"PRECIPITATION"
    )

    print(
        "#" * 70
    )


    # ========================================================
    # BUILD DOWNLOAD URL
    # ========================================================

    url = (

        f"{MRMS_BASE_URL}/"
        f"{configuration['directory']}/"
        f"{configuration['filename']}"

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
    # DECOMPRESS
    # ========================================================

    grib_data = (
        decompress_mrms(
            compressed_data
        )
    )


    # ========================================================
    # READ AND CROP
    # ========================================================

    (

        precipitation_mm,
        extent,
        crop_transform

    ) = read_mrms_grib(
        grib_data
    )


    # ========================================================
    # CONVERT MM -> INCHES
    #
    # THIS IS THE ARRAY USED FOR CONTOURF.
    # ========================================================

    precipitation_inches = (
        millimeters_to_inches(
            precipitation_mm
        )
    )


    # ========================================================
    # PRECIPITATION STATISTICS
    # ========================================================

    valid_values = precipitation_inches[

        np.isfinite(
            precipitation_inches
        )

    ]


    if (
        valid_values.size
        >
        0
    ):

        minimum_inches = float(

            np.nanmin(
                valid_values
            )

        )


        maximum_inches = float(

            np.nanmax(
                valid_values
            )

        )


        print()
        print(
            f"Minimum precipitation: "
            f"{minimum_inches:.3f} in"
        )

        print(
            f"Maximum precipitation: "
            f"{maximum_inches:.3f} in"
        )


    else:

        minimum_inches = (
            None
        )


        maximum_inches = (
            None
        )


    # ========================================================
    # RENDER CONTOURF PNG
    # ========================================================

    render_precipitation_png(

        precipitation_inches,

        configuration[
            "output"
        ],

        crop_transform

    )


    # ========================================================
    # PRODUCT INFORMATION
    #
    # No city_values are written anymore.
    # ========================================================

    return {

        "key":
            product_key,

        "label":
            configuration[
                "label"
            ],

        "image":
            str(
                configuration[
                    "output"
                ]
            ).replace(
                "\\",
                "/"
            ),

        "extent":
            extent,

        "minimum_inches":

            (
                round(
                    minimum_inches,
                    3
                )

                if
                minimum_inches
                is not None

                else
                None
            ),

        "maximum_inches":

            (
                round(
                    maximum_inches,
                    3
                )

                if
                maximum_inches
                is not None

                else
                None
            ),

        "source_url":
            url

    }


# ============================================================
# WRITE LATEST.JSON
# ============================================================

def write_manifest(
    completed_products
):

    generated_time = (

        datetime.now(
            timezone.utc
        )

        .isoformat()

        .replace(
            "+00:00",
            "Z"
        )

    )


    manifest = {

        "generated":
            generated_time,

        "source":
            "NOAA/NCEP MRMS MultiSensor QPE Pass 2",

        "units":
            "inches",

        "rendering":
            "contourf",

        "transparent_below_inches":
            0.01,

        "domain": {

            "west":
                WEST,

            "east":
                EAST,

            "south":
                SOUTH,

            "north":
                NORTH

        },

        "products":
            completed_products

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


    # ========================================================
    # WRITE TEMPORARY FILE
    # ========================================================

    with open(

        temporary_path,

        "w",

        encoding=
            "utf-8"

    ) as file:

        json.dump(

            manifest,

            file,

            indent=
                2,

            allow_nan=
                False

        )


    # ========================================================
    # ATOMIC REPLACE
    # ========================================================

    os.replace(

        temporary_path,

        output_path

    )


    print()
    print(
        "=" * 70
    )

    print(
        "MRMS MANIFEST SAVED"
    )

    print(
        "=" * 70
    )

    print(
        output_path
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print(
        "=" * 70
    )

    print(
        "NWS NORTH PLATTE MRMS UPDATE"
    )

    print(
        "=" * 70
    )


    print()
    print(
        "Map domain:"
    )

    print(
        f"West:  {WEST}"
    )

    print(
        f"East:  {EAST}"
    )

    print(
        f"South: {SOUTH}"
    )

    print(
        f"North: {NORTH}"
    )


    print()
    print(
        "Rendering:"
    )

    print(
        "  contourf"
    )


    print()
    print(
        "City precipitation labels:"
    )

    print(
        "  disabled"
    )


    completed_products = {}


    # ========================================================
    # PROCESS 24 / 48 / 72 HOUR PRODUCTS
    # ========================================================

    for (
        product_key,
        configuration
    ) in PRODUCTS.items():

        result = process_product(

            product_key,

            configuration

        )


        completed_products[
            product_key
        ] = (
            result
        )


    # ========================================================
    # WRITE MANIFEST
    # ========================================================

    write_manifest(
        completed_products
    )


    # ========================================================
    # COMPLETE
    # ========================================================

    print()
    print(
        "=" * 70
    )

    print(
        "MRMS UPDATE COMPLETE"
    )

    print(
        "=" * 70
    )


    print()
    print(
        "Generated files:"
    )

    print(
        f"  "
        f"{PRODUCTS['24h']['output']}"
    )

    print(
        f"  "
        f"{PRODUCTS['48h']['output']}"
    )

    print(
        f"  "
        f"{PRODUCTS['72h']['output']}"
    )

    print(
        f"  "
        f"{OUTPUT_DIR / 'latest.json'}"
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
        print(
            "=" * 70
        )

        print(
            "MRMS UPDATE FAILED"
        )

        print(
            "=" * 70
        )

        print(
            error
        )


        sys.exit(
            1
        )
