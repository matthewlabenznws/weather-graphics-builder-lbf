# ============================================================
# NWS WATCHES / WARNINGS / ADVISORIES UPDATER
#
# Official NWS source:
#
# Layer 0 = CurrentWarnings
#           Polygon warnings rendered as colored outlines
#
# Layer 1 = WatchesWarnings
#           County/zone hazards rendered with official fills
#
# Output:
#
#   data/nws_hazards.geojson
#
# The script reads the official renderer from the NWS
# MapServer so graphics.js can reproduce NWS colors.
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
# OUTPUT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = BASE_DIR / "data"

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

DOWNLOAD_ATTEMPTS = 3

RETRY_SLEEP_SECONDS = 5


# ============================================================
# LAYERS
# ============================================================

LAYERS = {

    0: {
        "name": "current_warnings",
        "renderer_field": "warning_code"
    },

    1: {
        "name": "watches_warnings",
        "renderer_field": "prod_type"
    }

}


# ============================================================
# HAZARD GROUPS
# ============================================================

SEVERE_PRODUCTS = {
    "Tornado Warning",
    "Severe Thunderstorm Warning",
}


WATCH_PRODUCTS = {
    "Tornado Watch",
    "Severe Thunderstorm Watch",
}


FLOOD_PRODUCTS = {
    "Flash Flood Warning",
    "Flash Flood Watch",
    "Flash Flood Statement",
    "Flood Warning",
    "Flood Watch",
    "Flood Advisory",
    "Flood Statement",
    "Coastal Flood Warning",
    "Coastal Flood Watch",
    "Coastal Flood Advisory",
    "Coastal Flood Statement",
    "Lakeshore Flood Warning",
    "Lakeshore Flood Watch",
    "Lakeshore Flood Advisory",
    "Lakeshore Flood Statement",
}


FIRE_PRODUCTS = {
    "Red Flag Warning",
    "Fire Weather Watch",
    "Extreme Fire Danger",
    "Fire Warning",
}


HEAT_PRODUCTS = {
    "Heat Advisory",
    "Extreme Heat Warning",
    "Extreme Heat Watch",
    "Excessive Heat Warning",
    "Excessive Heat Watch",
}


WINTER_PRODUCTS = {
    "Blizzard Warning",
    "Blizzard Watch",
    "Winter Storm Warning",
    "Winter Storm Watch",
    "Winter Weather Advisory",
    "Ice Storm Warning",
    "Snow Squall Warning",
    "Heavy Snow Warning",
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
# RGB(A) -> CSS COLOR
# ============================================================

def arcgis_color_to_css(color):

    if not color:
        return None

    if len(color) < 3:
        return None

    r = color[0]
    g = color[1]
    b = color[2]

    if len(color) >= 4:

        alpha = color[3] / 255.0

        return (
            f"rgba("
            f"{r},"
            f"{g},"
            f"{b},"
            f"{alpha:.3f}"
            f")"
        )

    return f"rgb({r},{g},{b})"


# ============================================================
# REQUEST WITH RETRIES
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
                f"GET {url} "
                f"(attempt {attempt}/"
                f"{DOWNLOAD_ATTEMPTS})"
            )

            response = requests.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS
            )

            response.raise_for_status()

            return response.json()

        except Exception as error:

            last_error = error

            print(
                f"Request failed: {error}"
            )

            if attempt < DOWNLOAD_ATTEMPTS:

                time.sleep(
                    RETRY_SLEEP_SECONDS
                )

    raise RuntimeError(
        f"Request failed after "
        f"{DOWNLOAD_ATTEMPTS} attempts: "
        f"{last_error}"
    )


# ============================================================
# DOWNLOAD OFFICIAL RENDERER
# ============================================================

