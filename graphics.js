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

    // ============================================================
    // COUNTY BOUNDARIES
    // ============================================================

    map.addSource("counties", {
        type: "geojson",
        data: "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
    });

    map.addLayer({
        id: "county-boundaries",
        type: "line",
        source: "counties",

        paint: {
            "line-color": "#000000",
            "line-width": [
                "interpolate",
                ["linear"],
                ["zoom"],
                4, 0.4,
                6, 0.8,
                8, 1.2,
                10, 1.5
            ],

            "line-opacity": 0.9
        }
    });


    // ============================================================
    // STATE BOUNDARIES
    // ============================================================

    map.addSource("states", {
        type: "geojson",
        data: "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json"
    });

    map.addLayer({
        id: "state-boundaries",
        type: "line",
        source: "states",

        paint: {
            "line-color": "#000000",

            "line-width": [
                "interpolate",
                ["linear"],
                ["zoom"],
                4, 1.2,
                6, 1.8,
                8, 2.2,
                10, 2.5
            ],

            "line-opacity": 1.0
        }
    });

});
