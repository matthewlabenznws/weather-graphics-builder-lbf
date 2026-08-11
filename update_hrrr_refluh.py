# ============================================================
# HRRR COMPOSITE REFLECTIVITY + 2-5 KM UH >= 75
#
# Progressive S3 publishing:
#
# F000 generated
#   -> upload f000.png
#   -> update/upload manifest.json
#
# F001 generated
#   -> upload f001.png
#   -> update/upload manifest.json
#
# etc.
# ============================================================

import gzip
import json
import time
import warnings

from datetime import datetime, timedelta, timezone
from pathlib import Path

import boto3
import numpy as np

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import cartopy.crs as ccrs

from matplotlib.colors import (
    LinearSegmentedColormap,
    Normalize
)

from scipy.ndimage import (
    zoom,
    gaussian_filter
)
from scipy.spatial import cKDTree

from herbie import Herbie


warnings.filterwarnings("ignore")


# ============================================================
# AWS SETTINGS
# ============================================================

AWS_REGION = "us-east-2"

S3_BUCKET = "mtl-nwslbf-model-data"

S3_PREFIX = (
    "weather-graphics/"
    "hrrr/"
    "reflUH/"
    "latest"
)


s3 = boto3.client(
    "s3",
    region_name=AWS_REGION
)


# ============================================================
# MAP DOMAIN
# ============================================================

WEST = -105.5
EAST = -96.0
SOUTH = 38.5
NORTH = 44.5



# ============================================================
# SAMPLING GRID SETTINGS
#
# The browser samples a lightweight regular lat/lon grid
# generated from the native model fields.
#
# 0.03 degree spacing is roughly 2-3 km across this domain.
# ============================================================

SAMPLE_DX = 0.03
SAMPLE_DY = 0.03
SAMPLE_BUFFER_DEG = 0.25

# Cache the nearest-native-point mapping because the HRRR grid
# geometry is unchanged from one forecast hour to the next.
SAMPLE_MAPPING_CACHE = None

# ============================================================
# REFLECTIVITY SETTINGS
# ============================================================

MIN_REFL = 10.0

UPSCALE = 4

SMOOTH_SIGMA = 0.4


# ============================================================
# UPDRAFT HELICITY
# ============================================================

UH_THRESHOLD = 75.0


# ============================================================
# IMAGE SETTINGS
# ============================================================

FIG_WIDTH = 16
FIG_HEIGHT = 10
DPI = 150


# ============================================================
# RETRIES
# ============================================================

MAX_RUN_LOOKBACK = 10

DOWNLOAD_ATTEMPTS = 3

RETRY_SLEEP_SECONDS = 10


# ============================================================
# LOCAL OUTPUT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = (
    BASE_DIR
    / "output"
    / "hrrr"
    / "reflUH"
    / "latest"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# RADARSCOPE-STYLE REFLECTIVITY COLOR TABLE
# ============================================================

REFL_POINTS = [

    (-15.00, (0, 0, 0)),

    (5.00, (29, 37, 60)),

    (17.50, (89, 155, 171)),

    (22.50, (33, 186, 72)),

    (32.50, (5, 101, 1)),

    # Yellow
    (37.49, (251, 252, 0)),
    (37.50, (199, 176, 0)),

    # Orange
    (42.49, (253, 149, 2)),
    (42.50, (172, 92, 2)),

    # Red
    (49.99, (253, 38, 0)),
    (50.00, (135, 43, 22)),

    # Pink
    (59.99, (193, 148, 179)),
    (60.00, (200, 23, 119)),

    # Purple
    (69.99, (165, 2, 215)),
    (70.00, (64, 0, 146)),

    # Cyan
    (74.99, (135, 255, 253)),
    (75.00, (54, 120, 142)),

    # Extreme
    (80.00, (173, 99, 64)),
    (85.00, (105, 0, 4)),
    (95.00, (0, 0, 0))

]


COLOR_MIN = -15.0
COLOR_MAX = 95.0


# ============================================================
# COLORMAP
# ============================================================

