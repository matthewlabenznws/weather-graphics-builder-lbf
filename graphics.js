// ============================================================
// MAPBOX TOKEN
// ============================================================

mapboxgl.accessToken = "pk.eyJ1IjoibWF0dGhld2xhYmVuejciLCJhIjoiY21zbjhxZ3ZkMXBoNDJ3cHl5eG5uNzlpZCJ9.UBy4k84SejJzzu2VF0TtcA";

// ============================================================
// MODEL CONFIG
// ============================================================

const MODEL_CONFIGS = {

    hrrr: {

        name: "HRRR",

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

        name: "RRFS",

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

    spc: true,

    cwa: true,

    counties: true,

    states: true

};


// ============================================================
// LOGO FOR EXPORT
// ============================================================

const exportLogoImage =
    new Image();


exportLogoImage.src =
    "assets/NOAANWSLogos.png";


// ============================================================
// CREATE SINGLE MAP
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
// CREATE MAP HELPER
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
// ACTIVE MODEL CONFIG
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
        || null
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
                    p =>
                        p.type === type
                )?.value
                || ""
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
// SETUP COMMON OVERLAYS FOR A MAP
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
    // BOUNDARY SOURCE
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
    // SPC
    // ========================================================

    map.addSource(

        "spc-day1-cat",

        {

            type:
                "geojson",

            data:
                "data/spc_day1_cat.geojson"

        }

    );


    map.addLayer(

        {

            id:
                "spc-day1-fill",

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

        roadLayer

    );


    map.addLayer(

        {

            id:
                "spc-day1-outline-dark",

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

        roadLayer

    );


    map.addLayer(

        {

            id:
                "spc-day1-outline",

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

        roadLayer

    );


    // ========================================================
    // COUNTY
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


    // ========================================================
    // STATE
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

                ["linear"],

                ["zoom"],

                4, 2.0,

                6, 2.7,

                8, 3.3,

                10, 4.0

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

                ["linear"],

                ["zoom"],

                4, 4,

                6, 5,

                8, 6,

                10, 7

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

                ["linear"],

                ["zoom"],

                4, 2,

                6, 3,

                8, 4,

                10, 5

            ]

        }

    });


    applyOverlayStateToMap(
        map
    );

}


// ============================================================
// APPLY OVERLAY STATE
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


function applyOverlayStateToMap(
    map
) {

    setLayerVisibility(

        map,

        [
            "spc-day1-fill",
            "spc-day1-outline-dark",
            "spc-day1-outline"
        ],

        overlayState.spc

    );


    setLayerVisibility(

        map,

        [
            "lbf-cwa-outline",
            "lbf-cwa-boundary"
        ],

        overlayState.cwa

    );


    setLayerVisibility(

        map,

        [
            "custom-county-boundaries"
        ],

        overlayState.counties

    );


    setLayerVisibility(

        map,

        [
            "custom-state-boundaries"
        ],

        overlayState.states

    );

}


// ============================================================
// MANIFEST FETCH
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


    const url =

        `${product.baseUrl}/manifest.json` +

        `?t=${Date.now()}`;


    const response =
        await fetch(

            url,

            {
                cache:
                    "no-store"
            }

        );


    if (!response.ok) {

        throw new Error(

            `${modelName} manifest ` +
            `HTTP ${response.status}`

        );

    }


    return (
        await response.json()
    );

}


// ============================================================
// GET FRAME BY FHR
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
                ) ===
                Number(
                    fhr
                )

        )

        || null

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
// DISPLAY MODEL IMAGE ON MAP
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


    const url =

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
                url,

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
                    url,

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
// REFRESH SINGLE MODEL
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
                (a, b) =>
                    Number(a.fhr)
                    -
                    Number(b.fhr)
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
                    availableFrames[0]?.fhr
                );

    }


    currentFrameIndex =
        availableFrames.findIndex(

            frame =>
                Number(frame.fhr)
                ===
                Number(targetFhr)

        );


    buildHourButtons();


    displayCurrentFrame();

}


