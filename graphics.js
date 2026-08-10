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
    // MAPBOX VECTOR DATA
    // Used for our custom county/state boundaries
    // ========================================================

    map.addSource("boundary-data", {
        type: "vector",
        url: "mapbox://mapbox.mapbox-streets-v8"
    });


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

            "line-opacity": 0.9
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

        // File stored in:
        // data/lbf_cwa.geojson

        data: "data/lbf_cwa.geojson"
    });


    // ========================================================
    // LBF CWA BLACK OUTLINE
    // Drawn first underneath the white line
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


});


// ============================================================
// MAPBOX ERROR REPORTING
// ============================================================

map.on("error", (e) => {

    console.error(
        "MAPBOX ERROR:",
        e.error
    );

});
