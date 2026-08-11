// ============================================================
// MAPBOX TOKEN
// ============================================================

mapboxgl.accessToken = "pk.eyJ1IjoibWF0dGhld2xhYmVuejciLCJhIjoiY21zbjhxZ3ZkMXBoNDJ3cHl5eG5uNzlpZCJ9.UBy4k84SejJzzu2VF0TtcA";


console.log("graphics.js started");


// ============================================================
// MODEL CONFIGURATION
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
// EXPORT BRANDING
// ============================================================

const exportLogoImage =
    new Image();


exportLogoImage.src =
    "assets/NOAANWSLogos.png";


// ============================================================
// VIEWER STATE
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


let animationPlaying =
    false;


let animationTimer =
    null;


let exportBusy =
    false;


// ============================================================
// REFRESH SETTINGS
// ============================================================

const MANIFEST_REFRESH_MS =
    30000;


// ============================================================
// EXPORT SETTINGS
// ============================================================

const PNG_FILENAME_PREFIX =
    "nws_lbf_hrrr_reflUH";


const GIF_MAX_WIDTH =
    1400;


const GIF_FRAME_DELAY_MS =
    700;


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


console.log(
    "Mapbox map object created"
);


// ============================================================
// MAP NAVIGATION
// ============================================================

map.addControl(

    new mapboxgl.NavigationControl(),

    "top-right"

);


// ============================================================
// MAPBOX ERROR HANDLING
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


// ============================================================
// ACTIVE PRODUCT CONFIGURATION
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


    return (

        model.products[
            activeProduct
        ]

        || null

    );

}


// ============================================================
// SHOW / HIDE MODEL UI
// ============================================================

