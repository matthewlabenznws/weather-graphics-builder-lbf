mapboxgl.accessToken = "pk.eyJ1IjoibWF0dGhld2xhYmVuejciLCJhIjoiY21zbjhxZ3ZkMXBoNDJ3cHl5eG5uNzlpZCJ9.UBy4k84SejJzzu2VF0TtcA";

const map = new mapboxgl.Map({
    container: "map",

    style: "mapbox://styles/mapbox/satellite-v9",

    center: [-100.75, 41.1],

    zoom: 6,

    preserveDrawingBuffer: true
});

map.addControl(
    new mapboxgl.NavigationControl(),
    "top-right"
);


// ============================================================
// MAP LOAD
// ============================================================

map.on("load", () => {

    // --------------------------------------------------------
    // MAPBOX STREETS VECTOR DATA
    // --------------------------------------------------------

    map.addSource("streets-data", {
        type: "vector",
        url: "mapbox://mapbox.mapbox-streets-v8"
    });


    // ========================================================
    // COUNTY BOUNDARIES
    // ========================================================

    map.addLayer({
        id: "county-boundaries",

        type: "line",

        source: "streets-data",

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
    // Thicker than before
    // ========================================================

    map.addLayer({
        id: "state-boundaries",

        type: "line",

        source: "streets-data",

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
                6, 2.5,
                8, 3.0,
                10, 3.5
            ],

            "line-opacity": 1
        }
    });


    // ========================================================
    // NORMAL ROADS
    // ========================================================

    map.addLayer({
        id: "roads",

        type: "line",

        source: "streets-data",

        "source-layer": "road",

        filter: [
            "match",
            ["get", "class"],

            [
                "primary",
                "secondary",
                "tertiary",
                "trunk"
            ],

            true,
            false
        ],

        paint: {

            "line-color": "#c8b68a",

            "line-width": [
                "interpolate",
                ["linear"],
                ["zoom"],

                5, 0.3,
                6, 0.5,
                8, 1.0,
                10, 1.5
            ],

            "line-opacity": 0.8
        }
    });


    // ========================================================
    // INTERSTATES
    // Blue like WeatherFront
    // ========================================================

    // Dark outline first
    map.addLayer({
        id: "interstate-outline",

        type: "line",

        source: "streets-data",

        "source-layer": "road",

        filter: [
            "==",
            ["get", "class"],
            "motorway"
        ],

        paint: {

            "line-color": "#000000",

            "line-width": [
                "interpolate",
                ["linear"],
                ["zoom"],

                4, 2.4,
                6, 3.0,
                8, 4.0,
                10, 5.0
            ],

            "line-opacity": 0.9
        }
    });


    // Blue interstate center
    map.addLayer({
        id: "interstates",

        type: "line",

        source: "streets-data",

        "source-layer": "road",

        filter: [
            "==",
            ["get", "class"],
            "motorway"
        ],

        paint: {

            "line-color": "#2878ff",

            "line-width": [
                "interpolate",
                ["linear"],
                ["zoom"],

                4, 1.2,
                6, 1.8,
                8, 2.5,
                10, 3.2
            ],

            "line-opacity": 1
        }
    });


    // ========================================================
    // CITY LABELS
    // ========================================================

    map.addLayer({
        id: "city-labels",

        type: "symbol",

        source: "streets-data",

        "source-layer": "place_label",

        filter: [
            "match",
            ["get", "type"],

            [
                "city",
                "town"
            ],

            true,
            false
        ],

        layout: {

            "text-field": ["get", "name"],

            "text-size": [
                "interpolate",
                ["linear"],
                ["zoom"],

                5, 10,
                7, 12,
                9, 14
            ],

            "text-font": [
                "DIN Pro Medium",
                "Arial Unicode MS Regular"
            ],

            "text-allow-overlap": false
        },

        paint: {

            "text-color": "#ffffff",

            "text-halo-color": "#000000",

            "text-halo-width": 1.5,

            "text-halo-blur": 0.5
        }
    });

});


// ============================================================
// ERROR REPORTING
// ============================================================

map.on("error", (e) => {
    console.error("MAPBOX ERROR:", e.error);
});
