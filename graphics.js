// ============================================================
// MAPBOX TOKEN
// ============================================================

mapboxgl.accessToken =
    "pk.eyJ1IjoibWF0dGhld2xhYmVuejciLCJhIjoiY21zbjhxZ3ZkMXBoNDJ3cHl5eG5uNzlpZCJ9.UBy4k84SejJzzu2VF0TtcA";


// ============================================================
// MODEL CONFIG
// ============================================================

const MODEL_CONFIGS = {

    hrrr: {

        name:
            "HRRR",

        products: {

            reflUH: {

                name:
                    "Reflectivity + UH ≥ 75",

                baseUrl:
                    "https://mtl-nwslbf-model-data.s3.us-east-2.amazonaws.com/" +
                    "weather-graphics/hrrr/reflUH/latest"

            }

        }

    },


    rrfs: {

        name:
            "RRFS",

        products: {

            reflUH: {

                name:
                    "Reflectivity + UH ≥ 75",

                baseUrl:
                    "https://mtl-nwslbf-model-data.s3.us-east-2.amazonaws.com/" +
                    "weather-graphics/rrfs/reflUH/latest"

            }

        }

    }

};


// ============================================================
// STATE
// ============================================================

let viewerMode =
    "single";


let activeModel =
    "hrrr";


let activeProduct =
    "reflUH";


let singleManifest =
    null;


let compareManifests = {

    hrrr: null,

    rrfs: null

};


let availableFrames =
    [];


let currentFrameIndex =
    0;


let animationTimer =
    null;


let animationPlaying =
    false;


let exportBusy =
    false;


// ============================================================
// SAMPLING
// ============================================================

const sampleCache =
    new Map();


let samplePopup =
    null;


// ============================================================
// SETTINGS
// ============================================================

const MANIFEST_REFRESH_MS =
    30000;


const GIF_MAX_WIDTH =
    1400;


const GIF_FRAME_DELAY_MS =
    700;


// ============================================================
// OVERLAY STATE
// ============================================================

const overlayState = {

    spcDay1:
        true,

    spcDay2:
        false,

    spcDay3:
        false,

    fireDay1:
        false,

    fireDay2:
        false,

    nwsAll:
        false,

    nwsSevere:
        false,

    nwsWatches:
        false,

    nwsFlood:
        false,

    nwsFire:
        false,

    nwsHeat:
        false,

    nwsWinter:
        false,

    wpcDay1:
        false,

    wpcDay2:
        false,

    wpcDay3:
        false,

    cwa:
        true,

    counties:
        true,

    states:
        true

};


// ============================================================
// EXPORT LOGO
// ============================================================

const exportLogoImage =
    new Image();


exportLogoImage.src =
    "assets/NOAANWSLogos.png";


// ============================================================
// SINGLE MAP
// ============================================================

const singleMap =
    createMap(
        "single-map"
    );


// ============================================================
// COMPARISON MAPS
// ============================================================

let leftMap =
    null;


let rightMap =
    null;


let comparisonInitialized =
    false;


let syncingMaps =
    false;


// ============================================================
// CREATE MAP
// ============================================================

function createMap(
    container
) {

    const map =
        new mapboxgl.Map({

            container:
                container,

            style:
                "mapbox://styles/mapbox/satellite-streets-v12",

            center: [
                -100.75,
                41.1
            ],

            zoom:
                6,

            preserveDrawingBuffer:
                true

        });


    map.addControl(

        new mapboxgl.NavigationControl(),

        "top-right"

    );


    map.on(
        "error",

        event => {

            console.error(

                `Map error (${container}):`,

                event.error

            );

        }
    );


    return map;

}


// ============================================================
// PRODUCT CONFIG
// ============================================================

function getProductConfig(
    modelName
) {

    const model =
        MODEL_CONFIGS[
            modelName
        ];


    if (!model) {

        return null;

    }


    return (

        model.products[
            activeProduct
        ]

        ||

        null

    );

}


// ============================================================
// CENTRAL TIME
// ============================================================

function formatValidTimeCentral(
    iso
) {

    const date =
        new Date(
            iso
        );


    const parts =
        new Intl.DateTimeFormat(

            "en-US",

            {

                timeZone:
                    "America/Chicago",

                weekday:
                    "short",

                month:
                    "2-digit",

                day:
                    "2-digit",

                year:
                    "2-digit",

                hour:
                    "numeric",

                minute:
                    "2-digit",

                hour12:
                    true

            }

        ).formatToParts(
            date
        );


    const get =
        type => {

            return (

                parts.find(
                    part =>
                        part.type === type
                )?.value

                ||

                ""

            );

        };


    return (

        `${get("weekday")} ` +

        `${get("month")}/` +
        `${get("day")}/` +
        `${get("year")} ` +

        `${get("hour")}:` +
        `${get("minute")} ` +

        `${get("dayPeriod")}`

    );

}
// ============================================================
// VALID LABEL
// ============================================================

function updateValidLabel(
    frame
) {

    const label =
        document.getElementById(
            "model-valid-label"
        );


    if (
        !label
        ||
        !frame
    ) {

        return;

    }


    const fhr =
        String(
            frame.fhr
        ).padStart(
            3,
            "0"
        );


    label.textContent =

        `F${fhr} • ` +

        formatValidTimeCentral(
            frame.valid
        );

}


// ============================================================
// FIND ROAD LAYER
// ============================================================

function findRoadLayer(
    map
) {

    const style =
        map.getStyle();


    if (
        !style
        ||
        !style.layers
    ) {

        return undefined;

    }


    const layer =
        style.layers.find(
            item => {

                return (

                    item[
                        "source-layer"
                    ] === "road"

                    ||

                    item.id
                        .toLowerCase()
                        .includes(
                            "road"
                        )

                );

            }
        );


    return layer
        ? layer.id
        : undefined;

}


// ============================================================
// ADD SPC OUTLOOK
// ============================================================

function addSpcOutlook(
    map,
    day,
    roadLayer
) {

    const sourceId =
        `spc-day${day}-cat`;


    const fillId =
        `spc-day${day}-fill`;


    const darkId =
        `spc-day${day}-outline-dark`;


    const outlineId =
        `spc-day${day}-outline`;


    map.addSource(

        sourceId,

        {

            type:
                "geojson",

            data:
                `data/spc_day${day}_cat.geojson`

        }

    );


    map.addLayer(

        {

            id:
                fillId,

            type:
                "fill",

            source:
                sourceId,

            paint: {

                "fill-color": [

                    "coalesce",

                    [
                        "get",
                        "fill"
                    ],

                    "#888888"

                ],

                "fill-opacity":
                    0.68

            }

        },

        roadLayer

    );


    map.addLayer(

        {

            id:
                darkId,

            type:
                "line",

            source:
                sourceId,

            paint: {

                "line-color":
                    "#1A1A1A",

                "line-width": [

                    "interpolate",

                    [
                        "linear"
                    ],

                    [
                        "zoom"
                    ],

                    4,
                    2.2,

                    6,
                    3.0,

                    8,
                    3.8,

                    10,
                    4.5

                ]

            }

        },

        roadLayer

    );


    map.addLayer(

        {

            id:
                outlineId,

            type:
                "line",

            source:
                sourceId,

            paint: {

                "line-color": [

                    "coalesce",

                    [
                        "get",
                        "stroke"
                    ],

                    "#000000"

                ],

                "line-width": [

                    "interpolate",

                    [
                        "linear"
                    ],

                    [
                        "zoom"
                    ],

                    4,
                    1.3,

                    6,
                    1.8,

                    8,
                    2.3,

                    10,
                    2.8

                ]

            }

        },

        roadLayer

    );

}


// ============================================================
// ADD SPC FIRE WEATHER OUTLOOK
// ============================================================

function addSpcFireWeather(
    map,
    day,
    roadLayer
) {

    const sourceId =
        `spc-fire-day${day}`;


    const fillId =
        `spc-fire-day${day}-fill`;


    const darkId =
        `spc-fire-day${day}-outline-dark`;


    const outlineId =
        `spc-fire-day${day}-outline`;


    map.addSource(

        sourceId,

        {

            type:
                "geojson",

            data:
                `data/spc_fire_day${day}.geojson`

        }

    );


    map.addLayer(

        {

            id:
                fillId,

            type:
                "fill",

            source:
                sourceId,

            paint: {

                "fill-color": [

                    "coalesce",

                    [
                        "get",
                        "fill"
                    ],

                    "#888888"

                ],

                "fill-opacity":
                    0.65

            }

        },

        roadLayer

    );


    map.addLayer(

        {

            id:
                darkId,

            type:
                "line",

            source:
                sourceId,

            paint: {

                "line-color":
                    "#1A1A1A",

                "line-width": [

                    "interpolate",

                    [
                        "linear"
                    ],

                    [
                        "zoom"
                    ],

                    4,
                    2.2,

                    6,
                    3.0,

                    8,
                    3.8,

                    10,
                    4.5

                ]

            }

        },

        roadLayer

    );


    map.addLayer(

        {

            id:
                outlineId,

            type:
                "line",

            source:
                sourceId,

            paint: {

                "line-color": [

                    "coalesce",

                    [
                        "get",
                        "stroke"
                    ],

                    "#000000"

                ],

                "line-width": [

                    "interpolate",

                    [
                        "linear"
                    ],

                    [
                        "zoom"
                    ],

                    4,
                    1.3,

                    6,
                    1.8,

                    8,
                    2.3,

                    10,
                    2.8

                ]

            }

        },

        roadLayer

    );

}


