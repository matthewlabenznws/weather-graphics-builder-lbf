# ============================================================
# WPC DAY 1 / DAY 2 / DAY 3
# EXCESSIVE RAINFALL OUTLOOK UPDATER
#
# Downloads WPC ERO polygons from the NOAA/NWS ArcGIS REST
# service and writes:
#
#   data/wpc_day1_ero.geojson
#   data/wpc_day2_ero.geojson
#   data/wpc_day3_ero.geojson
#
# These files can then be displayed by graphics.js.
# ============================================================


import json
import time

from pathlib import Path

import requests


# ============================================================
# NOAA / NWS WPC PRECIPITATION HAZARDS SERVICE
# ============================================================

WPC_MAPSERVER = (
    "https://mapservices.weather.noaa.gov/vector/rest/services/"
    "hazards/wpc_precip_hazards/MapServer"
)


# ============================================================
# WPC ERO LAYERS
#
# Day 1 = layer 0
# Day 2 = layer 1
# Day 3 = layer 2
# ============================================================

WPC_ERO_LAYERS = {

    1: {

        "name":
            "Day 1",

        "layer_id":
            0,

        "filename":
            "wpc_day1_ero.geojson",

    },


    2: {

        "name":
            "Day 2",

        "layer_id":
            1,

        "filename":
            "wpc_day2_ero.geojson",

    },


    3: {

        "name":
            "Day 3",

        "layer_id":
            2,

        "filename":
            "wpc_day3_ero.geojson",

    },

}


# ============================================================
# OUTPUT DIRECTORY
#
# Matches your repository:
#
# repository/
# ├── update_wpc.py
# └── data/
#     ├── wpc_day1_ero.geojson
#     ├── wpc_day2_ero.geojson
#     └── wpc_day3_ero.geojson
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)


OUTPUT_DIR = (
    BASE_DIR
    / "data"
)


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# REQUEST SETTINGS
# ============================================================

REQUEST_TIMEOUT_SECONDS = 45


DOWNLOAD_ATTEMPTS = 3


RETRY_SLEEP_SECONDS = 5


# ============================================================
# WPC ERO CATEGORY INFORMATION
#
# According to the WPC service:
#
# dn = 1 -> Marginal
# dn = 2 -> Slight
# dn = 3 -> Moderate
# dn = 4 -> High
#
# These fallback colors are close to standard ERO colors.
# ============================================================

CATEGORY_INFO = {

    1: {

        "label":
            "MRGL",

        "name":
            "Marginal",

        "probability":
            "At Least 5%",

        "fill":
            "#38A800",

        "stroke":
            "#00734C",

    },


    2: {

        "label":
            "SLGT",

        "name":
            "Slight",

        "probability":
            "At Least 15%",

        "fill":
            "#FFFF00",

        "stroke":
            "#E6C700",

    },


    3: {

        "label":
            "MDT",

        "name":
            "Moderate",

        "probability":
            "At Least 40%",

        "fill":
            "#FF0000",

        "stroke":
            "#A80000",

    },


    4: {

        "label":
            "HIGH",

        "name":
            "High",

        "probability":
            "At Least 70%",

        "fill":
            "#FF00FF",

        "stroke":
            "#A80084",

    },

}


# ============================================================
# DOWNLOAD ONE WPC ERO
# ============================================================

def fetch_wpc_geojson(
    day,
    layer_id,
):

    url = (
        f"{WPC_MAPSERVER}/"
        f"{layer_id}/query"
    )


    params = {

        "where":
            "1=1",

        "outFields":
            "*",

        "returnGeometry":
            "true",

        "outSR":
            "4326",

        "f":
            "geojson",

    }


    last_error = None


    for attempt in range(
        1,
        DOWNLOAD_ATTEMPTS + 1
    ):

        try:

            print()
            print("=" * 70)

            print(
                f"Downloading WPC Day {day} "
                f"Excessive Rainfall Outlook"
            )

            print(
                f"Layer ID: {layer_id}"
            )

            print(
                f"Attempt "
                f"{attempt}/"
                f"{DOWNLOAD_ATTEMPTS}"
            )

            print("=" * 70)


            response = requests.get(

                url,

                params=params,

                timeout=
                    REQUEST_TIMEOUT_SECONDS,

            )


            response.raise_for_status()


            data = response.json()


            if (
                "features"
                not in data
            ):

                raise RuntimeError(

                    "WPC response did not contain "
                    "a features array."

                )


            if (
                len(
                    data["features"]
                )
                == 0
            ):

                raise RuntimeError(

                    f"WPC Day {day} returned "
                    "zero ERO polygons."

                )


            print(
                f"Downloaded "
                f"{len(data['features'])} "
                f"features."
            )


            return data


        except Exception as error:

            last_error = error


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
                    f"{RETRY_SLEEP_SECONDS} seconds..."
                )


                time.sleep(
                    RETRY_SLEEP_SECONDS
                )


    raise RuntimeError(

        f"Could not download "
        f"WPC Day {day}: "
        f"{last_error}"

    )


# ============================================================
# GET DN VALUE SAFELY
# ============================================================

def get_dn(
    properties
):

    dn = (
        properties.get(
            "dn"
        )
    )


    if (
        dn is None
    ):

        dn = (
            properties.get(
                "DN"
            )
        )


    try:

        return int(
            dn
        )

    except (
        TypeError,
        ValueError
    ):

        return None


# ============================================================
# NORMALIZE FEATURE PROPERTIES
# ============================================================