def build_refl_colormap():

    cmap_points = []

    for value, rgb in REFL_POINTS:

        position = (
            (value - COLOR_MIN)
            /
            (COLOR_MAX - COLOR_MIN)
        )

        color = (
            rgb[0] / 255.0,
            rgb[1] / 255.0,
            rgb[2] / 255.0
        )

        cmap_points.append(
            (
                position,
                color
            )
        )

    cmap = LinearSegmentedColormap.from_list(
        "radarscope_br",
        cmap_points,
        N=2048
    )

    norm = Normalize(
        vmin=COLOR_MIN,
        vmax=COLOR_MAX
    )

    levels = np.arange(
        MIN_REFL,
        96,
        1.0
    )

    return cmap, norm, levels


REFL_CMAP, REFL_NORM, REFL_LEVELS = (
    build_refl_colormap()
)


# ============================================================
# FIND LATEST HRRR RUN
# ============================================================

def find_latest_hrrr():

    now = datetime.now(timezone.utc)

    start = now.replace(
        minute=0,
        second=0,
        microsecond=0
    )

    print("=" * 70)
    print("SEARCHING FOR LATEST AVAILABLE HRRR")
    print("=" * 70)

    for back in range(
        MAX_RUN_LOOKBACK + 1
    ):

        run = (
            start
            - timedelta(hours=back)
        )

        print(
            f"Trying "
            f"{run:%Y%m%d %HZ} F000"
        )

        try:

            H = Herbie(
                run.replace(
                    tzinfo=None
                ),
                model="hrrr",
                product="sfc",
                fxx=0
            )

            inv = H.inventory(
                r":REFC:"
            )

            if (
                inv is not None
                and len(inv) > 0
            ):

                print(
                    f"Using HRRR "
                    f"{run:%Y-%m-%d %HZ}"
                )

                return run

        except Exception as e:

            print(
                f"Unavailable: {e}"
            )

    raise RuntimeError(
        "Could not find a recent HRRR run."
    )


# ============================================================
# FORECAST LENGTH
# ============================================================

def get_max_fhr(run_time):

    if run_time.hour in [
        0,
        6,
        12,
        18
    ]:

        return 48

    return 18


# ============================================================
# DATA VARIABLE HELPER
# ============================================================

def get_2d_variable(
    ds,
    preferred_names=None
):

    if preferred_names is None:

        preferred_names = []

    for name in preferred_names:

        if name in ds.data_vars:

            return ds[name]

    for name in ds.data_vars:

        candidate = ds[name]

        if candidate.ndim >= 2:

            return candidate

    raise RuntimeError(
        "Could not locate 2-D variable."
    )


# ============================================================
# LOAD FORECAST HOUR
# ============================================================

def load_hour(
    run_time,
    fhr
):

    print()
    print("=" * 70)

    print(
        f"HRRR "
        f"{run_time:%Y%m%d %HZ} "
        f"F{fhr:03d}"
    )

    print("=" * 70)


    last_error = None


    for attempt in range(
        1,
        DOWNLOAD_ATTEMPTS + 1
    ):

        try:

            print(
                f"Attempt "
                f"{attempt}/"
                f"{DOWNLOAD_ATTEMPTS}"
            )


            H = Herbie(
                run_time.replace(
                    tzinfo=None
                ),
                model="hrrr",
                product="sfc",
                fxx=fhr
            )


            # =================================================
            # COMPOSITE REFLECTIVITY
            # =================================================

            ds_refl = H.xarray(
                r":REFC:"
            )


            refl_da = get_2d_variable(
                ds_refl,
                [
                    "refc",
                    "refd",
                    "REFC"
                ]
            )


            lat = ds_refl[
                "latitude"
            ].values

            lon = ds_refl[
                "longitude"
            ].values


            refl = np.squeeze(
                refl_da.values
            ).astype(float)


            # =================================================
            # 2-5 KM MAXIMUM UPDRAFT HELICITY
            #
            # F000 may occasionally not have a meaningful
            # hourly-max UH field. If unavailable, use zeros.
            # =================================================

            try:

                ds_uh = H.xarray(
                    r":MXUPHL:5000-2000 m above ground:"
                )


                uh_da = get_2d_variable(
                    ds_uh,
                    [
                        "mxuphl",
                        "MXUPHL",
                        "unknown"
                    ]
                )


                uh = np.squeeze(
                    uh_da.values
                ).astype(float)


            except Exception as uh_error:

                print(
                    "UH unavailable for "
                    f"F{fhr:03d}: "
                    f"{uh_error}"
                )

                print(
                    "Using zero UH field."
                )

                uh = np.zeros_like(
                    refl,
                    dtype=float
                )


            print(
                f"Reflectivity max: "
                f"{np.nanmax(refl):.1f} dBZ"
            )


            print(
                f"UH max: "
                f"{np.nanmax(uh):.1f}"
            )


            return (
                lon,
                lat,
                refl,
                uh
            )


        except Exception as e:

            last_error = e

            print(
                f"Attempt failed: {e}"
            )

            if attempt < DOWNLOAD_ATTEMPTS:

                time.sleep(
                    RETRY_SLEEP_SECONDS
                )


    raise RuntimeError(
        f"F{fhr:03d} failed: "
        f"{last_error}"
    )


