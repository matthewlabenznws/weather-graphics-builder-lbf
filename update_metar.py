#!/usr/bin/env python3

# ============================================================
# NWS LBF WEATHER GRAPHICS BUILDER
# METAR OBSERVATION UPDATER
#
# Data source:
# Aviation Weather Center METAR cache
#
# Output:
# data/metars.geojson
# ============================================================

from __future__ import annotations

import gzip
import io
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests


# ============================================================
# CONFIGURATION
# ============================================================

METAR_CACHE_URL = (
    "https://aviationweather.gov/"
    "data/cache/metars.cache.csv.gz"
)

OUTPUT_FILE = Path("data/metars.geojson")


# ============================================================
# MAP DOMAIN
#
# Central Plains / surrounding region.
# Change these later if you want.
# ============================================================

WEST = -106.0
EAST = -95.0

SOUTH = 36.5
NORTH = 46.5


# ============================================================
# AGE LIMIT
#
# The AWC cache contains current observations, but this provides
# another safeguard against plotting old stations.
# ============================================================

MAX_OBSERVATION_AGE_HOURS = 3.0


# ============================================================
# NETWORK SETTINGS
# ============================================================

REQUEST_TIMEOUT_SECONDS = 90

MAX_DOWNLOAD_ATTEMPTS = 5

RETRY_WAIT_SECONDS = 10


HEADERS = {

    "User-Agent":
        "NWS-LBF-Weather-Graphics-Builder/1.0",

    "Accept":
        "*/*"

}


# ============================================================
# UTILITY
# ============================================================

def safe_float(value):

    try:

        if pd.isna(value):
            return None

        value = float(value)

        if not math.isfinite(value):
            return None

        return value

    except Exception:
        return None


# ============================================================
# FIND COLUMN
#
# AWC has changed cache field naming in the past, so don't
# hard-code only one possible spelling.
# ============================================================

def find_column(
    df,
    candidates,
    required=False
):

    lookup = {

        str(column).strip().lower():
            column

        for column in df.columns

    }

    for candidate in candidates:

        key = candidate.lower()

        if key in lookup:
            return lookup[key]

    if required:

        raise RuntimeError(

            "Could not find required column. "
            f"Tried: {candidates}\n\n"
            f"Available columns:\n{list(df.columns)}"

        )

    return None


# ============================================================
# DOWNLOAD METAR CACHE
# ============================================================

def download_metar_cache():

    last_error = None

    for attempt in range(
        1,
        MAX_DOWNLOAD_ATTEMPTS + 1
    ):

        print()
        print("=" * 70)

        print(
            "Downloading Aviation Weather Center METAR cache"
        )

        print(
            f"Attempt {attempt}/{MAX_DOWNLOAD_ATTEMPTS}"
        )

        print("=" * 70)

        try:

            response = requests.get(

                METAR_CACHE_URL,

                headers=HEADERS,

                timeout=REQUEST_TIMEOUT_SECONDS

            )

            response.raise_for_status()

            content = response.content

            if not content:

                raise RuntimeError(
                    "AWC returned an empty response."
                )

            print(
                f"Downloaded {len(content):,} compressed bytes."
            )

            return content

        except Exception as exc:

            last_error = exc

            print(
                f"METAR cache request failed: {exc}"
            )

            if attempt < MAX_DOWNLOAD_ATTEMPTS:

                print(
                    f"Waiting {RETRY_WAIT_SECONDS} seconds..."
                )

                time.sleep(
                    RETRY_WAIT_SECONDS
                )

    raise RuntimeError(

        "Could not download the AWC METAR cache "
        f"after {MAX_DOWNLOAD_ATTEMPTS} attempts. "
        f"Last error: {last_error}"

    )


# ============================================================
# READ COMPRESSED CSV
# ============================================================

def read_metar_cache(
    compressed_data
):

    print()
    print("=" * 70)
    print("Reading METAR cache")
    print("=" * 70)

    try:

        with gzip.GzipFile(

            fileobj=io.BytesIO(
                compressed_data
            )

        ) as gz:

            raw_csv = gz.read()

    except Exception as exc:

        raise RuntimeError(

            f"Could not decompress METAR cache: {exc}"

        ) from exc


    # --------------------------------------------------------
    # AWC cache files may contain comment/header lines.
    # pandas comment="#" safely ignores those.
    # --------------------------------------------------------

    try:

        df = pd.read_csv(

            io.BytesIO(
                raw_csv
            ),

            comment="#",

            low_memory=False

        )

    except Exception as exc:

        raise RuntimeError(

            f"Could not parse METAR CSV: {exc}"

        ) from exc


    print(
        f"Rows in full AWC cache: {len(df):,}"
    )


    print()
    print("METAR columns:")

    for column in df.columns:

        print(
            f"  {column}"
        )


    return df


