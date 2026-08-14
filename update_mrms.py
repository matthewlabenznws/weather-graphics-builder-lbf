#!/usr/bin/env python3
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
# Display units:
#   inches
#
# Outputs:
#   data/mrms/qpe_24h.png
#   data/mrms/qpe_48h.png
#   data/mrms/qpe_72h.png
#   data/mrms/latest.json
#
# City labels:
#   5-km neighborhood mean precipitation
#
# The raster itself is NOT smoothed.
# ============================================================


from __future__ import annotations


import gzip
import json
import math
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
# ============================================================

WEST = -106.0

EAST = -95.0

SOUTH = 36.5

NORTH = 46.5


# ============================================================
# CITY LABEL SAMPLING
#
# The raster remains full-resolution MRMS.
#
# Only the displayed city values use a neighborhood mean.
# ============================================================

CITY_SAMPLE_RADIUS_KM = 5.0


# ============================================================
# LBF CWA CITY SAMPLE LOCATIONS
# ============================================================

CITIES = {

    "Gordon": {
        "lat": 42.8047,
        "lon": -102.2032
    },

    "Valentine": {
        "lat": 42.8728,
        "lon": -100.5509
    },

    "Ainsworth": {
        "lat": 42.5497,
        "lon": -99.8626
    },

    "Butte": {
        "lat": 42.9114,
        "lon": -98.8498
    },

    "O'Neill": {
        "lat": 42.4578,
        "lon": -98.6476
    },

    "Oshkosh": {
        "lat": 41.4053,
        "lon": -102.3446
    },

    "Chappell": {
        "lat": 41.0925,
        "lon": -102.4707
    },

    "Mullen": {
        "lat": 42.0428,
        "lon": -101.0427
    },

    "Thedford": {
        "lat": 41.9783,
        "lon": -100.5762
    },

    "Burwell": {
        "lat": 41.7817,
        "lon": -99.1332
    },

    "Ogallala": {
        "lat": 41.1281,
        "lon": -101.7196
    },

    "Stapleton": {
        "lat": 41.4803,
        "lon": -100.5129
    },

    "North Platte": {
        "lat": 41.1403,
        "lon": -100.7601
    },

    "Broken Bow": {
        "lat": 41.4019,
        "lon": -99.6393
    },

    "Grant": {
        "lat": 40.8414,
        "lon": -101.7252
    },

    "Imperial": {
        "lat": 40.5169,
        "lon": -101.6432
    },

    "Curtis": {
        "lat": 40.6308,
        "lon": -100.5107
    }

}


# ============================================================
# MRMS SERVER
# ============================================================

MRMS_BASE_URL = (
    "https://mrms.ncep.noaa.gov/2D"
)


# ============================================================
# PRODUCTS
# ============================================================