// ============================================================
// REFRESH COMPARISON
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


    // ========================================================
    // ONLY HOURS BOTH MODELS HAVE
    // ========================================================

    const hrrrFrames =
        compareManifests
            .hrrr
            .hours;


    availableFrames =
        hrrrFrames.filter(
            frame => {

                return !!findFrame(

                    compareManifests.rrfs,

                    frame.fhr

                );

            }
        );


    availableFrames.sort(
        (a, b) =>
            Number(a.fhr)
            -
            Number(b.fhr)
    );


    let targetFhr =
        previousFhr;


    if (
        targetFhr === null
        ||
        !availableFrames.some(

            f =>
                Number(f.fhr)
                ===
                Number(targetFhr)

        )
    ) {

        targetFhr =

            availableFrames.some(
                f =>
                    Number(f.fhr) === 0
            )

                ? 0

                : Number(
                    availableFrames[0]?.fhr
                );

    }


    currentFrameIndex =
        availableFrames.findIndex(

            frame =>
                Number(frame.fhr)
                ===
                Number(targetFhr)

        );


    buildHourButtons();


    displayCurrentFrame();

}


// ============================================================
// CURRENT FHR
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
// HOUR AVAILABILITY
// ============================================================

function hourIsAvailable(
    fhr
) {

    return (
        availableFrames.some(

            frame =>
                Number(frame.fhr)
                ===
                Number(fhr)

        )
    );

}


// ============================================================
// BUILD TIMELINE
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


            button.addEventListener(

                "click",

                () => {

                    stopAnimation();


                    selectFhr(
                        fhr
                    );

                }

            );

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
                Number(frame.fhr)
                ===
                Number(fhr)

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
// SELECTED BUTTON
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
// SCROLL SELECTED
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
// NEXT / PREVIOUS
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
        currentFrameIndex >=
        availableFrames.length
    ) {

        currentFrameIndex =
            0;

    }


    displayCurrentFrame();


    scrollSelectedHourIntoView();

}


// ============================================================
// PLAYBACK
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


    document.getElementById(
        "model-play-button"
    ).textContent =
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


    setupMapLayers(
        leftMap
    );


    setupMapLayers(
        rightMap
    );


    syncComparisonMaps();


    comparisonInitialized =
        true;

}


// ============================================================
// WAIT MAP LOAD
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
// SYNCHRONIZE MAPS
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
// SWITCH VIEW MODE
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


    // ========================================================
    // OVERLAYS ONLY
    // ========================================================

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


    // ========================================================
    // MODEL MODES
    // ========================================================

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


    // ========================================================
    // SINGLE
    // ========================================================

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


        singleMap.resize();


        await refreshSingleManifest();

    }


    // ========================================================
    // COMPARE
    // ========================================================

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
// REFRESH CURRENT MODE
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
    w,
    h,
    r
) {

    ctx.beginPath();

    ctx.roundRect(
        x,
        y,
        w,
        h,
        r
    );

}


