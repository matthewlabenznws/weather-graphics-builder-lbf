# ============================================================
# NWS WATCHES / WARNINGS / ADVISORIES UPDATER
#
# OFFICIAL NWS SERVICE:
#
#   Layer 0 = CurrentWarnings
#       - Actual warning polygons
#       - Transparent fill
#       - Colored outline
#
#   Layer 1 = WatchesWarnings
#       - County / zone-based watches, warnings, advisories
#       - Official NWS hazard fill colors
#
#
# OUTPUT:
#
#   data/nws_hazards.geojson
#
#
# IMPORTANT:
#
# Do NOT deduplicate only by CAP ID.
#
# One NWS product can contain MANY county/zone polygons that
# share the same CAP ID. Deduplicating only by CAP ID removes
# most of the polygons.
#
# This version only removes EXACT duplicate geometries.
# ============================================================


import json
import time

from pathlib import Path

import requests


# ============================================================
# NWS SERVICE
# ============================================================

BASE_SERVICE = (
    "https://mapservices.weather.noaa.gov/"
    "eventdriven/rest/services/"
    "WWA/watch_warn_adv/MapServer"
)


# ============================================================
# LAYERS
# ============================================================

CURRENT_WARNINGS_LAYER = 0

WATCHES_WARNINGS_LAYER = 1


# ============================================================
# OUTPUT
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


OUTPUT_FILE = (
    OUTPUT_DIR
    / "nws_hazards.geojson"
)


# ============================================================
# REQUEST SETTINGS
# ============================================================

REQUEST_TIMEOUT_SECONDS = 60

DOWNLOAD_ATTEMPTS = 4

RETRY_SLEEP_SECONDS = 5


# ============================================================
# PAGINATION
#
# NWS service has a maximum record count.
# Fetch in smaller chunks so nothing is silently omitted.
# ============================================================

PAGE_SIZE = 2000


# ============================================================
# SEVERE WARNING PRODUCTS
# ============================================================

SEVERE_PRODUCTS = {

    "Tornado Warning",

    "Severe Thunderstorm Warning",

}


# ============================================================
# SEVERE WATCHES
# ============================================================

WATCH_PRODUCTS = {

    "Tornado Watch",

    "Severe Thunderstorm Watch",

}


# ============================================================
# FLOOD PRODUCTS
# ============================================================

FLOOD_PRODUCTS = {

    "Flash Flood Warning",

    "Flash Flood Watch",

    "Flash Flood Statement",

    "Flood Warning",

    "Flood Watch",

    "Flood Advisory",

    "Flood Statement",

    "Areal Flood Warning",

    "Areal Flood Watch",

    "Areal Flood Advisory",

    "Coastal Flood Warning",

    "Coastal Flood Watch",

    "Coastal Flood Advisory",

    "Coastal Flood Statement",

    "Lakeshore Flood Warning",

    "Lakeshore Flood Watch",

    "Lakeshore Flood Advisory",

    "Lakeshore Flood Statement",

}


# ============================================================
# FIRE WEATHER PRODUCTS
# ============================================================

FIRE_PRODUCTS = {

    "Red Flag Warning",

    "Fire Weather Watch",

    "Extreme Fire Danger",

    "Fire Warning",

}


# ============================================================
# HEAT PRODUCTS
# ============================================================

HEAT_PRODUCTS = {

    "Heat Advisory",

    "Extreme Heat Warning",

    "Extreme Heat Watch",

    "Excessive Heat Warning",

    "Excessive Heat Watch",

}


# ============================================================
# WINTER PRODUCTS
# ============================================================

WINTER_PRODUCTS = {

    "Blizzard Warning",

    "Blizzard Watch",

    "Winter Storm Warning",

    "Winter Storm Watch",

    "Winter Weather Advisory",

    "Ice Storm Warning",

    "Heavy Snow Warning",

    "Heavy Snow Watch",

    "Snow Squall Warning",

    "Snow Squall Watch",

    "Snow Advisory",

    "Freezing Rain Advisory",

    "Freezing Fog Advisory",

    "Lake Effect Snow Warning",

    "Lake Effect Snow Watch",

    "Lake Effect Snow Advisory",

    "Wind Chill Warning",

    "Wind Chill Watch",

    "Wind Chill Advisory",

    "Extreme Cold Warning",

    "Extreme Cold Watch",

    "Cold Weather Advisory",

}