# ============================================================
# IDENTIFY COLUMNS
# ============================================================

def identify_columns(
    df
):

    columns = {}


    # --------------------------------------------------------
    # STATION ID
    # --------------------------------------------------------

    columns["station"] = find_column(

        df,

        [
            "station_id",
            "station",
            "icao_id",
            "icao",
            "stationId",
            "ident"
        ],

        required=True

    )


    # --------------------------------------------------------
    # OBSERVATION TIME
    # --------------------------------------------------------

    columns["time"] = find_column(

        df,

        [
            "observation_time",
            "obsTime",
            "obs_time",
            "reportTime",
            "report_time",
            "receipt_time",
            "valid"
        ],

        required=True

    )


    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    columns["latitude"] = find_column(

        df,

        [
            "latitude",
            "lat"
        ],

        required=True

    )


    columns["longitude"] = find_column(

        df,

        [
            "longitude",
            "lon",
            "lng"
        ],

        required=True

    )


    # --------------------------------------------------------
    # TEMPERATURE
    # --------------------------------------------------------

    columns["temperature"] = find_column(

        df,

        [
            "temp_c",
            "temp",
            "temperature",
            "temperature_c"
        ]

    )


    # --------------------------------------------------------
    # DEWPOINT
    # --------------------------------------------------------

    columns["dewpoint"] = find_column(

        df,

        [
            "dewpoint_c",
            "dewp_c",
            "dewp",
            "dewpoint"
        ]

    )


    # --------------------------------------------------------
    # WIND
    # --------------------------------------------------------

    columns["wind_direction"] = find_column(

        df,

        [
            "wind_dir_degrees",
            "wdir",
            "wind_dir",
            "wind_direction"
        ]

    )


    columns["wind_speed"] = find_column(

        df,

        [
            "wind_speed_kt",
            "wspd",
            "wind_speed",
            "wind_speed_kts"
        ]

    )


    columns["wind_gust"] = find_column(

        df,

        [
            "wind_gust_kt",
            "wgst",
            "wind_gust",
            "wind_gust_kts"
        ]

    )


    # --------------------------------------------------------
    # VISIBILITY
    # --------------------------------------------------------

    columns["visibility"] = find_column(

        df,

        [
            "visibility_statute_mi",
            "visib",
            "visibility",
            "visibility_mi"
        ]

    )


    # --------------------------------------------------------
    # ALTIMETER
    # --------------------------------------------------------

    columns["altimeter"] = find_column(

        df,

        [
            "altim_in_hg",
            "altim",
            "altimeter",
            "altimeter_in_hg"
        ]

    )


    # --------------------------------------------------------
    # WEATHER STRING
    # --------------------------------------------------------

    columns["weather"] = find_column(

        df,

        [
            "wx_string",
            "wxString",
            "weather",
            "present_weather"
        ]

    )


    # --------------------------------------------------------
    # RAW METAR
    # --------------------------------------------------------

    columns["raw"] = find_column(

        df,

        [
            "raw_text",
            "rawOb",
            "raw_ob",
            "raw_metar",
            "metar"
        ]

    )


    print()
    print("=" * 70)
    print("Detected METAR fields")
    print("=" * 70)

    for key, value in columns.items():

        print(
            f"{key:18s}: {value}"
        )


    return columns


# ============================================================
# RELATIVE HUMIDITY
# ============================================================