// ============================================================
// ADD NWS HAZARDS
// ============================================================

function addNwsHazards(
    map,
    roadLayer
) {

    // ========================================================
    // SOURCE
    // ========================================================

    if (
        !map.getSource(
            "nws-hazards"
        )
    ) {

        map.addSource(

            "nws-hazards",

            {

                type:
                    "geojson",

                data:
                    "data/nws_hazards.geojson"

            }

        );

    }


    // ========================================================
    // ALL NWS HAZARDS - FILLED WWA
    // ========================================================

    if (
        !map.getLayer(
            "nws-all-fill"
        )
    ) {

        map.addLayer(

            {

                id:
                    "nws-all-fill",

                type:
                    "fill",

                source:
                    "nws-hazards",

                filter: [

                    "==",

                    [
                        "get",
                        "source_layer"
                    ],

                    "watches_warnings"

                ],

                paint: {

                    "fill-color": [

                        "coalesce",

                        [
                            "get",
                            "fill"
                        ],

                        "rgb(128,128,128)"

                    ],

                    "fill-opacity":
                        0.78,

                    "fill-outline-color": [

                        "coalesce",

                        [
                            "get",
                            "stroke"
                        ],

                        "rgb(110,110,110)"

                    ]

                }

            },

            roadLayer

        );

    }


    // ========================================================
    // ALL CURRENT NWS WARNING POLYGONS
    // ========================================================

    if (
        !map.getLayer(
            "nws-all-current-warning"
        )
    ) {

        map.addLayer(

            {

                id:
                    "nws-all-current-warning",

                type:
                    "line",

                source:
                    "nws-hazards",

                filter: [

                    "==",

                    [
                        "get",
                        "source_layer"
                    ],

                    "current_warnings"

                ],

                paint: {

                    "line-color": [

                        "coalesce",

                        [
                            "get",
                            "stroke"
                        ],

                        "#ffffff"

                    ],

                    "line-width": [

                        "interpolate",

                        [
                            "linear"
                        ],

                        [
                            "zoom"
                        ],

                        4,
                        2.0,

                        6,
                        2.5,

                        8,
                        3.0,

                        10,
                        4.0

                    ],

                    "line-opacity":
                        1.0

                }

            },

            roadLayer

        );

    }


    // ========================================================
    // INDIVIDUAL NWS HAZARD GROUPS
    // ========================================================

    const groups = [

        {
            key:
                "severe",

            id:
                "nws-severe"
        },

        {
            key:
                "watches",

            id:
                "nws-watches"
        },

        {
            key:
                "flood",

            id:
                "nws-flood"
        },

        {
            key:
                "fire",

            id:
                "nws-fire"
        },

        {
            key:
                "heat",

            id:
                "nws-heat"
        },

        {
            key:
                "winter",

            id:
                "nws-winter"
        }

    ];


    groups.forEach(
        group => {

            // =================================================
            // COUNTY / ZONE FILLED HAZARDS
            // =================================================

            const fillId =
                `${group.id}-fill`;


            const fillFilter = [

                "all",

                [
                    "==",

                    [
                        "get",
                        "hazard_group"
                    ],

                    group.key

                ],

                [
                    "==",

                    [
                        "get",
                        "source_layer"
                    ],

                    "watches_warnings"

                ]

            ];


            if (
                !map.getLayer(
                    fillId
                )
            ) {

                map.addLayer(

                    {

                        id:
                            fillId,

                        type:
                            "fill",

                        source:
                            "nws-hazards",

                        filter:
                            fillFilter,

                        paint: {

                            "fill-color": [

                                "coalesce",

                                [
                                    "get",
                                    "fill"
                                ],

                                "rgb(128,128,128)"

                            ],

                            "fill-opacity":
                                0.78,

                            "fill-outline-color": [

                                "coalesce",

                                [
                                    "get",
                                    "stroke"
                                ],

                                "rgb(110,110,110)"

                            ]

                        }

                    },

                    roadLayer

                );

            }


            // =================================================
            // CURRENT WARNING POLYGONS
            // =================================================

            const warningId =
                `${group.id}-current-warning`;


            const warningFilter = [

                "all",

                [
                    "==",

                    [
                        "get",
                        "hazard_group"
                    ],

                    group.key

                ],

                [
                    "==",

                    [
                        "get",
                        "source_layer"
                    ],

                    "current_warnings"

                ]

            ];


            if (
                !map.getLayer(
                    warningId
                )
            ) {

                map.addLayer(

                    {

                        id:
                            warningId,

                        type:
                            "line",

                        source:
                            "nws-hazards",

                        filter:
                            warningFilter,

                        paint: {

                            "line-color": [

                                "coalesce",

                                [
                                    "get",
                                    "stroke"
                                ],

                                "#ffffff"

                            ],

                            "line-width": [

                                "interpolate",

                                [
                                    "linear"
                                ],

                                [
                                    "zoom"
                                ],

                                4,
                                2.0,

                                6,
                                2.5,

                                8,
                                3.0,

                                10,
                                4.0

                            ],

                            "line-opacity":
                                1.0

                        }

                    },

                    roadLayer

                );

            }

        }

    );

}


// ============================================================
// ADD WPC ERO
// ============================================================

function addWpcEro(
    map,
    day,
    roadLayer
) {

    const sourceId =
        `wpc-day${day}-ero`;


    const fillId =
        `wpc-day${day}-ero-fill`;


    const darkId =
        `wpc-day${day}-ero-outline-dark`;


    const outlineId =
        `wpc-day${day}-ero-outline`;


    map.addSource(

        sourceId,

        {

            type:
                "geojson",

            data:
                `data/wpc_day${day}_ero.geojson`

        }

    );


    map.addLayer(

        {

            id:
                fillId,

            type:
                "fill",

            source:
                sourceId,

            paint: {

                "fill-color": [

                    "coalesce",

                    [
                        "get",
                        "fill"
                    ],

                    "#888888"

                ],

                "fill-opacity":
                    0.62

            }

        },

        roadLayer

    );


    map.addLayer(

        {

            id:
                darkId,

            type:
                "line",

            source:
                sourceId,

            paint: {

                "line-color":
                    "#111111",

                "line-width": [

                    "interpolate",

                    [
                        "linear"
                    ],

                    [
                        "zoom"
                    ],

                    4,
                    2.0,

                    6,
                    2.8,

                    8,
                    3.5,

                    10,
                    4.2

                ]

            }

        },

        roadLayer

    );


    map.addLayer(

        {

            id:
                outlineId,

            type:
                "line",

            source:
                sourceId,

            paint: {

                "line-color": [

                    "coalesce",

                    [
                        "get",
                        "stroke"
                    ],

                    "#000000"

                ],

                "line-width": [

                    "interpolate",

                    [
                        "linear"
                    ],

                    [
                        "zoom"
                    ],

                    4,
                    1.2,

                    6,
                    1.7,

                    8,
                    2.2,

                    10,
                    2.7

                ]

            }

        },

        roadLayer

    );

}
// ============================================================
// SETUP MAP LAYERS
// ============================================================

function setupMapLayers(
    map
) {

    if (
        map.getSource(
            "boundary-data"
        )
    ) {

        return;

    }


    const roadLayer =
        findRoadLayer(
            map
        );


    // ========================================================
    // MAPBOX BOUNDARIES
    // ========================================================

    map.addSource(

        "boundary-data",

        {

            type:
                "vector",

            url:
                "mapbox://mapbox.mapbox-streets-v8"

        }

    );


    // ========================================================
    // SPC DAY 1-3
    // ========================================================

    addSpcOutlook(
        map,
        1,
        roadLayer
    );


    addSpcOutlook(
        map,
        2,
        roadLayer
    );


    addSpcOutlook(
        map,
        3,
        roadLayer
    );


    // ========================================================
    // SPC FIRE WEATHER DAY 1-2
    // ========================================================

    addSpcFireWeather(
        map,
        1,
        roadLayer
    );


    addSpcFireWeather(
        map,
        2,
        roadLayer
    );


    // ========================================================
    // NWS HAZARDS
    // ========================================================

    addNwsHazards(
        map,
        roadLayer
    );


    // ========================================================
    // WPC ERO DAY 1-3
    // ========================================================

    addWpcEro(
        map,
        1,
        roadLayer
    );


    addWpcEro(
        map,
        2,
        roadLayer
    );


    addWpcEro(
        map,
        3,
        roadLayer
    );


    // ========================================================
    // COUNTY BOUNDARIES
    // ========================================================

    map.addLayer({

        id:
            "custom-county-boundaries",

        type:
            "line",

        source:
            "boundary-data",

        "source-layer":
            "admin",

        filter: [

            "==",

            [
                "get",
                "admin_level"
            ],

            2

        ],

        paint: {

            "line-color":
                "#000000",

            "line-width": [

                "interpolate",

                [
                    "linear"
                ],

                [
                    "zoom"
                ],

                4,
                0.5,

                6,
                0.8,

                8,
                1.1,

                10,
                1.4

            ],

            "line-opacity":
                0.95

        }

    });


    // ========================================================
    // STATE BOUNDARIES
    // ========================================================

    map.addLayer({

        id:
            "custom-state-boundaries",

        type:
            "line",

        source:
            "boundary-data",

        "source-layer":
            "admin",

        filter: [

            "==",

            [
                "get",
                "admin_level"
            ],

            1

        ],

        paint: {

            "line-color":
                "#000000",

            "line-width": [

                "interpolate",

                [
                    "linear"
                ],

                [
                    "zoom"
                ],

                4,
                2.0,

                6,
                2.7,

                8,
                3.3,

                10,
                4.0

            ]

        }

    });


    // ========================================================
    // LBF CWA
    // ========================================================

    map.addSource(

        "lbf-cwa",

        {

            type:
                "geojson",

            data:
                "data/lbf_cwa.geojson"

        }

    );


    map.addLayer({

        id:
            "lbf-cwa-outline",

        type:
            "line",

        source:
            "lbf-cwa",

        paint: {

            "line-color":
                "#000000",

            "line-width": [

                "interpolate",

                [
                    "linear"
                ],

                [
                    "zoom"
                ],

                4,
                4,

                6,
                5,

                8,
                6,

                10,
                7

            ]

        }

    });


    map.addLayer({

        id:
            "lbf-cwa-boundary",

        type:
            "line",

        source:
            "lbf-cwa",

        paint: {

            "line-color":
                "#ffffff",

            "line-width": [

                "interpolate",

                [
                    "linear"
                ],

                [
                    "zoom"
                ],

                4,
                2,

                6,
                3,

                8,
                4,

                10,
                5

            ]

        }

    });


    // ========================================================
    // APPLY SAVED OVERLAY STATE
    // ========================================================

    applyOverlayStateToMap(
        map
    );


    // ========================================================
    // REMOVE UNWANTED BASEMAP LABELS
    // ========================================================

    hideUnwantedBasemapLabels(
        map
    );

}