function setModelUiVisible(
    visible
) {

    const label =
        document.getElementById(
            "model-valid-label"
        );


    const timeline =
        document.getElementById(
            "model-timeline"
        );


    const productSelect =
        document.getElementById(
            "product-select"
        );


    const credit =
        document.getElementById(
            "graphics-credit"
        );


    const exportControls =
        document.getElementById(
            "export-controls"
        );


    const gifPanel =
        document.getElementById(
            "gif-panel"
        );


    if (label) {

        label.style.display =
            visible
                ? "block"
                : "none";

    }


    if (timeline) {

        timeline.style.display =
            visible
                ? "flex"
                : "none";

    }


    if (productSelect) {

        productSelect.style.display =
            visible
                ? "block"
                : "none";

    }


    if (credit) {

        credit.classList.toggle(
            "no-timeline",
            !visible
        );

    }


    if (exportControls) {

        exportControls.style.display =
            visible
                ? "flex"
                : "none";

    }


    if (
        !visible
        &&
        gifPanel
    ) {

        gifPanel.classList.remove(
            "open"
        );

    }


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
// FORMAT VALID TIME IN CENTRAL TIME
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
// UPDATE ON-SCREEN VALID TIME
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
// EXPORT TIMESTAMP
// ============================================================

function getExportTimestamp(
    frame
) {

    if (!frame) {

        return "";

    }


    const fhr =
        String(
            frame.fhr
        ).padStart(
            3,
            "0"
        );


    return (

        `F${fhr} • ` +

        formatValidTimeCentral(
            frame.valid
        )

    );

}


// ============================================================
// GET MODEL IMAGE COORDINATES
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
// FIND FIRST ROAD LAYER
// ============================================================

function findFirstRoadLayerId() {

    const style =
        map.getStyle();


    if (
        !style
        ||
        !style.layers
    ) {

        return undefined;

    }


    const roadLayer =
        style.layers.find(
            layer => {

                const sourceLayer =
                    layer[
                        "source-layer"
                    ];


                const id =
                    layer.id
                        .toLowerCase();


                return (

                    sourceLayer === "road"

                    ||

                    id.includes(
                        "road"
                    )

                );

            }
        );


    return roadLayer
        ? roadLayer.id
        : undefined;

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


    const existingSource =
        map.getSource(
            "model-image-source"
        );


    // ========================================================
    // UPDATE EXISTING MODEL IMAGE
    // ========================================================

    if (existingSource) {

        existingSource.updateImage({

            url:
                imageUrl,

            coordinates:
                coordinates

        });

    }


    // ========================================================
    // CREATE MODEL IMAGE
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


        const beforeLayer =
            findFirstRoadLayerId();


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
// WAIT FOR MAP TO FINISH RENDERING
// ============================================================

function waitForMapIdle(
    timeoutMs = 8000
) {

    return new Promise(
        resolve => {

            let finished =
                false;


            const finish =
                () => {

                    if (finished) {

                        return;

                    }


                    finished =
                        true;


                    clearTimeout(
                        fallback
                    );


                    resolve();

                };


            const fallback =
                setTimeout(
                    finish,
                    timeoutMs
                );


            map.once(
                "idle",
                finish
            );


            map.triggerRepaint();

        }
    );

}


// ============================================================
// SET CURRENT AVAILABLE FRAME
// ============================================================

function setFrameIndex(
    index
) {

    if (
        availableFrames.length === 0
    ) {

        return;

    }


    if (index < 0) {

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
//
// ALWAYS display:
// F000 -> manifest.max_fhr
//
// Blue:
// Hour exists in manifest
//
// Dark:
// Hour has not arrived yet
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


    if (!currentManifest) {

        return;

    }


    const maxFhr =
        Number(
            currentManifest.max_fhr
        );


    if (
        !Number.isFinite(
            maxFhr
        )
    ) {

        return;

    }


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


        button.textContent =
            `F${String(
                fhr
            ).padStart(
                3,
                "0"
            )}`;


        button.dataset.fhr =
            String(
                fhr
            );


        // ====================================================
        // FIND THIS HOUR IN AVAILABLE FRAMES
        // ====================================================

        const frameIndex =
            availableFrames.findIndex(

                frame =>
                    Number(
                        frame.fhr
                    ) === fhr

            );


        const isAvailable =
            frameIndex >= 0;


        // ====================================================
        // AVAILABLE HOUR
        // ====================================================

        if (isAvailable) {

            button.classList.add(
                "available"
            );


            button.disabled =
                false;


            button.addEventListener(

                "click",

                () => {

                    stopAnimation();


                    setFrameIndex(
                        frameIndex
                    );

                }

            );

        }


        // ====================================================
        // NOT AVAILABLE YET
        // ====================================================

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


    rebuildGifRangeSelectors();

}


// ============================================================
// UPDATE SELECTED HOUR STYLE
// ============================================================

function updateHourButtonStyles() {

    const buttons =
        document.querySelectorAll(
            ".model-hour-button"
        );


    let selectedFhr =
        null;


    if (
        availableFrames.length > 0
        &&
        availableFrames[
            currentFrameIndex
        ]
    ) {

        selectedFhr =
            Number(

                availableFrames[
                    currentFrameIndex
                ].fhr

            );

    }


    buttons.forEach(
        button => {

            const fhr =
                Number(
                    button.dataset.fhr
                );


            button.classList.remove(
                "selected"
            );


            if (
                selectedFhr !== null
                &&
                fhr === selectedFhr
                &&
                button.classList.contains(
                    "available"
                )
            ) {

                button.classList.add(
                    "selected"
                );

            }

        }
    );

}


// ============================================================
// SCROLL SELECTED FORECAST HOUR INTO VIEW
// ============================================================

function scrollSelectedHourIntoView() {

    if (
        availableFrames.length === 0
        ||
        !availableFrames[
            currentFrameIndex
        ]
    ) {

        return;

    }


    const selectedFhr =
        Number(

            availableFrames[
                currentFrameIndex
            ].fhr

        );


    const selectedButton =
        document.querySelector(

            `.model-hour-button[data-fhr="${selectedFhr}"]`

        );


    if (!selectedButton) {

        return;

    }


    selectedButton.scrollIntoView({

        behavior:
            "smooth",

        block:
            "nearest",

        inline:
            "center"

    });

}


// ============================================================
// START ANIMATION
// ============================================================

function startAnimation() {

    if (
        animationPlaying
        ||
        availableFrames.length === 0
        ||
        exportBusy
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


// ============================================================
// STOP ANIMATION
// ============================================================

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
// ROUNDED RECTANGLE
// ============================================================

function roundRect(
    ctx,
    x,
    y,
    width,
    height,
    radius
) {

    const r =
        Math.min(
            radius,
            width / 2,
            height / 2
        );


    ctx.beginPath();


    ctx.moveTo(
        x + r,
        y
    );


    ctx.arcTo(
        x + width,
        y,
        x + width,
        y + height,
        r
    );


    ctx.arcTo(
        x + width,
        y + height,
        x,
        y + height,
        r
    );


    ctx.arcTo(
        x,
        y + height,
        x,
        y,
        r
    );


    ctx.arcTo(
        x,
        y,
        x + width,
        y,
        r
    );


    ctx.closePath();

}


// ============================================================
// CREATE EXPORT CANVAS
//
// EXPORT INCLUDES:
//
// Map
// Timestamp
// NOAA/NWS logos
// NWS North Platte, NE
//
// DOES NOT INCLUDE:
//
// Overlays button
// Model/product dropdown
// Timeline
// Save buttons
// Graphics credit
// Mapbox zoom controls
// ============================================================

function createExportCanvas(
    frame,
    targetWidth = null
) {

    const sourceCanvas =
        map.getCanvas();


    const sourceWidth =
        sourceCanvas.width;


    const sourceHeight =
        sourceCanvas.height;


    let width =
        sourceWidth;


    let height =
        sourceHeight;


    // ========================================================
    // OPTIONAL DOWNSCALE FOR GIF
    // ========================================================

    if (
        targetWidth
        &&
        sourceWidth >
            targetWidth
    ) {

        const ratio =
            targetWidth /
            sourceWidth;


        width =
            Math.round(
                sourceWidth *
                ratio
            );


        height =
            Math.round(
                sourceHeight *
                ratio
            );

    }


    const exportCanvas =
        document.createElement(
            "canvas"
        );


    exportCanvas.width =
        width;


    exportCanvas.height =
        height;


    const ctx =
        exportCanvas.getContext(
            "2d",
            {
                alpha:
                    false
            }
        );


    // ========================================================
    // DRAW MAP
    // ========================================================

    ctx.drawImage(

        sourceCanvas,

        0,
        0,

        width,
        height

    );


    // ========================================================
    // SCALE LABELS
    // ========================================================

    const cssWidth =
        Math.max(
            1,
            sourceCanvas.clientWidth
        );


    const scale =
        width /
        cssWidth;


    const fontSize =
        Math.max(
            17,
            18 * scale
        );


    const paddingX =
        11 * scale;


    const paddingY =
        7 * scale;


    const margin =
        10 * scale;


    // ========================================================
    // TIMESTAMP UPPER LEFT
    // ========================================================

    const timestamp =
        getExportTimestamp(
            frame
        );


    ctx.font =
        `700 ${fontSize}px Arial, sans-serif`;


    ctx.textBaseline =
        "middle";


    ctx.textAlign =
        "left";


    const timestampMetrics =
        ctx.measureText(
            timestamp
        );


    const timestampWidth =
        timestampMetrics.width +
        paddingX * 2;


    const timestampHeight =
        fontSize +
        paddingY * 2;


    ctx.fillStyle =
        "rgba(20,24,32,0.90)";


    roundRect(

        ctx,

        margin,
        margin,

        timestampWidth,
        timestampHeight,

        5 * scale

    );


    ctx.fill();


    ctx.fillStyle =
        "#ffffff";


    ctx.fillText(

        timestamp,

        margin +
        paddingX,

        margin +
        timestampHeight / 2

    );


    // ========================================================
    // NOAA/NWS LOGOS UPPER RIGHT
    // ========================================================

    const logoWidth =
        145 * scale;


    let logoHeight =
        0;


    if (
        exportLogoImage.complete
        &&
        exportLogoImage.naturalWidth > 0
    ) {

        logoHeight =

            logoWidth *

            (
                exportLogoImage.naturalHeight
                /
                exportLogoImage.naturalWidth
            );

    }


    const rightMargin =
        12 * scale;


    const topMargin =
        8 * scale;


    const logoX =

        width

        -

        rightMargin

        -

        logoWidth;


    const logoY =
        topMargin;


    if (
        exportLogoImage.complete
        &&
        exportLogoImage.naturalWidth > 0
    ) {

        ctx.drawImage(

            exportLogoImage,

            logoX,
            logoY,

            logoWidth,
            logoHeight

        );

    }


    // ========================================================
    // NWS NORTH PLATTE TEXT
    // ========================================================

    const officeText =
        "NWS North Platte, NE";


    const officeFontSize =
        Math.max(
            17,
            18 * scale
        );


    ctx.font =
        `700 ${officeFontSize}px Arial, sans-serif`;


    ctx.textAlign =
        "right";


    ctx.textBaseline =
        "top";


    const officeX =
        width -
        rightMargin;


    const officeY =

        logoY

        +

        logoHeight

        +

        3 * scale;


    ctx.lineJoin =
        "round";


    ctx.strokeStyle =
        "rgba(0,0,0,0.95)";


    ctx.lineWidth =
        Math.max(
            3,
            4 * scale
        );


    ctx.strokeText(

        officeText,

        officeX,
        officeY

    );


    ctx.fillStyle =
        "#ffffff";


    ctx.fillText(

        officeText,

        officeX,
        officeY

    );


    ctx.textAlign =
        "left";


    return exportCanvas;

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
// FILE-SAFE VALID TIME
// ============================================================

function makeFileTime(
    frame
) {

    if (!frame) {

        return "unknown";

    }


    return (

        frame.valid

            .replace(
                /[:-]/g,
                ""
            )

            .replace(
                ".000",
                ""
            )

            .replace(
                "T",
                "_"
            )

    );

}


// ============================================================
// SAVE PNG
// ============================================================

async function saveCurrentPng() {

    if (
        exportBusy
        ||
        availableFrames.length === 0
    ) {

        return;

    }


    stopAnimation();


    exportBusy =
        true;


    updateExportButtonState();


    try {

        const frame =
            availableFrames[
                currentFrameIndex
            ];


        await waitForMapIdle();


        const canvas =
            createExportCanvas(
                frame
            );


        const blob =
            await new Promise(
                (
                    resolve,
                    reject
                ) => {

                    canvas.toBlob(

                        result => {

                            if (result) {

                                resolve(
                                    result
                                );

                            }

                            else {

                                reject(
                                    new Error(
                                        "PNG creation failed."
                                    )
                                );

                            }

                        },

                        "image/png"

                    );

                }
            );


        const filename =

            `${PNG_FILENAME_PREFIX}_` +

            `f${String(
                frame.fhr
            ).padStart(
                3,
                "0"
            )}_` +

            `${makeFileTime(
                frame
            )}.png`;


        downloadBlob(
            blob,
            filename
        );

    }


    catch (error) {

        console.error(
            "PNG export failed:",
            error
        );


        alert(
            "Unable to create PNG."
        );

    }


    finally {

        exportBusy =
            false;


        updateExportButtonState();

    }

}


// ============================================================
// LOAD GIFENC
// ============================================================

let gifencModulePromise =
    null;


function loadGifenc() {

    if (
        !gifencModulePromise
    ) {

        gifencModulePromise =
            import(
                "https://unpkg.com/gifenc@1.0.3?module"
            );

    }


    return gifencModulePromise;

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
        ||
        availableFrames.length === 0
    ) {

        return;

    }


    if (
        startIndex < 0
        ||
        endIndex < 0
        ||
        startIndex >=
            availableFrames.length
        ||
        endIndex >=
            availableFrames.length
    ) {

        return;

    }


    if (
        startIndex >
        endIndex
    ) {

        const temp =
            startIndex;


        startIndex =
            endIndex;


        endIndex =
            temp;

    }


    stopAnimation();


    exportBusy =
        true;


    updateExportButtonState();


    const originalIndex =
        currentFrameIndex;


    const status =
        document.getElementById(
            "gif-status"
        );


    try {

        if (status) {

            status.textContent =
                "Loading GIF encoder...";

        }


        const {
            GIFEncoder,
            quantize,
            applyPalette
        } =
            await loadGifenc();


        const gif =
            GIFEncoder();


        let frameNumber =
            0;


        const totalFrames =

            (
                endIndex -
                startIndex
            )

            +

            1;


        for (
            let index =
                startIndex;

            index <=
                endIndex;

            index++
        ) {

            frameNumber++;


            const frame =
                availableFrames[
                    index
                ];


            if (status) {

                status.textContent =

                    `Capturing ${frameNumber}/${totalFrames} ` +

                    `(F${String(
                        frame.fhr
                    ).padStart(
                        3,
                        "0"
                    )})`;

            }


            currentFrameIndex =
                index;


            displayFrame(
                frame
            );


            updateHourButtonStyles();


            await waitForMapIdle();


            await new Promise(
                resolve => {

                    requestAnimationFrame(
                        () => {

                            requestAnimationFrame(
                                resolve
                            );

                        }
                    );

                }
            );


            const exportCanvas =
                createExportCanvas(

                    frame,

                    GIF_MAX_WIDTH

                );


            const ctx =
                exportCanvas.getContext(
                    "2d"
                );


            const width =
                exportCanvas.width;


            const height =
                exportCanvas.height;


            const image =
                ctx.getImageData(
                    0,
                    0,
                    width,
                    height
                );


            if (status) {

                status.textContent =

                    `Encoding ${frameNumber}/${totalFrames}`;

            }


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

                width,
                height,

                {

                    palette:
                        palette,

                    delay:
                        GIF_FRAME_DELAY_MS,

                    repeat:
                        0

                }

            );

        }


        if (status) {

            status.textContent =
                "Finishing GIF...";

        }


        gif.finish();


        const bytes =
            gif.bytes();


        const blob =
            new Blob(

                [
                    bytes
                ],

                {

                    type:
                        "image/gif"

                }

            );


        const firstFrame =
            availableFrames[
                startIndex
            ];


        const lastFrame =
            availableFrames[
                endIndex
            ];


        const filename =

            `${PNG_FILENAME_PREFIX}_` +

            `f${String(
                firstFrame.fhr
            ).padStart(
                3,
                "0"
            )}-` +

            `f${String(
                lastFrame.fhr
            ).padStart(
                3,
                "0"
            )}.gif`;


        downloadBlob(
            blob,
            filename
        );


        if (status) {

            status.textContent =
                "GIF complete.";

        }

    }


    catch (error) {

        console.error(
            "GIF export failed:",
            error
        );


        if (status) {

            status.textContent =
                "GIF export failed.";

        }


        alert(
            "Unable to create GIF."
        );

    }


    finally {

        // ====================================================
        // RETURN TO ORIGINAL FRAME
        // ====================================================

        currentFrameIndex =
            Math.min(

                originalIndex,

                availableFrames.length - 1

            );


        if (
            currentFrameIndex >= 0
            &&
            availableFrames[
                currentFrameIndex
            ]
        ) {

            displayFrame(

                availableFrames[
                    currentFrameIndex
                ]

            );


            await waitForMapIdle();

        }


        updateHourButtonStyles();


        scrollSelectedHourIntoView();


        exportBusy =
            false;


        updateExportButtonState();

    }

}


// ============================================================
// CREATE EXPORT CONTROLS
// ============================================================

function createExportControls() {

    if (
        document.getElementById(
            "export-controls"
        )
    ) {

        return;

    }


    // ========================================================
    // SAVE BUTTONS
    // ========================================================

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


    // ========================================================
    // GIF PANEL
    // ========================================================

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

                <label for="gif-start-hour">
                    Start Hour
                </label>

                <select id="gif-start-hour">
                </select>

            </div>


            <div class="gif-select-box">

                <label for="gif-end-hour">
                    End Hour
                </label>

                <select id="gif-end-hour">
                </select>

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


    // ========================================================
    // SAVE PNG
    // ========================================================

    document
        .getElementById(
            "save-png-button"
        )
        .addEventListener(
            "click",
            saveCurrentPng
        );


    // ========================================================
    // OPEN GIF PANEL
    // ========================================================

    document
        .getElementById(
            "save-gif-button"
        )
        .addEventListener(
            "click",
            () => {

                if (exportBusy) {

                    return;

                }


                panel.classList.toggle(
                    "open"
                );


                rebuildGifRangeSelectors();

            }
        );


    // ========================================================
    // CANCEL GIF
    // ========================================================

    document
        .getElementById(
            "gif-cancel-button"
        )
        .addEventListener(
            "click",
            () => {

                if (exportBusy) {

                    return;

                }


                panel.classList.remove(
                    "open"
                );

            }
        );


    // ========================================================
    // CREATE GIF
    // ========================================================

    document
        .getElementById(
            "gif-create-button"
        )
        .addEventListener(
            "click",
            async () => {

                const startSelect =
                    document.getElementById(
                        "gif-start-hour"
                    );


                const endSelect =
                    document.getElementById(
                        "gif-end-hour"
                    );


                if (
                    !startSelect
                    ||
                    !endSelect
                ) {

                    return;

                }


                const startIndex =
                    Number(
                        startSelect.value
                    );


                const endIndex =
                    Number(
                        endSelect.value
                    );


                await saveGif(
                    startIndex,
                    endIndex
                );

            }
        );


    updateExportButtonState();

}


// ============================================================
// BUILD GIF RANGE SELECTORS
//
// GIF selectors ONLY contain hours that actually exist.
// ============================================================

function rebuildGifRangeSelectors() {

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


    const oldStart =
        Number(
            start.value
        );


    const oldEnd =
        Number(
            end.value
        );


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


            const startOption =
                document.createElement(
                    "option"
                );


            startOption.value =
                String(
                    index
                );


            startOption.textContent =
                label;


            start.appendChild(
                startOption
            );


            const endOption =
                document.createElement(
                    "option"
                );


            endOption.value =
                String(
                    index
                );


            endOption.textContent =
                label;


            end.appendChild(
                endOption
            );

        }

    );


    if (
        availableFrames.length === 0
    ) {

        return;

    }


    start.value =
        String(

            Number.isFinite(
                oldStart
            )
            &&
            oldStart >= 0
            &&
            oldStart <
                availableFrames.length

                ? oldStart

                : 0

        );


    end.value =
        String(

            Number.isFinite(
                oldEnd
            )
            &&
            oldEnd >= 0
            &&
            oldEnd <
                availableFrames.length

                ? oldEnd

                :
                availableFrames.length - 1

        );

}


// ============================================================
// EXPORT BUTTON STATE
// ============================================================

function updateExportButtonState() {

    const png =
        document.getElementById(
            "save-png-button"
        );


    const gif =
        document.getElementById(
            "save-gif-button"
        );


    const gifCreate =
        document.getElementById(
            "gif-create-button"
        );


    const disabled =

        exportBusy

        ||

        activeModel === "none"

        ||

        availableFrames.length === 0;


    if (png) {

        png.disabled =
            disabled;

    }


    if (gif) {

        gif.disabled =
            disabled;

    }


    if (gifCreate) {

        gifCreate.disabled =
            disabled;

    }

}


// ============================================================
// REFRESH MANIFEST
//
// IMPORTANT BEHAVIOR:
//
// Initial page load:
//     Start on F000.
//
// New HRRR run:
//     Start on F000.
//
// More hours arrive:
//     Keep user on whatever hour they selected.
//
// Timeline:
//     Always shows every expected forecast hour.
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


        // ====================================================
        // REMEMBER CURRENT FORECAST HOUR
        // ====================================================

        if (
            availableFrames.length > 0
            &&
            availableFrames[
                currentFrameIndex
            ]
        ) {

            selectedFhr =
                Number(

                    availableFrames[
                        currentFrameIndex
                    ].fhr

                );

        }


        // ====================================================
        // MANIFEST URL
        // ====================================================

        const manifestUrl =

            `${product.baseUrl}/` +

            `manifest.json` +

            `?t=${Date.now()}`;


        // ====================================================
        // FETCH MANIFEST
        // ====================================================

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


        // ====================================================
        // VALIDATE
        // ====================================================

        if (
            !Array.isArray(
                manifest.hours
            )
        ) {

            throw new Error(
                "Manifest missing hours array"
            );

        }


        // ====================================================
        // DETECT NEW RUN
        // ====================================================

        const runChanged =

            currentManifest

            &&

            currentManifest.run
            !==
            manifest.run;


        currentManifest =
            manifest;


        // ====================================================
        // AVAILABLE HOURS
        // ====================================================

        availableFrames =
            [...manifest.hours]
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


        // ====================================================
        // NO HOURS AVAILABLE YET
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
                    "New HRRR run loading...";

            }


            buildHourButtons();


            updateExportButtonState();


            return;

        }


        let targetIndex =
            -1;


        // ====================================================
        // SAME RUN:
        //
        // Keep selected forecast hour if it still exists.
        // ====================================================

        if (
            !runChanged
            &&
            selectedFhr !== null
        ) {

            targetIndex =
                availableFrames.findIndex(

                    frame =>
                        Number(
                            frame.fhr
                        ) ===
                        selectedFhr

                );

        }


        // ====================================================
        // FIRST LOAD OR NEW RUN:
        //
        // AUTOMATICALLY START AT F000.
        // ====================================================

        if (
            targetIndex < 0
        ) {

            const f000Index =
                availableFrames.findIndex(

                    frame =>
                        Number(
                            frame.fhr
                        ) === 0

                );


            targetIndex =

                f000Index >= 0

                    ? f000Index

                    : 0;

        }


        currentFrameIndex =
            targetIndex;


        // ====================================================
        // REBUILD TIMELINE
        //
        // Newly available hours automatically turn blue here.
        // ====================================================

        buildHourButtons();


        // ====================================================
        // DISPLAY SELECTED FRAME
        // ====================================================

        displayFrame(

            availableFrames[
                currentFrameIndex
            ]

        );


        scrollSelectedHourIntoView();


        updateExportButtonState();

    }


    catch (error) {

        console.error(
            "Manifest error:",
            error
        );


        const label =
            document.getElementById(
                "model-valid-label"
            );


        if (label) {

            label.textContent =
                "HRRR data unavailable";

        }


        updateExportButtonState();

    }

}