# ============================================================
# ARC GIS COLOR -> CSS
# ============================================================

def arcgis_color_to_css(
    color
):

    if (
        not color
        or
        len(color) < 3
    ):

        return None


    r = int(
        color[0]
    )

    g = int(
        color[1]
    )

    b = int(
        color[2]
    )


    if (
        len(color) >= 4
    ):

        alpha = (
            float(
                color[3]
            )
            /
            255.0
        )


        return (
            f"rgba("
            f"{r},"
            f"{g},"
            f"{b},"
            f"{alpha:.3f}"
            f")"
        )


    return (
        f"rgb("
        f"{r},"
        f"{g},"
        f"{b}"
        f")"
    )


# ============================================================
# HTTP REQUEST WITH RETRIES
# ============================================================

def request_json(
    url,
    params=None
):

    last_error = None


    for attempt in range(
        1,
        DOWNLOAD_ATTEMPTS + 1
    ):

        try:

            print(
                f"GET {url}"
            )


            print(
                f"Attempt "
                f"{attempt}/"
                f"{DOWNLOAD_ATTEMPTS}"
            )


            response = requests.get(

                url,

                params=params,

                timeout=
                    REQUEST_TIMEOUT_SECONDS

            )


            response.raise_for_status()


            data = (
                response.json()
            )


            # =================================================
            # ARC GIS ERROR RESPONSE
            # =================================================

            if (
                isinstance(
                    data,
                    dict
                )
                and
                "error" in data
            ):

                raise RuntimeError(

                    json.dumps(
                        data[
                            "error"
                        ]
                    )

                )


            return data


        except Exception as error:

            last_error = error


            print(
                f"Request failed: "
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
                    f"seconds..."
                )


                time.sleep(
                    RETRY_SLEEP_SECONDS
                )


    raise RuntimeError(

        f"Request failed after "
        f"{DOWNLOAD_ATTEMPTS} attempts: "
        f"{last_error}"

    )


# ============================================================
# GET OFFICIAL NWS RENDERER
# ============================================================

def get_renderer(
    layer_id
):

    print()
    print("=" * 70)

    print(
        f"READING NWS RENDERER "
        f"FOR LAYER {layer_id}"
    )

    print("=" * 70)


    metadata = (
        request_json(

            f"{BASE_SERVICE}/"
            f"{layer_id}",

            {
                "f":
                    "json"
            }

        )
    )


    renderer = (

        metadata
        .get(
            "drawingInfo",
            {}
        )
        .get(
            "renderer",
            {}
        )

    )


    renderer_output = {}


    unique_values = (
        renderer.get(
            "uniqueValueInfos",
            []
        )
    )


    for item in unique_values:

        value = (
            str(
                item.get(
                    "value",
                    ""
                )
            )
            .strip()
        )


        if not value:

            continue


        symbol = (
            item.get(
                "symbol",
                {}
            )
            or {}
        )


        outline = (
            symbol.get(
                "outline",
                {}
            )
            or {}
        )


        fill_color = (
            arcgis_color_to_css(

                symbol.get(
                    "color"
                )

            )
        )


        stroke_color = (
            arcgis_color_to_css(

                outline.get(
                    "color"
                )

            )
        )


        stroke_width = (
            outline.get(
                "width",
                0
            )
        )


        renderer_output[
            value
        ] = {

            "label":
                item.get(
                    "label",
                    value
                ),

            "fill":
                fill_color,

            "stroke":
                stroke_color,

            "stroke_width":
                stroke_width

        }


    print(
        f"Renderer categories: "
        f"{len(renderer_output)}"
    )


    return renderer_output


# ============================================================
# DOWNLOAD ALL FEATURES WITH PAGINATION
# ============================================================