// ============================================================
// HIDE UNWANTED BASEMAP LABELS
// ============================================================

function hideUnwantedBasemapLabels(
    map
) {

    const style =
        map.getStyle();


    if (
        !style
        ||
        !style.layers
    ) {

        return;

    }


    const removeNames = [

        "Pine Ridge Indian Reservation",

        "Rosebud Indian Reservation",

        "Cheyenne River Indian Reservation",

        "Standing Rock Indian Reservation",

        "Badlands National Park",

        "Black Hills National Forest",

        "Buffalo Gap National Grassland",

        "Nebraska National Forest",

        "Samuel R. McKelvie National Forest",

        "Fort Niobrara National Wildlife Refuge",

        "Valentine National Wildlife Refuge",

        "Crescent Lake National Wildlife Refuge"

    ];


    style.layers.forEach(
        layer => {

            if (
                layer.type !== "symbol"
            ) {

                return;

            }


            const id =
                layer.id
                    .toLowerCase();


            if (
                id.includes(
                    "state-label"
                )

                ||

                id.includes(
                    "country-label"
                )

                ||

                id.includes(
                    "region-label"
                )

                ||

                id.includes(
                    "admin-label"
                )
            ) {

                try {

                    map.setLayoutProperty(

                        layer.id,

                        "visibility",

                        "none"

                    );

                }

                catch (error) {

                    console.warn(

                        "Could not hide:",

                        layer.id

                    );

                }


                return;

            }


            try {

                const existingFilter =
                    map.getFilter(
                        layer.id
                    );


                map.setFilter(

                    layer.id,

                    [

                        "all",

                        existingFilter
                            ? existingFilter
                            : true,

                        [

                            "match",

                            [
                                "get",
                                "name"
                            ],

                            removeNames,

                            false,

                            true

                        ]

                    ]

                );

            }

            catch (error) {

                // Some layers cannot accept this filter.

            }

        }
    );

}


// ============================================================
// SET LAYER VISIBILITY
// ============================================================

function setLayerVisibility(
    map,
    ids,
    visible
) {

    ids.forEach(
        id => {

            if (
                map.getLayer(
                    id
                )
            ) {

                map.setLayoutProperty(

                    id,

                    "visibility",

                    visible
                        ? "visible"
                        : "none"

                );

            }

        }
    );

}


// ============================================================
// APPLY OVERLAY STATE
// ============================================================

function applyOverlayStateToMap(
    map
) {

    // ========================================================
    // SPC DAY 1
    // ========================================================

    setLayerVisibility(

        map,

        [
            "spc-day1-fill",
            "spc-day1-outline-dark",
            "spc-day1-outline"
        ],

        overlayState.spcDay1

    );


    // ========================================================
    // SPC DAY 2
    // ========================================================

    setLayerVisibility(

        map,

        [
            "spc-day2-fill",
            "spc-day2-outline-dark",
            "spc-day2-outline"
        ],

        overlayState.spcDay2

    );


    // ========================================================
    // SPC DAY 3
    // ========================================================

    setLayerVisibility(

        map,

        [
            "spc-day3-fill",
            "spc-day3-outline-dark",
            "spc-day3-outline"
        ],

        overlayState.spcDay3

    );


    // ========================================================
    // SPC FIRE WEATHER DAY 1
    // ========================================================

    setLayerVisibility(

        map,

        [
            "spc-fire-day1-fill",
            "spc-fire-day1-outline-dark",
            "spc-fire-day1-outline"
        ],

        overlayState.fireDay1

    );


    // ========================================================
    // SPC FIRE WEATHER DAY 2
    // ========================================================

    setLayerVisibility(

        map,

        [
            "spc-fire-day2-fill",
            "spc-fire-day2-outline-dark",
            "spc-fire-day2-outline"
        ],

        overlayState.fireDay2

    );


    // ========================================================
    // NWS ALL HAZARDS
    // ========================================================

    setLayerVisibility(

        map,

        [
            "nws-all-fill",
            "nws-all-current-warning"
        ],

        overlayState.nwsAll

    );


    // ========================================================
    // NWS SEVERE
    // ========================================================

    setLayerVisibility(

        map,

        [
            "nws-severe-fill",
            "nws-severe-current-warning"
        ],

        overlayState.nwsSevere

    );


    // ========================================================
    // NWS WATCHES
    // ========================================================

    setLayerVisibility(

        map,

        [
            "nws-watches-fill",
            "nws-watches-current-warning"
        ],

        overlayState.nwsWatches

    );


    // ========================================================
    // NWS FLOOD
    // ========================================================

    setLayerVisibility(

        map,

        [
            "nws-flood-fill",
            "nws-flood-current-warning"
        ],

        overlayState.nwsFlood

    );


    // ========================================================
    // NWS FIRE
    // ========================================================

    setLayerVisibility(

        map,

        [
            "nws-fire-fill",
            "nws-fire-current-warning"
        ],

        overlayState.nwsFire

    );


    // ========================================================
    // NWS HEAT
    // ========================================================

    setLayerVisibility(

        map,

        [
            "nws-heat-fill",
            "nws-heat-current-warning"
        ],

        overlayState.nwsHeat

    );


    // ========================================================
    // NWS WINTER
    // ========================================================

    setLayerVisibility(

        map,

        [
            "nws-winter-fill",
            "nws-winter-current-warning"
        ],

        overlayState.nwsWinter

    );


    // ========================================================
    // WPC DAY 1
    // ========================================================

    setLayerVisibility(

        map,

        [
            "wpc-day1-ero-fill",
            "wpc-day1-ero-outline-dark",
            "wpc-day1-ero-outline"
        ],

        overlayState.wpcDay1

    );


    // ========================================================
    // WPC DAY 2
    // ========================================================

    setLayerVisibility(

        map,

        [
            "wpc-day2-ero-fill",
            "wpc-day2-ero-outline-dark",
            "wpc-day2-ero-outline"
        ],

        overlayState.wpcDay2

    );


    // ========================================================
    // WPC DAY 3
    // ========================================================

    setLayerVisibility(

        map,

        [
            "wpc-day3-ero-fill",
            "wpc-day3-ero-outline-dark",
            "wpc-day3-ero-outline"
        ],

        overlayState.wpcDay3

    );


    // ========================================================
    // CWA
    // ========================================================

    setLayerVisibility(

        map,

        [
            "lbf-cwa-outline",
            "lbf-cwa-boundary"
        ],

        overlayState.cwa

    );


    // ========================================================
    // COUNTIES
    // ========================================================

    setLayerVisibility(

        map,

        [
            "custom-county-boundaries"
        ],

        overlayState.counties

    );


    // ========================================================
    // STATES
    // ========================================================

    setLayerVisibility(

        map,

        [
            "custom-state-boundaries"
        ],

        overlayState.states

    );

}


// ============================================================
// MANIFEST
// ============================================================

async function fetchManifest(
    modelName
) {

    const product =
        getProductConfig(
            modelName
        );


    if (!product) {

        return null;

    }


    const response =
        await fetch(

            `${product.baseUrl}/manifest.json?t=${Date.now()}`,

            {

                cache:
                    "no-store"

            }

        );


    if (!response.ok) {

        throw new Error(

            `${modelName} manifest HTTP ${response.status}`

        );

    }


    return await response.json();

}


// ============================================================
// FIND FRAME
// ============================================================

function findFrame(
    manifest,
    fhr
) {

    if (
        !manifest
        ||
        !Array.isArray(
            manifest.hours
        )
    ) {

        return null;

    }


    return (

        manifest.hours.find(

            frame =>

                Number(
                    frame.fhr
                )

                ===

                Number(
                    fhr
                )

        )

        ||

        null

    );

}


