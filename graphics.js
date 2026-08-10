mapboxgl.accessToken = "pk.eyJ1IjoibWF0dGhld2xhYmVuejciLCJhIjoiY21zbjhxZ3ZkMXBoNDJ3cHl5eG5uNzlpZCJ9.UBy4k84SejJzzu2VF0TtcA";

const map = new mapboxgl.Map({
    container: "map",

    // Satellite imagery + roads + cities
    style: "mapbox://styles/mapbox/satellite-streets-v12",

    // North Platte / western Nebraska
    center: [-100.75, 41.1],

    zoom: 6,

    // Needed later for PNG/GIF exporting
    preserveDrawingBuffer: true
});


// ============================================================
// NAVIGATION CONTROLS
// ============================================================

map.addControl(
    new mapboxgl.NavigationControl(),
    "top-right"
);


// ============================================================
// MAP LOAD
// ============================================================

map.on("load", () => {

    console.log("Map loaded");


    // ========================================================
    // FIND FIRST MAPBOX ROAD LAYER
    //
    // SPC will be inserted below this layer so roads,
    // interstate shields, city labels, etc. stay visible.
    // ========================================================

    const styleLayers = map.getStyle().layers;

    const firstRoadLayer = styleLayers.find(layer => {

        return (
            layer["source-layer"] === "road" ||
            layer.id.toLowerCase().includes("road")
        );

    });


    const firstRoadLayerId = firstRoadLayer
        ? firstRoadLayer.id
        : null;


    console.log(
        "SPC layers inserted below:",
        firstRoadLayerId
    );


    // ========================================================
    // MAPBOX VECTOR DATA
    //
    // Used for custom county/state boundaries.
    // ========================================================

    map.addSource("boundary-data", {
        type: "vector",
        url: "mapbox://mapbox.mapbox-streets-v8"
    });


    // ========================================================
    // SPC DAY 1 CATEGORICAL SOURCE
    // ========================================================

    map.addSource("spc-day1-cat", {
        type: "geojson",
        data: "data/spc_day1_cat.geojson"
    });


    // ========================================================
    // SPC DAY 1 FILL
    //
    // Drawn above satellite imagery but below Mapbox roads
    // and labels.
    // ========================================================

    map.addLayer(
        {
            id: "spc-day1-cat-fill",

            type: "fill",

            source: "spc-day1-cat",

            layout: {
                visibility: "visible"
            },

            paint: {

                "fill-color": [
                    "coalesce",
                    ["get", "fill"],
                    "#888888"
                ],

                "fill-opacity": 0.68
            }
        },

        firstRoadLayerId
    );


    // ========================================================
    // SPC DARK OUTLINE
    // ========================================================

    map.addLayer(
        {
            id: "spc-day1-cat-outline-dark",

            type: "line",

            source: "spc-day1-cat",

            layout: {
                visibility: "visible"
            },

            paint: {

                "line-color": "#1A1A1A",

                "line-width": [
                    "interpolate",
                    ["linear"],
                    ["zoom"],

                    4, 2.2,
                    6, 3.0,
                    8, 3.8,
                    10, 4.5
                ],

                "line-opacity": 1
            }
        },

        firstRoadLayerId
    );


    // ========================================================
    // SPC OFFICIAL COLORED OUTLINE
    // ========================================================

    map.addLayer(
        {
            id: "spc-day1-cat-outline",

            type: "line",

            source: "spc-day1-cat",

            layout: {
                visibility: "visible"
            },

            paint: {

                "line-color": [
                    "coalesce",
                    ["get", "stroke"],
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

                "line-opacity": 1
            }
        },

        firstRoadLayerId
    );


    // ========================================================
    // COUNTY BOUNDARIES
    // ========================================================

    map.addLayer({
        id: "custom-county-boundaries",

        type: "line",

        source: "boundary-data",

        "source-layer": "admin",

        filter: [
            "==",
            ["get", "admin_level"],
            2
        ],

        paint: {

            "line-color": "#000000",

            "line-width": [
                "interpolate",
                ["linear"],
                ["zoom"],

                4, 0.5,
                6, 0.8,
                8, 1.1,
                10, 1.4
            ],

            "line-opacity": 0.95
        }
    });


    // ========================================================
    // STATE BOUNDARIES
    // ========================================================

    map.addLayer({
        id: "custom-state-boundaries",

        type: "line",

        source: "boundary-data",

        "source-layer": "admin",

        filter: [
            "==",
            ["get", "admin_level"],
            1
        ],

        paint: {

            "line-color": "#000000",

            "line-width": [
                "interpolate",
                ["linear"],
                ["zoom"],

                4, 2.0,
                6, 2.7,
                8, 3.3,
                10, 4.0
            ],

            "line-opacity": 1
        }
    });


    // ========================================================
    // NWS NORTH PLATTE CWA SOURCE
    // ========================================================

    map.addSource("lbf-cwa", {
        type: "geojson",
        data: "data/lbf_cwa.geojson"
    });


    // ========================================================
    // LBF CWA BLACK OUTLINE
    // ========================================================

    map.addLayer({
        id: "lbf-cwa-outline",

        type: "line",

        source: "lbf-cwa",

        paint: {

            "line-color": "#000000",

            "line-width": [
                "interpolate",
                ["linear"],
                ["zoom"],

                4, 4.0,
                6, 5.0,
                8, 6.0,
                10, 7.0
            ],

            "line-opacity": 1
        }
    });


    // ========================================================
    // LBF CWA WHITE BOUNDARY
    // ========================================================

    map.addLayer({
        id: "lbf-cwa-boundary",

        type: "line",

        source: "lbf-cwa",

        paint: {

            "line-color": "#FFFFFF",

            "line-width": [
                "interpolate",
                ["linear"],
                ["zoom"],

                4, 2.0,
                6, 3.0,
                8, 4.0,
                10, 5.0
            ],

            "line-opacity": 1
        }
    });


    console.log(
        "Map layers loaded successfully."
    );

});


// ============================================================
// SPC DAY 1 TOGGLE
// ============================================================

const spcToggle = document.getElementById(
    "spc-toggle"
);


spcToggle.addEventListener(
    "change",
    () => {

        const visibility =
            spcToggle.checked
                ? "visible"
                : "none";


        const spcLayers = [

            "spc-day1-cat-fill",

            "spc-day1-cat-outline-dark",

            "spc-day1-cat-outline"

        ];


        spcLayers.forEach(
            layerId => {

                if (
                    map.getLayer(layerId)
                ) {

                    map.setLayoutProperty(
                        layerId,
                        "visibility",
                        visibility
                    );

                }

            }
        );


        console.log(
            `SPC Day 1 visibility: ${visibility}`
        );

    }
);


// ============================================================
// MAPBOX ERROR REPORTING
// ============================================================

map.on(
    "error",
    (e) => {

        console.error(
            "MAPBOX ERROR:",
            e.error
        );

    }
);
