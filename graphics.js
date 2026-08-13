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
// NWS HAZARD SERVICE
// ============================================================

const NWS_HAZARD_SERVICE =
    "https://mapservices.weather.noaa.gov/" +
    "eventdriven/rest/services/" +
    "WWA/watch_warn_adv/MapServer";


const NWS_CURRENT_WARNINGS_LAYER =
    0;


const NWS_WATCHES_WARNINGS_LAYER =
    1;


const NWS_PAGE_SIZE =
    2000;


const NWS_REQUEST_TIMEOUT_MS =
    30000;


// ============================================================
// NWS HAZARD GROUPS
// ============================================================

const NWS_SEVERE_PRODUCTS = [

    "Tornado Warning",

    "Severe Thunderstorm Warning"

];


const NWS_WATCH_PRODUCTS = [

    "Tornado Watch",

    "Severe Thunderstorm Watch"

];


const NWS_FLOOD_PRODUCTS = [

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

    "Lakeshore Flood Statement"

];


const NWS_FIRE_PRODUCTS = [

    "Red Flag Warning",

    "Fire Weather Watch",

    "Extreme Fire Danger",

    "Fire Warning"

];


const NWS_HEAT_PRODUCTS = [

    "Heat Advisory",

    "Extreme Heat Warning",

    "Extreme Heat Watch",

    "Excessive Heat Warning",

    "Excessive Heat Watch"

];


const NWS_WINTER_PRODUCTS = [

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

    "Cold Weather Advisory"

];


// ============================================================
// OBSERVATION CONFIG
//
// update_metar.py will create:
//
// data/metar.geojson
//
// Expected properties:
//
// station
// temp_f
// dewpoint_f
// rh
// wind_dir_deg
// wind_speed_mph
// wind_gust_mph
// ============================================================

const METAR_GEOJSON_URL =
    "data/metar.geojson";


const OBSERVATION_REFRESH_MS =
    5 * 60 * 1000;


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

    hrrr:
        null,

    rrfs:
        null

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
// OBSERVATION STATE
// ============================================================

let observationParameter =
    "gust";


let metarData =
    {

        type:
            "FeatureCollection",

        features:
            []

    };


let mesonetData =
    {

        type:
            "FeatureCollection",

        features:
            []

    };


// ============================================================
// NWS HAZARD CACHE
// ============================================================

let nwsCurrentWarningsData =
    null;


let nwsWatchesWarningsData =
    null;


let nwsCurrentWarningRenderer =
    null;


let nwsWatchesWarningsRenderer =
    null;