def normalize_feature_properties(
    feature,
    day,
):

    properties = (
        feature.get(
            "properties",
            {}
        )
        or {}
    )


    dn = (
        get_dn(
            properties
        )
    )


    category = (
        CATEGORY_INFO.get(
            dn,
            {}
        )
    )


    # ========================================================
    # LABEL
    # ========================================================

    category_name = (

        category.get(
            "name"
        )

        or

        properties.get(
            "label"
        )

        or

        properties.get(
            "LABEL"
        )

        or

        "Unknown"

    )


    risk_code = (

        category.get(
            "label"
        )

        or

        category_name

    )


    probability = (

        category.get(
            "probability"
        )

        or

        ""

    )


    # ========================================================
    # COLORS
    # ========================================================

    fill = (

        properties.get(
            "fill"
        )

        or

        category.get(
            "fill"
        )

        or

        "#888888"

    )


    stroke = (

        properties.get(
            "stroke"
        )

        or

        category.get(
            "stroke"
        )

        or

        "#000000"

    )


    # ========================================================
    # STANDARDIZED VALUES FOR GRAPHICS.JS
    # ========================================================

    properties[
        "day"
    ] = day


    properties[
        "dn"
    ] = dn


    properties[
        "category"
    ] = category_name


    properties[
        "risk"
    ] = risk_code


    properties[
        "probability"
    ] = probability


    properties[
        "fill"
    ] = fill


    properties[
        "stroke"
    ] = stroke


    feature[
        "properties"
    ] = properties


    return feature


# ============================================================
# NORMALIZE GEOJSON
# ============================================================

def normalize_geojson(
    data,
    day,
):

    cleaned_features = []


    for feature in data.get(
        "features",
        []
    ):

        geometry = (
            feature.get(
                "geometry"
            )
        )


        if (
            not geometry
        ):

            continue


        cleaned_feature = (
            normalize_feature_properties(

                feature,

                day

            )
        )


        cleaned_features.append(
            cleaned_feature
        )


    return {

        "type":
            "FeatureCollection",

        "features":
            cleaned_features,

    }


# ============================================================
# WRITE GEOJSON
# ============================================================

def write_geojson(
    data,
    filename,
):

    output_file = (
        OUTPUT_DIR
        /
        filename
    )


    with output_file.open(

        "w",

        encoding=
            "utf-8"

    ) as file:

        json.dump(

            data,

            file,

            separators=(
                ",",
                ":"
            ),

        )


    print(
        f"Wrote: "
        f"{output_file}"
    )


    return output_file


# ============================================================
# PRINT ERO SUMMARY
# ============================================================

def print_ero_info(
    day,
    data,
):

    print()
    print(
        f"WPC DAY {day} ERO SUMMARY"
    )

    print("-" * 70)


    categories = []


    for feature in data.get(
        "features",
        []
    ):

        properties = (
            feature.get(
                "properties",
                {}
            )
        )


        category = (
            properties.get(
                "category"
            )
        )


        if (
            category
            and
            category not in categories
        ):

            categories.append(
                category
            )


    print(
        "Categories:",
        ", ".join(
            categories
        )
    )


    print(
        "Number of polygons:",
        len(
            data.get(
                "features",
                []
            )
        )
    )


# ============================================================
# PROCESS ONE DAY
# ============================================================

def process_day(
    day,
    config,
):

    layer_id = (
        config[
            "layer_id"
        ]
    )


    filename = (
        config[
            "filename"
        ]
    )


    print()
    print(
        f"Processing WPC ERO Day {day}"
    )


    # ========================================================
    # DOWNLOAD
    # ========================================================

    raw_data = (
        fetch_wpc_geojson(

            day,

            layer_id

        )
    )


    # ========================================================
    # NORMALIZE
    # ========================================================

    data = (
        normalize_geojson(

            raw_data,

            day

        )
    )


    # ========================================================
    # VERIFY VALID FEATURES
    # ========================================================

    if (
        len(
            data["features"]
        )
        == 0
    ):

        raise RuntimeError(

            f"WPC Day {day} "
            "contains no valid geometries."

        )


    # ========================================================
    # WRITE
    # ========================================================

    output_file = (
        write_geojson(

            data,

            filename

        )
    )


    print_ero_info(

        day,

        data

    )


    return output_file


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)

    print(
        "WPC DAY 1 / DAY 2 / DAY 3 "
        "EXCESSIVE RAINFALL OUTLOOK UPDATE"
    )

    print("=" * 70)


    print()
    print(
        f"Output directory: "
        f"{OUTPUT_DIR}"
    )


    completed = []


    failed = []


    # ========================================================
    # DAYS 1 THROUGH 3
    # ========================================================

    for day, config in (
        WPC_ERO_LAYERS.items()
    ):

        try:

            output_file = (
                process_day(

                    day,

                    config

                )
            )


            completed.append(
                (
                    day,
                    output_file
                )
            )


        except Exception as error:

            print()
            print("=" * 70)

            print(
                f"ERROR updating "
                f"WPC Day {day}"
            )

            print("=" * 70)


            print(
                error
            )


            failed.append(
                (
                    day,
                    str(
                        error
                    )
                )
            )


    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 70)

    print(
        "WPC ERO UPDATE SUMMARY"
    )

    print("=" * 70)


    for (
        day,
        output_file
    ) in completed:

        print(
            f"Day {day}: OK"
        )

        print(
            f"  {output_file}"
        )


    for (
        day,
        error
    ) in failed:

        print(
            f"Day {day}: FAILED"
        )

        print(
            f"  {error}"
        )


    print()

    print(
        f"Successful: "
        f"{len(completed)}"
    )


    print(
        f"Failed: "
        f"{len(failed)}"
    )


    if (
        len(completed)
        == 0
    ):

        raise RuntimeError(

            "No WPC ERO files "
            "were successfully updated."

        )


    if failed:

        print()

        print(
            "WARNING: One or more "
            "WPC ERO days failed."
        )


    print()

    print(
        "WPC ERO update complete."
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