def get_all_features(
    layer_id
):

    print()
    print("=" * 70)

    print(
        f"DOWNLOADING NWS LAYER "
        f"{layer_id}"
    )

    print("=" * 70)


    query_url = (

        f"{BASE_SERVICE}/"
        f"{layer_id}/query"

    )


    all_features = []


    offset = 0


    page_number = 1


    while True:

        print()
        print(
            f"Downloading page "
            f"{page_number}"
        )


        print(
            f"Result offset: "
            f"{offset}"
        )


        data = (
            request_json(

                query_url,

                {

                    "where":
                        "1=1",

                    "outFields":
                        "*",

                    "returnGeometry":
                        "true",

                    "outSR":
                        "4326",

                    "returnZ":
                        "false",

                    "returnM":
                        "false",

                    "orderByFields":
                        "objectid ASC",

                    "resultOffset":
                        offset,

                    "resultRecordCount":
                        PAGE_SIZE,

                    "f":
                        "geojson"

                }

            )
        )


        features = (
            data.get(
                "features",
                []
            )
        )


        print(
            f"Features on page: "
            f"{len(features)}"
        )


        all_features.extend(
            features
        )


        # ====================================================
        # FINISHED
        # ====================================================

        if (
            len(features)
            <
            PAGE_SIZE
        ):

            break


        offset += (
            len(features)
        )


        page_number += 1


    print()
    print(
        f"Total features downloaded "
        f"from layer {layer_id}: "
        f"{len(all_features)}"
    )


    return all_features


# ============================================================
# CLASSIFY HAZARD
# ============================================================

def classify_hazard(
    product
):

    if not product:

        return "other"


    product = (
        str(
            product
        )
        .strip()
    )


    if (
        product
        in SEVERE_PRODUCTS
    ):

        return "severe"


    if (
        product
        in WATCH_PRODUCTS
    ):

        return "watches"


    if (
        product
        in FLOOD_PRODUCTS
    ):

        return "flood"


    if (
        product
        in FIRE_PRODUCTS
    ):

        return "fire"


    if (
        product
        in HEAT_PRODUCTS
    ):

        return "heat"


    if (
        product
        in WINTER_PRODUCTS
    ):

        return "winter"


    # ========================================================
    # FALLBACK CLASSIFICATION
    # ========================================================

    lower = (
        product.lower()
    )


    if (
        "tornado" in lower
        or
        "severe thunderstorm" in lower
    ):

        if (
            "watch"
            in lower
        ):

            return "watches"


        return "severe"


    if (
        "flood"
        in lower
    ):

        return "flood"


    if (
        "red flag"
        in lower
        or
        "fire weather"
        in lower
        or
        product == "Fire Warning"
    ):

        return "fire"


    if (
        "heat"
        in lower
    ):

        return "heat"


    winter_keywords = [

        "winter",

        "snow",

        "blizzard",

        "ice storm",

        "freezing rain",

        "freezing fog",

        "wind chill",

        "extreme cold",

        "cold weather",

        "lake effect"

    ]


    if any(

        keyword in lower

        for keyword
        in winter_keywords

    ):

        return "winter"


    return "other"


# ============================================================
# CURRENT WARNING RENDERER KEY
#
# Layer 0 uses:
#
# phenom + "," + sig
#
# Examples:
#
# TO,W = Tornado Warning
# SV,W = Severe Thunderstorm Warning
# FF,W = Flash Flood Warning
# SQ,W = Snow Squall Warning
# MA,W = Special Marine Warning
# ============================================================

def make_current_warning_key(
    properties
):

    phenom = (
        properties.get(
            "phenom"
        )
        or
        ""
    )


    sig = (
        properties.get(
            "sig"
        )
        or
        ""
    )


    phenom = (
        str(
            phenom
        )
        .strip()
    )


    sig = (
        str(
            sig
        )
        .strip()
    )


    return (
        f"{phenom},"
        f"{sig}"
    )


# ============================================================
# VALID POLYGON
# ============================================================

def is_valid_polygon(
    feature
):

    geometry = (
        feature.get(
            "geometry"
        )
    )


    if (
        not geometry
    ):

        return False


    return (

        geometry.get(
            "type"
        )

        in

        (
            "Polygon",
            "MultiPolygon"
        )

    )


# ============================================================
# NORMALIZE CURRENT WARNING
# ============================================================