# ============================================================
# PROCESS REFLECTIVITY
# ============================================================

def process_reflectivity(
    lon,
    lat,
    refl
):

    original_min = np.nanmin(
        refl
    )

    original_max = np.nanmax(
        refl
    )


    refl_clean = np.where(
        np.isfinite(refl),
        refl,
        -20.0
    )


    # ========================================================
    # 4X CUBIC DISPLAY INTERPOLATION
    # ========================================================

    refl_fine = zoom(
        refl_clean,
        UPSCALE,
        order=3
    )

    lon_fine = zoom(
        lon,
        UPSCALE,
        order=3
    )

    lat_fine = zoom(
        lat,
        UPSCALE,
        order=3
    )


    # Prevent cubic overshoot

    refl_fine = np.clip(
        refl_fine,
        original_min,
        original_max
    )


    # ========================================================
    # LIGHT DISPLAY SMOOTHING
    # ========================================================

    refl_fine = gaussian_filter(
        refl_fine,
        sigma=SMOOTH_SIGMA
    )


    refl_fine = np.clip(
        refl_fine,
        original_min,
        original_max
    )


    # ========================================================
    # HIDE < 10 DBZ
    # ========================================================

    refl_plot = np.ma.masked_where(
        refl_fine < MIN_REFL,
        refl_fine
    )


    return (
        lon_fine,
        lat_fine,
        refl_plot
    )


# ============================================================
# PROCESS UH
# ============================================================

def process_uh(
    lon,
    lat,
    uh
):

    uh_clean = np.where(
        np.isfinite(uh),
        uh,
        0.0
    )


    # Linear interpolation is intentional for UH.
    # Avoid cubic overshoot around the >=75 threshold.

    uh_fine = zoom(
        uh_clean,
        UPSCALE,
        order=1
    )

    lon_fine = zoom(
        lon,
        UPSCALE,
        order=1
    )

    lat_fine = zoom(
        lat,
        UPSCALE,
        order=1
    )


    return (
        lon_fine,
        lat_fine,
        uh_fine
    )


# ============================================================
# CREATE FRAME
# ============================================================

def plot_hour(
    run_time,
    fhr,
    lon,
    lat,
    refl,
    uh
):

    output_file = (
        OUTPUT_DIR
        / f"f{fhr:03d}.png"
    )


    (
        lon_refl,
        lat_refl,
        refl_plot

    ) = process_reflectivity(
        lon,
        lat,
        refl
    )


    (
        lon_uh,
        lat_uh,
        uh_fine

    ) = process_uh(
        lon,
        lat,
        uh
    )


    # ========================================================
    # FIGURE
    # ========================================================

    fig = plt.figure(
        figsize=(
            FIG_WIDTH,
            FIG_HEIGHT
        ),
        dpi=DPI,
        facecolor="none"
    )


    ax = fig.add_axes(
        [0, 0, 1, 1],
        projection=ccrs.PlateCarree()
    )


    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)


    ax.set_extent(
        [
            WEST,
            EAST,
            SOUTH,
            NORTH
        ],
        crs=ccrs.PlateCarree()
    )


    # ========================================================
    # REFLECTIVITY
    # ========================================================

    ax.contourf(
        lon_refl,
        lat_refl,
        refl_plot,

        levels=REFL_LEVELS,

        cmap=REFL_CMAP,

        norm=REFL_NORM,

        extend="max",

        transform=ccrs.PlateCarree(),

        antialiased=True,

        zorder=1
    )


    # ========================================================
    # UH >= 75
    # BLACK FILL + BLACK OUTLINE
    # ========================================================

    uh_max = np.nanmax(
        uh_fine
    )


    if uh_max >= UH_THRESHOLD:

        ax.contourf(
            lon_uh,
            lat_uh,
            uh_fine,

            levels=[
                UH_THRESHOLD,
                max(
                    1000.0,
                    uh_max + 1.0
                )
            ],

            colors=[
                "#000000"
            ],
            alpha = 0.45,
            
            transform=ccrs.PlateCarree(),

            antialiased=True,

            zorder=5
        )


        ax.contour(
            lon_uh,
            lat_uh,
            uh_fine,

            levels=[
                UH_THRESHOLD
            ],

            colors=[
                "#000000"
            ],

            linewidths=1.5,

            transform=ccrs.PlateCarree(),

            zorder=6
        )


    ax.set_axis_off()


    # ========================================================
    # SAVE
    # ========================================================

    plt.savefig(
        output_file,

        dpi=DPI,

        transparent=True,

        facecolor="none",

        edgecolor="none",

        bbox_inches=None,

        pad_inches=0
    )


    plt.close(
        fig
    )


    valid_time = (
        run_time
        + timedelta(hours=fhr)
    )


    frame = {

        "fhr": fhr,

        "file": (
            f"f{fhr:03d}.png"
        ),

        "valid": (
            valid_time.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        )

    }


    print(
        f"Created "
        f"{output_file.name}"
    )


    return (
        output_file,
        frame
    )


