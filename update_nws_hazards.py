# ============================================================
# NWS WATCHES / WARNINGS / ADVISORIES UPDATER
#
# Downloads current NWS hazard polygons from the official
# NOAA/NWS Watches, Warnings and Advisories ArcGIS service.
#
# Output:
#
#   data/nws_hazards.geojson
#
# Each feature is given a standardized hazard_group:
#
#   severe
#   watches
#   flood
#   fire
#   heat
#   winter
#   other
#
# graphics.js can then use ONE GeoJSON source and filter
# different NWS hazard layers from it.
# ============================================================

import json
import time

from pathlib import Path

import requests


# ============================================================
# NOAA / NWS WWA SERVICE
# ============================================================

NWS_WWA_MAPSERVER = (
    "https://mapservices.weather.noaa.gov/eventdriven/rest/services/"
    "WWA/watch_warn_adv/MapServer"
)


# ============================================================
# LAYERS
#
# 0 = CurrentWarnings
#     Tornado Warning
#     Severe Thunderstorm Warning
#     Flash Flood Warning
#     Snow Squall Warning
#     Special Marine Warning
#
# 1 = WatchesWarnings
#     Watches, warnings, advisories, statements, etc.
# ============================================================

NWS_WWA_LAYERS = [

    {
        "layer_id": 0,
        "source_layer": "current_warnings",
    },

    {
        "layer_id": 1,
        "source_layer": "watches_warnings",
    },

]


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
# SEVERE WEATHER PRODUCTS
# ============================================================

SEVERE_PRODUCTS = {

    "Tornado Warning",

    "Severe Thunderstorm Warning",

}


# ============================================================
# WATCH PRODUCTS
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

    "Areal Flood Advisory",

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
#
# Keep the common Plains winter headlines together.
# ============================================================