def get_renderer(
    layer_id
):

    print()
    print(
        f"Reading official renderer "
        f"for layer {layer_id}..."
    )

    metadata = request_json(
        f"{BASE_SERVICE}/{layer_id}",
        {
            "f": "json"
        }
    )

    renderer = (
        metadata
        .get("drawingInfo", {})
        .get("renderer", {})
    )

    renderer_type = (
        renderer.get("type")
    )

    print(
        f"Renderer type: "
        f"{renderer_type}"
    )

    output = {}

    for info in renderer.get(
        "uniqueValueInfos",
        []
    ):

        value = str(
            info.get(
                "value",
                ""
            )
        ).strip()

        if not value:
            continue

        symbol = (
            info.get(
                "symbol",
                {}
            )
        )

        fill_color = (
            arcgis_color_to_css(
                symbol.get(
                    "color"
                )
            )
        )

        outline = (
            symbol.get(
                "outline",
                {}
            )
        )

        outline_color = (
            arcgis_color_to_css(
                outline.get(
                    "color"
                )
            )
        )

        outline_width = (
            outline.get(
                "width",
                0
            )
        )

        output[value] = {

            "label":
                info.get(
                    "label",
                    value
                ),

            "fill":
                fill_color,

            "stroke":
                outline_color,

            "stroke_width":
                outline_width

        }

    print(
        f"Renderer categories found: "
        f"{len(output)}"
    )

    return output


# ============================================================
# DOWNLOAD FEATURES
# ============================================================

def get_features(
    layer_id
):

    print()
    print("=" * 70)

    print(
        f"Downloading NWS layer "
        f"{layer_id}"
    )

    print("=" * 70)

    data = request_json(

        f"{BASE_SERVICE}/"
        f"{layer_id}/query",

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

            "f":
                "geojson"
        }

    )

    features = (
        data.get(
            "features",
            []
        )
    )

    print(
        f"Downloaded "
        f"{len(features)} features."
    )

    return features


# ============================================================
# CLASSIFY HAZARD
# ============================================================

def classify_hazard(
    product
):

    if not product:
        return "other"

    product = str(
        product
    ).strip()

    if product in SEVERE_PRODUCTS:
        return "severe"

    if product in WATCH_PRODUCTS:
        return "watches"

    if product in FLOOD_PRODUCTS:
        return "flood"

    if product in FIRE_PRODUCTS:
        return "fire"

    if product in HEAT_PRODUCTS:
        return "heat"

    if product in WINTER_PRODUCTS:
        return "winter"


    # ========================================================
    # FALLBACK CLASSIFICATION
    # ========================================================

    lower = product.lower()

    if (
        "tornado" in lower
        or
        "severe thunderstorm" in lower
    ):

        if "watch" in lower:
            return "watches"

        return "severe"


    if "flood" in lower:
        return "flood"


    if (
        "red flag" in lower
        or
        "fire" in lower
    ):
        return "fire"


    if "heat" in lower:
        return "heat"


    winter_words = [

        "winter",
        "snow",
        "blizzard",
        "ice",
        "freezing",
        "wind chill",
        "extreme cold",
        "cold weather",
        "lake effect"

    ]

    if any(
        word in lower
        for word in winter_words
    ):
        return "winter"


    return "other"


# ============================================================
# CURRENT WARNING CODE
#
# Layer 0 renderer is based on:
#
#   phenom + "," + sig
#
# Examples:
#
#   TO,W
#   SV,W
#   FF,W
#   SQ,W
#   MA,W
# ============================================================

def make_warning_code(
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

    return (
        f"{phenom},{sig}"
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
        "Unknown"
    )

    warning_code = (
        make_warning_code(
            properties
        )
    )

    style = (
        renderer.get(
            warning_code,
            {}
        )
    )


    # ========================================================
    # FALLBACK WARNING COLORS
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
    ] = "current_warnings"


    properties[
        "hazard"
    ] = product


    properties[
        "hazard_group"
    ] = classify_hazard(
        product
    )


    properties[
        "warning_code"
    ] = warning_code


    # CurrentWarnings are intentionally transparent.

    properties[
        "fill"
    ] = "rgba(0,0,0,0)"


    properties[
        "stroke"
    ] = (
        style.get(
            "stroke"
        )
        or
        fallback_strokes.get(
            warning_code,
            "rgb(255,255,255)"
        )
    )


    properties[
        "stroke_width"
    ] = (
        style.get(
            "stroke_width",
            2
        )
    )


    feature[
        "properties"
    ] = properties

    return feature