# ============================================================
# UPLOAD FRAME
# ============================================================

def upload_frame(
    output_file,
    fhr
):

    key = (
        f"{S3_PREFIX}/"
        f"f{fhr:03d}.png"
    )


    print(
        f"Uploading "
        f"{output_file.name}..."
    )


    s3.upload_file(
        str(output_file),

        S3_BUCKET,

        key,

        ExtraArgs={
            "ContentType":
                "image/png",

            "CacheControl":
                "no-cache, no-store, must-revalidate"
        }
    )


    print(
        f"Uploaded s3://"
        f"{S3_BUCKET}/"
        f"{key}"
    )




# ============================================================
# BUILD / CACHE SAMPLING MAPPING
# ============================================================

def get_sample_mapping(lon, lat):
    global SAMPLE_MAPPING_CACHE

    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)

    # Normalize longitudes to -180..180.
    lon = np.where(lon > 180.0, lon - 360.0, lon)

    # Reuse the mapping after the first hour because the model
    # grid geometry is fixed within a run.
    if SAMPLE_MAPPING_CACHE is not None:
        if SAMPLE_MAPPING_CACHE["native_shape"] == lon.shape:
            return SAMPLE_MAPPING_CACHE

    native_mask = (
        np.isfinite(lon)
        & np.isfinite(lat)
        & (lon >= WEST - SAMPLE_BUFFER_DEG)
        & (lon <= EAST + SAMPLE_BUFFER_DEG)
        & (lat >= SOUTH - SAMPLE_BUFFER_DEG)
        & (lat <= NORTH + SAMPLE_BUFFER_DEG)
    )

    flat_mask = native_mask.ravel()

    native_lon = lon.ravel()[flat_mask]
    native_lat = lat.ravel()[flat_mask]

    if native_lon.size == 0:
        raise RuntimeError(
            "No native model points found inside sampling domain."
        )

    sample_lons = np.arange(
        WEST,
        EAST + SAMPLE_DX / 2.0,
        SAMPLE_DX,
        dtype=float
    )

    sample_lats = np.arange(
        SOUTH,
        NORTH + SAMPLE_DY / 2.0,
        SAMPLE_DY,
        dtype=float
    )

    sample_lon_2d, sample_lat_2d = np.meshgrid(
        sample_lons,
        sample_lats
    )

    native_points = np.column_stack(
        (native_lon, native_lat)
    )

    sample_points = np.column_stack(
        (
            sample_lon_2d.ravel(),
            sample_lat_2d.ravel()
        )
    )

    print(
        "Building sampling nearest-neighbor mapping..."
    )

    tree = cKDTree(native_points)

    _, nearest_index = tree.query(
        sample_points,
        k=1
    )

    SAMPLE_MAPPING_CACHE = {
        "native_shape": lon.shape,
        "flat_mask": flat_mask,
        "nearest_index": nearest_index,
        "sample_lons": sample_lons,
        "sample_lats": sample_lats
    }

    return SAMPLE_MAPPING_CACHE