WINTER_PRODUCTS = {

    "Blizzard Warning",

    "Blizzard Watch",

    "Winter Storm Warning",

    "Winter Storm Watch",

    "Winter Weather Advisory",

    "Ice Storm Warning",

    "Heavy Snow Warning",

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
# NWS-STYLE FALLBACK COLORS
#
# These are used by graphics.js unless we later choose to
# style individual hazards directly in JavaScript.
# ============================================================

HAZARD_COLORS = {

    # --------------------------------------------------------
    # SEVERE
    # --------------------------------------------------------

    "Tornado Warning": {
        "fill": "#FF0000",
        "stroke": "#FF0000",
    },

    "Severe Thunderstorm Warning": {
        "fill": "#FFA500",
        "stroke": "#FFA500",
    },


    # --------------------------------------------------------
    # FLASH FLOOD / FLOOD
    # --------------------------------------------------------

    "Flash Flood Warning": {
        "fill": "#8B0000",
        "stroke": "#8B0000",
    },

    "Flash Flood Watch": {
        "fill": "#2E8B57",
        "stroke": "#2E8B57",
    },

    "Flood Warning": {
        "fill": "#00FF00",
        "stroke": "#00AA00",
    },

    "Flood Watch": {
        "fill": "#2E8B57",
        "stroke": "#2E8B57",
    },

    "Flood Advisory": {
        "fill": "#00FF7F",
        "stroke": "#00AA55",
    },


    # --------------------------------------------------------
    # WATCHES
    # --------------------------------------------------------

    "Tornado Watch": {
        "fill": "#FFFF00",
        "stroke": "#FFFF00",
    },

    "Severe Thunderstorm Watch": {
        "fill": "#DB7093",
        "stroke": "#DB7093",
    },


    # --------------------------------------------------------
    # FIRE
    # --------------------------------------------------------

    "Red Flag Warning": {
        "fill": "#FF1493",
        "stroke": "#FF1493",
    },

    "Fire Weather Watch": {
        "fill": "#FFDEAD",
        "stroke": "#FF8C00",
    },

    "Extreme Fire Danger": {
        "fill": "#FF00FF",
        "stroke": "#FF00FF",
    },


    # --------------------------------------------------------
    # HEAT
    # --------------------------------------------------------

    "Heat Advisory": {
        "fill": "#FF7F50",
        "stroke": "#FF7F50",
    },

    "Extreme Heat Warning": {
        "fill": "#C71585",
        "stroke": "#C71585",
    },

    "Extreme Heat Watch": {
        "fill": "#800000",
        "stroke": "#800000",
    },

    "Excessive Heat Warning": {
        "fill": "#C71585",
        "stroke": "#C71585",
    },

    "Excessive Heat Watch": {
        "fill": "#800000",
        "stroke": "#800000",
    },


    # --------------------------------------------------------
    # WINTER
    # --------------------------------------------------------

    "Blizzard Warning": {
        "fill": "#FF4500",
        "stroke": "#FF4500",
    },

    "Blizzard Watch": {
        "fill": "#ADFF2F",
        "stroke": "#ADFF2F",
    },

    "Winter Storm Warning": {
        "fill": "#FF69B4",
        "stroke": "#FF69B4",
    },

    "Winter Storm Watch": {
        "fill": "#4682B4",
        "stroke": "#4682B4",
    },

    "Winter Weather Advisory": {
        "fill": "#7B68EE",
        "stroke": "#7B68EE",
    },

    "Ice Storm Warning": {
        "fill": "#8B008B",
        "stroke": "#8B008B",
    },

    "Snow Squall Warning": {
        "fill": "#C71585",
        "stroke": "#C71585",
    },

    "Extreme Cold Warning": {
        "fill": "#0000FF",
        "stroke": "#0000FF",
    },

    "Extreme Cold Watch": {
        "fill": "#5F9EA0",
        "stroke": "#5F9EA0",
    },

    "Cold Weather Advisory": {
        "fill": "#AFEEEE",
        "stroke": "#5F9EA0",
    },

}


# ============================================================
# GENERIC COLORS BY GROUP
# ============================================================

GROUP_COLORS = {

    "severe": {
        "fill": "#FF0000",
        "stroke": "#FFFFFF",
    },

    "watches": {
        "fill": "#FFFF00",
        "stroke": "#FFFFFF",
    },

    "flood": {
        "fill": "#00FF00",
        "stroke": "#FFFFFF",
    },

    "fire": {
        "fill": "#FF1493",
        "stroke": "#FFFFFF",
    },

    "heat": {
        "fill": "#FF7F50",
        "stroke": "#FFFFFF",
    },

    "winter": {
        "fill": "#7B68EE",
        "stroke": "#FFFFFF",
    },

    "other": {
        "fill": "#BEBEBE",
        "stroke": "#FFFFFF",
    },

}


# ============================================================
# GET PROPERTY SAFELY
# ============================================================

def get_property(
    properties,
    *names,
):

    for name in names:

        value = properties.get(
            name
        )

        if (
            value is not None
            and
            value != ""
        ):

            return value


    return None


# ============================================================
# DETERMINE HAZARD GROUP
# ============================================================

def classify_hazard(
    product
):

    if not product:

        return "other"


    product = str(
        product
    ).strip()


    # ========================================================
    # SEVERE WARNINGS
    # ========================================================

    if product in SEVERE_PRODUCTS:

        return "severe"


    # ========================================================
    # SEVERE WATCHES
    # ========================================================

    if product in WATCH_PRODUCTS:

        return "watches"


    # ========================================================
    # FLOOD
    # ========================================================

    if product in FLOOD_PRODUCTS:

        return "flood"


    # ========================================================
    # FIRE
    # ========================================================

    if product in FIRE_PRODUCTS:

        return "fire"


    # ========================================================
    # HEAT
    # ========================================================

    if product in HEAT_PRODUCTS:

        return "heat"


    # ========================================================
    # WINTER
    # ========================================================

    if product in WINTER_PRODUCTS:

        return "winter"


    # ========================================================
    # FALLBACK KEYWORD CLASSIFICATION
    #
    # Useful if NWS adds/renames a closely related product.
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


    if (
        "flood" in lower
    ):

        return "flood"


    if (
        "fire" in lower
        or
        "red flag" in lower
    ):

        return "fire"


    if (
        "heat" in lower
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

        "lake effect",

    ]


    if any(
        keyword in lower
        for keyword in winter_keywords
    ):

        return "winter"


    return "other"


# ============================================================
# GET HAZARD COLOR
# ============================================================

def get_hazard_colors(
    product,
    hazard_group,
):

    if (
        product
        in HAZARD_COLORS
    ):

        return HAZARD_COLORS[
            product
        ]


    return GROUP_COLORS.get(

        hazard_group,

        GROUP_COLORS[
            "other"
        ]

    )


# ============================================================
# DOWNLOAD ONE WWA LAYER
# ============================================================

def fetch_layer(
    layer_id,
    source_layer,
):

    url = (
        f"{NWS_WWA_MAPSERVER}/"
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
                "Downloading NWS hazards"
            )

            print(
                f"Layer ID: {layer_id}"
            )

            print(
                f"Source type: {source_layer}"
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

                    "NWS hazard response "
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

                print(
                    f"Waiting "
                    f"{RETRY_SLEEP_SECONDS} seconds..."
                )


                time.sleep(
                    RETRY_SLEEP_SECONDS
                )


    raise RuntimeError(

        f"Could not download NWS WWA "
        f"layer {layer_id}: "
        f"{last_error}"

    )


# ============================================================
# NORMALIZE ONE FEATURE
# ============================================================

def normalize_feature(
    feature,
    source_layer,
):

    properties = (
        feature.get(
            "properties",
            {}
        )
        or {}
    )


    # ========================================================
    # PRODUCT TYPE
    # ========================================================

    product = get_property(

        properties,

        "prod_type",

        "event",

        "product",

        "EVENT",

        "PROD_TYPE",

    )


    if product is not None:

        product = str(
            product
        ).strip()


    # ========================================================
    # GROUP
    # ========================================================

    hazard_group = (
        classify_hazard(
            product
        )
    )


    # ========================================================
    # COLORS
    # ========================================================

    colors = (
        get_hazard_colors(

            product,

            hazard_group

        )
    )


    # ========================================================
    # COMMON PROPERTIES
    # ========================================================

    properties[
        "source_layer"
    ] = source_layer


    properties[
        "hazard"
    ] = product or "Unknown"


    properties[
        "hazard_group"
    ] = hazard_group


    properties[
        "fill"
    ] = colors[
        "fill"
    ]


    properties[
        "stroke"
    ] = colors[
        "stroke"
    ]


    # ========================================================
    # MESSAGE TYPE
    # ========================================================

    msg_type = get_property(

        properties,

        "msg_type",

        "message_type",

        "MSG_TYPE",

    )


    if msg_type is not None:

        properties[
            "message_type"
        ] = str(
            msg_type
        )


    # ========================================================
    # PHENOMENON
    # ========================================================

    phenom = get_property(

        properties,

        "phenom",

        "phenomena",

        "PHENOM",

    )


    if phenom is not None:

        properties[
            "phenom"
        ] = str(
            phenom
        )


    feature[
        "properties"
    ] = properties


    return feature


# ============================================================
# NORMALIZE ONE LAYER
# ============================================================

def normalize_layer(
    data,
    source_layer,
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


        # ====================================================
        # SKIP FEATURES WITHOUT POLYGON GEOMETRY
        # ====================================================

        if not geometry:

            continue


        geometry_type = (
            geometry.get(
                "type"
            )
        )


        if (
            geometry_type
            not in
            (
                "Polygon",
                "MultiPolygon",
            )
        ):

            continue


        cleaned_feature = (
            normalize_feature(

                feature,

                source_layer

            )
        )


        cleaned_features.append(
            cleaned_feature
        )


    return cleaned_features


# ============================================================
# REMOVE DUPLICATE FEATURES
#
# Because some active warnings may appear in both service
# layers, use CAP ID / object ID / geometry as a fallback.
# ============================================================

def deduplicate_features(
    features
):

    output = []

    seen = set()


    for feature in features:

        properties = (
            feature.get(
                "properties",
                {}
            )
        )


        geometry = (
            feature.get(
                "geometry"
            )
        )


        cap_id = get_property(

            properties,

            "cap_id",

            "CAP_ID",

            "id",

            "identifier",

        )


        if cap_id:

            key = (
                "cap",
                str(
                    cap_id
                ),
            )


        else:

            product = (
                properties.get(
                    "hazard"
                )
            )


            start = get_property(

                properties,

                "onset",

                "start",

                "issue",

                "issue_time",

            )


            end = get_property(

                properties,

                "expires",

                "end",

                "expire",

                "end_time",

            )


            geometry_text = (
                json.dumps(

                    geometry,

                    sort_keys=True,

                    separators=(
                        ",",
                        ":",
                    )

                )
            )


            key = (

                "fallback",

                product,

                str(
                    start
                ),

                str(
                    end
                ),

                geometry_text,

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
# PRINT SUMMARY
# ============================================================

def print_summary(
    features
):

    groups = {

        "severe": 0,

        "watches": 0,

        "flood": 0,

        "fire": 0,

        "heat": 0,

        "winter": 0,

        "other": 0,

    }


    product_counts = {}


    for feature in features:

        properties = (
            feature.get(
                "properties",
                {}
            )
        )


        group = (
            properties.get(
                "hazard_group",
                "other"
            )
        )


        hazard = (
            properties.get(
                "hazard",
                "Unknown"
            )
        )


        groups[
            group
        ] = (
            groups.get(
                group,
                0
            )
            +
            1
        )


        product_counts[
            hazard
        ] = (
            product_counts.get(
                hazard,
                0
            )
            +
            1
        )


    print()
    print("=" * 70)

    print(
        "NWS HAZARD SUMMARY"
    )

    print("=" * 70)


    print(
        f"Total polygons: "
        f"{len(features)}"
    )


    print()


    for group, count in groups.items():

        print(
            f"{group}: "
            f"{count}"
        )


    print()
    print(
        "Active products:"
    )


    for product in sorted(
        product_counts
    ):

        print(

            f"  {product}: "
            f"{product_counts[product]}"

        )


# ============================================================
# WRITE GEOJSON
# ============================================================

def write_geojson(
    features
):

    output_data = {

        "type":
            "FeatureCollection",

        "features":
            features,

    }


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
                ":",
            )

        )


    print()
    print(
        f"Wrote: "
        f"{OUTPUT_FILE}"
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
        f"Output file: "
        f"{OUTPUT_FILE}"
    )


    all_features = []


    successful_layers = 0


    # ========================================================
    # DOWNLOAD BOTH WWA LAYERS
    # ========================================================

    for layer_config in (
        NWS_WWA_LAYERS
    ):

        layer_id = (
            layer_config[
                "layer_id"
            ]
        )


        source_layer = (
            layer_config[
                "source_layer"
            ]
        )


        try:

            data = (
                fetch_layer(

                    layer_id,

                    source_layer

                )
            )


            features = (
                normalize_layer(

                    data,

                    source_layer

                )
            )


            print(
                f"Valid polygon features "
                f"from layer {layer_id}: "
                f"{len(features)}"
            )


            all_features.extend(
                features
            )


            successful_layers += 1


        except Exception as error:

            print()
            print(
                f"ERROR downloading "
                f"NWS layer {layer_id}:"
            )

            print(
                error
            )


    # ========================================================
    # FAIL ONLY IF BOTH SERVICE LAYERS FAILED
    # ========================================================

    if (
        successful_layers
        ==
        0
    ):

        raise RuntimeError(

            "Both NWS WWA layers failed."

        )


    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    all_features = (
        deduplicate_features(
            all_features
        )
    )


    # ========================================================
    # WRITE FILE
    #
    # Zero features is allowed. It simply means no active
    # polygons were returned at that moment.
    # ========================================================

    write_geojson(
        all_features
    )


    # ========================================================
    # SUMMARY
    # ========================================================

    print_summary(
        all_features
    )


    print()
    print(
        "NWS hazards update complete."
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