# ============================================================
# NORMALIZE WATCH / WARNING / ADVISORY
# ============================================================

def normalize_wwa(
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

    product = str(
        product
    ).strip()


    style = (
        renderer.get(
            product,
            {}
        )
    )


    properties[
        "source_layer"
    ] = "watches_warnings"


    properties[
        "hazard"
    ] = product


    properties[
        "hazard_group"
    ] = classify_hazard(
        product
    )


    properties[
        "fill"
    ] = (
        style.get(
            "fill"
        )
        or
        "rgb(128,128,128)"
    )


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
            "stroke_width",
            0
        )
    )


    feature[
        "properties"
    ] = properties

    return feature


# ============================================================
# VALID POLYGON?
# ============================================================

def valid_polygon(
    feature
):

    geometry = (
        feature.get(
            "geometry"
        )
    )

    if not geometry:
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
# REMOVE DUPLICATES WITHIN EACH SOURCE
# ============================================================

def deduplicate(
    features
):

    seen = set()

    output = []

    for feature in features:

        properties = (
            feature.get(
                "properties",
                {}
            )
        )

        source_layer = (
            properties.get(
                "source_layer"
            )
        )

        cap_id = (
            properties.get(
                "cap_id"
            )
        )

        geometry = (
            feature.get(
                "geometry"
            )
        )

        if cap_id:

            key = (
                source_layer,
                cap_id
            )

        else:

            key = (

                source_layer,

                properties.get(
                    "hazard"
                ),

                json.dumps(
                    geometry,
                    sort_keys=True,
                    separators=(",", ":")
                )

            )

        if key in seen:
            continue

        seen.add(
            key
        )

        output.append(
            feature
        )

    return output


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)

    print(
        "NWS WATCH / WARNING / "
        "ADVISORY UPDATE"
    )

    print("=" * 70)


    # ========================================================
    # READ OFFICIAL NWS RENDERERS
    # ========================================================

    warning_renderer = (
        get_renderer(
            0
        )
    )

    wwa_renderer = (
        get_renderer(
            1
        )
    )


    # ========================================================
    # DOWNLOAD DATA
    # ========================================================

    current_warnings = (
        get_features(
            0
        )
    )

    watches_warnings = (
        get_features(
            1
        )
    )


    output_features = []


    # ========================================================
    # CURRENT WARNINGS
    # ========================================================

    for feature in current_warnings:

        if not valid_polygon(
            feature
        ):
            continue

        output_features.append(

            normalize_current_warning(
                feature,
                warning_renderer
            )

        )


    # ========================================================
    # WATCHES / WARNINGS / ADVISORIES
    # ========================================================

    for feature in watches_warnings:

        if not valid_polygon(
            feature
        ):
            continue

        output_features.append(

            normalize_wwa(
                feature,
                wwa_renderer
            )

        )


    output_features = (
        deduplicate(
            output_features
        )
    )


    # ========================================================
    # COUNTS
    # ========================================================

    group_counts = {}

    source_counts = {}


    for feature in output_features:

        properties = (
            feature[
                "properties"
            ]
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

        group_counts[group] = (
            group_counts.get(
                group,
                0
            )
            +
            1
        )

        source_counts[source] = (
            source_counts.get(
                source,
                0
            )
            +
            1
        )


    # ========================================================
    # WRITE GEOJSON
    # ========================================================

    output_data = {

        "type":
            "FeatureCollection",

        "features":
            output_features

    }


    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output_data,
            file,
            separators=(",", ":")
        )


    print()
    print("=" * 70)

    print(
        "OUTPUT SUMMARY"
    )

    print("=" * 70)


    print(
        f"Current warning polygons: "
        f"{source_counts.get('current_warnings', 0)}"
    )


    print(
        f"WWA polygons: "
        f"{source_counts.get('watches_warnings', 0)}"
    )


    print(
        f"Total polygons: "
        f"{len(output_features)}"
    )


    print()


    for group in sorted(
        group_counts
    ):

        print(
            f"{group}: "
            f"{group_counts[group]}"
        )


    print()
    print(
        f"Wrote: {OUTPUT_FILE}"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