// ============================================================
// IMAGE COORDINATES
// ============================================================

function getCoordinates(
    manifest
) {

    const b =
        manifest.bounds;


    return [

        [
            b.west,
            b.north
        ],

        [
            b.east,
            b.north
        ],

        [
            b.east,
            b.south
        ],

        [
            b.west,
            b.south
        ]

    ];

}


// ============================================================
// SHOW MODEL FRAME
// ============================================================

function showModelFrame(
    map,
    modelName,
    manifest,
    frame
) {

    if (
        !map
        ||
        !manifest
        ||
        !frame
    ) {

        return;

    }


    const product =
        getProductConfig(
            modelName
        );


    const imageUrl =

        `${product.baseUrl}/${frame.file}` +

        `?run=${encodeURIComponent(
            manifest.run
        )}`;


    const coordinates =
        getCoordinates(
            manifest
        );


    const source =
        map.getSource(
            "model-image-source"
        );


    if (source) {

        source.updateImage({

            url:
                imageUrl,

            coordinates:
                coordinates

        });

    }

    else {

        map.addSource(

            "model-image-source",

            {

                type:
                    "image",

                url:
                    imageUrl,

                coordinates:
                    coordinates

            }

        );


        map.addLayer(

            {

                id:
                    "model-raster-layer",

                type:
                    "raster",

                source:
                    "model-image-source",

                paint: {

                    "raster-opacity":
                        1,

                    "raster-fade-duration":
                        0,

                    "raster-resampling":
                        "linear"

                }

            },

            findRoadLayer(
                map
            )

        );

    }

}
// ============================================================
// REFRESH SINGLE MANIFEST
// ============================================================

async function refreshSingleManifest() {

    const previousFhr =
        getSelectedFhr();


    singleManifest =
        await fetchManifest(
            activeModel
        );


    availableFrames =
        [...singleManifest.hours]
            .sort(

                (
                    a,
                    b
                ) =>

                    Number(
                        a.fhr
                    )

                    -

                    Number(
                        b.fhr
                    )

            );


    let targetFhr =
        previousFhr;


    if (
        targetFhr === null

        ||

        !findFrame(
            singleManifest,
            targetFhr
        )
    ) {

        targetFhr =

            findFrame(
                singleManifest,
                0
            )

                ? 0

                : Number(
                    availableFrames[
                        0
                    ]?.fhr
                );

    }


    currentFrameIndex =
        availableFrames.findIndex(

            frame =>

                Number(
                    frame.fhr
                )

                ===

                Number(
                    targetFhr
                )

        );


    buildHourButtons();


    displayCurrentFrame();

}


// ============================================================
// REFRESH COMPARISON MANIFESTS
// ============================================================

async function refreshCompareManifests() {

    const previousFhr =
        getSelectedFhr();


    const results =
        await Promise.all([

            fetchManifest(
                "hrrr"
            ),

            fetchManifest(
                "rrfs"
            )

        ]);


    compareManifests.hrrr =
        results[0];


    compareManifests.rrfs =
        results[1];


    availableFrames =
        compareManifests
            .hrrr
            .hours
            .filter(
                frame => {

                    return !!findFrame(

                        compareManifests.rrfs,

                        frame.fhr

                    );

                }
            );


    availableFrames.sort(

        (
            a,
            b
        ) =>

            Number(
                a.fhr
            )

            -

            Number(
                b.fhr
            )

    );


    let targetFhr =
        previousFhr;


    if (
        targetFhr === null

        ||

        !availableFrames.some(

            frame =>

                Number(
                    frame.fhr
                )

                ===

                Number(
                    targetFhr
                )

        )
    ) {

        targetFhr =

            availableFrames.some(

                frame =>

                    Number(
                        frame.fhr
                    )

                    ===

                    0

            )

                ? 0

                : Number(
                    availableFrames[
                        0
                    ]?.fhr
                );

    }


    currentFrameIndex =
        availableFrames.findIndex(

            frame =>

                Number(
                    frame.fhr
                )

                ===

                Number(
                    targetFhr
                )

        );


    buildHourButtons();


    displayCurrentFrame();

}


// ============================================================
// LOAD SAMPLE GRID
// ============================================================

async function loadSampleGrid(
    modelName,
    manifest,
    frame
) {

    if (
        !manifest
        ||
        !frame
        ||
        !frame.sample_file
    ) {

        return null;

    }


    const cacheKey =

        `${modelName}_` +
        `${manifest.run}_` +
        `${frame.fhr}`;


    if (
        sampleCache.has(
            cacheKey
        )
    ) {

        return sampleCache.get(
            cacheKey
        );

    }


    const product =
        getProductConfig(
            modelName
        );


    const response =
        await fetch(

            `${product.baseUrl}/${frame.sample_file}` +

            `?run=${encodeURIComponent(
                manifest.run
            )}`,

            {

                cache:
                    "no-store"

            }

        );


    if (!response.ok) {

        throw new Error(

            `Sample data HTTP ${response.status}`

        );

    }


    const data =
        await response.json();


    sampleCache.set(

        cacheKey,

        data

    );


    return data;

}


// ============================================================
// SAMPLE GRID
// ============================================================

function sampleGridAtPoint(
    data,
    lon,
    lat
) {

    if (!data) {

        return null;

    }


    if (
        lon < data.west
        ||
        lon > data.east
        ||
        lat < data.south
        ||
        lat > data.north
    ) {

        return null;

    }


    const ix =
        Math.round(

            (
                lon
                -
                data.west
            )

            /

            data.dx

        );


    const iy =
        Math.round(

            (
                lat
                -
                data.south
            )

            /

            data.dy

        );


    if (
        ix < 0
        ||
        iy < 0
        ||
        ix >= data.nx
        ||
        iy >= data.ny
    ) {

        return null;

    }


    const index =

        iy
        *
        data.nx

        +

        ix;


    let refl =
        Number(
            data.refl[
                index
            ]
        );


    let uh =
        Number(
            data.uh[
                index
            ]
        );


    if (
        refl <= -9990
    ) {

        refl =
            null;

    }


    if (
        uh <= -9990
    ) {

        uh =
            null;

    }


    return {

        refl:
            refl,

        uh:
            uh

    };

}


// ============================================================
// FORMAT SAMPLE VALUE
// ============================================================

function formatSampleValue(
    value,
    digits = 1
) {

    if (
        value === null
        ||
        value === undefined
        ||
        !Number.isFinite(
            value
        )
    ) {

        return "N/A";

    }


    return value.toFixed(
        digits
    );

}


// ============================================================
// SINGLE MODEL SAMPLE POPUP
// ============================================================

function makeSingleSampleHtml(
    modelName,
    lngLat,
    sample,
    frame
) {

    return `

        <div style="
            font-family: Arial, sans-serif;
            min-width: 215px;
        ">

            <div style="
                font-size: 15px;
                font-weight: 800;
                margin-bottom: 3px;
            ">

                ${MODEL_CONFIGS[modelName].name}
                —
                F${String(
                    frame.fhr
                ).padStart(
                    3,
                    "0"
                )}

            </div>


            <div style="
                font-size: 11px;
                color: #666;
                margin-bottom: 8px;
            ">

                ${formatValidTimeCentral(
                    frame.valid
                )}

            </div>


            <div style="
                font-size: 12px;
                color: #555;
                margin-bottom: 8px;
            ">

                ${lngLat.lat.toFixed(3)}°N,

                ${Math.abs(
                    lngLat.lng
                ).toFixed(3)}°W

            </div>


            <div style="
                font-size: 13px;
                line-height: 1.7;
            ">

                <b>Composite Reflectivity:</b>

                ${formatSampleValue(
                    sample?.refl
                )}
                dBZ

                <br>

                <b>2–5 km UH:</b>

                ${formatSampleValue(
                    sample?.uh,
                    0
                )}
                m²/s²

            </div>

        </div>

    `;

}


// ============================================================
// COMPARISON SAMPLE POPUP
// ============================================================

function makeComparisonSampleHtml(
    lngLat,
    hrrrSample,
    rrfsSample,
    frame
) {

    return `

        <div style="
            font-family: Arial, sans-serif;
            min-width: 245px;
        ">

            <div style="
                font-size: 14px;
                font-weight: 800;
                margin-bottom: 3px;
            ">

                Model Comparison
                —
                F${String(
                    frame.fhr
                ).padStart(
                    3,
                    "0"
                )}

            </div>


            <div style="
                font-size: 11px;
                color: #666;
                margin-bottom: 7px;
            ">

                ${formatValidTimeCentral(
                    frame.valid
                )}

            </div>


            <div style="
                font-size: 12px;
                color: #555;
                margin-bottom: 9px;
            ">

                ${lngLat.lat.toFixed(3)}°N,

                ${Math.abs(
                    lngLat.lng
                ).toFixed(3)}°W

            </div>


            <b>HRRR</b><br>

            Reflectivity:
            ${formatSampleValue(
                hrrrSample?.refl
            )}
            dBZ<br>

            UH:
            ${formatSampleValue(
                hrrrSample?.uh,
                0
            )}
            m²/s²


            <hr>


            <b>RRFS</b><br>

            Reflectivity:
            ${formatSampleValue(
                rrfsSample?.refl
            )}
            dBZ<br>

            UH:
            ${formatSampleValue(
                rrfsSample?.uh,
                0
            )}
            m²/s²

        </div>

    `;

}


