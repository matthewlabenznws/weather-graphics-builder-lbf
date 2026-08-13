# ============================================================
# METAR OBSERVATION UPDATER
#
# Source:
#   Aviation Weather Center Data API
#
# Output:
#   data/metar.geojson
#
# Expected properties for graphics.js:
#
#   station
#   temp_f
#   dewpoint_f
#   rh
#   wind_dir_deg
#   wind_speed_mph
#   wind_gust_mph
#
# ============================================================

import json
import math
import time
from pathlib import Path

import requests


# ============================================================
# AWC METAR API
# ============================================================

METAR_API_URL = (
    "https://aviationweather.gov/api/data/metar"
)


# ============================================================
# OUTPUT
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)


DATA_DIR = (
    BASE_DIR
    / "data"
)


DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)


OUTPUT_FILE = (
    DATA_DIR
    / "metar.geojson"
)


# ============================================================
# DOMAIN
#
# Large enough to cover the LBF graphics area and surrounding
# stations.
#
# Change these later if you want a larger domain.
# ============================================================

WEST = -106.0
EAST = -95.0
SOUTH = 36.5
NORTH = 46.5


# ============================================================
# REQUEST SETTINGS
# ============================================================

REQUEST_TIMEOUT_SECONDS = 60

DOWNLOAD_ATTEMPTS = 4

RETRY_SLEEP_SECONDS = 5


HEADERS = {

    "User-Agent":
        "NWS-North-Platte-Weather-Graphics-Builder/1.0",

    "Accept":
        "application/json"

}


# ============================================================
# UNIT CONVERSIONS
# ============================================================

KNOTS_TO_MPH = 1.150779448


def c_to_f(
    value
):

    if value is None:
        return None


    try:

        return (
            float(value)
            *
            9.0
            /
            5.0
            +
            32.0
        )

    except Exception:

        return None


def knots_to_mph(
    value
):

    if value is None:
        return None


    try:

        return (
            float(value)
            *
            KNOTS_TO_MPH
        )

    except Exception:

        return None


# ============================================================
# RELATIVE HUMIDITY
#
# Magnus formula using temperature and dew point in Celsius.
# ============================================================

def calculate_rh(
    temp_c,
    dewpoint_c
):

    if (
        temp_c is None
        or
        dewpoint_c is None
    ):

        return None


    try:

        temp_c = float(
            temp_c
        )


        dewpoint_c = float(
            dewpoint_c
        )


        a = 17.625
        b = 243.04


        numerator = math.exp(

            (
                a
                *
                dewpoint_c
            )
            /
            (
                b
                +
                dewpoint_c
            )

        )


        denominator = math.exp(

            (
                a
                *
                temp_c
            )
            /
            (
                b
                +
                temp_c
            )

        )


        rh = (
            100.0
            *
            numerator
            /
            denominator
        )


        rh = max(
            0.0,
            min(
                100.0,
                rh
            )
        )


        return rh


    except Exception:

        return None


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(
    value
):

    if (
        value is None
        or
        value == ""
    ):

        return None


    try:

        return float(
            value
        )

    except Exception:

        return None


# ============================================================
# SAFE INT
# ============================================================

def safe_int(
    value
):

    number = safe_float(
        value
    )


    if number is None:

        return None


    return int(
        round(
            number
        )
    )


# ============================================================
# API REQUEST
# ============================================================

def request_metars():

    last_error = None


    # ========================================================
    # AWC supports a geographic bounding box through bbox.
    #
    # Format:
    #   min_lon,min_lat,max_lon,max_lat
    #
    # Request the most recent observations.
    # ========================================================

    params = {

        "format":
            "json",

        "bbox":
            f"{WEST},{SOUTH},{EAST},{NORTH}",

        "hours":
            "2"

    }


    for attempt in range(
        1,
        DOWNLOAD_ATTEMPTS + 1
    ):

        try:

            print()
            print("=" * 70)

            print(
                "Downloading METAR observations"
            )

            print(
                f"Attempt "
                f"{attempt}/"
                f"{DOWNLOAD_ATTEMPTS}"
            )

            print("=" * 70)


            response = requests.get(

                METAR_API_URL,

                params=params,

                headers=HEADERS,

                timeout=
                    REQUEST_TIMEOUT_SECONDS

            )


            response.raise_for_status()


            data = (
                response.json()
            )


            if (
                not isinstance(
                    data,
                    list
                )
            ):

                raise RuntimeError(

                    "AWC METAR response was not a JSON list."

                )


            print(
                f"Downloaded "
                f"{len(data)} METAR records."
            )


            return data


        except Exception as error:

            last_error = error


            print(
                f"METAR request failed: "
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

        f"Could not download METAR data: "
        f"{last_error}"

    )


