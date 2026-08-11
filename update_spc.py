# ============================================================
# SPC DAY 1 / DAY 2 / DAY 3 CATEGORICAL OUTLOOK UPDATER
#
# Downloads categorical outlook polygons from the NOAA/NWS
# ArcGIS REST service and writes:
#
#   site/data/spc_day1_cat.geojson
#   site/data/spc_day2_cat.geojson
#   site/data/spc_day3_cat.geojson
#
# These GeoJSON files are then read directly by graphics.js.
# ============================================================


import json
import time

from pathlib import Path

import requests


# ============================================================
# NOAA / NWS SPC MAP SERVICE
# ============================================================

SPC_MAPSERVER = (
    "https://mapservices.weather.noaa.gov/vector/rest/services/"
    "outlooks/SPC_wx_outlks/MapServer"
)


# ============================================================
# CATEGORICAL LAYER IDS
#
# Day 1 categorical = 1
# Day 2 categorical = 9
# Day 3 categorical = 17
# ============================================================

SPC_LAYERS = {

    1: {
        "name": "Day 1",
        "layer_id": 1,
        "filename": "spc_day1_cat.geojson",
    },

    2: {
        "name": "Day 2",
        "layer_id": 9,
        "filename": "spc_day2_cat.geojson",
    },

    3: {
        "name": "Day 3",
        "layer_id": 17,
        "filename": "spc_day3_cat.geojson",
    },

}


# ============================================================
# OUTPUT DIRECTORY
#
# If update_spc.py is in the repository root and your site is:
#
# repository/
# ├── update_spc.py
# └── site/
#     └── data/
#
# this writes directly into site/data.
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)