// ============================================================
// OVERLAY VISIBILITY
// ============================================================

function setLayersVisible(
    layerIds,
    visible
) {

    const visibility =
        visible
            ? "visible"
            : "none";


    layerIds.forEach(
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


        updateExportButtonState();


        return;

    }


    // ========================================================
    // MODEL MODE
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
// MAP LOAD
// ============================================================

map.on(

    "load",

    async () => {


        console.log(
            "Mapbox map loaded"
        );


        // ====================================================
        // BOUNDARY SOURCE
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


        const roadLayer =
            findFirstRoadLayerId();


        // ====================================================
        // SPC DAY 1 SOURCE
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

            roadLayer

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

            roadLayer

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

            roadLayer

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
        // LBF CWA SOURCE
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
        // LBF CWA BLACK HALO
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

                    4, 4,

                    6, 5,

                    8, 6,

                    10, 7

                ]

            }

        });


        // ====================================================
        // LBF CWA WHITE LINE
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

                    4, 2,

                    6, 3,

                    8, 4,

                    10, 5

                ]

            }

        });


        // ====================================================
        // EXPORT CONTROLS
        // ====================================================

        createExportControls();


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


        if (
            overlayButton
            &&
            overlayContent
        ) {

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

        }


        // ====================================================
        // SPC TOGGLE
        // ====================================================

        const spcToggle =
            document.getElementById(
                "spc-toggle"
            );


        if (spcToggle) {

            spcToggle.addEventListener(

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

        }


        // ====================================================
        // CWA TOGGLE
        // ====================================================

        const cwaToggle =
            document.getElementById(
                "cwa-toggle"
            );


        if (cwaToggle) {

            cwaToggle.addEventListener(

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

        }


        // ====================================================
        // COUNTY TOGGLE
        // ====================================================

        const countyToggle =
            document.getElementById(
                "county-toggle"
            );


        if (countyToggle) {

            countyToggle.addEventListener(

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

        }


        // ====================================================
        // STATE TOGGLE
        // ====================================================

        const stateToggle =
            document.getElementById(
                "state-toggle"
            );


        if (stateToggle) {

            stateToggle.addEventListener(

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

        }


        // ====================================================
        // MODEL SELECT
        // ====================================================

        const modelSelect =
            document.getElementById(
                "model-select"
            );


        if (modelSelect) {

            modelSelect.addEventListener(

                "change",

                async event => {

                    await switchModel(
                        event.target.value
                    );

                }

            );

        }


        // ====================================================
        // PRODUCT SELECT
        // ====================================================

        const productSelect =
            document.getElementById(
                "product-select"
            );


        if (productSelect) {

            productSelect.addEventListener(

                "change",

                async event => {

                    activeProduct =
                        event.target.value;


                    currentManifest =
                        null;


                    availableFrames =
                        [];


                    currentFrameIndex =
                        0;


                    await refreshManifest();

                }

            );

        }


        // ====================================================
        // PLAY
        // ====================================================

        const playButton =
            document.getElementById(
                "model-play-button"
            );


        if (playButton) {

            playButton.addEventListener(

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

        }


        // ====================================================
        // PREVIOUS
        // ====================================================

        const prevButton =
            document.getElementById(
                "model-prev-button"
            );


        if (prevButton) {

            prevButton.addEventListener(

                "click",

                () => {

                    stopAnimation();


                    setFrameIndex(
                        currentFrameIndex - 1
                    );

                }

            );

        }


        // ====================================================
        // NEXT
        // ====================================================

        const nextButton =
            document.getElementById(
                "model-next-button"
            );


        if (nextButton) {

            nextButton.addEventListener(

                "click",

                () => {

                    stopAnimation();


                    setFrameIndex(
                        currentFrameIndex + 1
                    );

                }

            );

        }


        // ====================================================
        // INITIAL HRRR LOAD
        //
        // refreshManifest() now automatically chooses F000.
        // ====================================================

        await refreshManifest();


        // ====================================================
        // CHECK S3 FOR NEW FORECAST HOURS
        //
        // Any newly published hour automatically changes
        // from dark -> blue.
        // ====================================================

        setInterval(

            () => {

                if (
                    activeModel !==
                    "none"
                    &&
                    !exportBusy
                ) {

                    refreshManifest();

                }

            },

            MANIFEST_REFRESH_MS

        );


        console.log(
            "Viewer initialized successfully"
        );

    }

);
