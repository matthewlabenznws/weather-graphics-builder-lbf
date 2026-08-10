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

map.on("load", () => {

    console.log("Map loaded");

    // ============================================================
    // MAPBOX STREETS VECTOR DATA
    // ============================================================

    map.addSource("streets-data", {
        type: "vector",
        url: "mapbox://mapbox.mapbox-streets-v8"
    });


    // ============================================================
    // COUNTY BOUNDARIES
    // admin_level = 2 is generally state/country level
    // admin_level = 3/4 contains lower administrative boundaries
    // ============================================================

    map.addLayer({
        id: "county-boundaries",

        type: "line",

        source: "streets-data",

        "source-layer": "admin",

        filter: [
            "all",
            ["==", ["get", "admin_level"], 2]
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


    // ============================================================
    // STRONGER STATE BOUNDARIES
    // ============================================================

    map.addLayer({
        id: "state-boundaries",

        type: "line",

        source: "streets-data",

        "source-layer": "admin",

        filter: [
            "all",
            ["==", ["get", "admin_level"], 1]
        ],

        paint: {
            "line-color": "#000000",

            "line-width": [
                "interpolate",
                ["linear"],
                ["zoom"],
                4, 1.2,
                6, 1.7,
                8, 2.0,
                10, 2.4
            ],

            "line-opacity": 1
        }
    });

});