# ============================================================
# GET VALUE USING POSSIBLE FIELD NAMES
# ============================================================

def get_field(
    record,
    *names
):

    for name in names:

        if name in record:

            value = (
                record.get(
                    name
                )
            )


            if (
                value is not None
                and
                value != ""
            ):

                return value


    return None


# ============================================================
# NORMALIZE ONE METAR
# ============================================================

def normalize_metar(
    record
):

    # ========================================================
    # STATION
    # ========================================================

    station = get_field(

        record,

        "icaoId",

        "station_id",

        "station",

        "id"

    )


    if not station:

        return None


    station = (
        str(
            station
        )
        .strip()
        .upper()
    )


    # ========================================================
    # LOCATION
    # ========================================================

    lat = safe_float(

        get_field(

            record,

            "lat",

            "latitude"

        )

    )


    lon = safe_float(

        get_field(

            record,

            "lon",

            "longitude"

        )

    )


    if (
        lat is None
        or
        lon is None
    ):

        return None


    # ========================================================
    # DOMAIN CHECK
    # ========================================================

    if (
        lon < WEST
        or
        lon > EAST
        or
        lat < SOUTH
        or
        lat > NORTH
    ):

        return None


    # ========================================================
    # TEMPERATURE / DEWPOINT
    # ========================================================

    temp_c = safe_float(

        get_field(

            record,

            "temp",

            "tempC",

            "temperature"

        )

    )


    dewpoint_c = safe_float(

        get_field(

            record,

            "dewp",

            "dewpoint",

            "dewpointC"

        )

    )


    temp_f = c_to_f(
        temp_c
    )


    dewpoint_f = c_to_f(
        dewpoint_c
    )


    rh = calculate_rh(

        temp_c,

        dewpoint_c

    )


    # ========================================================
    # WIND
    # ========================================================

    wind_dir = safe_float(

        get_field(

            record,

            "wdir",

            "windDir",

            "wind_dir_degrees"

        )

    )


    wind_speed_kt = safe_float(

        get_field(

            record,

            "wspd",

            "windSpeed",

            "wind_speed_kt"

        )

    )


    wind_gust_kt = safe_float(

        get_field(

            record,

            "wgst",

            "windGust",

            "wind_gust_kt"

        )

    )


    wind_speed_mph = (
        knots_to_mph(
            wind_speed_kt
        )
    )


    wind_gust_mph = (
        knots_to_mph(
            wind_gust_kt
        )
    )


    # ========================================================
    # OBSERVATION TIME
    # ========================================================

    observation_time = get_field(

        record,

        "obsTime",

        "observation_time",

        "reportTime",

        "receiptTime"

    )


    # ========================================================
    # RAW METAR
    # ========================================================

    raw_metar = get_field(

        record,

        "rawOb",

        "raw_text",

        "raw"

    )


    # ========================================================
    # OPTIONAL CONDITIONS
    # ========================================================

    visibility = safe_float(

        get_field(

            record,

            "visib",

            "visibility"

        )

    )


    altimeter = safe_float(

        get_field(

            record,

            "altim",

            "altimeter"

        )

    )


    flight_category = get_field(

        record,

        "fltCat",

        "flight_category"

    )


    # ========================================================
    # FEATURE
    # ========================================================

    feature = {

        "type":
            "Feature",

        "geometry": {

            "type":
                "Point",

            "coordinates": [

                lon,

                lat

            ]

        },

        "properties": {

            "station":
                station,

            "temp_f":
                round(
                    temp_f,
                    1
                )
                if temp_f is not None
                else None,

            "dewpoint_f":
                round(
                    dewpoint_f,
                    1
                )
                if dewpoint_f is not None
                else None,

            "rh":
                round(
                    rh,
                    1
                )
                if rh is not None
                else None,

            "wind_dir_deg":
                round(
                    wind_dir,
                    0
                )
                if wind_dir is not None
                else None,

            "wind_speed_mph":
                round(
                    wind_speed_mph,
                    1
                )
                if wind_speed_mph is not None
                else None,

            "wind_gust_mph":
                round(
                    wind_gust_mph,
                    1
                )
                if wind_gust_mph is not None
                else None,

            "wind_speed_kt":
                round(
                    wind_speed_kt,
                    1
                )
                if wind_speed_kt is not None
                else None,

            "wind_gust_kt":
                round(
                    wind_gust_kt,
                    1
                )
                if wind_gust_kt is not None
                else None,

            "visibility_sm":
                visibility,

            "altimeter":
                altimeter,

            "flight_category":
                flight_category,

            "observation_time":
                observation_time,

            "raw_metar":
                raw_metar

        }

    }


    return feature