OUTPUT_DIR = (
    BASE_DIR
    / "site"
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
# SPC CATEGORY INFORMATION
#
# dn values from the NOAA/NWS categorical outlook layers:
#
# 2 = Thunderstorm
# 3 = Marginal
# 4 = Slight
# 5 = Enhanced
# 6 = Moderate
# 8 = High
#
# The service already provides fill/stroke values, but this
# table gives us a reliable fallback.
# ============================================================

CATEGORY_INFO = {

    2: {
        "label": "TSTM",
        "name": "Thunderstorm",
        "fill": "#C1E9C1",
        "stroke": "#55BB55",
    },

    3: {
        "label": "MRGL",
        "name": "Marginal",
        "fill": "#66A366",
        "stroke": "#005500",
    },

    4: {
        "label": "SLGT",
        "name": "Slight",
        "fill": "#FFE066",
        "stroke": "#DDAA00",
    },

    5: {
        "label": "ENH",
        "name": "Enhanced",
        "fill": "#FFA366",
        "stroke": "#FF6600",
    },

    6: {
        "label": "MDT",
        "name": "Moderate",
        "fill": "#E06666",
        "stroke": "#CC0000",
    },

    8: {
        "label": "HIGH",
        "name": "High",
        "fill": "#EE99EE",
        "stroke": "#CC00CC",
    },

}


# ============================================================
# DOWNLOAD ONE CATEGORICAL OUTLOOK
# ============================================================

def fetch_spc_geojson(
    day,
    layer_id,
):

    url = (
        f"{SPC_MAPSERVER}/"
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
                f"Downloading SPC Day {day} "
                f"Categorical Outlook"
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
                "features" not in data
            ):

                raise RuntimeError(

                    "SPC response did not contain "
                    "a features array."

                )


            if (
                len(
                    data["features"]
                )
                == 0
            ):

                raise RuntimeError(

                    f"SPC Day {day} returned "
                    "zero categorical polygons."

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
        f"SPC Day {day}: "
        f"{last_error}"

    )


# ============================================================
# CLEAN / NORMALIZE PROPERTIES
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


    # ========================================================
    # DN / CATEGORY
    # ========================================================

    dn = properties.get(
        "dn"
    )


    try:

        dn = int(
            dn
        )

    except (
        TypeError,
        ValueError
    ):

        dn = None


    fallback = (
        CATEGORY_INFO.get(
            dn,
            {}
        )
    )


    # ========================================================
    # LABEL
    #
    # NOAA often returns:
    #
    # Thunderstorm
    # Marginal
    # Slight
    # Enhanced
    # Moderate
    # High
    #
    # We also preserve a short risk code.
    # ========================================================

    service_label = (
        properties.get(
            "label"
        )
    )


    category_name = (
        fallback.get(
            "name"
        )
        or service_label
        or "Unknown"
    )


    risk_code = (
        fallback.get(
            "label"
        )
        or str(
            service_label
            or ""
        )
    )


    # ========================================================
    # COLORS
    #
    # Prefer colors provided by NOAA.
    #
    # If missing, use fallback colors above.
    # ========================================================

    fill = (
        properties.get(
            "fill"
        )
        or fallback.get(
            "fill"
        )
        or "#888888"
    )


    stroke = (
        properties.get(
            "stroke"
        )
        or fallback.get(
            "stroke"
        )
        or "#000000"
    )


    # ========================================================
    # CLEAN PROPERTY OBJECT
    #
    # Keep original fields AND add standardized fields.
    # ========================================================

    properties[
        "day"
    ] = day


    properties[
        "category"
    ] = category_name


    properties[
        "risk"
    ] = risk_code


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
# NORMALIZE ENTIRE GEOJSON
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

        if (
            not feature.get(
                "geometry"
            )
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
        / filename
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
# PRINT OUTLOOK INFORMATION
# ============================================================

def print_outlook_info(
    day,
    data,
):

    print()
    print(
        f"SPC DAY {day} SUMMARY"
    )

    print("-" * 70)


    categories = []


    valid_times = set()

    issue_times = set()

    expire_times = set()


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


        valid = (
            properties.get(
                "valid"
            )
        )


        issue = (
            properties.get(
                "issue"
            )
        )


        expire = (
            properties.get(
                "expire"
            )
        )


        if valid:

            valid_times.add(
                str(valid)
            )


        if issue:

            issue_times.add(
                str(issue)
            )


        if expire:

            expire_times.add(
                str(expire)
            )


    print(
        "Categories:",
        ", ".join(
            categories
        )
    )


    if issue_times:

        print(
            "Issue:",
            " | ".join(
                sorted(
                    issue_times
                )
            )
        )


    if valid_times:

        print(
            "Valid:",
            " | ".join(
                sorted(
                    valid_times
                )
            )
        )


    if expire_times:

        print(
            "Expire:",
            " | ".join(
                sorted(
                    expire_times
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


    raw_data = (
        fetch_spc_geojson(
            day,
            layer_id
        )
    )


    data = (
        normalize_geojson(
            raw_data,
            day
        )
    )


    if (
        len(
            data["features"]
        )
        == 0
    ):

        raise RuntimeError(

            f"SPC Day {day} "
            "contains no valid geometries."

        )


    output_file = (
        write_geojson(
            data,
            filename
        )
    )


    print_outlook_info(
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
        "SPC DAY 1 / DAY 2 / DAY 3 "
        "OUTLOOK UPDATE"
    )
    print("=" * 70)


    completed = []


    failed = []


    for day, config in (
        SPC_LAYERS.items()
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
            print(
                f"ERROR updating "
                f"Day {day}:"
            )

            print(
                error
            )


            failed.append(
                (
                    day,
                    str(error)
                )
            )


    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 70)

    print(
        "SPC OUTLOOK UPDATE SUMMARY"
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


    # If absolutely nothing worked,
    # fail the GitHub workflow.

    if (
        len(completed)
        == 0
    ):

        raise RuntimeError(

            "No SPC outlook files "
            "were successfully updated."

        )


    print()
    print(
        "SPC update complete."
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