def normalize_current_warning(
    feature,
    renderer
):

    properties = (
        feature.get(
            "properties",
            {}
        )
        or {}
    )


    product = (
        properties.get(
            "prod_type"
        )
        or
        properties.get(
            "event"
        )
        or
        "Unknown"
    )


    product = (
        str(
            product
        )
        .strip()
    )


    renderer_key = (
        make_current_warning_key(
            properties
        )
    )


    style = (
        renderer.get(
            renderer_key,
            {}
        )
    )


    # ========================================================
    # OFFICIAL CURRENT WARNING FALLBACK COLORS
    # ========================================================

    fallback_strokes = {

        "TO,W":
            "rgb(255,0,0)",

        "SV,W":
            "rgb(255,255,0)",

        "FF,W":
            "rgb(57,121,57)",

        "SQ,W":
            "rgb(199,21,133)",

        "MA,W":
            "rgb(230,152,0)"

    }


    properties[
        "source_layer"
    ] = (
        "current_warnings"
    )


    properties[
        "hazard"
    ] = product


    properties[
        "hazard_group"
    ] = (
        classify_hazard(
            product
        )
    )


    properties[
        "renderer_key"
    ] = (
        renderer_key
    )


    # ========================================================
    # CURRENT WARNINGS:
    # TRANSPARENT INTERIOR
    # ========================================================

    properties[
        "fill"
    ] = (
        "rgba(0,0,0,0)"
    )


    properties[
        "stroke"
    ] = (

        style.get(
            "stroke"
        )

        or

        fallback_strokes.get(
            renderer_key
        )

        or

        "rgb(255,255,255)"

    )


    properties[
        "stroke_width"
    ] = (

        style.get(
            "stroke_width"
        )

        or

        2

    )


    feature[
        "properties"
    ] = properties


    return feature


# ============================================================
# NORMALIZE WATCH / WARNING / ADVISORY
# ============================================================

def normalize_watch_warning(
    feature,
    renderer
):

    properties = (
        feature.get(
            "properties",
            {}
        )
        or {}
    )


    product = (
        properties.get(
            "prod_type"
        )
        or
        "Unknown"
    )


    product = (
        str(
            product
        )
        .strip()
    )


    style = (
        renderer.get(
            product,
            {}
        )
    )


    properties[
        "source_layer"
    ] = (
        "watches_warnings"
    )


    properties[
        "hazard"
    ] = (
        product
    )


    properties[
        "hazard_group"
    ] = (
        classify_hazard(
            product
        )
    )


    # ========================================================
    # OFFICIAL NWS FILL
    # ========================================================

    properties[
        "fill"
    ] = (

        style.get(
            "fill"
        )

        or

        "rgb(128,128,128)"

    )


    # ========================================================
    # OFFICIAL NWS OUTLINE
    # ========================================================

    properties[
        "stroke"
    ] = (

        style.get(
            "stroke"
        )

        or

        "rgb(110,110,110)"

    )


    properties[
        "stroke_width"
    ] = (

        style.get(
            "stroke_width"
        )

        if (
            style.get(
                "stroke_width"
            )
            is not None
        )

        else

        0

    )


    feature[
        "properties"
    ] = properties


    return feature


# ============================================================
# EXACT DUPLICATE REMOVAL
#
# CRITICAL:
#
# CAP ID is NOT enough.
#
# Many county/zone polygons belonging to one alert have the
# same CAP ID.
#
# Geometry is included in the key so each distinct county/
# zone remains in the output.
# ============================================================

def remove_exact_duplicates(
    features
):

    seen = set()


    output = []


    duplicate_count = 0


    for feature in features:

        properties = (
            feature.get(
                "properties",
                {}
            )
            or {}
        )


        geometry = (
            feature.get(
                "geometry"
            )
        )


        source_layer = (
            properties.get(
                "source_layer",
                ""
            )
        )


        cap_id = (
            properties.get(
                "cap_id"
            )
            or
            ""
        )


        hazard = (
            properties.get(
                "hazard"
            )
            or
            ""
        )


        geometry_string = (
            json.dumps(

                geometry,

                sort_keys=True,

                separators=(
                    ",",
                    ":"
                )

            )
        )


        key = (

            str(
                source_layer
            ),

            str(
                cap_id
            ),

            str(
                hazard
            ),

            geometry_string

        )


        if (
            key in seen
        ):

            duplicate_count += 1

            continue


        seen.add(
            key
        )


        output.append(
            feature
        )


    print()
    print(
        f"Exact duplicate polygons removed: "
        f"{duplicate_count}"
    )


    return output


# ============================================================
# PRINT PRODUCT SUMMARY
# ============================================================

