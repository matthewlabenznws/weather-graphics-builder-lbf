# ============================================================
# SPC DAY 1 / DAY 2 FIRE WEATHER OUTLOOK UPDATER
#
# Downloads the complete SPC Fire Weather Outlook for:
#
#   Day 1:
#       Layer 1 = Elevated / Critical / Extreme
#       Layer 2 = Dry Thunderstorm
#
#   Day 2:
#       Layer 4 = Elevated / Critical / Extreme
#       Layer 5 = Dry Thunderstorm
#
# The two sublayers for each day are merged into ONE GeoJSON:
#
#   data/spc_fire_day1.geojson
#   data/spc_fire_day2.geojson
#
# Each feature includes:
#
#   day
#   outlook_type
#   category
#   risk
#   fill
#   stroke
#
# This lets graphics.js display each complete day with one toggle.
# ============================================================


import json
import time

from pathlib import Path

import requests


# ============================================================
# NOAA / NWS SPC FIRE WEATHER SERVICE
# ============================================================

SPC_FIRE_MAPSERVER = (
    "https://mapservices.weather.noaa.gov/vector/rest/services/"
    "fire_weather/SPC_firewx/MapServer"
)


# ============================================================
# FIRE WEATHER LAYERS
#
# Official NOAA service:
#
# Day 1:
#   1 = Wind / RH outlook
#   2 = Dry Thunderstorm outlook
#
# Day 2:
#   4 = Wind / RH outlook
#   5 = Dry Thunderstorm outlook
# ============================================================

FIREWX_CONFIG = {

    1: {

        "filename":
            "spc_fire_day1.geojson",

        "layers": [

            {
                "layer_id":
                    1,

                "type":
                    "fire"
            },

            {
                "layer_id":
                    2,

                "type":
                    "dry_thunder"
            }

        ]

    },


    2: {

        "filename":
            "spc_fire_day2.geojson",

        "layers": [

            {
                "layer_id":
                    4,

                "type":
                    "fire"
            },

            {
                "layer_id":
                    5,

                "type":
                    "dry_thunder"
            }

        ]

    }

}


# ============================================================
# OUTPUT DIRECTORY
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

REQUEST_TIMEOUT_SECONDS =
    45


DOWNLOAD_ATTEMPTS =
    3


RETRY_SLEEP_SECONDS =
    5


# ============================================================
# NORMAL FIRE WEATHER CATEGORIES
#
# NOAA SPC renderer:
#
# 5  = Elevated
# 8  = Critical
# 10 = Extreme
# ============================================================

FIRE_CATEGORY_INFO = {

    5: {

        "category":
            "Elevated",

        "risk":
            "ELEV",

        "fill":
            "#E69800",

        "stroke":
            "#9B6500"

    },


    8: {

        "category":
            "Critical",

        "risk":
            "CRIT",

        "fill":
            "#FF0000",

        "stroke":
            "#9E0000"

    },


    10: {

        "category":
            "Extremely Critical",

        "risk":
            "EXTM",

        "fill":
            "#E600A9",

        "stroke":
            "#8F0069"

    }

}


# ============================================================
# DRY THUNDERSTORM CATEGORIES
#
# NOAA SPC renderer:
#
# 5 = Isolated Dry Thunderstorm
# 8 = Scattered Dry Thunderstorm
#
# These are kept in the SAME output file.
# ============================================================

DRYT_CATEGORY_INFO = {

    5: {

        "category":
            "Isolated Dry Thunderstorm",

        "risk":
            "ISODRYT",

        "fill":
            "#732600",

        "stroke":
            "#4A1800"

    },


    8: {

        "category":
            "Scattered Dry Thunderstorm",

        "risk":
            "SCTDRYT",

        "fill":
            "#FF0000",

        "stroke":
            "#9E0000"

    }

}


# ============================================================
# FETCH ONE FEATURE LAYER
# ============================================================