# ============================================================
# OBSERVATION TIME SORT VALUE
# ============================================================

def observation_sort_value(
    record
):

    value = get_field(

        record,

        "obsTime",

        "observation_time",

        "reportTime",

        "receiptTime"

    )


    if (
        value is None
    ):

        return ""


    return str(
        value
    )


# ============================================================
# KEEP MOST RECENT REPORT PER STATION
# ============================================================

def keep_latest_per_station(
    records
):

    latest = {}


    # Sort oldest -> newest.
    # Newer records overwrite older ones.

    records = sorted(

        records,

        key=
            observation_sort_value

    )


    for record in records:

        station = get_field(

            record,

            "icaoId",

            "station_id",

            "station",

            "id"

        )


        if not station:

            continue


        station = (
            str(
                station
            )
            .strip()
            .upper()
        )


        latest[
            station
        ] = record


    return list(
        latest.values()
    )


# ============================================================
# WRITE GEOJSON
# ============================================================

def write_geojson(
    features
):

    output = {

        "type":
            "FeatureCollection",

        "features":
            features

    }


    with OUTPUT_FILE.open(

        "w",

        encoding=
            "utf-8"

    ) as file:

        json.dump(

            output,

            file,

            separators=(
                ",",
                ":"
            )

        )


    print()
    print(
        f"Wrote: "
        f"{OUTPUT_FILE}"
    )


# ============================================================
# PRINT SUMMARY
# ============================================================

def print_summary(
    features
):

    print()
    print("=" * 70)

    print(
        "METAR SUMMARY"
    )

    print("=" * 70)


    print(
        f"Stations written: "
        f"{len(features)}"
    )


    gust_features = [

        feature

        for feature in features

        if (
            feature
            .get(
                "properties",
                {}
            )
            .get(
                "wind_gust_mph"
            )
            is not None
        )

    ]


    print(
        f"Stations reporting gusts: "
        f"{len(gust_features)}"
    )


    if gust_features:

        strongest = max(

            gust_features,

            key=lambda feature:

                feature[
                    "properties"
                ][
                    "wind_gust_mph"
                ]

        )


        properties = (
            strongest[
                "properties"
            ]
        )


        print(

            f"Strongest gust: "
            f"{properties['station']} "
            f"{properties['wind_gust_mph']} mph"

        )


    print()
    print(
        "Sample stations:"
    )


    for feature in (
        features[
            :15
        ]
    ):

        properties = (
            feature[
                "properties"
            ]
        )


        print(

            f"  "
            f"{properties['station']}: "

            f"T={properties['temp_f']}F, "

            f"Td={properties['dewpoint_f']}F, "

            f"RH={properties['rh']}%, "

            f"Wind={properties['wind_dir_deg']} "
            f"@ {properties['wind_speed_mph']} mph, "

            f"Gust={properties['wind_gust_mph']} mph"

        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)

    print(
        "METAR OBSERVATION UPDATE"
    )

    print("=" * 70)


    print(
        f"Domain: "
        f"{WEST} to {EAST} longitude, "
        f"{SOUTH} to {NORTH} latitude"
    )


    # ========================================================
    # DOWNLOAD
    # ========================================================

    records = (
        request_metars()
    )


    # ========================================================
    # KEEP LATEST OBSERVATION PER STATION
    # ========================================================

    records = (
        keep_latest_per_station(
            records
        )
    )


    print(
        f"Unique stations after latest-report filter: "
        f"{len(records)}"
    )


    # ========================================================
    # NORMALIZE
    # ========================================================

    features = []


    skipped = 0


    for record in records:

        feature = (
            normalize_metar(
                record
            )
        )


        if (
            feature is None
        ):

            skipped += 1

            continue


        features.append(
            feature
        )


    # ========================================================
    # SORT BY STATION NAME
    # ========================================================

    features.sort(

        key=lambda feature:

            feature[
                "properties"
            ][
                "station"
            ]

    )


    print(
        f"Valid stations: "
        f"{len(features)}"
    )


    print(
        f"Skipped records: "
        f"{skipped}"
    )


    # ========================================================
    # SAFETY
    #
    # Do not overwrite a previously valid file if the API
    # unexpectedly returns nothing.
    # ========================================================

    if (
        len(features)
        ==
        0
    ):

        raise RuntimeError(

            "No valid METAR stations were produced. "
            "Existing metar.geojson was not overwritten."

        )


    # ========================================================
    # WRITE
    # ========================================================

    write_geojson(
        features
    )


    # ========================================================
    # SUMMARY
    # ========================================================

    print_summary(
        features
    )


    print()
    print(
        "METAR update complete."
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