def calculate_relative_humidity(
    temperature_c,
    dewpoint_c
):

    if (
        temperature_c is None
        or
        dewpoint_c is None
    ):

        return None


    try:

        numerator = math.exp(

            (
                17.625
                *
                dewpoint_c
            )

            /

            (
                243.04
                +
                dewpoint_c
            )

        )


        denominator = math.exp(

            (
                17.625
                *
                temperature_c
            )

            /

            (
                243.04
                +
                temperature_c
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


        return round(
            rh,
            1
        )

    except Exception:

        return None


# ============================================================
# CELSIUS -> FAHRENHEIT
# ============================================================

def c_to_f(
    value
):

    if value is None:
        return None

    return round(
        value * 9.0 / 5.0 + 32.0,
        1
    )


# ============================================================
# KNOTS -> MPH
# ============================================================

def knots_to_mph(
    value
):

    if value is None:
        return None

    return round(
        value * 1.150779448,
        1
    )


# ============================================================
# FILTER METARS
# ============================================================

def filter_metars(
    df,
    columns
):

    print()
    print("=" * 70)
    print("Filtering METAR observations")
    print("=" * 70)


    lat_col = columns["latitude"]
    lon_col = columns["longitude"]
    time_col = columns["time"]
    station_col = columns["station"]


    # --------------------------------------------------------
    # NUMERIC LAT/LON
    # --------------------------------------------------------

    df[lat_col] = pd.to_numeric(

        df[lat_col],

        errors="coerce"

    )


    df[lon_col] = pd.to_numeric(

        df[lon_col],

        errors="coerce"

    )


    # --------------------------------------------------------
    # TIME
    # --------------------------------------------------------

    df["_observation_time"] = pd.to_datetime(

        df[time_col],

        utc=True,

        errors="coerce"

    )


    # --------------------------------------------------------
    # REMOVE INVALID LOCATION/TIME
    # --------------------------------------------------------

    df = df.dropna(

        subset=[

            lat_col,
            lon_col,
            "_observation_time"

        ]

    ).copy()


    # --------------------------------------------------------
    # DOMAIN
    # --------------------------------------------------------

    df = df[

        (
            df[lon_col] >= WEST
        )

        &

        (
            df[lon_col] <= EAST
        )

        &

        (
            df[lat_col] >= SOUTH
        )

        &

        (
            df[lat_col] <= NORTH
        )

    ].copy()


    print(
        f"Stations/observations inside domain: {len(df):,}"
    )


    # --------------------------------------------------------
    # AGE FILTER
    # --------------------------------------------------------

    now = pd.Timestamp.now(
        tz="UTC"
    )


    df["_age_hours"] = (

        now
        -
        df["_observation_time"]

    ).dt.total_seconds() / 3600.0


    df = df[

        (
            df["_age_hours"] >= -0.25
        )

        &

        (
            df["_age_hours"]
            <=
            MAX_OBSERVATION_AGE_HOURS
        )

    ].copy()


    print(

        "Observations after age filter: "
        f"{len(df):,}"

    )


    # --------------------------------------------------------
    # KEEP NEWEST OBSERVATION PER STATION
    # --------------------------------------------------------

    df["_station_sort"] = (

        df[station_col]
        .astype(str)
        .str.strip()
        .str.upper()

    )


    df = (

        df
        .sort_values(
            "_observation_time"
        )
        .drop_duplicates(
            subset="_station_sort",
            keep="last"
        )
        .copy()

    )


    print(
        f"Unique stations retained: {len(df):,}"
    )


    return df


# ============================================================
# GET ROW VALUE
# ============================================================

def row_value(
    row,
    column
):

    if column is None:
        return None

    try:

        value = row[column]

        if pd.isna(value):
            return None

        return value

    except Exception:
        return None


# ============================================================
# CREATE GEOJSON
# ============================================================

def create_geojson(
    df,
    columns
):

    print()
    print("=" * 70)
    print("Creating METAR GeoJSON")
    print("=" * 70)


    features = []


    for _, row in df.iterrows():

        station = str(

            row[
                columns["station"]
            ]

        ).strip().upper()


        lat = safe_float(

            row[
                columns["latitude"]
            ]

        )


        lon = safe_float(

            row[
                columns["longitude"]
            ]

        )


        if (
            lat is None
            or
            lon is None
        ):

            continue


        # ----------------------------------------------------
        # TEMPERATURE
        # ----------------------------------------------------

        temp_c = safe_float(

            row_value(
                row,
                columns["temperature"]
            )

        )


        dewpoint_c = safe_float(

            row_value(
                row,
                columns["dewpoint"]
            )

        )


        # ----------------------------------------------------
        # WIND
        # ----------------------------------------------------

        wind_direction = safe_float(

            row_value(
                row,
                columns["wind_direction"]
            )

        )


        wind_speed_kt = safe_float(

            row_value(
                row,
                columns["wind_speed"]
            )

        )


        wind_gust_kt = safe_float(

            row_value(
                row,
                columns["wind_gust"]
            )

        )


        # ----------------------------------------------------
        # VISIBILITY
        # ----------------------------------------------------

        visibility_mi = safe_float(

            row_value(
                row,
                columns["visibility"]
            )

        )


        # ----------------------------------------------------
        # ALTIMETER
        # ----------------------------------------------------

        altimeter = safe_float(

            row_value(
                row,
                columns["altimeter"]
            )

        )


        # ----------------------------------------------------
        # WEATHER
        # ----------------------------------------------------

        weather = row_value(

            row,
            columns["weather"]

        )


        if weather is not None:

            weather = str(
                weather
            ).strip()


        # ----------------------------------------------------
        # RAW METAR
        # ----------------------------------------------------

        raw_metar = row_value(

            row,
            columns["raw"]

        )


        if raw_metar is not None:

            raw_metar = str(
                raw_metar
            ).strip()


        # ----------------------------------------------------
        # OBSERVATION TIME
        # ----------------------------------------------------

        observation_time = row[
            "_observation_time"
        ]


        observation_iso = (

            observation_time
            .to_pydatetime()
            .astimezone(
                timezone.utc
            )
            .isoformat()
            .replace(
                "+00:00",
                "Z"
            )

        )


        # ----------------------------------------------------
        # DERIVED VALUES
        # ----------------------------------------------------

        rh = calculate_relative_humidity(

            temp_c,
            dewpoint_c

        )


        temp_f = c_to_f(
            temp_c
        )


        dewpoint_f = c_to_f(
            dewpoint_c
        )


        wind_speed_mph = knots_to_mph(
            wind_speed_kt
        )


        wind_gust_mph = knots_to_mph(
            wind_gust_kt
        )


        # ----------------------------------------------------
        # FEATURE
        # ----------------------------------------------------

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

                "observation_time":
                    observation_iso,

                "age_hours":
                    round(
                        safe_float(
                            row["_age_hours"]
                        ) or 0,
                        2
                    ),

                # --------------------------------------------
                # TEMPERATURE
                # --------------------------------------------

                "temp_c":
                    temp_c,

                "temp_f":
                    temp_f,

                "dewpoint_c":
                    dewpoint_c,

                "dewpoint_f":
                    dewpoint_f,

                "relative_humidity":
                    rh,

                # --------------------------------------------
                # WIND
                # --------------------------------------------

                "wind_direction":
                    wind_direction,

                "wind_speed_kt":
                    wind_speed_kt,

                "wind_speed_mph":
                    wind_speed_mph,

                "wind_gust_kt":
                    wind_gust_kt,

                "wind_gust_mph":
                    wind_gust_mph,

                # --------------------------------------------
                # OTHER
                # --------------------------------------------

                "visibility_mi":
                    visibility_mi,

                "altimeter_inhg":
                    altimeter,

                "weather":
                    weather,

                "raw_metar":
                    raw_metar,

                # --------------------------------------------
                # NETWORK
                # --------------------------------------------

                "network":
                    "METAR",

                "source":
                    "Aviation Weather Center"

            }

        }


        features.append(
            feature
        )


    geojson = {

        "type":
            "FeatureCollection",

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
            "Aviation Weather Center METAR Cache",

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

        "feature_count":
            len(
                features
            ),

        "features":
            features

    }


    print(
        f"GeoJSON features created: {len(features):,}"
    )


    return geojson