let nwsHazardsLoaded =
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

    // ========================================================
    // OBSERVATIONS
    // ========================================================

    metar:
        false,

    mesonet:
        false,


    // ========================================================
    // SPC
    // ========================================================

    spcDay1:
        true,

    spcDay2:
        false,

    spcDay3:
        false,


    // ========================================================
    // SPC FIRE WEATHER
    // ========================================================

    fireDay1:
        false,

    fireDay2:
        false,


    // ========================================================
    // NWS HAZARDS
    // ========================================================

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


    // ========================================================
    // WPC
    // ========================================================

    wpcDay1:
        false,

    wpcDay2:
        false,

    wpcDay3:
        false,


    // ========================================================
    // BOUNDARIES
    // ========================================================

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


    if (
        !model
    ) {

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
// OBSERVATION VALUE
// ============================================================

function getObservationValue(
    properties
) {

    if (
        !properties
    ) {

        return null;

    }


    if (
        observationParameter === "gust"
    ) {

        const gust =
            Number(
                properties.wind_gust_mph
            );


        if (
            Number.isFinite(
                gust
            )
        ) {

            return Math.round(
                gust
            );

        }


        return null;

    }


    if (
        observationParameter === "wind"
    ) {

        const speed =
            Number(
                properties.wind_speed_mph
            );


        if (
            Number.isFinite(
                speed
            )
        ) {

            return Math.round(
                speed
            );

        }


        return null;

    }


    if (
        observationParameter === "temp"
    ) {

        const temp =
            Number(
                properties.temp_f
            );


        if (
            Number.isFinite(
                temp
            )
        ) {

            return Math.round(
                temp
            );

        }


        return null;

    }


    if (
        observationParameter === "dewpoint"
    ) {

        const dewpoint =
            Number(
                properties.dewpoint_f
            );


        if (
            Number.isFinite(
                dewpoint
            )
        ) {

            return Math.round(
                dewpoint
            );

        }


        return null;

    }


    if (
        observationParameter === "rh"
    ) {

        const rh =
            Number(
                properties.rh
            );


        if (
            Number.isFinite(
                rh
            )
        ) {

            return Math.round(
                rh
            );

        }


        return null;

    }


    return null;

}


// ============================================================
// FORMAT OBSERVATION LABEL
// ============================================================

function getObservationLabel(
    properties
) {

    const value =
        getObservationValue(
            properties
        );


    if (
        value === null
    ) {

        return "";

    }


    if (
        observationParameter === "gust"
    ) {

        return `G${value}`;

    }


    if (
        observationParameter === "rh"
    ) {

        return `${value}%`;

    }


    return String(
        value
    );

}


// ============================================================
// WIND ARROW ROTATION
//
// METAR wind direction tells where the wind is FROM.
//
// Example:
// 270° = wind FROM west.
//
// Add 180 degrees so the arrow points toward where
// the wind is moving:
//
// 270° + 180° = 90°
// arrow points east.
//
// ============================================================

function getWindArrowRotation(
    properties
) {

    if (
        !properties
    ) {

        return 0;

    }


    const direction =
        Number(
            properties.wind_dir_deg
        );


    if (
        !Number.isFinite(
            direction
        )
    ) {

        return 0;

    }


    return (
        direction
        +
        180
    ) % 360;

}


// ============================================================
// DOES PARAMETER USE WIND ARROW?
// ============================================================

function observationUsesWindArrow() {

    return (

        observationParameter === "gust"

        ||

        observationParameter === "wind"

    );

}
// ============================================================
// LOAD METAR GEOJSON
// ============================================================

async function loadMetarData() {

    try {

        const response =
            await fetch(

                `${METAR_GEOJSON_URL}?t=${Date.now()}`,

                {

                    cache:
                        "no-store"

                }

            );


        if (
            !response.ok
        ) {

            throw new Error(

                `METAR GeoJSON HTTP ${response.status}`

            );

        }


        const data =
            await response.json();


        if (
            !data
            ||
            !Array.isArray(
                data.features
            )
        ) {

            throw new Error(
                "METAR GeoJSON is invalid."
            );

        }


        metarData =
            data;


        return data;

    }

    catch (error) {

        console.error(

            "METAR load failed:",

            error

        );


        return {

            type:
                "FeatureCollection",

            features:
                []

        };

    }

}


// ============================================================
// REFRESH METAR SOURCE
// ============================================================

async function refreshMetarData() {

    const data =
        await loadMetarData();


    allMaps().forEach(
        map => {

            if (
                !map
                ||
                !map.isStyleLoaded()
            ) {

                return;

            }


            const source =
                map.getSource(
                    "metar-observations"
                );


            if (
                source
            ) {

                source.setData(
                    data
                );

            }


            updateObservationLayerState(
                map
            );

        }
    );

}


// ============================================================
// CREATE WIND ARROW IMAGE
// ============================================================

function createWindArrowImage() {

    const size =
        64;


    const canvas =
        document.createElement(
            "canvas"
        );


    canvas.width =
        size;


    canvas.height =
        size;


    const ctx =
        canvas.getContext(
            "2d"
        );


    ctx.clearRect(
        0,
        0,
        size,
        size
    );


    ctx.save();


    ctx.translate(
        size / 2,
        size / 2
    );


    // ========================================================
    // ARROW SHAFT
    // ========================================================

    ctx.strokeStyle =
        "#ffffff";


    ctx.lineWidth =
        5;


    ctx.lineCap =
        "round";


    ctx.beginPath();


    ctx.moveTo(
        0,
        18
    );


    ctx.lineTo(
        0,
        -17
    );


    ctx.stroke();


    // ========================================================
    // ARROW HEAD
    // ========================================================

    ctx.fillStyle =
        "#ffffff";


    ctx.beginPath();


    ctx.moveTo(
        0,
        -26
    );


    ctx.lineTo(
        -10,
        -10
    );


    ctx.lineTo(
        10,
        -10
    );


    ctx.closePath();


    ctx.fill();


    // ========================================================
    // DARK OUTLINE FOR VISIBILITY
    // ========================================================

    ctx.strokeStyle =
        "#000000";


    ctx.lineWidth =
        2;


    ctx.beginPath();


    ctx.moveTo(
        0,
        18
    );


    ctx.lineTo(
        0,
        -17
    );


    ctx.stroke();


    ctx.beginPath();


    ctx.moveTo(
        0,
        -26
    );


    ctx.lineTo(
        -10,
        -10
    );


    ctx.lineTo(
        10,
        -10
    );


    ctx.closePath();


    ctx.stroke();


    ctx.restore();


    return ctx.getImageData(
        0,
        0,
        size,
        size
    );

}


// ============================================================
// ENSURE WIND ARROW IMAGE
// ============================================================

function ensureWindArrowImage(
    map
) {

    if (
        map.hasImage(
            "metar-wind-arrow"
        )
    ) {

        return;

    }


    const image =
        createWindArrowImage();


    map.addImage(

        "metar-wind-arrow",

        image,

        {

            pixelRatio:
                2

        }

    );

}


// ============================================================
// ADD METAR OBSERVATIONS
// ============================================================

function addMetarObservations(
    map,
    roadLayer
) {

    ensureWindArrowImage(
        map
    );


    // ========================================================
    // SOURCE
    // ========================================================

    if (
        !map.getSource(
            "metar-observations"
        )
    ) {

        map.addSource(

            "metar-observations",

            {

                type:
                    "geojson",

                data:
                    metarData

            }

        );

    }


    // ========================================================
    // STATION DOT
    // ========================================================

    if (
        !map.getLayer(
            "metar-station-dot"
        )
    ) {

        map.addLayer(

            {

                id:
                    "metar-station-dot",

                type:
                    "circle",

                source:
                    "metar-observations",

                paint: {

                    "circle-radius": [

                        "interpolate",

                        [
                            "linear"
                        ],

                        [
                            "zoom"
                        ],

                        4,
                        2.5,

                        6,
                        3.5,

                        8,
                        4.5,

                        10,
                        5.5

                    ],

                    "circle-color":
                        "#ffffff",

                    "circle-stroke-color":
                        "#000000",

                    "circle-stroke-width":
                        1.5

                }

            },

            roadLayer

        );

    }


    // ========================================================
    // WIND ARROW
    // ========================================================

    if (
        !map.getLayer(
            "metar-wind-arrow-layer"
        )
    ) {

        map.addLayer(

            {

                id:
                    "metar-wind-arrow-layer",

                type:
                    "symbol",

                source:
                    "metar-observations",

                layout: {

                    "icon-image":
                        "metar-wind-arrow",

                    "icon-size": [

                        "interpolate",

                        [
                            "linear"
                        ],

                        [
                            "zoom"
                        ],

                        4,
                        0.55,

                        6,
                        0.70,

                        8,
                        0.85,

                        10,
                        1.0

                    ],

                    "icon-allow-overlap":
                        true,

                    "icon-ignore-placement":
                        true,

                    "icon-rotation-alignment":
                        "map",

                    "icon-pitch-alignment":
                        "map",

                    "icon-rotate": [

                        "case",

                        [

                            "all",

                            [
                                "has",
                                "wind_dir_deg"
                            ],

                            [
                                "!=",
                                [
                                    "get",
                                    "wind_dir_deg"
                                ],
                                null
                            ]

                        ],

                        [

                            "%",

                            [

                                "+",

                                [
                                    "to-number",
                                    [
                                        "get",
                                        "wind_dir_deg"
                                    ]
                                ],

                                180

                            ],

                            360

                        ],

                        0

                    ],

                    "icon-offset": [
                        0,
                        -28
                    ]

                }

            },

            roadLayer

        );

    }


    // ========================================================
    // OBSERVATION VALUE LABEL
    // ========================================================

    if (
        !map.getLayer(
            "metar-value-label"
        )
    ) {

        map.addLayer(

            {

                id:
                    "metar-value-label",

                type:
                    "symbol",

                source:
                    "metar-observations",

                layout: {

                    "text-field":
                        "",

                    "text-size": [

                        "interpolate",

                        [
                            "linear"
                        ],

                        [
                            "zoom"
                        ],

                        4,
                        11,

                        6,
                        13,

                        8,
                        15,

                        10,
                        17

                    ],

                    "text-font": [
                        "DIN Pro Bold",
                        "Arial Unicode MS Bold"
                    ],

                    "text-anchor":
                        "center",

                    "text-offset": [
                        0,
                        1.4
                    ],

                    "text-allow-overlap":
                        true,

                    "text-ignore-placement":
                        true

                },

                paint: {

                    "text-color":
                        "#ffffff",

                    "text-halo-color":
                        "#000000",

                    "text-halo-width":
                        2

                }

            },

            roadLayer

        );

    }


    // ========================================================
    // STATION ID
    // ========================================================

    if (
        !map.getLayer(
            "metar-station-label"
        )
    ) {

        map.addLayer(

            {

                id:
                    "metar-station-label",

                type:
                    "symbol",

                source:
                    "metar-observations",

                minzoom:
                    6.0,

                layout: {

                    "text-field": [

                        "coalesce",

                        [
                            "get",
                            "station"
                        ],

                        ""

                    ],

                    "text-size":
                        10,

                    "text-font": [
                        "DIN Pro Medium",
                        "Arial Unicode MS Regular"
                    ],

                    "text-anchor":
                        "top",

                    "text-offset": [
                        0,
                        2.8
                    ],

                    "text-allow-overlap":
                        true,

                    "text-ignore-placement":
                        true

                },

                paint: {

                    "text-color":
                        "#ffffff",

                    "text-halo-color":
                        "#000000",

                    "text-halo-width":
                        1.5

                }

            },

            roadLayer

        );

    }


    updateObservationLayerState(
        map
    );

}


// ============================================================
// OBSERVATION TEXT EXPRESSION
// ============================================================

function buildObservationTextExpression() {

    if (
        observationParameter === "gust"
    ) {

        return [

            "case",

            [
                "has",
                "wind_gust_mph"
            ],

            [

                "concat",

                "G",

                [

                    "to-string",

                    [

                        "round",

                        [
                            "to-number",
                            [
                                "get",
                                "wind_gust_mph"
                            ]
                        ]

                    ]

                ]

            ],

            ""

        ];

    }


    if (
        observationParameter === "wind"
    ) {

        return [

            "case",

            [
                "has",
                "wind_speed_mph"
            ],

            [

                "to-string",

                [

                    "round",

                    [
                        "to-number",
                        [
                            "get",
                            "wind_speed_mph"
                        ]
                    ]

                ]

            ],

            ""

        ];

    }


    if (
        observationParameter === "temp"
    ) {

        return [

            "case",

            [
                "has",
                "temp_f"
            ],

            [

                "to-string",

                [

                    "round",

                    [
                        "to-number",
                        [
                            "get",
                            "temp_f"
                        ]
                    ]

                ]

            ],

            ""

        ];

    }


    if (
        observationParameter === "dewpoint"
    ) {

        return [

            "case",

            [
                "has",
                "dewpoint_f"
            ],

            [

                "to-string",

                [

                    "round",

                    [
                        "to-number",
                        [
                            "get",
                            "dewpoint_f"
                        ]
                    ]

                ]

            ],

            ""

        ];

    }


    if (
        observationParameter === "rh"
    ) {

        return [

            "case",

            [
                "has",
                "rh"
            ],

            [

                "concat",

                [

                    "to-string",

                    [

                        "round",

                        [
                            "to-number",
                            [
                                "get",
                                "rh"
                            ]
                        ]

                    ]

                ],

                "%"

            ],

            ""

        ];

    }


    return "";

}


// ============================================================
// UPDATE OBSERVATION LAYER STATE
// ============================================================

function updateObservationLayerState(
    map
) {

    if (
        !map
    ) {

        return;

    }


    const metarVisible =
        !!overlayState.metar;


    // ========================================================
    // METAR BASE VISIBILITY
    // ========================================================

    setLayerVisibility(

        map,

        [
            "metar-station-dot",
            "metar-value-label",
            "metar-station-label"
        ],

        metarVisible

    );


    // ========================================================
    // WIND ARROW ONLY FOR WIND / GUST
    // ========================================================

    setLayerVisibility(

        map,

        [
            "metar-wind-arrow-layer"
        ],

        metarVisible
        &&
        observationUsesWindArrow()

    );


    // ========================================================
    // VALUE LABEL
    // ========================================================

    if (
        map.getLayer(
            "metar-value-label"
        )
    ) {

        map.setLayoutProperty(

            "metar-value-label",

            "text-field",

            buildObservationTextExpression()

        );

    }

}


// ============================================================
// CHANGE OBSERVATION PARAMETER
// ============================================================

function setObservationParameter(
    parameter
) {

    observationParameter =
        parameter;


    allMaps().forEach(
        map => {

            if (
                map
                &&
                map.isStyleLoaded()
            ) {

                updateObservationLayerState(
                    map
                );

            }

        }
    );

}


// ============================================================
// METAR POPUP HTML
// ============================================================

function makeMetarPopupHtml(
    properties
) {

    const station =
        properties.station
        ||
        "METAR";


    const temp =
        Number(
            properties.temp_f
        );


    const dewpoint =
        Number(
            properties.dewpoint_f
        );


    const rh =
        Number(
            properties.rh
        );


    const windDir =
        Number(
            properties.wind_dir_deg
        );


    const windSpeed =
        Number(
            properties.wind_speed_mph
        );


    const windGust =
        Number(
            properties.wind_gust_mph
        );


    const format =
        value => {

            return Number.isFinite(
                value
            )
                ? Math.round(
                    value
                )
                : "N/A";

        };


    return `

        <div style="
            font-family: Arial, sans-serif;
            min-width: 190px;
        ">

            <div style="
                font-size: 15px;
                font-weight: 800;
                margin-bottom: 8px;
            ">
                ${station}
            </div>

            <div style="
                font-size: 12px;
                line-height: 1.65;
            ">

                <b>Temperature:</b>
                ${format(temp)}°F

                <br>

                <b>Dew Point:</b>
                ${format(dewpoint)}°F

                <br>

                <b>RH:</b>
                ${format(rh)}%

                <br>

                <b>Wind:</b>
                ${format(windDir)}°
                at
                ${format(windSpeed)} mph

                <br>

                <b>Gust:</b>
                ${format(windGust)} mph

            </div>

        </div>

    `;

}


// ============================================================
// CONNECT METAR POPUPS
// ============================================================

function connectMetarPopups(
    map
) {

    map.on(

        "click",

        "metar-station-dot",

        event => {

            if (
                !event.features
                ||
                !event.features.length
            ) {

                return;

            }


            const feature =
                event.features[
                    0
                ];


            const coordinates =
                feature.geometry.coordinates.slice();


            new mapboxgl.Popup({

                closeButton:
                    true,

                closeOnClick:
                    true

            })
                .setLngLat(
                    coordinates
                )
                .setHTML(

                    makeMetarPopupHtml(

                        feature.properties
                        ||
                        {}

                    )

                )
                .addTo(
                    map
                );

        }

    );


    map.on(

        "mouseenter",

        "metar-station-dot",

        () => {

            map
                .getCanvas()
                .style
                .cursor =
                    "pointer";

        }

    );


    map.on(

        "mouseleave",

        "metar-station-dot",

        () => {

            map
                .getCanvas()
                .style
                .cursor =
                    "crosshair";

        }

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
        !Array.isArray(
            style.layers
        )
    ) {

        return undefined;

    }


    const preferredLayers = [

        "road-label",

        "road-number-shield",

        "road-exit-shield",

        "road-intersection",

        "road"

    ];


    for (
        const preferred of preferredLayers
    ) {

        const layer =
            style.layers.find(

                item =>

                    item.id === preferred

            );


        if (
            layer
        ) {

            return layer.id;

        }

    }


    const roadLayer =
        style.layers.find(

            layer => {

                const id =
                    String(
                        layer.id
                    ).toLowerCase();


                return (

                    id.includes(
                        "road"
                    )

                    &&

                    (
                        layer.type === "line"

                        ||

                        layer.type === "symbol"
                    )

                );

            }

        );


    return roadLayer
        ? roadLayer.id
        : undefined;

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
// SETUP MAP LAYERS
// ============================================================

async function setupMapLayers(
    map
) {

    const roadLayer =
        findRoadLayer(
            map
        );


    // ========================================================
    // METAR OBSERVATIONS
    // ========================================================

    addMetarObservations(

        map,

        roadLayer

    );


    connectMetarPopups(
        map
    );


    // ========================================================
    // SPC DAY 1
    // ========================================================

    addSpcOutlook(

        map,

        1,

        roadLayer

    );


    // ========================================================
    // SPC DAY 2
    // ========================================================

    addSpcOutlook(

        map,

        2,

        roadLayer

    );


    // ========================================================
    // SPC DAY 3
    // ========================================================

    addSpcOutlook(

        map,

        3,

        roadLayer

    );


    // ========================================================
    // SPC FIRE WEATHER DAY 1
    // ========================================================

    addSpcFireWeather(

        map,

        1,

        roadLayer

    );


    // ========================================================
    // SPC FIRE WEATHER DAY 2
    // ========================================================

    addSpcFireWeather(

        map,

        2,

        roadLayer

    );


    // ========================================================
    // LIVE NWS HAZARDS
    // ========================================================

    await addNwsHazards(

        map,

        roadLayer

    );


    // ========================================================
    // WPC ERO DAY 1
    // ========================================================

    addWpcEro(

        map,

        1,

        roadLayer

    );


    // ========================================================
    // WPC ERO DAY 2
    // ========================================================

    addWpcEro(

        map,

        2,

        roadLayer

    );


    // ========================================================
    // WPC ERO DAY 3
    // ========================================================

    addWpcEro(

        map,

        3,

        roadLayer

    );


    // ========================================================
    // MAPBOX BOUNDARY SOURCE
    // ========================================================

    if (
        !map.getSource(
            "boundary-data"
        )
    ) {

        map.addSource(

            "boundary-data",

            {

                type:
                    "vector",

                url:
                    "mapbox://mapbox.mapbox-streets-v8"

            }

        );

    }


    // ========================================================
    // COUNTY BOUNDARIES
    // ========================================================

    if (
        !map.getLayer(
            "custom-county-boundaries"
        )
    ) {

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

    }


    // ========================================================
    // STATE BOUNDARIES
    // ========================================================

    if (
        !map.getLayer(
            "custom-state-boundaries"
        )
    ) {

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

    }


    // ========================================================
    // LBF CWA SOURCE
    // ========================================================

    if (
        !map.getSource(
            "lbf-cwa"
        )
    ) {

        map.addSource(

            "lbf-cwa",

            {

                type:
                    "geojson",

                data:
                    "data/lbf_cwa.geojson"

            }

        );

    }


    // ========================================================
    // LBF CWA DARK OUTLINE
    // ========================================================

    if (
        !map.getLayer(
            "lbf-cwa-outline"
        )
    ) {

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

    }


    // ========================================================
    // LBF CWA WHITE INNER LINE
    // ========================================================

    if (
        !map.getLayer(
            "lbf-cwa-boundary"
        )
    ) {

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

    }


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
                layer.id.toLowerCase();


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

                    // Ignore unsupported basemap layers.

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

                // Some Mapbox symbol layers cannot
                // accept this filter.

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
    // METAR
    // ========================================================

    updateObservationLayerState(
        map
    );


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
    // SPC FIRE DAY 1
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
    // SPC FIRE DAY 2
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
    // NWS FIRE WEATHER
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
// REFRESH OVERLAY MAPS
// ============================================================

function refreshOverlayMaps() {

    allMaps().forEach(
        map => {

            if (
                map
                &&
                map.isStyleLoaded()
            ) {

                applyOverlayStateToMap(
                    map
                );

            }

        }
    );

}


// ============================================================
// CONNECT OVERLAY TOGGLE
// ============================================================

function connectOverlayToggle(
    elementId,
    stateKey
) {

    const element =
        document.getElementById(
            elementId
        );


    if (
        !element
    ) {

        console.warn(

            `Overlay toggle not found: ${elementId}`

        );


        return;

    }


    element.checked =
        !!overlayState[
            stateKey
        ];


    element.addEventListener(

        "change",

        event => {

            overlayState[
                stateKey
            ] =
                event.target.checked;


            refreshOverlayMaps();

        }

    );

}


// ============================================================
// CONNECT OBSERVATION CONTROLS
// ============================================================

function connectObservationControls() {

    // ========================================================
    // METAR CHECKBOX
    // ========================================================

    connectOverlayToggle(

        "metar-toggle",

        "metar"

    );


    // ========================================================
    // MESONET CHECKBOX
    //
    // The UI is ready, but Mesonet data will be connected
    // after METAR is working.
    // ========================================================

    connectOverlayToggle(

        "mesonet-toggle",

        "mesonet"

    );


    // ========================================================
    // PARAMETER SELECT
    // ========================================================

    const parameterSelect =
        document.getElementById(
            "observation-parameter-select"
        );


    if (
        parameterSelect
    ) {

        parameterSelect.value =
            observationParameter;


        parameterSelect.addEventListener(

            "change",

            event => {

                setObservationParameter(

                    event.target.value

                );

            }

        );

    }

}


// ============================================================
// LOAD INITIAL OBSERVATION DATA
// ============================================================

async function initializeObservationData() {

    try {

        await loadMetarData();


        allMaps().forEach(
            map => {

                if (
                    !map
                    ||
                    !map.isStyleLoaded()
                ) {

                    return;

                }


                const source =
                    map.getSource(
                        "metar-observations"
                    );


                if (
                    source
                ) {

                    source.setData(
                        metarData
                    );

                }


                updateObservationLayerState(
                    map
                );

            }
        );


        console.log(

            `Loaded ${metarData.features.length} METAR observations.`

        );

    }

    catch (error) {

        console.error(

            "Initial METAR load failed:",

            error

        );

    }

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


    if (
        !product
    ) {

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


    if (
        !response.ok
    ) {

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


    if (
        !product
    ) {

        return;

    }


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


    if (
        source
    ) {

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


    if (
        !singleManifest
        ||
        !Array.isArray(
            singleManifest.hours
        )
    ) {

        throw new Error(
            "Invalid single-model manifest."
        );

    }


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


    if (
        currentFrameIndex < 0
        &&
        availableFrames.length
    ) {

        currentFrameIndex =
            0;

    }


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


    if (
        !compareManifests.hrrr
        ||
        !compareManifests.rrfs
    ) {

        throw new Error(
            "Comparison manifests unavailable."
        );

    }


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


    if (
        currentFrameIndex < 0
        &&
        availableFrames.length
    ) {

        currentFrameIndex =
            0;

    }


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


    if (
        !product
    ) {

        return null;

    }


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


    if (
        !response.ok
    ) {

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

    if (
        !data
    ) {

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


    if (
        !frame
    ) {

        return;

    }


    try {

        const grid =
            await loadSampleGrid(

                activeModel,

                singleManifest,

                frame

            );


        if (
            !grid
        ) {

            return;

        }


        const sample =
            sampleGridAtPoint(

                grid,

                lngLat.lng,

                lngLat.lat

            );


        if (
            !sample
        ) {

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
// DISPLAY CURRENT FRAME
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
// EXPECTED MAX FORECAST HOUR
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
// BUILD HOUR BUTTONS
// ============================================================

function buildHourButtons() {

    const container =
        document.getElementById(
            "model-hour-list"
        );


    if (
        !container
    ) {

        return;

    }


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
// SELECT FORECAST HOUR
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
// UPDATE HOUR BUTTON STYLE
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
// SCROLL SELECTED HOUR INTO VIEW
// ============================================================

function scrollSelectedHourIntoView() {

    const fhr =
        getSelectedFhr();


    const button =
        document.querySelector(

            `.model-hour-button[data-fhr="${fhr}"]`

        );


    if (
        button
    ) {

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
// START ANIMATION
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


    const playButton =
        document.getElementById(
            "model-play-button"
        );


    if (
        playButton
    ) {

        playButton.textContent =
            "❚❚";

    }


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


// ============================================================
// STOP ANIMATION
// ============================================================

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


    if (
        button
    ) {

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
// INITIALIZE COMPARISON MAPS
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


    // ========================================================
    // SETUP OVERLAYS
    // ========================================================

    await Promise.all([

        setupMapLayers(
            leftMap
        ),

        setupMapLayers(
            rightMap
        )

    ]);


    // ========================================================
    // METAR DATA
    // ========================================================

    const leftMetarSource =
        leftMap.getSource(
            "metar-observations"
        );


    if (
        leftMetarSource
    ) {

        leftMetarSource.setData(
            metarData
        );

    }


    const rightMetarSource =
        rightMap.getSource(
            "metar-observations"
        );


    if (
        rightMetarSource
    ) {

        rightMetarSource.setData(
            metarData
        );

    }


    // ========================================================
    // CURSORS
    // ========================================================

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


    // ========================================================
    // COMPARISON SAMPLING
    // ========================================================

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


    // ========================================================
    // SYNCHRONIZE MAPS
    // ========================================================

    function syncMap(
        source,
        target
    ) {

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

    }


    leftMap.on(

        "move",

        () => {

            syncMap(

                leftMap,

                rightMap

            );

        }

    );


    rightMap.on(

        "move",

        () => {

            syncMap(

                rightMap,

                leftMap

            );

        }

    );


    // ========================================================
    // START AT CURRENT SINGLE-MAP LOCATION
    // ========================================================

    const center =
        singleMap.getCenter();


    const camera = {

        center: [
            center.lng,
            center.lat
        ],

        zoom:
            singleMap.getZoom(),

        bearing:
            singleMap.getBearing(),

        pitch:
            singleMap.getPitch()

    };


    leftMap.jumpTo(
        camera
    );


    rightMap.jumpTo(
        camera
    );


    comparisonInitialized =
        true;


    console.log(
        "Comparison maps initialized."
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


    const singleContainer =
        document.getElementById(
            "single-map"
        );


    const comparisonContainer =
        document.getElementById(
            "comparison-container"
        );


    const modelSelect =
        document.getElementById(
            "model-select"
        );


    const productSelect =
        document.getElementById(
            "product-select"
        );


    const timeline =
        document.getElementById(
            "model-timeline"
        );


    const validLabel =
        document.getElementById(
            "model-valid-label"
        );


    const credit =
        document.getElementById(
            "graphics-credit"
        );


    // ========================================================
    // SINGLE MODEL
    // ========================================================

    if (
        mode === "single"
    ) {

        comparisonContainer
            ?.classList
            .add(
                "hidden"
            );


        singleContainer
            ?.classList
            .remove(
                "hidden"
            );


        if (
            modelSelect
        ) {

            modelSelect.disabled =
                false;

        }


        if (
            productSelect
        ) {

            productSelect.disabled =
                false;

        }


        if (
            timeline
        ) {

            timeline.style.display =
                "flex";

        }


        if (
            validLabel
        ) {

            validLabel.style.display =
                "block";

        }


        if (
            credit
        ) {

            credit.classList.remove(
                "no-timeline"
            );

        }


        setTimeout(

            () => {

                singleMap.resize();

            },

            50

        );


        await refreshSingleManifest();

    }


    // ========================================================
    // COMPARISON
    // ========================================================

    else if (
        mode === "compare"
    ) {

        singleContainer
            ?.classList
            .add(
                "hidden"
            );


        comparisonContainer
            ?.classList
            .remove(
                "hidden"
            );


        if (
            modelSelect
        ) {

            modelSelect.disabled =
                true;

        }


        if (
            productSelect
        ) {

            productSelect.disabled =
                false;

        }


        if (
            timeline
        ) {

            timeline.style.display =
                "flex";

        }


        if (
            validLabel
        ) {

            validLabel.style.display =
                "block";

        }


        if (
            credit
        ) {

            credit.classList.remove(
                "no-timeline"
            );

        }


        await initializeComparison();


        setTimeout(

            () => {

                leftMap.resize();

                rightMap.resize();

            },

            50

        );


        await refreshCompareManifests();

    }


    // ========================================================
    // OVERLAYS ONLY
    // ========================================================

    else if (
        mode === "overlays"
    ) {

        comparisonContainer
            ?.classList
            .add(
                "hidden"
            );


        singleContainer
            ?.classList
            .remove(
                "hidden"
            );


        if (
            modelSelect
        ) {

            modelSelect.disabled =
                true;

        }


        if (
            productSelect
        ) {

            productSelect.disabled =
                true;

        }


        if (
            timeline
        ) {

            timeline.style.display =
                "none";

        }


        if (
            validLabel
        ) {

            validLabel.style.display =
                "none";

        }


        if (
            credit
        ) {

            credit.classList.add(
                "no-timeline"
            );

        }


        setTimeout(

            () => {

                singleMap.resize();

            },

            50

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

    }


    // ========================================================
    // MODEL RASTER VISIBILITY
    // ========================================================

    if (
        mode !== "overlays"
        &&
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


    refreshOverlayMaps();


    updateExportVisibility();

}


// ============================================================
// SWITCH SINGLE MODEL
// ============================================================

async function switchSingleModel(
    modelName
) {

    stopAnimation();


    activeModel =
        modelName;


    sampleCache.clear();


    await refreshSingleManifest();

}


// ============================================================
// UPDATE VALID LABEL
// ============================================================

function updateValidLabel(
    frame
) {

    const element =
        document.getElementById(
            "model-valid-label"
        );


    if (
        !element
    ) {

        return;

    }


    if (
        !frame
        ||
        !frame.valid
    ) {

        element.textContent =
            "Valid time unavailable";


        return;

    }


    element.textContent =

        `Valid: ${formatValidTimeCentral(
            frame.valid
        )}`;

}


// ============================================================
// REFRESH CURRENT MODEL DATA
// ============================================================

async function refreshCurrentData() {

    try {

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

            "Model refresh failed:",

            error

        );

    }

}


// ============================================================
// WAIT FOR MAP IDLE
// ============================================================

function waitForMapIdle(
    map,
    timeoutMs = 8000
) {

    return new Promise(
        resolve => {

            if (
                !map
            ) {

                resolve();

                return;

            }


            let finished =
                false;


            const finish =
                () => {

                    if (
                        finished
                    ) {

                        return;

                    }


                    finished =
                        true;


                    resolve();

                };


            map.once(

                "idle",

                finish

            );


            setTimeout(

                finish,

                timeoutMs

            );

        }
    );

}


// ============================================================
// LOAD IMAGE
// ============================================================

function loadImageForExport(
    src
) {

    return new Promise(

        (
            resolve,
            reject
        ) => {

            const image =
                new Image();


            image.onload =
                () => {

                    resolve(
                        image
                    );

                };


            image.onerror =
                reject;


            image.src =
                src;

        }

    );

}


// ============================================================
// CREATE EXPORT CANVAS
// ============================================================

async function createExportCanvas(
    map
) {

    await waitForMapIdle(
        map
    );


    const sourceCanvas =
        map.getCanvas();


    const width =
        sourceCanvas.width;


    const height =
        sourceCanvas.height;


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


    // ========================================================
    // MAP
    // ========================================================

    ctx.drawImage(

        sourceCanvas,

        0,
        0,

        width,
        height

    );


    // ========================================================
    // HEADER BACKGROUND
    // ========================================================

    const headerHeight =
        Math.max(

            80,

            Math.round(
                height * 0.10
            )

        );


    ctx.fillStyle =
        "rgba(16,21,28,0.88)";


    ctx.fillRect(

        0,
        0,

        width,
        headerHeight

    );


    // ========================================================
    // LOGO
    // ========================================================

    try {

        let logo =
            exportLogoImage;


        if (
            !logo.complete
            ||
            !logo.naturalWidth
        ) {

            logo =
                await loadImageForExport(

                    "assets/NOAANWSLogos.png"

                );

        }


        const logoHeight =
            headerHeight * 0.70;


        const logoWidth =

            logo.naturalWidth

            /

            logo.naturalHeight

            *

            logoHeight;


        ctx.drawImage(

            logo,

            16,

            (
                headerHeight
                -
                logoHeight
            )
            /
            2,

            logoWidth,

            logoHeight

        );


        // ====================================================
        // TITLE
        // ====================================================

        const titleX =
            logoWidth + 34;


        ctx.fillStyle =
            "#ffffff";


        ctx.font =
            `bold ${Math.max(
                18,
                Math.round(
                    headerHeight * 0.26
                )
            )}px Arial`;


        ctx.textBaseline =
            "middle";


        ctx.fillText(

            "NWS North Platte, NE",

            titleX,

            headerHeight * 0.40

        );


        // ====================================================
        // SUBTITLE
        // ====================================================

        ctx.font =
            `${Math.max(
                12,
                Math.round(
                    headerHeight * 0.16
                )
            )}px Arial`;


        ctx.fillStyle =
            "rgba(255,255,255,0.82)";


        ctx.fillText(

            "Weather Graphics Builder",

            titleX,

            headerHeight * 0.69

        );

    }

    catch (error) {

        console.warn(

            "Export logo could not be drawn:",

            error

        );

    }


    // ========================================================
    // VALID TIME
    // ========================================================

    if (
        viewerMode !== "overlays"
    ) {

        const fhr =
            getSelectedFhr();


        let frame =
            null;


        if (
            viewerMode === "single"
        ) {

            frame =
                findFrame(

                    singleManifest,

                    fhr

                );

        }


        else if (
            viewerMode === "compare"
        ) {

            frame =
                findFrame(

                    compareManifests.hrrr,

                    fhr

                );

        }


        if (
            frame
            &&
            frame.valid
        ) {

            const text =

                `Valid: ${formatValidTimeCentral(
                    frame.valid
                )}`;


            ctx.font =
                `bold ${Math.max(
                    13,
                    Math.round(
                        headerHeight * 0.18
                    )
                )}px Arial`;


            ctx.textAlign =
                "right";


            ctx.textBaseline =
                "middle";


            ctx.fillStyle =
                "#ffffff";


            ctx.fillText(

                text,

                width - 18,

                headerHeight / 2

            );


            ctx.textAlign =
                "left";

        }

    }


    return canvas;

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


    const link =
        document.createElement(
            "a"
        );


    link.href =
        url;


    link.download =
        filename;


    document.body.appendChild(
        link
    );


    link.click();


    link.remove();


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
    ) {

        return;

    }


    exportBusy =
        true;


    try {

        const map =

            viewerMode === "compare"

                ? leftMap

                : singleMap;


        if (
            !map
        ) {

            return;

        }


        const canvas =
            await createExportCanvas(
                map
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


        if (
            !blob
        ) {

            throw new Error(
                "PNG creation failed."
            );

        }


        const timestamp =
            new Date()
                .toISOString()
                .replace(
                    /[:.]/g,
                    "-"
                );


        downloadBlob(

            blob,

            `nws-lbf-graphics-${timestamp}.png`

        );

    }

    catch (error) {

        console.error(

            "PNG export failed:",

            error

        );

    }

    finally {

        exportBusy =
            false;

    }

}


// ============================================================
// WAIT
// ============================================================

function sleep(
    milliseconds
) {

    return new Promise(

        resolve =>

            setTimeout(
                resolve,
                milliseconds
            )

    );

}


// ============================================================
// CAPTURE GIF FRAME
// ============================================================

async function captureGifFrame(
    map
) {

    const canvas =
        await createExportCanvas(
            map
        );


    // ========================================================
    // LIMIT GIF SIZE
    // ========================================================

    if (
        canvas.width <= GIF_MAX_WIDTH
    ) {

        return canvas;

    }


    const scale =

        GIF_MAX_WIDTH

        /

        canvas.width;


    const resized =
        document.createElement(
            "canvas"
        );


    resized.width =
        GIF_MAX_WIDTH;


    resized.height =
        Math.round(

            canvas.height
            *
            scale

        );


    const ctx =
        resized.getContext(
            "2d"
        );


    ctx.drawImage(

        canvas,

        0,
        0,

        resized.width,
        resized.height

    );


    return resized;

}


// ============================================================
// SAVE GIF
// ============================================================

async function saveGif(
    startIndex,
    endIndex
) {

    if (
        exportBusy
    ) {

        return;

    }


    if (
        typeof GIF === "undefined"
    ) {

        console.error(

            "GIF library is not loaded."

        );


        const status =
            document.getElementById(
                "gif-status"
            );


        if (
            status
        ) {

            status.textContent =
                "GIF library is not loaded.";

        }


        return;

    }


    if (
        !availableFrames.length
    ) {

        return;

    }


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

        const first =
            Math.max(

                0,

                Math.min(
                    startIndex,
                    endIndex
                )

            );


        const last =
            Math.min(

                availableFrames.length - 1,

                Math.max(
                    startIndex,
                    endIndex
                )

            );


        const map =

            viewerMode === "compare"

                ? leftMap

                : singleMap;


        if (
            !map
        ) {

            return;

        }


        const gif =
            new GIF({

                workers:
                    2,

                quality:
                    10,

                workerScript:
                    "gif.worker.js"

            });


        for (
            let index = first;
            index <= last;
            index++
        ) {

            currentFrameIndex =
                index;


            displayCurrentFrame();


            if (
                status
            ) {

                status.textContent =

                    `Capturing ` +

                    `${index - first + 1} of ` +

                    `${last - first + 1}...`;

            }


            await waitForMapIdle(
                map
            );


            await sleep(
                120
            );


            const canvas =
                await captureGifFrame(
                    map
                );


            gif.addFrame(

                canvas,

                {

                    copy:
                        true,

                    delay:
                        GIF_FRAME_DELAY_MS

                }

            );

        }


        gif.on(

            "progress",

            progress => {

                if (
                    status
                ) {

                    status.textContent =

                        `Rendering GIF ` +

                        `${Math.round(
                            progress * 100
                        )}%`;

                }

            }

        );


        gif.on(

            "finished",

            blob => {

                const timestamp =
                    new Date()
                        .toISOString()
                        .replace(
                            /[:.]/g,
                            "-"
                        );


                downloadBlob(

                    blob,

                    `nws-lbf-loop-${timestamp}.gif`

                );


                if (
                    status
                ) {

                    status.textContent =
                        "GIF complete.";

                }


                currentFrameIndex =
                    originalIndex;


                displayCurrentFrame();


                exportBusy =
                    false;

            }

        );


        if (
            status
        ) {

            status.textContent =
                "Rendering GIF...";

        }


        gif.render();

    }

    catch (error) {

        console.error(

            "GIF export failed:",

            error

        );


        if (
            status
        ) {

            status.textContent =
                "GIF export failed.";

        }


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

                const startIndex =
                    Number(

                        document
                            .getElementById(
                                "gif-start-hour"
                            )
                            .value

                    );


                const endIndex =
                    Number(

                        document
                            .getElementById(
                                "gif-end-hour"
                            )
                            .value

                    );


                if (
                    !Number.isFinite(
                        startIndex
                    )
                    ||
                    !Number.isFinite(
                        endIndex
                    )
                ) {

                    return;

                }


                if (
                    startIndex > endIndex
                ) {

                    const status =
                        document.getElementById(
                            "gif-status"
                        );


                    if (
                        status
                    ) {

                        status.textContent =
                            "Start hour must be before end hour.";

                    }


                    return;

                }


                saveGif(

                    startIndex,

                    endIndex

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


    const gifPanel =
        document.getElementById(
            "gif-panel"
        );


    if (
        !controls
    ) {

        return;

    }


    // Keep PNG available in overlays-only mode.
    // GIF only makes sense when model frames exist.

    controls.style.display =
        "flex";


    const gifButton =
        document.getElementById(
            "save-gif-button"
        );


    if (
        viewerMode === "overlays"
    ) {

        if (
            gifButton
        ) {

            gifButton.style.display =
                "none";

        }


        if (
            gifPanel
        ) {

            gifPanel.classList.remove(
                "open"
            );

        }

    }

    else {

        if (
            gifButton
        ) {

            gifButton.style.display =
                "block";

        }

    }

}


// ============================================================
// ALL MAPS
// ============================================================

function allMaps() {

    const maps =
        [];


    if (
        singleMap
    ) {

        maps.push(
            singleMap
        );

    }


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
// SAFE ELEMENT LOOKUP
// ============================================================

function getElement(
    id
) {

    return document.getElementById(
        id
    );

}


// ============================================================
// SETUP UI EVENTS
// ============================================================

function setupUiEvents() {

    // ========================================================
    // OVERLAY MENU
    // ========================================================

    const overlayMenuButton =
        getElement(
            "overlay-menu-button"
        );


    const overlayMenuContent =
        getElement(
            "overlay-menu-content"
        );


    if (
        overlayMenuButton
        &&
        overlayMenuContent
    ) {

        overlayMenuButton.onclick =
            () => {

                overlayMenuContent
                    .classList
                    .toggle(
                        "open"
                    );

            };

    }


    // ========================================================
    // OBSERVATIONS
    // ========================================================

    connectObservationControls();


    // ========================================================
    // SPC OUTLOOKS
    // ========================================================

    connectOverlayToggle(

        "spc-day1-toggle",

        "spcDay1"

    );


    connectOverlayToggle(

        "spc-day2-toggle",

        "spcDay2"

    );


    connectOverlayToggle(

        "spc-day3-toggle",

        "spcDay3"

    );


    // ========================================================
    // SPC FIRE WEATHER
    // ========================================================

    connectOverlayToggle(

        "fire-day1-toggle",

        "fireDay1"

    );


    connectOverlayToggle(

        "fire-day2-toggle",

        "fireDay2"

    );


    // ========================================================
    // NWS ALL HAZARDS
    // ========================================================

    connectOverlayToggle(

        "nws-all-toggle",

        "nwsAll"

    );


    // ========================================================
    // NWS SEVERE WARNINGS
    // ========================================================

    connectOverlayToggle(

        "nws-severe-toggle",

        "nwsSevere"

    );


    // ========================================================
    // NWS WATCHES
    // ========================================================

    connectOverlayToggle(

        "nws-watches-toggle",

        "nwsWatches"

    );


    // ========================================================
    // NWS FLOOD
    // ========================================================

    connectOverlayToggle(

        "nws-flood-toggle",

        "nwsFlood"

    );


    // ========================================================
    // NWS FIRE WEATHER
    // ========================================================

    connectOverlayToggle(

        "nws-fire-toggle",

        "nwsFire"

    );


    // ========================================================
    // NWS HEAT
    // ========================================================

    connectOverlayToggle(

        "nws-heat-toggle",

        "nwsHeat"

    );


    // ========================================================
    // NWS WINTER
    // ========================================================

    connectOverlayToggle(

        "nws-winter-toggle",

        "nwsWinter"

    );


    // ========================================================
    // WPC
    // ========================================================

    connectOverlayToggle(

        "wpc-day1-toggle",

        "wpcDay1"

    );


    connectOverlayToggle(

        "wpc-day2-toggle",

        "wpcDay2"

    );


    connectOverlayToggle(

        "wpc-day3-toggle",

        "wpcDay3"

    );


    // ========================================================
    // BOUNDARIES
    // ========================================================

    connectOverlayToggle(

        "cwa-toggle",

        "cwa"

    );


    connectOverlayToggle(

        "county-toggle",

        "counties"

    );


    connectOverlayToggle(

        "state-toggle",

        "states"

    );


    // ========================================================
    // VIEWER MODE
    // ========================================================

    const viewerModeSelect =
        getElement(
            "viewer-mode-select"
        );


    if (
        viewerModeSelect
    ) {

        viewerModeSelect.onchange =
            async event => {

                try {

                    await switchViewerMode(
                        event.target.value
                    );

                }

                catch (error) {

                    console.error(

                        "Viewer mode switch failed:",

                        error

                    );

                }

            };

    }


    // ========================================================
    // MODEL SELECT
    // ========================================================

    const modelSelect =
        getElement(
            "model-select"
        );


    if (
        modelSelect
    ) {

        modelSelect.onchange =
            async event => {

                try {

                    await switchSingleModel(
                        event.target.value
                    );

                }

                catch (error) {

                    console.error(

                        "Model switch failed:",

                        error

                    );

                }

            };

    }


    // ========================================================
    // PRODUCT SELECT
    // ========================================================

    const productSelect =
        getElement(
            "product-select"
        );


    if (
        productSelect
    ) {

        productSelect.onchange =
            async event => {

                activeProduct =
                    event.target.value;


                sampleCache.clear();


                try {

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

                        "Product switch failed:",

                        error

                    );

                }

            };

    }


    // ========================================================
    // PREVIOUS FRAME
    // ========================================================

    const previousButton =
        getElement(
            "model-prev-button"
        );


    if (
        previousButton
    ) {

        previousButton.onclick =
            () => {

                stopAnimation();


                moveFrame(
                    -1
                );

            };

    }


    // ========================================================
    // NEXT FRAME
    // ========================================================

    const nextButton =
        getElement(
            "model-next-button"
        );


    if (
        nextButton
    ) {

        nextButton.onclick =
            () => {

                stopAnimation();


                moveFrame(
                    1
                );

            };

    }


    // ========================================================
    // PLAY / PAUSE
    // ========================================================

    const playButton =
        getElement(
            "model-play-button"
        );


    if (
        playButton
    ) {

        playButton.onclick =
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

}


// ============================================================
// REFRESH LIVE NWS HAZARDS
// ============================================================

async function refreshNwsHazards() {

    try {

        nwsHazardsLoaded =
            false;


        await loadNwsHazardData();


        allMaps().forEach(
            map => {

                if (
                    !map
                    ||
                    !map.isStyleLoaded()
                ) {

                    return;

                }


                const currentSource =
                    map.getSource(
                        "nws-current-warnings"
                    );


                if (
                    currentSource
                ) {

                    currentSource.setData(
                        nwsCurrentWarningsData
                    );

                }


                const wwaSource =
                    map.getSource(
                        "nws-watches-warnings"
                    );


                if (
                    wwaSource
                ) {

                    wwaSource.setData(
                        nwsWatchesWarningsData
                    );

                }


                applyOverlayStateToMap(
                    map
                );

            }
        );


        console.log(
            "Live NWS hazards refreshed."
        );

    }

    catch (error) {

        console.error(

            "NWS hazard refresh failed:",

            error

        );

    }

}


// ============================================================
// NWS AUTOMATIC REFRESH
// ============================================================

const NWS_HAZARD_REFRESH_MS =
    5 * 60 * 1000;


// ============================================================
// REFRESH OBSERVATIONS
// ============================================================

async function refreshObservations() {

    try {

        await refreshMetarData();


        console.log(

            `METAR observations refreshed: ` +
            `${metarData.features.length} stations`

        );

    }

    catch (error) {

        console.error(

            "Observation refresh failed:",

            error

        );

    }

}


// ============================================================
// INITIAL MAP LOAD
// ============================================================

singleMap.on(

    "load",

    async () => {

        try {

            // =================================================
            // LOAD METAR DATA FIRST
            //
            // If data/metar.geojson does not exist yet,
            // loadMetarData() will return an empty collection.
            // The rest of the site can still initialize.
            // =================================================

            await loadMetarData();


            // =================================================
            // ADD MAP OVERLAYS
            // =================================================

            await setupMapLayers(
                singleMap
            );


            // =================================================
            // PUT LOADED METARS INTO SOURCE
            // =================================================

            const metarSource =
                singleMap.getSource(
                    "metar-observations"
                );


            if (
                metarSource
            ) {

                metarSource.setData(
                    metarData
                );

            }


            console.log(

                `Initial METAR observations: ` +
                `${metarData.features.length}`

            );


            // =================================================
            // CURSOR
            // =================================================

            singleMap
                .getCanvas()
                .style
                .cursor =
                    "crosshair";


            // =================================================
            // SINGLE MODEL SAMPLING
            // =================================================

            singleMap.on(

                "click",

                event => {

                    if (
                        viewerMode === "single"
                    ) {

                        // Do not model-sample when the user
                        // clicked directly on a METAR station.

                        const metarFeatures =
                            singleMap.queryRenderedFeatures(

                                event.point,

                                {

                                    layers:
                                        singleMap.getLayer(
                                            "metar-station-dot"
                                        )

                                            ? [
                                                "metar-station-dot"
                                            ]

                                            : []

                                }

                            );


                        if (
                            metarFeatures.length
                        ) {

                            return;

                        }


                        sampleSingleModel(

                            singleMap,

                            event.lngLat

                        );

                    }

                }

            );


            // =================================================
            // EXPORT CONTROLS
            // =================================================

            createExportControls();


            // =================================================
            // UI EVENTS
            // =================================================

            setupUiEvents();


            // =================================================
            // INITIAL OVERLAY STATE
            // =================================================

            applyOverlayStateToMap(
                singleMap
            );


            // =================================================
            // INITIAL MODEL MANIFEST
            // =================================================

            try {

                await refreshSingleManifest();

            }

            catch (error) {

                console.error(

                    "Initial model manifest failed:",

                    error

                );

            }


            // =================================================
            // EXPORT VISIBILITY
            // =================================================

            updateExportVisibility();


            // =================================================
            // MODEL REFRESH
            // =================================================

            setInterval(

                refreshCurrentData,

                MANIFEST_REFRESH_MS

            );


            // =================================================
            // LIVE NWS HAZARD REFRESH
            // =================================================

            setInterval(

                refreshNwsHazards,

                NWS_HAZARD_REFRESH_MS

            );


            // =================================================
            // METAR REFRESH
            //
            // Reads data/metar.geojson every five minutes.
            // =================================================

            setInterval(

                refreshObservations,

                OBSERVATION_REFRESH_MS

            );


            console.log(
                "Weather graphics viewer initialized."
            );

        }

        catch (error) {

            console.error(

                "Initial map setup failed:",

                error

            );

        }

    }

);