// ============================================================
// SHOW SAMPLE POPUP
// ============================================================

function showSamplePopup(
    map,
    lngLat,
    html
) {

    if (
        samplePopup
    ) {

        samplePopup.remove();

    }


    samplePopup =
        new mapboxgl.Popup({

            closeButton:
                true,

            closeOnClick:
                true,

            offset:
                10,

            maxWidth:
                "320px"

        })
        .setLngLat(
            lngLat
        )
        .setHTML(
            html
        )
        .addTo(
            map
        );

}


// ============================================================
// SAMPLE SINGLE MODEL
// ============================================================

async function sampleSingleModel(
    map,
    lngLat
) {

    const fhr =
        getSelectedFhr();


    if (
        fhr === null
        ||
        !singleManifest
    ) {

        return;

    }


    const frame =
        findFrame(

            singleManifest,

            fhr

        );


    if (!frame) {

        return;

    }


    try {

        const grid =
            await loadSampleGrid(

                activeModel,

                singleManifest,

                frame

            );


        if (!grid) {

            return;

        }


        const sample =
            sampleGridAtPoint(

                grid,

                lngLat.lng,

                lngLat.lat

            );


        if (!sample) {

            return;

        }


        showSamplePopup(

            map,

            lngLat,

            makeSingleSampleHtml(

                activeModel,

                lngLat,

                sample,

                frame

            )

        );

    }

    catch (error) {

        console.error(

            "Sampling failed:",

            error

        );

    }

}


// ============================================================
// SAMPLE COMPARISON
// ============================================================

async function sampleComparison(
    map,
    lngLat
) {

    const fhr =
        getSelectedFhr();


    if (
        fhr === null
        ||
        !compareManifests.hrrr
        ||
        !compareManifests.rrfs
    ) {

        return;

    }


    const hrrrFrame =
        findFrame(

            compareManifests.hrrr,

            fhr

        );


    const rrfsFrame =
        findFrame(

            compareManifests.rrfs,

            fhr

        );


    if (
        !hrrrFrame
        ||
        !rrfsFrame
    ) {

        return;

    }


    try {

        const [
            hrrrGrid,
            rrfsGrid
        ] =
            await Promise.all([

                loadSampleGrid(

                    "hrrr",

                    compareManifests.hrrr,

                    hrrrFrame

                ),

                loadSampleGrid(

                    "rrfs",

                    compareManifests.rrfs,

                    rrfsFrame

                )

            ]);


        if (
            !hrrrGrid
            ||
            !rrfsGrid
        ) {

            return;

        }


        const hrrrSample =
            sampleGridAtPoint(

                hrrrGrid,

                lngLat.lng,

                lngLat.lat

            );


        const rrfsSample =
            sampleGridAtPoint(

                rrfsGrid,

                lngLat.lng,

                lngLat.lat

            );


        showSamplePopup(

            map,

            lngLat,

            makeComparisonSampleHtml(

                lngLat,

                hrrrSample,

                rrfsSample,

                hrrrFrame

            )

        );

    }

    catch (error) {

        console.error(

            "Comparison sampling failed:",

            error

        );

    }

}


// ============================================================
// SELECTED FORECAST HOUR
// ============================================================

function getSelectedFhr() {

    if (
        currentFrameIndex < 0
        ||
        !availableFrames[
            currentFrameIndex
        ]
    ) {

        return null;

    }


    return Number(

        availableFrames[
            currentFrameIndex
        ].fhr

    );

}


// ============================================================
// DISPLAY FRAME
// ============================================================

function displayCurrentFrame() {

    const fhr =
        getSelectedFhr();


    if (
        fhr === null
    ) {

        return;

    }


    if (
        viewerMode === "single"
    ) {

        const frame =
            findFrame(

                singleManifest,

                fhr

            );


        showModelFrame(

            singleMap,

            activeModel,

            singleManifest,

            frame

        );


        updateValidLabel(
            frame
        );

    }


    else if (
        viewerMode === "compare"
    ) {

        const hrrrFrame =
            findFrame(

                compareManifests.hrrr,

                fhr

            );


        const rrfsFrame =
            findFrame(

                compareManifests.rrfs,

                fhr

            );


        showModelFrame(

            leftMap,

            "hrrr",

            compareManifests.hrrr,

            hrrrFrame

        );


        showModelFrame(

            rightMap,

            "rrfs",

            compareManifests.rrfs,

            rrfsFrame

        );


        updateValidLabel(
            hrrrFrame
        );

    }


    updateHourButtonStyles();

}


// ============================================================
// EXPECTED MAX FHR
// ============================================================

function getExpectedMaxFhr() {

    if (
        viewerMode === "single"
        &&
        singleManifest
    ) {

        return Number(
            singleManifest.max_fhr
        );

    }


    if (
        viewerMode === "compare"
        &&
        compareManifests.hrrr
        &&
        compareManifests.rrfs
    ) {

        return Math.min(

            Number(
                compareManifests
                    .hrrr
                    .max_fhr
            ),

            Number(
                compareManifests
                    .rrfs
                    .max_fhr
            )

        );

    }


    return 0;

}


// ============================================================
// HOUR AVAILABLE
// ============================================================

function hourIsAvailable(
    fhr
) {

    return availableFrames.some(

        frame =>

            Number(
                frame.fhr
            )

            ===

            Number(
                fhr
            )

    );

}


// ============================================================
// BUILD HOURS
// ============================================================

function buildHourButtons() {

    const container =
        document.getElementById(
            "model-hour-list"
        );


    container.innerHTML =
        "";


    const maxFhr =
        getExpectedMaxFhr();


    for (
        let fhr = 0;
        fhr <= maxFhr;
        fhr++
    ) {

        const button =
            document.createElement(
                "button"
            );


        button.className =
            "model-hour-button";


        button.dataset.fhr =
            String(
                fhr
            );


        button.textContent =
            `F${String(
                fhr
            ).padStart(
                3,
                "0"
            )}`;


        if (
            hourIsAvailable(
                fhr
            )
        ) {

            button.classList.add(
                "available"
            );


            button.onclick =
                () => {

                    stopAnimation();


                    selectFhr(
                        fhr
                    );

                };

        }

        else {

            button.classList.add(
                "unavailable"
            );


            button.disabled =
                true;

        }


        container.appendChild(
            button
        );

    }


    updateHourButtonStyles();


    rebuildGifSelectors();

}


// ============================================================
// SELECT FHR
// ============================================================

function selectFhr(
    fhr
) {

    const index =
        availableFrames.findIndex(

            frame =>

                Number(
                    frame.fhr
                )

                ===

                Number(
                    fhr
                )

        );


    if (
        index < 0
    ) {

        return;

    }


    currentFrameIndex =
        index;


    displayCurrentFrame();


    scrollSelectedHourIntoView();

}


// ============================================================
// HOUR BUTTON STYLE
// ============================================================

function updateHourButtonStyles() {

    const selectedFhr =
        getSelectedFhr();


    document
        .querySelectorAll(
            ".model-hour-button"
        )
        .forEach(
            button => {

                button.classList.toggle(

                    "selected",

                    Number(
                        button.dataset.fhr
                    )

                    ===

                    selectedFhr

                );

            }
        );

}


// ============================================================
// SCROLL HOUR
// ============================================================

function scrollSelectedHourIntoView() {

    const fhr =
        getSelectedFhr();


    const button =
        document.querySelector(

            `.model-hour-button[data-fhr="${fhr}"]`

        );


    if (button) {

        button.scrollIntoView({

            behavior:
                "smooth",

            block:
                "nearest",

            inline:
                "center"

        });

    }

}


// ============================================================
// MOVE FRAME
// ============================================================

function moveFrame(
    amount
) {

    if (
        availableFrames.length === 0
    ) {

        return;

    }


    currentFrameIndex +=
        amount;


    if (
        currentFrameIndex < 0
    ) {

        currentFrameIndex =
            availableFrames.length - 1;

    }


    if (
        currentFrameIndex
        >=
        availableFrames.length
    ) {

        currentFrameIndex =
            0;

    }


    displayCurrentFrame();


    scrollSelectedHourIntoView();

}


// ============================================================
// PLAY
// ============================================================

function startAnimation() {

    if (
        animationPlaying
        ||
        availableFrames.length === 0
    ) {

        return;

    }


    animationPlaying =
        true;


    document
        .getElementById(
            "model-play-button"
        )
        .textContent =
            "❚❚";


    animationTimer =
        setInterval(

            () => {

                moveFrame(
                    1
                );

            },

            700

        );

}


function stopAnimation() {

    animationPlaying =
        false;


    if (
        animationTimer
    ) {

        clearInterval(
            animationTimer
        );


        animationTimer =
            null;

    }


    const button =
        document.getElementById(
            "model-play-button"
        );


    if (button) {

        button.textContent =
            "▶";

    }

}


// ============================================================
// WAIT FOR MAP
// ============================================================

function waitForMapLoad(
    map
) {

    return new Promise(
        resolve => {

            if (
                map.loaded()
            ) {

                resolve();

            }

            else {

                map.once(

                    "load",

                    resolve

                );

            }

        }
    );

}
// ============================================================
// INITIALIZE COMPARISON
// ============================================================