# ============================================================
# BUILD SAMPLING DATA
# ============================================================

def build_sample_grid(lon, lat, refl, uh):
    mapping = get_sample_mapping(
        lon,
        lat
    )

    refl = np.asarray(refl, dtype=float)
    uh = np.asarray(uh, dtype=float)

    if refl.shape != mapping["native_shape"]:
        raise RuntimeError(
            "Reflectivity shape does not match sampling grid."
        )

    if uh.shape != mapping["native_shape"]:
        raise RuntimeError(
            "UH shape does not match sampling grid."
        )

    flat_mask = mapping["flat_mask"]
    nearest_index = mapping["nearest_index"]

    native_refl = refl.ravel()[flat_mask]
    native_uh = uh.ravel()[flat_mask]

    sample_refl = native_refl[nearest_index]
    sample_uh = native_uh[nearest_index]

    sample_refl = np.where(
        np.isfinite(sample_refl),
        sample_refl,
        -9999.0
    )

    sample_uh = np.where(
        np.isfinite(sample_uh),
        sample_uh,
        -9999.0
    )

    sample_refl = np.round(
        sample_refl,
        1
    )

    sample_uh = np.round(
        sample_uh,
        1
    )

    sample_lons = mapping["sample_lons"]
    sample_lats = mapping["sample_lats"]

    return {
        "west": float(sample_lons[0]),
        "east": float(sample_lons[-1]),
        "south": float(sample_lats[0]),
        "north": float(sample_lats[-1]),
        "dx": float(SAMPLE_DX),
        "dy": float(SAMPLE_DY),
        "nx": int(sample_lons.size),
        "ny": int(sample_lats.size),
        "missing": -9999.0,
        "refl": sample_refl.astype(np.float32).tolist(),
        "uh": sample_uh.astype(np.float32).tolist()
    }


# ============================================================
# WRITE + UPLOAD SAMPLING DATA
# ============================================================

def publish_sample_grid(
    fhr,
    lon,
    lat,
    refl,
    uh
):
    print(
        f"Building sampling data for F{fhr:03d}..."
    )

    sample_data = build_sample_grid(
        lon,
        lat,
        refl,
        uh
    )

    filename = (
        f"f{fhr:03d}_sample.json.gz"
    )

    local_file = (
        OUTPUT_DIR
        / filename
    )

    with gzip.open(
        local_file,
        "wt",
        encoding="utf-8",
        compresslevel=6
    ) as f:
        json.dump(
            sample_data,
            f,
            separators=(",", ":")
        )

    key = (
        f"{S3_PREFIX}/"
        f"{filename}"
    )

    s3.upload_file(
        str(local_file),
        S3_BUCKET,
        key,
        ExtraArgs={
            "ContentType": "application/json",
            "ContentEncoding": "gzip",
            "CacheControl":
                "no-cache, no-store, must-revalidate"
        }
    )

    print(
        f"Uploaded sampling data: "
        f"s3://{S3_BUCKET}/{key}"
    )

    return filename

# ============================================================
# BUILD MANIFEST
# ============================================================

def build_manifest(
    run_time,
    max_fhr,
    hours,
    status
):

    return {

        "model": "HRRR",

        "product": "reflUH",

        "description":
            "Composite Reflectivity + 2-5 km UH >= 75",

        "run": (
            run_time.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        ),

        "cycle": (
            run_time.strftime(
                "%HZ"
            )
        ),

        "max_fhr": max_fhr,

        "reflectivity_min_dbz":
            MIN_REFL,

        "uh_threshold":
            UH_THRESHOLD,

        "status":
            status,

        "bounds": {

            "west": WEST,

            "east": EAST,

            "south": SOUTH,

            "north": NORTH

        },

        "hours":
            hours

    }


# ============================================================
# WRITE + UPLOAD MANIFEST
# ============================================================

def publish_manifest(
    run_time,
    max_fhr,
    hours,
    status="building"
):

    manifest = build_manifest(
        run_time,
        max_fhr,
        hours,
        status
    )


    manifest_file = (
        OUTPUT_DIR
        / "manifest.json"
    )


    with manifest_file.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            manifest,
            f,
            indent=2
        )


    s3.upload_file(
        str(manifest_file),

        S3_BUCKET,

        f"{S3_PREFIX}/manifest.json",

        ExtraArgs={
            "ContentType":
                "application/json",

            "CacheControl":
                "no-cache, no-store, must-revalidate"
        }
    )


    print(
        f"Manifest published "
        f"({len(hours)} hours)"
    )


