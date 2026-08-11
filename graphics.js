mapboxgl.accessToken = "pk.eyJ1IjoibWF0dGhld2xhYmVuejciLCJhIjoiY21zbjhxZ3ZkMXBoNDJ3cHl5eG5uNzlpZCJ9.UBy4k84SejJzzu2VF0TtcA";

// ============================================================
// AWS HRRR SETTINGS
// ============================================================

const HRRR_BASE_URL =
    "https://mtl-nwslbf-model-data.s3.us-east-2.amazonaws.com/" +
    "weather-graphics/hrrr/reflUH/latest";


const HRRR_MANIFEST_URL =
    `${HRRR_BASE_URL}/manifest.json`;


// Refresh manifest every 30 seconds while the page is open

const MANIFEST_REFRESH_MS = 30000;


// ============================================================
// HRRR STATE
// ============================================================

let hrrrManifest = null;

let availableHrrrFrames = [];

let currentHrrrIndex = 0;

let hrrrSourceCreated = false;


// ============================================================
// CREATE MAP
// ============================================================

const map = new mapboxgl.Map({

    container: "map",

    style:
        "mapbox://styles/mapbox/satellite-streets-v12",

    center: [
        -100.75,
        41.1
    ],

    zoom: 6,

    preserveDrawingBuffer: true

});


// ============================================================
// NAVIGATION
// ============================================================

map.addControl(
    new mapboxgl.NavigationControl(),
    "top-right"
);


// ============================================================
// CREATE HRRR USER INTERFACE
// ============================================================

function createHrrrUI() {

    let controls =
        document.getElementById(
            "map-controls"
        );


    // --------------------------------------------------------
    // Create controls container if needed
    // --------------------------------------------------------

    if (!controls) {

        controls =
            document.createElement(
                "div"
            );

        controls.id =
            "map-controls";

        controls.style.position =
            "absolute";

        controls.style.top =
            "15px";

        controls.style.left =
            "15px";

        controls.style.zIndex =
            "20";

        controls.style.background =
            "rgba(0,0,0,0.72)";

        controls.style.color =
            "white";

        controls.style.padding =
            "10px 12px";

        controls.style.borderRadius =
            "5px";

        controls.style.fontFamily =
            "Arial, sans-serif";

        document.body.appendChild(
            controls
        );

    }


    // ========================================================
    // HRRR TOGGLE
    // ========================================================

    if (
        !document.getElementById(
            "hrrr-toggle"
        )
    ) {

        const toggleRow =
            document.createElement(
                "label"
            );

        toggleRow.style.display =
            "flex";

        toggleRow.style.alignItems =
            "center";

        toggleRow.style.gap =
            "8px";

        toggleRow.style.marginTop =
            "8px";

        toggleRow.style.cursor =
            "pointer";


        toggleRow.innerHTML = `

            <input
                type="checkbox"
                id="hrrr-toggle"
                checked
            >

            <span>
                HRRR Refl + UH
            </span>

        `;


        controls.appendChild(
            toggleRow
        );

    }


    // ========================================================
    // HRRR SLIDER
    // ========================================================

    if (
        !document.getElementById(
            "hrrr-slider"
        )
    ) {

        const sliderWrap =
            document.createElement(
                "div"
            );


        sliderWrap.id =
            "hrrr-slider-wrap";


        sliderWrap.style.marginTop =
            "10px";


        sliderWrap.innerHTML = `

            <input
                type="range"
                id="hrrr-slider"
                min="0"
                max="0"
                value="0"
                step="1"
                style="
                    width: 220px;
                    cursor: pointer;
                "
            >

        `;


        controls.appendChild(
            sliderWrap
        );

    }


    // ========================================================
    // VALID TIME LABEL
    // ========================================================

    if (
        !document.getElementById(
            "hrrr-valid-label"
        )
    ) {

        const label =
            document.createElement(
                "div"
            );


        label.id =
            "hrrr-valid-label";


        label.style.position =
            "absolute";


        /*
         * Positioned below the upper-left controls.
         */

        label.style.top =
            "130px";

        label.style.left =
            "15px";

        label.style.zIndex =
            "20";

        label.style.background =
            "rgba(0,0,0,0.72)";

        label.style.color =
            "#ffffff";

        label.style.padding =
            "8px 12px";

        label.style.borderRadius =
            "4px";

        label.style.fontFamily =
            "Arial, sans-serif";

        label.style.fontSize =
            "19px";

        label.style.fontWeight =
            "700";

        label.style.whiteSpace =
            "nowrap";

        label.style.textShadow =
            "1px 1px 2px #000";

        label.textContent =
            "Loading HRRR...";


        document.body.appendChild(
            label
        );

    }

}


