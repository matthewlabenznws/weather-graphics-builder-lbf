mapboxgl.accessToken = "pk.eyJ1IjoibWF0dGhld2xhYmVuejciLCJhIjoiY21zbjhxZ3ZkMXBoNDJ3cHl5eG5uNzlpZCJ9.UBy4k84SejJzzu2VF0TtcA";

const map = new mapboxgl.Map({
    container: "map",

    // Satellite + Mapbox roads + cities
    style: "mapbox://styles/mapbox/satellite-streets-v12",

    center: [-100.75, 41.1],

    zoom: 6,

    preserveDrawingBuffer: true
});

map.addControl(
    new mapboxgl.NavigationControl(),
    "top-right"
);


map.on("load", () => {

    // ============================================================
    // VECTOR DATA FOR OUR CUSTOM BOUNDARIES
    // ============================================================

    map.addSource("boundary-data", {
        type: "vector",
        url: "mapbox://mapbox.mapbox-streets-v8"
    });


    // ============================================================
    // COUNTY BOUNDARIES
    // ============================================================

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


    // ============================================================
    // STATE BOUNDARIES
    // ============================================================

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

});


map.on("error", (e) => {
    console.error("MAPBOX ERROR:", e.error);
});
