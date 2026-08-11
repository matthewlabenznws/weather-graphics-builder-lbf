mapboxgl.accessToken = "pk.eyJ1IjoibWF0dGhld2xhYmVuejciLCJhIjoiY21zbjhxZ3ZkMXBoNDJ3cHl5eG5uNzlpZCJ9.UBy4k84SejJzzu2VF0TtcA";

// ============================================================
// MODEL CONFIGURATION
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

    }

};


// ============================================================
// CURRENT VIEWER STATE
// ============================================================

let activeModel =
    "hrrr";

let activeProduct =
    "reflUH";

let currentManifest =
    null;

let availableFrames =
    [];

let currentFrameIndex =
    0;

let animationTimer =
    null;

let animationPlaying =
    false;


// ============================================================
// MANIFEST POLLING
// ============================================================

const MANIFEST_REFRESH_MS =
    30000;


// ============================================================
// CREATE MAP
// ============================================================

const map =
    new mapboxgl.Map({

        container:
            "map",

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


// ============================================================
// NAVIGATION
// ============================================================

map.addControl(

    new mapboxgl.NavigationControl(),

    "top-right"

);


// ============================================================
// GET ACTIVE PRODUCT CONFIG
// ============================================================

function getActiveProductConfig() {

    if (
        activeModel === "none"
    ) {

        return null;

    }


    const model =
        MODEL_CONFIGS[
            activeModel
        ];


    if (!model) {

        return null;

    }


    return model.products[
        activeProduct
    ] || null;

}


// ============================================================
// MODEL UI VISIBILITY
// ============================================================

function setModelUiVisible(
    visible
) {

    const elements = [

        document.getElementById(
            "model-valid-label"
        ),

        document.getElementById(
            "model-timeline"
        ),

        document.getElementById(
            "product-select"
        )

    ];


    elements.forEach(
        element => {

            if (!element) {

                return;

            }


            if (visible) {

                element.classList.remove(
                    "hidden"
                );

            }

            else {

                element.classList.add(
                    "hidden"
                );

            }

        }
    );


    if (
        map.getLayer(
            "model-raster-layer"
        )
    ) {

        map.setLayoutProperty(

            "model-raster-layer",

            "visibility",

            visible
                ? "visible"
                : "none"

        );

    }

}


// ============================================================
// CENTRAL TIME FORMAT
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
        type => {

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
// VALID TIME LABEL
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


    const valid =
        formatValidTimeCentral(
            frame.valid
        );


    label.textContent =
        `F${fhr} • ${valid}`;

}


// ============================================================
// MANIFEST COORDINATES
// ============================================================

function getImageCoordinates() {

    if (
        !currentManifest
        ||
        !currentManifest.bounds
    ) {

        return null;

    }


    const b =
        currentManifest.bounds;


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
// DISPLAY MODEL FRAME
// ============================================================

function displayFrame(
    frame
) {

    const product =
        getActiveProductConfig();


    if (
        !product
        ||
        !frame
        ||
        !currentManifest
    ) {

        return;

    }


    const coordinates =
        getImageCoordinates();


    if (!coordinates) {

        return;

    }


    const imageUrl =

        `${product.baseUrl}/` +

        `${frame.file}` +

        `?run=${encodeURIComponent(
            currentManifest.run
        )}`;


    // ========================================================
    // UPDATE EXISTING IMAGE
    // ========================================================

    if (
        map.getSource(
            "model-image-source"
        )
    ) {

        map.getSource(
            "model-image-source"
        ).updateImage({

            url:
                imageUrl,

            coordinates:
                coordinates

        });

    }


    // ========================================================
    // CREATE IMAGE SOURCE
    // ========================================================

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


        const beforeLayer =
            firstRoadLayer
                ? firstRoadLayer.id
                : undefined;


        map.addLayer(

            {

                id:
                    "model-raster-layer",

                type:
                    "raster",

                source:
                    "model-image-source",

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

            beforeLayer

        );

    }


    updateValidLabel(
        frame
    );


    updateHourButtonStyles();

}


// ============================================================
// SET CURRENT FRAME
// ============================================================

function setFrameIndex(
    index
) {

    if (
        availableFrames.length === 0
    ) {

        return;

    }


    if (
        index < 0
    ) {

        index =
            availableFrames.length - 1;

    }


    if (
        index >=
        availableFrames.length
    ) {

        index =
            0;

    }


    currentFrameIndex =
        index;


    displayFrame(

        availableFrames[
            currentFrameIndex
        ]

    );


    scrollSelectedHourIntoView();

}


// ============================================================
// BUILD FORECAST-HOUR BUTTONS
// ============================================================

function buildHourButtons() {

    const container =
        document.getElementById(
            "model-hour-list"
        );


    if (!container) {

        return;

    }


    container.innerHTML =
        "";


    availableFrames.forEach(

        (
            frame,
            index
        ) => {


            const button =
                document.createElement(
                    "button"
                );


            button.className =
                "model-hour-button";


            button.textContent =
                `F${String(
                    frame.fhr
                ).padStart(
                    3,
                    "0"
                )}`;


            button.dataset.index =
                String(
                    index
                );


            button.addEventListener(

                "click",

                () => {

                    stopAnimation();

                    setFrameIndex(
                        index
                    );

                }

            );


            container.appendChild(
                button
            );

        }

    );


    updateHourButtonStyles();

}


// ============================================================
// SELECTED FORECAST-HOUR STYLE
// ============================================================

function updateHourButtonStyles() {

    const buttons =
        document.querySelectorAll(
            ".model-hour-button"
        );


    buttons.forEach(

        (
            button,
            index
        ) => {


            if (
                index ===
                currentFrameIndex
            ) {

                button.classList.add(
                    "selected"
                );

            }

            else {

                button.classList.remove(
                    "selected"
                );

            }

        }

    );

}


// ============================================================
// KEEP SELECTED HOUR VISIBLE
// ============================================================

function scrollSelectedHourIntoView() {

    const buttons =
        document.querySelectorAll(
            ".model-hour-button"
        );


    const selected =
        buttons[
            currentFrameIndex
        ];


    if (!selected) {

        return;

    }


    selected.scrollIntoView({

        behavior:
            "smooth",

        block:
            "nearest",

        inline:
            "center"

    });

}


// ============================================================
// ANIMATION
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


    const button =
        document.getElementById(
            "model-play-button"
        );


    if (button) {

        button.textContent =
            "❚❚";

    }


    animationTimer =
        setInterval(

            () => {

                setFrameIndex(
                    currentFrameIndex + 1
                );

            },

            700

        );

}


function stopAnimation() {

    animationPlaying =
        false;


    if (animationTimer) {

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
// REFRESH MODEL MANIFEST
// ============================================================

async function refreshManifest() {

    if (
        activeModel === "none"
    ) {

        return;

    }


    const product =
        getActiveProductConfig();


    if (!product) {

        return;

    }


    try {

        let selectedFhr =
            null;


        if (
            availableFrames.length > 0
        ) {

            const current =
                availableFrames[
                    currentFrameIndex
                ];


            if (current) {

                selectedFhr =
                    current.fhr;

            }

        }


        const manifestUrl =

            `${product.baseUrl}/` +

            `manifest.json` +

            `?t=${Date.now()}`;


        const response =
            await fetch(

                manifestUrl,

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


        const manifest =
            await response.json();


        const runChanged =

            currentManifest

            &&

            currentManifest.run
            !==
            manifest.run;


        currentManifest =
            manifest;


        availableFrames =
            [...manifest.hours]
            .sort(
                (a, b) =>
                    a.fhr - b.fhr
            );


        // ====================================================
        // NEW RUN BUT NO FRAME YET
        // ====================================================

        if (
            availableFrames.length === 0
        ) {

            const label =
                document.getElementById(
                    "model-valid-label"
                );


            if (label) {

                label.textContent =
                    "New model run loading...";

            }


            buildHourButtons();

            return;

        }


        let targetIndex =
            -1;


        if (
            !runChanged
            &&
            selectedFhr !== null
        ) {

            targetIndex =
                availableFrames.findIndex(

                    frame =>
                        frame.fhr ===
                        selectedFhr

                );

        }


        // New run:
        // use newest frame currently available.

        if (
            targetIndex < 0
        ) {

            targetIndex =
                availableFrames.length - 1;

        }


        currentFrameIndex =
            targetIndex;


        buildHourButtons();


        displayFrame(

            availableFrames[
                currentFrameIndex
            ]

        );


        scrollSelectedHourIntoView();


    }

    catch (error) {

        console.error(
            "Model manifest error:",
            error
        );

    }

}


// ============================================================
// SWITCH MODEL
// ============================================================

async function switchModel(
    modelName
) {

    stopAnimation();


    activeModel =
        modelName;


    // ========================================================
    // OVERLAYS ONLY
    // ========================================================

    if (
        modelName === "none"
    ) {

        setModelUiVisible(
            false
        );


        currentManifest =
            null;

        availableFrames =
            [];

        currentFrameIndex =
            0;


        return;

    }


    // ========================================================
    // MODEL VIEW
    // ========================================================

    setModelUiVisible(
        true
    );


    activeProduct =
        "reflUH";


    const productSelect =
        document.getElementById(
            "product-select"
        );


    if (productSelect) {

        productSelect.value =
            activeProduct;

    }


    currentManifest =
        null;

    availableFrames =
        [];

    currentFrameIndex =
        0;


    await refreshManifest();

}


// ============================================================
// OVERLAY VISIBILITY HELPER
// ============================================================

function setLayersVisible(
    layers,
    visible
) {

    const visibility =
        visible
            ? "visible"
            : "none";


    layers.forEach(
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


// ============================================================
// MAP LOAD
// ============================================================

map.on(

    "load",

    async () => {


        // ====================================================
        // FIRST ROAD LAYER
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

                    ]

                }

            },

            firstRoadLayerId

        );


        // ====================================================
        // SPC COLOR OUTLINE
        // ====================================================

        map.addLayer(

            {

                id:
                    "spc-day1-cat-outline",

                type:
                    "line",

                source:
                    "spc-day1-cat",

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

                    ]

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


        // BLACK HALO

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

                    4, 4,

                    6, 5,

                    8, 6,

                    10, 7

                ]

            }

        });


        // WHITE CWA

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

                    4, 2,

                    6, 3,

                    8, 4,

                    10, 5

                ]

            }

        });


        // ====================================================
        // OVERLAY MENU
        // ====================================================

        const overlayButton =
            document.getElementById(
                "overlay-menu-button"
            );


        const overlayContent =
            document.getElementById(
                "overlay-menu-content"
            );


        overlayButton.addEventListener(

            "click",

            () => {

                overlayContent
                    .classList
                    .toggle(
                        "open"
                    );

            }

        );


        // ====================================================
        // SPC TOGGLE
        // ====================================================

        document
            .getElementById(
                "spc-toggle"
            )
            .addEventListener(

                "change",

                event => {

                    setLayersVisible(

                        [

                            "spc-day1-cat-fill",

                            "spc-day1-cat-outline-dark",

                            "spc-day1-cat-outline"

                        ],

                        event.target.checked

                    );

                }

            );


        // ====================================================
        // CWA TOGGLE
        // ====================================================

        document
            .getElementById(
                "cwa-toggle"
            )
            .addEventListener(

                "change",

                event => {

                    setLayersVisible(

                        [

                            "lbf-cwa-outline",

                            "lbf-cwa-boundary"

                        ],

                        event.target.checked

                    );

                }

            );


        // ====================================================
        // COUNTY TOGGLE
        // ====================================================

        document
            .getElementById(
                "county-toggle"
            )
            .addEventListener(

                "change",

                event => {

                    setLayersVisible(

                        [
                            "custom-county-boundaries"
                        ],

                        event.target.checked

                    );

                }

            );


        // ====================================================
        // STATE TOGGLE
        // ====================================================

        document
            .getElementById(
                "state-toggle"
            )
            .addEventListener(

                "change",

                event => {

                    setLayersVisible(

                        [
                            "custom-state-boundaries"
                        ],

                        event.target.checked

                    );

                }

            );


        // ====================================================
        // MODEL SELECT
        // ====================================================

        document
            .getElementById(
                "model-select"
            )
            .addEventListener(

                "change",

                async event => {

                    await switchModel(
                        event.target.value
                    );

                }

            );


        // ====================================================
        // PRODUCT SELECT
        // ====================================================

        document
            .getElementById(
                "product-select"
            )
            .addEventListener(

                "change",

                async event => {

                    activeProduct =
                        event.target.value;


                    currentManifest =
                        null;


                    availableFrames =
                        [];


                    await refreshManifest();

                }

            );


        // ====================================================
        // PLAY
        // ====================================================

        document
            .getElementById(
                "model-play-button"
            )
            .addEventListener(

                "click",

                () => {

                    if (
                        animationPlaying
                    ) {

                        stopAnimation();

                    }

                    else {

                        startAnimation();

                    }

                }

            );


        // ====================================================
        // PREVIOUS
        // ====================================================

        document
            .getElementById(
                "model-prev-button"
            )
            .addEventListener(

                "click",

                () => {

                    stopAnimation();

                    setFrameIndex(
                        currentFrameIndex - 1
                    );

                }

            );


        // ====================================================
        // NEXT
        // ====================================================

        document
            .getElementById(
                "model-next-button"
            )
            .addEventListener(

                "click",

                () => {

                    stopAnimation();

                    setFrameIndex(
                        currentFrameIndex + 1
                    );

                }

            );


        // ====================================================
        // FIRST HRRR MANIFEST
        // ====================================================

        await refreshManifest();


        // ====================================================
        // PROGRESSIVE MANIFEST POLLING
        // ====================================================

        setInterval(

            () => {

                if (
                    activeModel !==
                    "none"
                ) {

                    refreshManifest();

                }

            },

            MANIFEST_REFRESH_MS

        );

    }

);


// ============================================================
// MAPBOX ERROR LOGGING
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
    }
);