async function initializeComparison() {

    if (
        comparisonInitialized
    ) {

        return;

    }


    leftMap =
        createMap(
            "left-map"
        );


    rightMap =
        createMap(
            "right-map"
        );


    await Promise.all([

        waitForMapLoad(
            leftMap
        ),

        waitForMapLoad(
            rightMap
        )

    ]);


    setupMapLayers(
        leftMap
    );


    setupMapLayers(
        rightMap
    );


    leftMap
        .getCanvas()
        .style
        .cursor =
            "crosshair";


    rightMap
        .getCanvas()
        .style
        .cursor =
            "crosshair";


    leftMap.on(

        "click",

        event => {

            if (
                viewerMode === "compare"
            ) {

                sampleComparison(

                    leftMap,

                    event.lngLat

                );

            }

        }

    );


    rightMap.on(

        "click",

        event => {

            if (
                viewerMode === "compare"
            ) {

                sampleComparison(

                    rightMap,

                    event.lngLat

                );

            }

        }

    );


    syncComparisonMaps();


    comparisonInitialized =
        true;

}


// ============================================================
// SYNC COMPARISON MAPS
// ============================================================

function syncComparisonMaps() {

    const sync =
        (
            source,
            target
        ) => {

            if (
                syncingMaps
            ) {

                return;

            }


            syncingMaps =
                true;


            target.jumpTo({

                center:
                    source.getCenter(),

                zoom:
                    source.getZoom(),

                bearing:
                    source.getBearing(),

                pitch:
                    source.getPitch()

            });


            syncingMaps =
                false;

        };


    leftMap.on(

        "move",

        () => {

            sync(
                leftMap,
                rightMap
            );

        }

    );


    rightMap.on(

        "move",

        () => {

            sync(
                rightMap,
                leftMap
            );

        }

    );

}


// ============================================================
// SWITCH VIEWER MODE
// ============================================================

async function switchViewerMode(
    mode
) {

    stopAnimation();


    viewerMode =
        mode;


    const singleEl =
        document.getElementById(
            "single-map"
        );


    const compareEl =
        document.getElementById(
            "comparison-container"
        );


    const timeline =
        document.getElementById(
            "model-timeline"
        );


    const validLabel =
        document.getElementById(
            "model-valid-label"
        );


    const modelSelect =
        document.getElementById(
            "model-select"
        );


    const productSelect =
        document.getElementById(
            "product-select"
        );


    const credit =
        document.getElementById(
            "graphics-credit"
        );


    if (
        mode === "overlays"
    ) {

        singleEl.classList.remove(
            "hidden"
        );


        compareEl.classList.add(
            "hidden"
        );


        timeline.classList.add(
            "hidden"
        );


        validLabel.classList.add(
            "hidden"
        );


        productSelect.classList.add(
            "hidden"
        );


        modelSelect.classList.add(
            "hidden"
        );


        credit.classList.add(
            "no-timeline"
        );


        if (
            singleMap.getLayer(
                "model-raster-layer"
            )
        ) {

            singleMap.setLayoutProperty(

                "model-raster-layer",

                "visibility",

                "none"

            );

        }


        updateExportVisibility();


        return;

    }


    timeline.classList.remove(
        "hidden"
    );


    validLabel.classList.remove(
        "hidden"
    );


    productSelect.classList.remove(
        "hidden"
    );


    credit.classList.remove(
        "no-timeline"
    );


    if (
        mode === "single"
    ) {

        modelSelect.classList.remove(
            "hidden"
        );


        singleEl.classList.remove(
            "hidden"
        );


        compareEl.classList.add(
            "hidden"
        );


        if (
            singleMap.getLayer(
                "model-raster-layer"
            )
        ) {

            singleMap.setLayoutProperty(

                "model-raster-layer",

                "visibility",

                "visible"

            );

        }


        singleMap.resize();


        await refreshSingleManifest();

    }


    else if (
        mode === "compare"
    ) {

        modelSelect.classList.add(
            "hidden"
        );


        singleEl.classList.add(
            "hidden"
        );


        compareEl.classList.remove(
            "hidden"
        );


        await initializeComparison();


        leftMap.resize();


        rightMap.resize();


        await refreshCompareManifests();

    }


    updateExportVisibility();

}


// ============================================================
// SWITCH SINGLE MODEL
// ============================================================

async function switchSingleModel(
    model
) {

    activeModel =
        model;


    singleManifest =
        null;


    availableFrames =
        [];


    currentFrameIndex =
        0;


    if (
        viewerMode === "single"
    ) {

        await refreshSingleManifest();

    }

}


// ============================================================
// REFRESH CURRENT DATA
// ============================================================

async function refreshCurrentData() {

    try {

        if (
            exportBusy
        ) {

            return;

        }


        if (
            viewerMode === "single"
        ) {

            await refreshSingleManifest();

        }


        else if (
            viewerMode === "compare"
        ) {

            await refreshCompareManifests();

        }

    }

    catch (error) {

        console.error(

            "Manifest refresh failed:",

            error

        );

    }

}


// ============================================================
// ROUNDED RECT
// ============================================================

function roundRect(
    ctx,
    x,
    y,
    width,
    height,
    radius
) {

    ctx.beginPath();


    if (
        typeof ctx.roundRect
        ===
        "function"
    ) {

        ctx.roundRect(

            x,
            y,

            width,
            height,

            radius

        );

    }

    else {

        ctx.rect(

            x,
            y,

            width,
            height

        );

    }

}


// ============================================================
// GRAPHICS CREDIT
// ============================================================

function drawGraphicsCredit(
    canvas
) {

    const ctx =
        canvas.getContext(
            "2d"
        );


    const scale =
        canvas.width /
        1400;


    const text =
        "Graphics created by: Matthew Labenz";


    const fontSize =
        Math.max(
            12,
            14 * scale
        );


    ctx.font =
        `600 ${fontSize}px Arial, sans-serif`;


    ctx.textAlign =
        "left";


    ctx.textBaseline =
        "bottom";


    const paddingX =
        Math.max(
            7,
            8 * scale
        );


    const paddingY =
        Math.max(
            4,
            5 * scale
        );


    const margin =
        Math.max(
            6,
            8 * scale
        );


    const width =
        ctx.measureText(
            text
        ).width
        +
        paddingX * 2;


    const height =
        fontSize
        +
        paddingY * 2;


    const x =
        margin;


    const y =
        canvas.height
        -
        margin
        -
        height;


    ctx.fillStyle =
        "rgba(20,24,32,0.75)";


    roundRect(

        ctx,

        x,
        y,

        width,
        height,

        4 * scale

    );


    ctx.fill();


    ctx.fillStyle =
        "#ffffff";


    ctx.fillText(

        text,

        x
        +
        paddingX,

        canvas.height
        -
        margin
        -
        paddingY

    );

}


// ============================================================
// EXPORT BRANDING
// ============================================================

function drawExportBranding(
    canvas,
    frame
) {

    const ctx =
        canvas.getContext(
            "2d"
        );


    const scale =
        canvas.width /
        1400;


    const timestamp =

        `F${String(
            frame.fhr
        ).padStart(
            3,
            "0"
        )} • `

        +

        formatValidTimeCentral(
            frame.valid
        );


    const fontSize =
        Math.max(
            16,
            20 * scale
        );


    ctx.font =
        `700 ${fontSize}px Arial`;


    ctx.textAlign =
        "left";


    ctx.textBaseline =
        "middle";


    const pad =
        10 * scale;


    const metrics =
        ctx.measureText(
            timestamp
        );


    const boxWidth =
        metrics.width
        +
        pad * 2;


    const boxHeight =
        fontSize
        +
        pad * 1.4;


    ctx.fillStyle =
        "rgba(20,24,32,0.90)";


    roundRect(

        ctx,

        10 * scale,
        10 * scale,

        boxWidth,
        boxHeight,

        5 * scale

    );


    ctx.fill();


    ctx.fillStyle =
        "#ffffff";


    ctx.fillText(

        timestamp,

        10 * scale
        +
        pad,

        10 * scale
        +
        boxHeight / 2

    );


    if (
        exportLogoImage.complete
        &&
        exportLogoImage.naturalWidth
    ) {

        const logoWidth =
            145 * scale;


        const logoHeight =

            logoWidth

            *

            exportLogoImage.naturalHeight

            /

            exportLogoImage.naturalWidth;


        let brandingCenterX;


        if (
            viewerMode === "compare"
        ) {

            const panelWidth =
                canvas.width / 2;


            brandingCenterX =

                panelWidth

                +

                panelWidth * 0.82;

        }

        else {

            brandingCenterX =
                canvas.width * 0.88;

        }


        const logoX =
            brandingCenterX
            -
            logoWidth / 2;


        const logoY =
            8 * scale;


        ctx.drawImage(

            exportLogoImage,

            logoX,
            logoY,

            logoWidth,
            logoHeight

        );


        ctx.font =
            `700 ${fontSize}px Arial`;


        ctx.textAlign =
            "center";


        ctx.textBaseline =
            "top";


        const textY =
            logoY
            +
            logoHeight
            +
            3 * scale;


        ctx.strokeStyle =
            "#000000";


        ctx.lineWidth =
            Math.max(
                2,
                4 * scale
            );


        ctx.strokeText(

            "NWS North Platte, NE",

            brandingCenterX,

            textY

        );


        ctx.fillStyle =
            "#ffffff";


        ctx.fillText(

            "NWS North Platte, NE",

            brandingCenterX,

            textY

        );

    }


    drawGraphicsCredit(
        canvas
    );

}