# ============================================================
# CLEAR OLD LOCAL FILES
# ============================================================

def clean_local_output():

    for file in OUTPUT_DIR.glob(
        "f*.png"
    ):

        file.unlink()


    for file in OUTPUT_DIR.glob(
        "f*_sample.json.gz"
    ):

        file.unlink()


    manifest_file = (
        OUTPUT_DIR
        / "manifest.json"
    )


    if manifest_file.exists():

        manifest_file.unlink()


# ============================================================
# CLEAR OLD S3 FRAMES
# ============================================================

def clear_old_s3_frames():

    print()
    print(
        "Clearing previous latest HRRR frames..."
    )


    paginator = (
        s3.get_paginator(
            "list_objects_v2"
        )
    )


    objects_to_delete = []


    for page in paginator.paginate(
        Bucket=S3_BUCKET,
        Prefix=f"{S3_PREFIX}/"
    ):

        for obj in page.get(
            "Contents",
            []
        ):

            key = obj["Key"]

            if (
                key.endswith(".png")
                or
                key.endswith("_sample.json.gz")
                or
                key.endswith("manifest.json")
            ):

                objects_to_delete.append(
                    {
                        "Key": key
                    }
                )


                if len(
                    objects_to_delete
                ) == 1000:

                    s3.delete_objects(
                        Bucket=S3_BUCKET,
                        Delete={
                            "Objects":
                                objects_to_delete
                        }
                    )

                    objects_to_delete = []


    if objects_to_delete:

        s3.delete_objects(
            Bucket=S3_BUCKET,
            Delete={
                "Objects":
                    objects_to_delete
            }
        )


    print(
        "Previous latest frames cleared."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("HRRR REFL + UH PROGRESSIVE UPDATE")
    print("=" * 70)


    # ========================================================
    # FIND RUN
    # ========================================================

    run_time = (
        find_latest_hrrr()
    )


    max_fhr = get_max_fhr(
        run_time
    )


    print(
        f"Forecast range: "
        f"F000-F{max_fhr:03d}"
    )


    # ========================================================
    # RESET CURRENT LATEST PRODUCT
    # ========================================================

    clean_local_output()

    clear_old_s3_frames()


    hours_written = []


    # Publish empty manifest first so the site knows
    # a new cycle is currently being built.

    publish_manifest(
        run_time,
        max_fhr,
        hours_written,
        status="building"
    )


    # ========================================================
    # PROCESS FORECAST HOURS
    # ========================================================

    for fhr in range(
        0,
        max_fhr + 1
    ):

        try:

            (
                lon,
                lat,
                refl,
                uh

            ) = load_hour(
                run_time,
                fhr
            )


            (
                output_file,
                frame_info

            ) = plot_hour(
                run_time,
                fhr,
                lon,
                lat,
                refl,
                uh
            )


            # =================================================
            # UPLOAD FRAME IMMEDIATELY
            # =================================================

            upload_frame(
                output_file,
                fhr
            )


            # =================================================
            # BUILD + UPLOAD SAMPLING DATA
            # =================================================

            sample_file = publish_sample_grid(
                fhr,
                lon,
                lat,
                refl,
                uh
            )


            frame_info[
                "sample_file"
            ] = sample_file


            # =================================================
            # ADD HOUR TO MANIFEST
            # =================================================

            hours_written.append(
                frame_info
            )


            # =================================================
            # PUBLISH MANIFEST IMMEDIATELY
            # =================================================

            publish_manifest(
                run_time,
                max_fhr,
                hours_written,
                status="building"
            )


            print(
                f"F{fhr:03d} is now "
                f"available on the website."
            )


        except Exception as e:

            print()

            print(
                f"Skipping "
                f"F{fhr:03d}: "
                f"{e}"
            )


    # ========================================================
    # FINAL MANIFEST
    # ========================================================

    publish_manifest(
        run_time,
        max_fhr,
        hours_written,
        status="complete"
    )


    print()
    print("=" * 70)

    print(
        "HRRR UPDATE COMPLETE"
    )

    print(
        f"Frames available: "
        f"{len(hours_written)}"
    )

    print("=" * 70)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