// ============================================================
// CENTRAL-TIME FORMATTER
// ============================================================

function formatValidTimeCentral(
    isoTime
) {

    const date =
        new Date(
            isoTime
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
        (type) => {

            const part =
                parts.find(
                    item =>
                        item.type === type
                );

            return part
                ? part.value
                : "";

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
// UPDATE VALID TIME LABEL
// ============================================================

function updateHrrrLabel(
    frame
) {

    const label =
        document.getElementById(
            "hrrr-valid-label"
        );


    if (
        !label
        ||
        !frame
    ) {

        return;

    }


    const validText =
        formatValidTimeCentral(
            frame.valid
        );


    const fhr =
        String(
            frame.fhr
        ).padStart(
            3,
            "0"
        );


    label.textContent =
        `${validText} • F${fhr}`;

}


// ============================================================
// GET IMAGE COORDINATES FROM MANIFEST
// ============================================================

function getHrrrCoordinates() {

    if (
        !hrrrManifest
        ||
        !hrrrManifest.bounds
    ) {

        return null;

    }


    const b =
        hrrrManifest.bounds;


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
// CREATE / UPDATE HRRR IMAGE SOURCE
// ============================================================

function displayHrrrFrame(
    frame
) {

    if (
        !frame
        ||
        !hrrrManifest
    ) {

        return;

    }


    const coordinates =
        getHrrrCoordinates();


    if (!coordinates) {

        return;

    }


    // --------------------------------------------------------
    // Cache-busting query
    //
    // Prevent browser from showing a frame left over from
    // the previous HRRR cycle.
    // --------------------------------------------------------

    const imageUrl =

        `${HRRR_BASE_URL}/` +

        `${frame.file}` +

        `?run=${encodeURIComponent(
            hrrrManifest.run
        )}`;


    // ========================================================
    // SOURCE ALREADY EXISTS
    // ========================================================

    if (
        map.getSource(
            "hrrr-reflectivity-source"
        )
    ) {

        map.getSource(
            "hrrr-reflectivity-source"
        ).updateImage({

            url:
                imageUrl,

            coordinates:
                coordinates

        });

    }


    // ========================================================
    // CREATE SOURCE
    // ========================================================

    else {

        map.addSource(
            "hrrr-reflectivity-source",
            {

                type:
                    "image",

                url:
                    imageUrl,

                coordinates:
                    coordinates

            }
        );


        // ----------------------------------------------------
        // Keep HRRR beneath Mapbox roads/labels
        // ----------------------------------------------------

        const styleLayers =
            map.getStyle().layers;


        const firstRoadLayer =
            styleLayers.find(
                layer => {

                    return (

                        layer[
                            "source-layer"
                        ] === "road"

                        ||

                        layer.id
                            .toLowerCase()
                            .includes(
                                "road"
                            )

                    );

                }
            );


        const firstRoadLayerId =
            firstRoadLayer
                ? firstRoadLayer.id
                : undefined;


        map.addLayer(

            {

                id:
                    "hrrr-reflectivity",

                type:
                    "raster",

                source:
                    "hrrr-reflectivity-source",

                layout: {

                    visibility:
                        "visible"

                },

                paint: {

                    "raster-opacity":
                        1.0,

                    "raster-fade-duration":
                        0,

                    "raster-resampling":
                        "linear"

                }

            },

            firstRoadLayerId

        );


        hrrrSourceCreated =
            true;

    }


    updateHrrrLabel(
        frame
    );

}


// ============================================================
// UPDATE SLIDER
// ============================================================

function updateHrrrSlider(
    previousFhr = null
) {

    const slider =
        document.getElementById(
            "hrrr-slider"
        );


    if (
        !slider
        ||
        availableHrrrFrames.length === 0
    ) {

        return;

    }


    slider.min =
        0;


    slider.max =
        availableHrrrFrames.length - 1;


    // --------------------------------------------------------
    // Preserve selected forecast hour if possible.
    // --------------------------------------------------------

    let targetIndex = -1;


    if (
        previousFhr !== null
    ) {

        targetIndex =
            availableHrrrFrames.findIndex(
                frame =>
                    frame.fhr === previousFhr
            );

    }


    // --------------------------------------------------------
    // If current selection doesn't exist, use newest hour.
    // --------------------------------------------------------

    if (
        targetIndex < 0
    ) {

        targetIndex =
            availableHrrrFrames.length - 1;

    }


    currentHrrrIndex =
        targetIndex;


    slider.value =
        String(
            currentHrrrIndex
        );


    displayHrrrFrame(
        availableHrrrFrames[
            currentHrrrIndex
        ]
    );

}


// ============================================================
// LOAD MANIFEST
// ============================================================

async function refreshHrrrManifest() {

    try {

        // ----------------------------------------------------
        // Preserve currently selected F-hour
        // ----------------------------------------------------

        let selectedFhr = null;


        if (
            availableHrrrFrames.length > 0
        ) {

            const current =
                availableHrrrFrames[
                    currentHrrrIndex
                ];


            if (current) {

                selectedFhr =
                    current.fhr;

            }

        }


        // ----------------------------------------------------
        // Cache-busting query
        // ----------------------------------------------------

        const response =
            await fetch(

                `${HRRR_MANIFEST_URL}` +
                `?t=${Date.now()}`,

                {
                    cache:
                        "no-store"
                }

            );


        if (!response.ok) {

            throw new Error(

                `Manifest HTTP ` +
                `${response.status}`

            );

        }


        const newManifest =
            await response.json();


        if (
            !Array.isArray(
                newManifest.hours
            )
        ) {

            throw new Error(
                "Manifest does not contain hours array."
            );

        }


        // ====================================================
        // NEW HRRR RUN?
        // ====================================================

        const runChanged =

            hrrrManifest

            &&

            hrrrManifest.run
            !==
            newManifest.run;


        hrrrManifest =
            newManifest;


        availableHrrrFrames =
            [...newManifest.hours]
            .sort(
                (a, b) =>
                    a.fhr - b.fhr
            );


        console.log(

            "HRRR manifest:",

            hrrrManifest.run,

            availableHrrrFrames.length,

            "hours",

            hrrrManifest.status

        );


        // ====================================================
        // NO FRAMES YET
        // ====================================================

        if (
            availableHrrrFrames.length
            === 0
        ) {

            const label =
                document.getElementById(
                    "hrrr-valid-label"
                );


            if (label) {

                label.textContent =
                    "New HRRR run loading...";

            }


            return;

        }


        // ====================================================
        // IF RUN CHANGED, START WITH NEWEST CURRENTLY
        // AVAILABLE FRAME
        // ====================================================

        if (runChanged) {

            selectedFhr =
                null;

        }


        updateHrrrSlider(
            selectedFhr
        );


    }

    catch (error) {

        console.error(
            "HRRR manifest error:",
            error
        );

    }

}


// ============================================================
// MAP LOAD
// ============================================================

map.on(
    "load",
    async () => {

        console.log(
            "Map loaded"
        );


        // ====================================================
        // UI
        // ====================================================

        createHrrrUI();


        // ====================================================
        // FIND FIRST ROAD LAYER
        // ====================================================

        const styleLayers =
            map.getStyle().layers;


        const firstRoadLayer =
            styleLayers.find(
                layer => {

                    return (

                        layer[
                            "source-layer"
                        ] === "road"

                        ||

                        layer.id
                            .toLowerCase()
                            .includes(
                                "road"
                            )

                    );

                }
            );


        const firstRoadLayerId =
            firstRoadLayer
                ? firstRoadLayer.id
                : undefined;


        // ====================================================
        // MAPBOX BOUNDARY SOURCE
        // ====================================================

        map.addSource(
            "boundary-data",
            {

                type:
                    "vector",

                url:
                    "mapbox://mapbox.mapbox-streets-v8"

            }
        );


        // ====================================================
        // SPC SOURCE
        // ====================================================

        map.addSource(
            "spc-day1-cat",
            {

                type:
                    "geojson",

                data:
                    "data/spc_day1_cat.geojson"

            }
        );


        // ====================================================
        // SPC FILL
        // ====================================================

        map.addLayer(

            {

                id:
                    "spc-day1-cat-fill",

                type:
                    "fill",

                source:
                    "spc-day1-cat",

                layout: {

                    visibility:
                        "visible"

                },

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

            firstRoadLayerId

        );


        // ====================================================
        // SPC DARK OUTLINE
        // ====================================================

        map.addLayer(

            {

                id:
                    "spc-day1-cat-outline-dark",

                type:
                    "line",

                source:
                    "spc-day1-cat",

                layout: {

                    visibility:
                        "visible"

                },

                paint: {

                    "line-color":
                        "#1A1A1A",

                    "line-width": [

                        "interpolate",

                        ["linear"],

                        ["zoom"],

                        4, 2.2,

                        6, 3.0,

                        8, 3.8,

                        10, 4.5

                    ],

                    "line-opacity":
                        1

                }

            },

            firstRoadLayerId

        );


        // ====================================================
        // SPC OFFICIAL OUTLINE
        // ====================================================

        map.addLayer(

            {

                id:
                    "spc-day1-cat-outline",

                type:
                    "line",

                source:
                    "spc-day1-cat",

                layout: {

                    visibility:
                        "visible"

                },

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

                        ["linear"],

                        ["zoom"],

                        4, 1.3,

                        6, 1.8,

                        8, 2.3,

                        10, 2.8

                    ],

                    "line-opacity":
                        1

                }

            },

            firstRoadLayerId

        );


        // ====================================================
        // COUNTY BOUNDARIES
        // ====================================================

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

                    ["linear"],

                    ["zoom"],

                    4, 0.5,

                    6, 0.8,

                    8, 1.1,

                    10, 1.4

                ],

                "line-opacity":
                    0.95

            }

        });


        // ====================================================
        // STATE BOUNDARIES
        // ====================================================

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

                    ["linear"],

                    ["zoom"],

                    4, 2.0,

                    6, 2.7,

                    8, 3.3,

                    10, 4.0

                ],

                "line-opacity":
                    1

            }

        });


        // ====================================================
        // LBF CWA
        // ====================================================

        map.addSource(
            "lbf-cwa",
            {

                type:
                    "geojson",

                data:
                    "data/lbf_cwa.geojson"

            }
        );


        // ====================================================
        // LBF BLACK HALO
        // ====================================================

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

                    ["linear"],

                    ["zoom"],

                    4, 4.0,

                    6, 5.0,

                    8, 6.0,

                    10, 7.0

                ],

                "line-opacity":
                    1

            }

        });


        // ====================================================
        // LBF WHITE CWA
        // ====================================================

        map.addLayer({

            id:
                "lbf-cwa-boundary",

            type:
                "line",

            source:
                "lbf-cwa",

            paint: {

                "line-color":
                    "#FFFFFF",

                "line-width": [

                    "interpolate",

                    ["linear"],

                    ["zoom"],

                    4, 2.0,

                    6, 3.0,

                    8, 4.0,

                    10, 5.0

                ],

                "line-opacity":
                    1

            }

        });


        // ====================================================
        // SPC TOGGLE
        // ====================================================

        const spcToggle =
            document.getElementById(
                "spc-toggle"
            );


        const spcLayers = [

            "spc-day1-cat-fill",

            "spc-day1-cat-outline-dark",

            "spc-day1-cat-outline"

        ];


        if (spcToggle) {

            spcToggle.addEventListener(
                "change",
                () => {

                    const visibility =

                        spcToggle.checked

                            ? "visible"

                            : "none";


                    spcLayers.forEach(
                        layerId => {

                            if (
                                map.getLayer(
                                    layerId
                                )
                            ) {

                                map.setLayoutProperty(

                                    layerId,

                                    "visibility",

                                    visibility

                                );

                            }

                        }
                    );

                }
            );

        }


        // ====================================================
        // HRRR TOGGLE
        // ====================================================

        const hrrrToggle =
            document.getElementById(
                "hrrr-toggle"
            );


        if (hrrrToggle) {

            hrrrToggle.addEventListener(
                "change",
                () => {

                    if (
                        !map.getLayer(
                            "hrrr-reflectivity"
                        )
                    ) {

                        return;

                    }


                    map.setLayoutProperty(

                        "hrrr-reflectivity",

                        "visibility",

                        hrrrToggle.checked

                            ? "visible"

                            : "none"

                    );

                }
            );

        }


        // ====================================================
        // HRRR SLIDER
        // ====================================================

        const slider =
            document.getElementById(
                "hrrr-slider"
            );


        if (slider) {

            slider.addEventListener(
                "input",
                () => {

                    const index =
                        Number(
                            slider.value
                        );


                    if (
                        index < 0
                        ||
                        index >=
                        availableHrrrFrames.length
                    ) {

                        return;

                    }


                    currentHrrrIndex =
                        index;


                    displayHrrrFrame(
                        availableHrrrFrames[
                            currentHrrrIndex
                        ]
                    );

                }
            );

        }


        // ====================================================
        // INITIAL MANIFEST
        // ====================================================

        await refreshHrrrManifest();


        // ====================================================
        // POLL MANIFEST
        // ====================================================

        setInterval(
            refreshHrrrManifest,
            MANIFEST_REFRESH_MS
        );


        console.log(
            "Map + progressive HRRR loader ready."
        );

    }
);


// ============================================================
// MAPBOX ERROR REPORTING
// ============================================================

map.on(
    "error",
    event => {

        console.error(
            "MAPBOX ERROR:",
            event.error
        );

    }
);