// ============================================================
// SINGLE EXPORT CANVAS
// ============================================================

function createSingleExportCanvas(
    frame,
    maxWidth = null
) {

    const source =
        singleMap.getCanvas();


    let width =
        source.width;


    let height =
        source.height;


    if (
        maxWidth
        &&
        width > maxWidth
    ) {

        const ratio =
            maxWidth /
            width;


        width =
            Math.round(
                width * ratio
            );


        height =
            Math.round(
                height * ratio
            );

    }


    const canvas =
        document.createElement(
            "canvas"
        );


    canvas.width =
        width;


    canvas.height =
        height;


    canvas
        .getContext(
            "2d"
        )
        .drawImage(

            source,

            0,
            0,

            width,
            height

        );


    drawExportBranding(

        canvas,

        frame

    );


    return canvas;

}


// ============================================================
// COMPARISON EXPORT CANVAS
// ============================================================

function createCompareExportCanvas(
    frame,
    maxWidth = null
) {

    const leftCanvas =
        leftMap.getCanvas();


    const rightCanvas =
        rightMap.getCanvas();


    let panelWidth =
        Math.min(

            leftCanvas.width,

            rightCanvas.width

        );


    let height =
        Math.min(

            leftCanvas.height,

            rightCanvas.height

        );


    let width =
        panelWidth * 2;


    if (
        maxWidth
        &&
        width > maxWidth
    ) {

        const ratio =
            maxWidth /
            width;


        panelWidth =
            Math.round(
                panelWidth * ratio
            );


        height =
            Math.round(
                height * ratio
            );


        width =
            panelWidth * 2;

    }


    const canvas =
        document.createElement(
            "canvas"
        );


    canvas.width =
        width;


    canvas.height =
        height;


    const ctx =
        canvas.getContext(
            "2d"
        );


    ctx.drawImage(

        leftCanvas,

        0,
        0,

        panelWidth,
        height

    );


    ctx.drawImage(

        rightCanvas,

        panelWidth,
        0,

        panelWidth,
        height

    );


    // ========================================================
    // CENTER DIVIDER
    // ========================================================

    ctx.fillStyle =
        "#ffffff";


    ctx.fillRect(

        panelWidth - 1,

        0,

        2,

        height

    );


    // ========================================================
    // MODEL LABELS
    // ========================================================

    const labelFont =
        Math.max(
            16,
            width / 70
        );


    ctx.font =
        `800 ${labelFont}px Arial`;


    ctx.textAlign =
        "center";


    ctx.textBaseline =
        "top";


    ctx.strokeStyle =
        "#000000";


    ctx.lineWidth =
        Math.max(
            2,
            width / 350
        );


    ctx.fillStyle =
        "#ffffff";


    ctx.strokeText(

        "HRRR",

        panelWidth / 2,

        10

    );


    ctx.fillText(

        "HRRR",

        panelWidth / 2,

        10

    );


    ctx.strokeText(

        "RRFS",

        panelWidth
        +
        panelWidth / 2,

        10

    );


    ctx.fillText(

        "RRFS",

        panelWidth
        +
        panelWidth / 2,

        10

    );


    drawExportBranding(

        canvas,

        frame

    );


    return canvas;

}


// ============================================================
// CURRENT EXPORT CANVAS
// ============================================================

function createCurrentExportCanvas(
    frame,
    maxWidth = null
) {

    if (
        viewerMode === "compare"
    ) {

        return createCompareExportCanvas(

            frame,

            maxWidth

        );

    }


    return createSingleExportCanvas(

        frame,

        maxWidth

    );

}


// ============================================================
// DOWNLOAD BLOB
// ============================================================

function downloadBlob(
    blob,
    filename
) {

    const url =
        URL.createObjectURL(
            blob
        );


    const anchor =
        document.createElement(
            "a"
        );


    anchor.href =
        url;


    anchor.download =
        filename;


    anchor.click();


    setTimeout(

        () => {

            URL.revokeObjectURL(
                url
            );

        },

        1000

    );

}


// ============================================================
// SAVE PNG
// ============================================================

async function savePng() {

    if (
        exportBusy
        ||
        availableFrames.length === 0
    ) {

        return;

    }


    exportBusy =
        true;


    stopAnimation();


    try {

        const frame =
            availableFrames[
                currentFrameIndex
            ];


        const canvas =
            createCurrentExportCanvas(
                frame
            );


        const blob =
            await new Promise(
                resolve => {

                    canvas.toBlob(

                        resolve,

                        "image/png"

                    );

                }
            );


        const modeLabel =

            viewerMode === "compare"

                ? "hrrr_vs_rrfs"

                : activeModel;


        downloadBlob(

            blob,

            `nws_lbf_${modeLabel}_f${String(
                frame.fhr
            ).padStart(
                3,
                "0"
            )}.png`

        );

    }

    finally {

        exportBusy =
            false;

    }

}


// ============================================================
// GIF ENCODER
// ============================================================

let gifencPromise =
    null;


function loadGifenc() {

    if (
        !gifencPromise
    ) {

        gifencPromise =
            import(
                "https://unpkg.com/gifenc@1.0.3?module"
            );

    }


    return gifencPromise;

}


// ============================================================
// SAVE GIF
// ============================================================

async function saveGif(
    startIndex,
    endIndex
) {

    exportBusy =
        true;


    stopAnimation();


    const originalIndex =
        currentFrameIndex;


    const status =
        document.getElementById(
            "gif-status"
        );


    try {

        const {

            GIFEncoder,

            quantize,

            applyPalette

        } =
            await loadGifenc();


        const gif =
            GIFEncoder();


        for (
            let i = startIndex;
            i <= endIndex;
            i++
        ) {

            currentFrameIndex =
                i;


            displayCurrentFrame();


            await new Promise(
                resolve => {

                    setTimeout(

                        resolve,

                        500

                    );

                }
            );


            const frame =
                availableFrames[
                    i
                ];


            const canvas =
                createCurrentExportCanvas(

                    frame,

                    GIF_MAX_WIDTH

                );


            const ctx =
                canvas.getContext(
                    "2d"
                );


            const image =
                ctx.getImageData(

                    0,
                    0,

                    canvas.width,
                    canvas.height

                );


            const palette =
                quantize(

                    image.data,

                    256

                );


            const indexed =
                applyPalette(

                    image.data,

                    palette

                );


            gif.writeFrame(

                indexed,

                canvas.width,

                canvas.height,

                {

                    palette:
                        palette,

                    delay:
                        GIF_FRAME_DELAY_MS,

                    repeat:
                        0

                }

            );


            if (status) {

                status.textContent =

                    `Encoding ${i - startIndex + 1}/` +

                    `${endIndex - startIndex + 1}`;

            }

        }


        gif.finish();


        const blob =
            new Blob(

                [
                    gif.bytes()
                ],

                {

                    type:
                        "image/gif"

                }

            );


        const modeLabel =

            viewerMode === "compare"

                ? "hrrr_vs_rrfs"

                : activeModel;


        downloadBlob(

            blob,

            `nws_lbf_${modeLabel}_comparison.gif`

        );

    }

    catch (error) {

        console.error(

            "GIF failed:",

            error

        );


        if (status) {

            status.textContent =
                "GIF creation failed.";

        }

    }

    finally {

        currentFrameIndex =
            originalIndex;


        displayCurrentFrame();


        exportBusy =
            false;

    }

}
// ============================================================
// EXPORT CONTROLS
// ============================================================

function createExportControls() {

    const controls =
        document.createElement(
            "div"
        );


    controls.id =
        "export-controls";


    controls.innerHTML = `

        <button
            id="save-png-button"
            class="export-button"
        >
            Save PNG
        </button>

        <button
            id="save-gif-button"
            class="export-button"
        >
            Save GIF
        </button>

    `;


    document.body.appendChild(
        controls
    );


    const panel =
        document.createElement(
            "div"
        );


    panel.id =
        "gif-panel";


    panel.innerHTML = `

        <div id="gif-panel-title">
            Save GIF
        </div>


        <div class="gif-select-row">

            <div class="gif-select-box">

                <label>
                    Start Hour
                </label>

                <select
                    id="gif-start-hour"
                ></select>

            </div>


            <div class="gif-select-box">

                <label>
                    End Hour
                </label>

                <select
                    id="gif-end-hour"
                ></select>

            </div>

        </div>


        <div id="gif-panel-actions">

            <button id="gif-create-button">
                Create GIF
            </button>

            <button id="gif-cancel-button">
                Cancel
            </button>

        </div>


        <div id="gif-status"></div>

    `;


    document.body.appendChild(
        panel
    );


    document
        .getElementById(
            "save-png-button"
        )
        .onclick =
            savePng;


    document
        .getElementById(
            "save-gif-button"
        )
        .onclick =
            () => {

                panel
                    .classList
                    .toggle(
                        "open"
                    );


                rebuildGifSelectors();

            };


    document
        .getElementById(
            "gif-cancel-button"
        )
        .onclick =
            () => {

                panel
                    .classList
                    .remove(
                        "open"
                    );

            };


    document
        .getElementById(
            "gif-create-button"
        )
        .onclick =
            () => {

                saveGif(

                    Number(
                        document
                            .getElementById(
                                "gif-start-hour"
                            )
                            .value
                    ),

                    Number(
                        document
                            .getElementById(
                                "gif-end-hour"
                            )
                            .value
                    )

                );

            };

}