PRODUCTS = {

    "24h": {

        "directory":
            "MultiSensor_QPE_24H_Pass2",

        "filename":
            "MRMS_MultiSensor_QPE_24H_Pass2.latest.grib2.gz",

        "output":
            OUTPUT_DIR / "qpe_24h.png",

        "label":
            "24-Hour MRMS Precipitation"

    },


    "48h": {

        "directory":
            "MultiSensor_QPE_48H_Pass2",

        "filename":
            "MRMS_MultiSensor_QPE_48H_Pass2.latest.grib2.gz",

        "output":
            OUTPUT_DIR / "qpe_48h.png",

        "label":
            "48-Hour MRMS Precipitation"

    },


    "72h": {

        "directory":
            "MultiSensor_QPE_72H_Pass2",

        "filename":
            "MRMS_MultiSensor_QPE_72H_Pass2.latest.grib2.gz",

        "output":
            OUTPUT_DIR / "qpe_72h.png",

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
# KEEPING YOUR ORIGINAL SCALE.
#
# Units = inches.
#
# Values below 0.01 inch are explicitly masked before
# rendering so the Mapbox basemap remains visible.
# ============================================================

COLORS = [

    (
        1.0,
        1.0,
        1.0,
        0.0
    ),

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


# ============================================================
# ORIGINAL PRECIPITATION BOUNDS
# ============================================================

BOUNDS = np.concatenate(

    [

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

    ]

)


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
# VERIFY COLORMAP
# ============================================================

NUMBER_OF_INTERVALS = (
    len(BOUNDS)
    -
    1
)


if (
    len(COLORS)
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


CMAP.set_bad(

    (
        0.0,
        0.0,
        0.0,
        0.0
    )

)


NORM = BoundaryNorm(

    BOUNDS,

    CMAP.N,

    clip=True

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
        MAX_DOWNLOAD_ATTEMPTS + 1
    ):

        print()
        print("=" * 70)
        print("DOWNLOADING MRMS DATA")
        print("=" * 70)

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
# DECOMPRESS MRMS
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

        with tempfile.NamedTemporaryFile(

            suffix=".grib2",

            delete=False

        ) as temporary_file:

            temporary_file.write(
                grib_data
            )


            temporary_path = (
                temporary_file.name
            )


        with rasterio.open(
            temporary_path
        ) as source:

            print()
            print("=" * 70)
            print("MRMS GRID INFORMATION")
            print("=" * 70)

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


            crop_transform = (
                source.window_transform(
                    window
                )
            )


            # =================================================
            # ACTUAL IMAGE EXTENT
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
            # INVALID / MISSING VALUES
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
# MILLIMETERS -> INCHES
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
# CALCULATE DISTANCE FROM CITY
#
# Small-distance approximation is more than adequate for a
# 5-km sampling radius.
# ============================================================

def calculate_distance_km(
    grid_latitudes,
    grid_longitudes,
    city_latitude,
    city_longitude
):

    latitude_scale_km = (
        111.32
    )


    longitude_scale_km = (

        111.32

        *

        math.cos(
            math.radians(
                city_latitude
            )
        )

    )


    delta_y = (

        grid_latitudes
        -
        city_latitude

    ) * latitude_scale_km


    delta_x = (

        grid_longitudes
        -
        city_longitude

    ) * longitude_scale_km


    return np.sqrt(

        delta_x ** 2

        +

        delta_y ** 2

    )


# ============================================================
# SAMPLE 5-KM NEIGHBORHOOD MEAN
# ============================================================

def sample_city_precipitation(
    precipitation_inches,
    crop_transform,
    latitude,
    longitude,
    radius_km=
        CITY_SAMPLE_RADIUS_KM
):

    height, width = (
        precipitation_inches.shape
    )


    # ========================================================
    # APPROXIMATE LAT/LON SEARCH WINDOW
    # ========================================================

    latitude_radius_degrees = (

        radius_km
        /
        111.32

    )


    cosine_latitude = math.cos(
        math.radians(
            latitude
        )
    )


    if (
        abs(
            cosine_latitude
        )
        <
        0.01
    ):

        return None


    longitude_radius_degrees = (

        radius_km

        /

        (
            111.32
            *
            cosine_latitude
        )

    )


    west = (
        longitude
        -
        longitude_radius_degrees
    )


    east = (
        longitude
        +
        longitude_radius_degrees
    )


    south = (
        latitude
        -
        latitude_radius_degrees
    )


    north = (
        latitude
        +
        latitude_radius_degrees
    )


    # ========================================================
    # CONVERT SEARCH BOX TO PIXEL BOUNDS
    # ========================================================

    inverse_transform = (
        ~crop_transform
    )


    corner_pixels = [

        inverse_transform
        *
        (
            west,
            north
        ),

        inverse_transform
        *
        (
            east,
            north
        ),

        inverse_transform
        *
        (
            west,
            south
        ),

        inverse_transform
        *
        (
            east,
            south
        )

    ]


    columns = [
        point[0]
        for point in corner_pixels
    ]


    rows = [
        point[1]
        for point in corner_pixels
    ]


    column_min = max(

        0,

        int(
            math.floor(
                min(
                    columns
                )
            )
        )

    )


    column_max = min(

        width - 1,

        int(
            math.ceil(
                max(
                    columns
                )
            )
        )

    )


    row_min = max(

        0,

        int(
            math.floor(
                min(
                    rows
                )
            )
        )

    )


    row_max = min(

        height - 1,

        int(
            math.ceil(
                max(
                    rows
                )
            )
        )

    )


    if (
        row_min
        >
        row_max

        or

        column_min
        >
        column_max
    ):

        return None


    # ========================================================
    # SUBSET
    # ========================================================

    subset = precipitation_inches[

        row_min:
        row_max + 1,

        column_min:
        column_max + 1

    ]


    # ========================================================
    # GRID CELL CENTER COORDINATES
    # ========================================================

    row_indices = np.arange(

        row_min,
        row_max + 1,

        dtype=np.float64

    )


    column_indices = np.arange(

        column_min,
        column_max + 1,

        dtype=np.float64

    )


    column_grid, row_grid = np.meshgrid(

        column_indices,
        row_indices

    )


    grid_longitudes = (

        crop_transform.c

        +

        (
            column_grid
            +
            0.5
        )
        *
        crop_transform.a

        +

        (
            row_grid
            +
            0.5
        )
        *
        crop_transform.b

    )


    grid_latitudes = (

        crop_transform.f

        +

        (
            column_grid
            +
            0.5
        )
        *
        crop_transform.d

        +

        (
            row_grid
            +
            0.5
        )
        *
        crop_transform.e

    )


    # ========================================================
    # TRUE 5-KM CIRCLE
    # ========================================================

    distances = calculate_distance_km(

        grid_latitudes,
        grid_longitudes,

        latitude,
        longitude

    )


    valid_mask = (

        distances
        <=
        radius_km

    ) & np.isfinite(
        subset
    )


    values = subset[
        valid_mask
    ]


    if (
        values.size
        ==
        0
    ):

        return None


    # ========================================================
    # NEIGHBORHOOD MEAN
    # ========================================================

    mean_value = float(

        np.nanmean(
            values
        )

    )


    return mean_value


# ============================================================
# SAMPLE ALL LBF CITIES
# ============================================================

def sample_city_values(
    precipitation_inches,
    crop_transform
):

    city_values = []


    print()
    print("=" * 70)

    print(
        f"LBF CWA CITY PRECIPITATION "
        f"({CITY_SAMPLE_RADIUS_KM:.0f}-KM MEAN)"
    )

    print("=" * 70)


    for (
        city_name,
        location
    ) in CITIES.items():

        latitude = (
            location[
                "lat"
            ]
        )


        longitude = (
            location[
                "lon"
            ]
        )


        precipitation = (
            sample_city_precipitation(

                precipitation_inches,

                crop_transform,

                latitude,

                longitude,

                radius_km=
                    CITY_SAMPLE_RADIUS_KM

            )
        )


        if (
            precipitation
            is
            None
        ):

            print(
                f"{city_name:<15} missing"
            )


            continue


        rounded_precipitation = round(

            precipitation,

            2

        )


        label = (

            f"{rounded_precipitation:.2f}\""

        )


        city_values.append(

            {

                "name":
                    city_name,

                "lat":
                    latitude,

                "lon":
                    longitude,

                "precip_inches":
                    rounded_precipitation,

                "label":
                    label,

                "sample_radius_km":
                    CITY_SAMPLE_RADIUS_KM

            }

        )


        print(

            f"{city_name:<15} "
            f"{rounded_precipitation:.2f} in"

        )


    return city_values


# ============================================================
# RENDER TRANSPARENT PRECIPITATION PNG
#
# IMPORTANT:
# THIS USES THE RAW FULL-RESOLUTION precipitation_inches
# ARRAY. THE RASTER IS NOT A 5-km AVERAGE.
# ============================================================

def render_precipitation_png(
    precipitation_inches,
    output_path
):

    print()
    print("=" * 70)
    print("RENDERING PRECIPITATION IMAGE")
    print("=" * 70)

    print(
        output_path
    )


    # ========================================================
    # MASK ZERO / TRACE VALUES
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
    # PRESERVE GRID DIMENSIONS
    # ========================================================

    image_height = (
        plot_data.shape[0]
    )


    image_width = (
        plot_data.shape[1]
    )


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
    # FIGURE
    # ========================================================

    figure = plt.figure(

        figsize=(

            figure_width,
            figure_height

        ),

        dpi=dpi,

        frameon=False

    )


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
    # RENDER
    # ========================================================

    axis.imshow(

        plot_data,

        cmap=
            CMAP,

        norm=
            NORM,

        origin=
            "upper",

        interpolation=
            "nearest",

        aspect=
            "auto"

    )


    # ========================================================
    # SAVE
    # ========================================================

    figure.savefig(

        output_path,

        dpi=dpi,

        transparent=True,

        bbox_inches=None,

        pad_inches=0

    )


    plt.close(
        figure
    )


    print(
        "Saved precipitation PNG."
    )


# ============================================================
# PROCESS ONE PRODUCT
# ============================================================

def process_product(
    product_key,
    configuration
):

    print()
    print()
    print("#" * 70)

    print(
        f"MRMS "
        f"{product_key.upper()} "
        f"PRECIPITATION"
    )

    print("#" * 70)


    # ========================================================
    # URL
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
    # READ
    # ========================================================

    (
        precipitation_mm,
        extent,
        crop_transform

    ) = read_mrms_grib(
        grib_data
    )


    # ========================================================
    # MM -> INCHES
    #
    # THIS ARRAY IS USED FOR BOTH:
    #
    # 1. raster coloring
    # 2. city sampling
    #
    # ========================================================

    precipitation_inches = (
        millimeters_to_inches(
            precipitation_mm
        )
    )


    # ========================================================
    # STATS
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

        minimum_inches = None

        maximum_inches = None


    # ========================================================
    # CITY VALUES
    #
    # Uses 5-km means.
    # ========================================================

    city_values = (
        sample_city_values(

            precipitation_inches,

            crop_transform

        )
    )


    # ========================================================
    # RENDER
    #
    # Uses full-resolution field.
    # ========================================================

    render_precipitation_png(

        precipitation_inches,

        configuration[
            "output"
        ]

    )


    # ========================================================
    # MANIFEST
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

        "city_sample_radius_km":
            CITY_SAMPLE_RADIUS_KM,

        "city_values":
            city_values,

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

        "transparent_below_inches":
            0.01,

        "city_sample_radius_km":
            CITY_SAMPLE_RADIUS_KM,

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
    print("=" * 70)
    print("MRMS MANIFEST SAVED")
    print("=" * 70)

    print(
        output_path
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("NWS NORTH PLATTE MRMS UPDATE")
    print("=" * 70)


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
        f"City sampling: "
        f"{CITY_SAMPLE_RADIUS_KM:.0f}-km mean"
    )


    print()
    print(
        "LBF city labels:"
    )


    for city_name in (
        CITIES.keys()
    ):

        print(
            f"  {city_name}"
        )


    completed_products = {}


    # ========================================================
    # PROCESS 24 / 48 / 72 HOURS
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
        ] = result


    # ========================================================
    # MANIFEST
    # ========================================================

    write_manifest(
        completed_products
    )


    # ========================================================
    # FINISHED
    # ========================================================

    print()
    print("=" * 70)
    print("MRMS UPDATE COMPLETE")
    print("=" * 70)


    print()
    print(
        "Generated files:"
    )

    print(
        f"  {PRODUCTS['24h']['output']}"
    )

    print(
        f"  {PRODUCTS['48h']['output']}"
    )

    print(
        f"  {PRODUCTS['72h']['output']}"
    )

    print(
        f"  {OUTPUT_DIR / 'latest.json'}"
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
        print("MRMS UPDATE FAILED")
        print("=" * 70)

        print(
            error
        )


        sys.exit(
            1
        )
