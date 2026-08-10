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