// ============================================================
// GIF SELECTORS
// ============================================================

function rebuildGifSelectors() {

    const start =
        document.getElementById(
            "gif-start-hour"
        );


    const end =
        document.getElementById(
            "gif-end-hour"
        );


    if (
        !start
        ||
        !end
    ) {

        return;

    }


    start.innerHTML =
        "";


    end.innerHTML =
        "";


    availableFrames.forEach(

        (
            frame,
            index
        ) => {

            const label =
                `F${String(
                    frame.fhr
                ).padStart(
                    3,
                    "0"
                )}`;


            start.add(

                new Option(
                    label,
                    index
                )

            );


            end.add(

                new Option(
                    label,
                    index
                )

            );

        }

    );


    if (
        availableFrames.length
    ) {

        start.value =
            "0";


        end.value =
            String(
                availableFrames.length - 1
            );

    }

}


// ============================================================
// EXPORT VISIBILITY
// ============================================================

function updateExportVisibility() {

    const controls =
        document.getElementById(
            "export-controls"
        );


    if (!controls) {

        return;

    }


    controls.style.display =

        viewerMode === "overlays"

            ? "none"

            : "flex";

}


// ============================================================
// APPLY OVERLAY STATE TO ALL MAPS
// ============================================================

function refreshOverlayMaps() {

    allMaps().forEach(

        map => {

            applyOverlayStateToMap(
                map
            );

        }

    );

}


// ============================================================
// UI EVENTS
// ============================================================

function setupUiEvents() {

    // ========================================================
    // OVERLAY MENU
    // ========================================================

    document
        .getElementById(
            "overlay-menu-button"
        )
        .onclick =
            () => {

                document
                    .getElementById(
                        "overlay-menu-content"
                    )
                    .classList
                    .toggle(
                        "open"
                    );

            };


    // ========================================================
    // SPC DAY 1
    // ========================================================

    document
        .getElementById(
            "spc-day1-toggle"
        )
        .onchange =
            event => {

                overlayState.spcDay1 =
                    event.target.checked;


                refreshOverlayMaps();

            };


    // ========================================================
    // SPC DAY 2
    // ========================================================

    document
        .getElementById(
            "spc-day2-toggle"
        )
        .onchange =
            event => {

                overlayState.spcDay2 =
                    event.target.checked;


                refreshOverlayMaps();

            };


    // ========================================================
    // SPC DAY 3
    // ========================================================

    document
        .getElementById(
            "spc-day3-toggle"
        )
        .onchange =
            event => {

                overlayState.spcDay3 =
                    event.target.checked;


                refreshOverlayMaps();

            };


    // ========================================================
    // SPC FIRE WEATHER DAY 1
    // ========================================================

    document
        .getElementById(
            "fire-day1-toggle"
        )
        .onchange =
            event => {

                overlayState.fireDay1 =
                    event.target.checked;


                refreshOverlayMaps();

            };


    // ========================================================
    // SPC FIRE WEATHER DAY 2
    // ========================================================

    document
        .getElementById(
            "fire-day2-toggle"
        )
        .onchange =
            event => {

                overlayState.fireDay2 =
                    event.target.checked;


                refreshOverlayMaps();

            };


    // ========================================================
    // NWS ALL HAZARDS
    // ========================================================

    document
        .getElementById(
            "nws-all-toggle"
        )
        .onchange =
            event => {

                overlayState.nwsAll =
                    event.target.checked;


                refreshOverlayMaps();

            };


    // ========================================================
    // NWS SEVERE
    // ========================================================

    document
        .getElementById(
            "nws-severe-toggle"
        )
        .onchange =
            event => {

                overlayState.nwsSevere =
                    event.target.checked;


                refreshOverlayMaps();

            };


    // ========================================================
    // NWS WATCHES
    // ========================================================

    document
        .getElementById(
            "nws-watches-toggle"
        )
        .onchange =
            event => {

                overlayState.nwsWatches =
                    event.target.checked;


                refreshOverlayMaps();

            };


    // ========================================================
    // NWS FLOOD
    // ========================================================

    document
        .getElementById(
            "nws-flood-toggle"
        )
        .onchange =
            event => {

                overlayState.nwsFlood =
                    event.target.checked;


                refreshOverlayMaps();

            };


    // ========================================================
    // NWS FIRE WEATHER
    // ========================================================

    document
        .getElementById(
            "nws-fire-toggle"
        )
        .onchange =
            event => {

                overlayState.nwsFire =
                    event.target.checked;


                refreshOverlayMaps();

            };


    // ========================================================
    // NWS HEAT
    // ========================================================

    document
        .getElementById(
            "nws-heat-toggle"
        )
        .onchange =
            event => {

                overlayState.nwsHeat =
                    event.target.checked;


                refreshOverlayMaps();

            };


    // ========================================================
    // NWS WINTER
    // ========================================================

    document
        .getElementById(
            "nws-winter-toggle"
        )
        .onchange =
            event => {

                overlayState.nwsWinter =
                    event.target.checked;


                refreshOverlayMaps();

            };


    // ========================================================
    // WPC DAY 1
    // ========================================================

    document
        .getElementById(
            "wpc-day1-toggle"
        )
        .onchange =
            event => {

                overlayState.wpcDay1 =
                    event.target.checked;


                refreshOverlayMaps();

            };


    // ========================================================
    // WPC DAY 2
    // ========================================================

    document
        .getElementById(
            "wpc-day2-toggle"
        )
        .onchange =
            event => {

                overlayState.wpcDay2 =
                    event.target.checked;


                refreshOverlayMaps();

            };


    // ========================================================
    // WPC DAY 3
    // ========================================================

    document
        .getElementById(
            "wpc-day3-toggle"
        )
        .onchange =
            event => {

                overlayState.wpcDay3 =
                    event.target.checked;


                refreshOverlayMaps();

            };


    // ========================================================
    // CWA
    // ========================================================

    document
        .getElementById(
            "cwa-toggle"
        )
        .onchange =
            event => {

                overlayState.cwa =
                    event.target.checked;


                refreshOverlayMaps();

            };


    // ========================================================
    // COUNTIES
    // ========================================================

    document
        .getElementById(
            "county-toggle"
        )
        .onchange =
            event => {

                overlayState.counties =
                    event.target.checked;


                refreshOverlayMaps();

            };


    // ========================================================
    // STATES
    // ========================================================

    document
        .getElementById(
            "state-toggle"
        )
        .onchange =
            event => {

                overlayState.states =
                    event.target.checked;


                refreshOverlayMaps();

            };


    // ========================================================
    // VIEWER MODE
    // ========================================================

    document
        .getElementById(
            "viewer-mode-select"
        )
        .onchange =
            event => {

                switchViewerMode(
                    event.target.value
                );

            };


    // ========================================================
    // MODEL
    // ========================================================

    document
        .getElementById(
            "model-select"
        )
        .onchange =
            event => {

                switchSingleModel(
                    event.target.value
                );

            };


    // ========================================================
    // PREVIOUS
    // ========================================================

    document
        .getElementById(
            "model-prev-button"
        )
        .onclick =
            () => {

                stopAnimation();


                moveFrame(
                    -1
                );

            };


    // ========================================================
    // NEXT
    // ========================================================

    document
        .getElementById(
            "model-next-button"
        )
        .onclick =
            () => {

                stopAnimation();


                moveFrame(
                    1
                );

            };


    // ========================================================
    // PLAY
    // ========================================================

    document
        .getElementById(
            "model-play-button"
        )
        .onclick =
            () => {

                if (
                    animationPlaying
                ) {

                    stopAnimation();

                }

                else {

                    startAnimation();

                }

            };

}


// ============================================================
// ALL MAPS
// ============================================================

function allMaps() {

    const maps = [
        singleMap
    ];


    if (
        leftMap
    ) {

        maps.push(
            leftMap
        );

    }


    if (
        rightMap
    ) {

        maps.push(
            rightMap
        );

    }


    return maps;

}


// ============================================================
// INITIAL LOAD
// ============================================================

singleMap.on(

    "load",

    async () => {

        // ====================================================
        // ADD MAP OVERLAYS / BOUNDARIES
        // ====================================================

        setupMapLayers(
            singleMap
        );


        // ====================================================
        // SAMPLING CURSOR
        // ====================================================

        singleMap
            .getCanvas()
            .style
            .cursor =
                "crosshair";


        // ====================================================
        // SINGLE MODEL SAMPLING
        // ====================================================

        singleMap.on(

            "click",

            event => {

                if (
                    viewerMode === "single"
                ) {

                    sampleSingleModel(

                        singleMap,

                        event.lngLat

                    );

                }

            }

        );


        // ====================================================
        // EXPORT CONTROLS
        // ====================================================

        createExportControls();


        // ====================================================
        // UI EVENTS
        // ====================================================

        setupUiEvents();


        // ====================================================
        // LOAD INITIAL HRRR / RRFS MANIFEST
        // ====================================================

        await refreshSingleManifest();


        // ====================================================
        // PERIODIC MODEL REFRESH
        // ====================================================

        setInterval(

            refreshCurrentData,

            MANIFEST_REFRESH_MS

        );

    }

);