def fetch_layer(
    day,
    layer_id,
    outlook_type,
):

    url = (
        f"{SPC_FIRE_MAPSERVER}/"
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
                f"Downloading SPC Fire Weather "
                f"Day {day}"
            )

            print(
                f"Layer ID: {layer_id}"
            )

            print(
                f"Type: {outlook_type}"
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

                    "SPC Fire Weather response "
                    "did not contain a features array."

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

                time.sleep(
                    RETRY_SLEEP_SECONDS
                )


    raise RuntimeError(

        f"Could not download "
        f"SPC Fire Weather Day {day}, "
        f"layer {layer_id}: "
        f"{last_error}"

    )


# ============================================================
# SAFE INTEGER DN
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
# NORMALIZE ONE FEATURE
# ============================================================

def normalize_feature(
    feature,
    day,
    outlook_type,
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


    # ========================================================
    # NORMAL FIRE WEATHER
    # ========================================================

    if (
        outlook_type
        ==
        "fire"
    ):

        info = (
            FIRE_CATEGORY_INFO.get(
                dn,
                {}
            )
        )


    # ========================================================
    # DRY THUNDERSTORM
    # ========================================================

    else:

        info = (
            DRYT_CATEGORY_INFO.get(
                dn,
                {}
            )
        )


    category = (
        info.get(
            "category"
        )
        or
        "Unknown"
    )


    risk = (
        info.get(
            "risk"
        )
        or
        "UNKNOWN"
    )


    fill = (
        info.get(
            "fill"
        )
        or
        "#888888"
    )


    stroke = (
        info.get(
            "stroke"
        )
        or
        "#000000"
    )


    properties[
        "day"
    ] = day


    properties[
        "outlook_type"
    ] = outlook_type


    properties[
        "dn"
    ] = dn


    properties[
        "category"
    ] = category


    properties[
        "risk"
    ] = risk


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
# NORMALIZE ONE LAYER
# ============================================================

def normalize_layer(
    data,
    day,
    outlook_type,
):

    cleaned = []


    for feature in data.get(
        "features",
        []
    ):

        if (
            not feature.get(
                "geometry"
            )
        ):

            continue


        cleaned.append(

            normalize_feature(

                feature,

                day,

                outlook_type

            )

        )


    return cleaned


# ============================================================
# PROCESS ONE DAY
# ============================================================

def process_day(
    day,
    config,
):

    all_features = []


    for layer_config in (
        config[
            "layers"
        ]
    ):

        layer_id = (
            layer_config[
                "layer_id"
            ]
        )


        outlook_type = (
            layer_config[
                "type"
            ]
        )


        raw_data = (
            fetch_layer(

                day,

                layer_id,

                outlook_type

            )
        )


        normalized = (
            normalize_layer(

                raw_data,

                day,

                outlook_type

            )
        )


        all_features.extend(
            normalized
        )


    # ========================================================
    # EMPTY OUTLOOK IS VALID
    #
    # For example, there may be no dry-thunderstorm polygons.
    # The regular outlook may also be empty on a quiet day.
    # ========================================================

    output_data = {

        "type":
            "FeatureCollection",

        "features":
            all_features

    }


    filename = (
        config[
            "filename"
        ]
    )


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

            output_data,

            file,

            separators=(
                ",",
                ":"
            )

        )


    print()
    print(
        f"Wrote:"
    )

    print(
        output_file
    )


    print(
        f"Total Day {day} features: "
        f"{len(all_features)}"
    )


    # ========================================================
    # PRINT CATEGORIES
    # ========================================================

    categories = []


    for feature in all_features:

        category = (
            feature
            .get(
                "properties",
                {}
            )
            .get(
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


    if categories:

        print(
            "Categories:"
        )


        for category in categories:

            print(
                f"  - {category}"
            )


    else:

        print(
            "No fire-weather polygons "
            "were present for this day."
        )


    return output_file


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)

    print(
        "SPC DAY 1 / DAY 2 "
        "FIRE WEATHER OUTLOOK UPDATE"
    )

    print("=" * 70)


    print(
        f"Output directory: "
        f"{OUTPUT_DIR}"
    )


    completed = []


    failed = []


    for day, config in (
        FIREWX_CONFIG.items()
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
                f"SPC Fire Weather Day {day}"
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
        "SPC FIRE WEATHER UPDATE SUMMARY"
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

            "No SPC Fire Weather files "
            "were successfully updated."

        )


    print()
    print(
        "SPC Fire Weather update complete."
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