# ============================================================
# WRITE GEOJSON
# ============================================================

def write_geojson(
    geojson
):

    OUTPUT_FILE.parent.mkdir(

        parents=True,

        exist_ok=True

    )


    temporary_file = OUTPUT_FILE.with_suffix(
        ".geojson.tmp"
    )


    with open(

        temporary_file,

        "w",

        encoding="utf-8"

    ) as file:

        json.dump(

            geojson,

            file,

            separators=(
                ",",
                ":"
            ),

            allow_nan=False

        )


    # --------------------------------------------------------
    # Atomic replacement prevents the website from reading
    # a partially written GeoJSON file.
    # --------------------------------------------------------

    os.replace(

        temporary_file,

        OUTPUT_FILE

    )


    print()
    print("=" * 70)

    print(
        f"Saved: {OUTPUT_FILE}"
    )

    print(
        f"Features: {geojson['feature_count']:,}"
    )

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("NWS LBF METAR OBSERVATION UPDATE")
    print("=" * 70)

    print(
        "Domain:"
    )

    print(
        f"  Longitude: {WEST} to {EAST}"
    )

    print(
        f"  Latitude:  {SOUTH} to {NORTH}"
    )

    print(
        f"  Maximum age: {MAX_OBSERVATION_AGE_HOURS} hours"
    )


    # --------------------------------------------------------
    # DOWNLOAD
    # --------------------------------------------------------

    compressed_data = (
        download_metar_cache()
    )


    # --------------------------------------------------------
    # READ
    # --------------------------------------------------------

    df = read_metar_cache(
        compressed_data
    )


    # --------------------------------------------------------
    # COLUMNS
    # --------------------------------------------------------

    columns = identify_columns(
        df
    )


    # --------------------------------------------------------
    # FILTER
    # --------------------------------------------------------

    df = filter_metars(

        df,

        columns

    )


    # --------------------------------------------------------
    # GEOJSON
    # --------------------------------------------------------

    geojson = create_geojson(

        df,

        columns

    )


    # --------------------------------------------------------
    # SAFETY CHECK
    # --------------------------------------------------------

    if (
        geojson[
            "feature_count"
        ]
        ==
        0
    ):

        raise RuntimeError(

            "No METAR observations were found inside "
            "the requested domain. Existing output "
            "was NOT overwritten."

        )


    # --------------------------------------------------------
    # WRITE
    # --------------------------------------------------------

    write_geojson(
        geojson
    )


    print()
    print(
        "METAR update complete."
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
        print("METAR UPDATE FAILED")
        print("=" * 70)

        print(
            str(exc)
        )

        print()

        sys.exit(
            1
        )