// ============================================================
// DRAW EXPORT BRANDING
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
        )} • ` +
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
        "rgba(20,24,32,0.9)";


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
        "white";


    ctx.fillText(

        timestamp,

        10 * scale
        +
        pad,

        10 * scale
        +
        boxHeight / 2

    );


    // ========================================================
    // LOGOS + OFFICE
    // ========================================================

    if (
        exportLogoImage.complete
        &&
        exportLogoImage.naturalWidth
    ) {

        const logoWidth =
            145 * scale;


        const logoHeight =

            logoWidth *

            exportLogoImage.naturalHeight

            /

            exportLogoImage.naturalWidth;


        const x =

            canvas.width

            -

            logoWidth

            -

            12 * scale;


        const y =
            8 * scale;


        ctx.drawImage(

            exportLogoImage,

            x,
            y,

            logoWidth,
            logoHeight

        );


        ctx.font =
            `700 ${fontSize}px Arial`;


        ctx.textAlign =
            "right";


        ctx.textBaseline =
            "top";


        const textX =
            canvas.width
            -
            12 * scale;


        const textY =
            y
            +
            logoHeight
            +
            3 * scale;


        ctx.lineWidth =
            4 * scale;


        ctx.strokeStyle =
            "black";


        ctx.strokeText(

            "NWS North Platte, NE",

            textX,

            textY

        );


        ctx.fillStyle =
            "white";


        ctx.fillText(

            "NWS North Platte, NE",

            textX,

            textY

        );


        ctx.textAlign =
            "left";

    }

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
// COMPARE EXPORT CANVAS
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


    // divider

    ctx.fillStyle =
        "white";


    ctx.fillRect(

        panelWidth - 1,

        0,

        2,

        height

    );


    // panel model labels

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
        "black";


    ctx.lineWidth =
        4;


    ctx.fillStyle =
        "white";


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


    ctx.textAlign =
        "left";


    drawExportBranding(
        canvas,
        frame
    );


    return canvas;

}


// ============================================================
// EXPORT CANVAS FOR CURRENT MODE
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
// DOWNLOAD
// ============================================================

function downloadBlob(
    blob,
    filename
) {

    const url =
        URL.createObjectURL(
            blob
        );


    const a =
        document.createElement(
            "a"
        );


    a.href =
        url;


    a.download =
        filename;


    a.click();


    setTimeout(
        () =>
            URL.revokeObjectURL(
                url
            ),
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

            `nws_lbf_${modeLabel}_` +

            `f${String(
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
// GIFENC
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
                resolve =>
                    setTimeout(
                        resolve,
                        500
                    )
            );


            const frame =
                availableFrames[i];


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

                    `Encoding ` +

                    `${i - startIndex + 1}/` +

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
// CREATE EXPORT UI
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

                <select id="gif-start-hour"></select>

            </div>

            <div class="gif-select-box">

                <label>
                    End Hour
                </label>

                <select id="gif-end-hour"></select>

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

                panel.classList.toggle(
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

                panel.classList.remove(
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
// UI EVENT LISTENERS
// ============================================================

function setupUiEvents() {

    // overlay menu

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
    // OVERLAYS
    // ========================================================

    document
        .getElementById(
            "spc-toggle"
        )
        .onchange =
            event => {

                overlayState.spc =
                    event.target.checked;


                allMaps().forEach(
                    map =>
                        applyOverlayStateToMap(
                            map
                        )
                );

            };


    document
        .getElementById(
            "cwa-toggle"
        )
        .onchange =
            event => {

                overlayState.cwa =
                    event.target.checked;


                allMaps().forEach(
                    map =>
                        applyOverlayStateToMap(
                            map
                        )
                );

            };


    document
        .getElementById(
            "county-toggle"
        )
        .onchange =
            event => {

                overlayState.counties =
                    event.target.checked;


                allMaps().forEach(
                    map =>
                        applyOverlayStateToMap(
                            map
                        )
                );

            };


    document
        .getElementById(
            "state-toggle"
        )
        .onchange =
            event => {

                overlayState.states =
                    event.target.checked;


                allMaps().forEach(
                    map =>
                        applyOverlayStateToMap(
                            map
                        )
                );

            };


    // ========================================================
    // VIEW MODE
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
    // TIMELINE
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
// ALL INITIALIZED MAPS
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
// INITIAL SINGLE MAP LOAD
// ============================================================

singleMap.on(
    "load",
    async () => {

        setupMapLayers(
            singleMap
        );


        createExportControls();


        setupUiEvents();


        await refreshSingleManifest();


        setInterval(

            refreshCurrentData,

            MANIFEST_REFRESH_MS

        );

    }
);