def print_product_summary(
    features
):

    product_counts = {}


    group_counts = {}


    source_counts = {}


    for feature in features:

        properties = (
            feature.get(
                "properties",
                {}
            )
            or {}
        )


        product = (
            properties.get(
                "hazard",
                "Unknown"
            )
        )


        group = (
            properties.get(
                "hazard_group",
                "other"
            )
        )


        source = (
            properties.get(
                "source_layer",
                "unknown"
            )
        )


        product_counts[
            product
        ] = (

            product_counts.get(
                product,
                0
            )

            +

            1

        )


        group_counts[
            group
        ] = (

            group_counts.get(
                group,
                0
            )

            +

            1

        )


        source_counts[
            source
        ] = (

            source_counts.get(
                source,
                0
            )

            +

            1

        )


    print()
    print("=" * 70)

    print(
        "NWS HAZARD OUTPUT SUMMARY"
    )

    print("=" * 70)


    print()
    print(
        "BY SOURCE:"
    )


    for source in sorted(
        source_counts
    ):

        print(

            f"  {source}: "
            f"{source_counts[source]}"

        )


    print()
    print(
        "BY GROUP:"
    )


    for group in sorted(
        group_counts
    ):

        print(

            f"  {group}: "
            f"{group_counts[group]}"

        )


    print()
    print(
        "ACTIVE PRODUCTS:"
    )


    for product in sorted(
        product_counts
    ):

        print(

            f"  {product}: "
            f"{product_counts[product]}"

        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)

    print(
        "NWS WATCHES / WARNINGS / "
        "ADVISORIES UPDATE"
    )

    print("=" * 70)


    print()
    print(
        f"Output file:"
    )

    print(
        OUTPUT_FILE
    )


    # ========================================================
    # READ OFFICIAL NWS COLORS
    # ========================================================

    current_warning_renderer = (
        get_renderer(
            CURRENT_WARNINGS_LAYER
        )
    )


    watches_warnings_renderer = (
        get_renderer(
            WATCHES_WARNINGS_LAYER
        )
    )


    # ========================================================
    # DOWNLOAD CURRENT WARNING POLYGONS
    # ========================================================

    current_warning_features = (
        get_all_features(
            CURRENT_WARNINGS_LAYER
        )
    )


    # ========================================================
    # DOWNLOAD COUNTY / ZONE WWA POLYGONS
    # ========================================================

    watches_warnings_features = (
        get_all_features(
            WATCHES_WARNINGS_LAYER
        )
    )


    normalized_features = []


    # ========================================================
    # NORMALIZE CURRENT WARNINGS
    # ========================================================

    current_valid_count = 0


    for feature in (
        current_warning_features
    ):

        if (
            not is_valid_polygon(
                feature
            )
        ):

            continue


        normalized = (
            normalize_current_warning(

                feature,

                current_warning_renderer

            )
        )


        normalized_features.append(
            normalized
        )


        current_valid_count += 1


    print()
    print(
        f"Valid CurrentWarnings polygons: "
        f"{current_valid_count}"
    )


    # ========================================================
    # NORMALIZE WATCHES / WARNINGS / ADVISORIES
    # ========================================================

    wwa_valid_count = 0


    for feature in (
        watches_warnings_features
    ):

        if (
            not is_valid_polygon(
                feature
            )
        ):

            continue


        normalized = (
            normalize_watch_warning(

                feature,

                watches_warnings_renderer

            )
        )


        normalized_features.append(
            normalized
        )


        wwa_valid_count += 1


    print()
    print(
        f"Valid WatchesWarnings polygons: "
        f"{wwa_valid_count}"
    )


    # ========================================================
    # REMOVE ONLY EXACT DUPLICATES
    # ========================================================

    normalized_features = (
        remove_exact_duplicates(
            normalized_features
        )
    )


    # ========================================================
    # GEOJSON
    # ========================================================

    output_data = {

        "type":
            "FeatureCollection",

        "features":
            normalized_features

    }


    # ========================================================
    # WRITE FILE
    # ========================================================

    with OUTPUT_FILE.open(

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


    # ========================================================
    # SUMMARY
    # ========================================================

    print_product_summary(
        normalized_features
    )


    print()
    print("=" * 70)

    print(
        "UPDATE COMPLETE"
    )

    print("=" * 70)


    print(
        f"Total output polygons: "
        f"{len(normalized_features)}"
    )


    print(
        f"Wrote: "
        f"{OUTPUT_FILE}"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
