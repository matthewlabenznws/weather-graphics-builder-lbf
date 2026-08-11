# ============================================================
# HRRR COMPOSITE REFLECTIVITY + 2-5 KM UH
# PRODUCTION SCRIPT FOR MAPBOX / AWS
#
# Output:
#   output/hrrr/reflUH/latest/
#       f000.png
#       f001.png
#       ...
#       manifest.json
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import json
import os
import shutil
import warnings

from datetime import datetime, timedelta, timezone
from pathlib import Path

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

from herbie import Herbie


warnings.filterwarnings("ignore")


# ============================================================
# SETTINGS
# ============================================================

# ------------------------------------------------------------
# Geographic bounds
#
# These MUST match the image-source coordinates used
# by Mapbox.
# ------------------------------------------------------------

WEST = -105.5
EAST = -96.0
SOUTH = 38.5
NORTH = 44.5


# ------------------------------------------------------------
# Reflectivity
# ------------------------------------------------------------

MIN_REFL = 10.0

UPSCALE = 4

SMOOTH_SIGMA = 0.4


# ------------------------------------------------------------
# Updraft helicity
# ------------------------------------------------------------

UH_THRESHOLD = 75.0


# ------------------------------------------------------------
# Image
# ------------------------------------------------------------

FIG_WIDTH = 16
FIG_HEIGHT = 10
DPI = 150


# ------------------------------------------------------------
# Retry settings
# ------------------------------------------------------------

MAX_RUN_LOOKBACK = 10

DOWNLOAD_ATTEMPTS = 3


# ============================================================
# PATHS
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
# RADARSCOPE-STYLE REFLECTIVITY PALETTE
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


    # Extreme values
    (80.00, (173, 99, 64)),

    (85.00, (105, 0, 4)),

    (95.00, (0, 0, 0))

]


COLOR_MIN = -15.0
COLOR_MAX = 95.0


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
# FIND LATEST AVAILABLE HRRR RUN
# ============================================================

def find_latest_hrrr():

    now = datetime.now(timezone.utc)

    start = now.replace(
        minute=0,
        second=0,
        microsecond=0
    )


    print("=" * 70)
    print("SEARCHING FOR LATEST AVAILABLE HRRR RUN")
    print("=" * 70)


    for back in range(MAX_RUN_LOOKBACK + 1):

        run = start - timedelta(
            hours=back
        )


        print(
            f"Trying HRRR "
            f"{run:%Y%m%d %HZ} F000..."
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

                print()

                print(
                    f"Using HRRR run: "
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
# GET FIRST 2-D VARIABLE
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
        "Could not find a 2-D variable."
    )


# ============================================================
# LOAD A FORECAST HOUR
# ============================================================

def load_hour(
    run_time,
    fhr
):

    print()
    print("=" * 70)

    print(
        f"PROCESSING HRRR "
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
                preferred_names=[
                    "refc",
                    "refd",
                    "REFC"
                ]
            )


            # =================================================
            # 2-5 KM MAXIMUM UPDRAFT HELICITY
            #
            # NOAA inventory:
            #
            # MXUPHL
            # 5000-2000 m above ground
            # =================================================

            ds_uh = H.xarray(
                r":MXUPHL:5000-2000 m above ground:"
            )


            uh_da = get_2d_variable(
                ds_uh,
                preferred_names=[
                    "mxuphl",
                    "MXUPHL",
                    "unknown"
                ]
            )


            # =================================================
            # COORDINATES
            # =================================================

            lat = ds_refl[
                "latitude"
            ].values


            lon = ds_refl[
                "longitude"
            ].values


            refl = np.squeeze(
                refl_da.values
            ).astype(float)


            uh = np.squeeze(
                uh_da.values
            ).astype(float)


            print(
                f"Reflectivity max: "
                f"{np.nanmax(refl):.1f} dBZ"
            )


            print(
                f"2-5 km UH max: "
                f"{np.nanmax(uh):.1f} "
                f"m²/s²"
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


    raise RuntimeError(
        f"Failed F{fhr:03d}: "
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


    # --------------------------------------------------------
    # 4x cubic interpolation
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # Prevent cubic overshoot
    # --------------------------------------------------------

    refl_fine = np.clip(
        refl_fine,
        original_min,
        original_max
    )


    # --------------------------------------------------------
    # Light display smoothing
    # --------------------------------------------------------

    refl_fine = gaussian_filter(
        refl_fine,
        sigma=SMOOTH_SIGMA
    )


    refl_fine = np.clip(
        refl_fine,
        original_min,
        original_max
    )


    # --------------------------------------------------------
    # Mask below 10 dBZ
    # --------------------------------------------------------

    refl_plot = np.ma.masked_where(
        refl_fine < MIN_REFL,
        refl_fine
    )


    return (
        lon_fine,
        lat_fine,
        refl_fine,
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


    # --------------------------------------------------------
    # Use LINEAR interpolation for UH.
    #
    # We intentionally do not use cubic because we do not want
    # interpolation overshoot creating artificial >75 values.
    # --------------------------------------------------------

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
# PLOT FORECAST HOUR
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
        /
        f"f{fhr:03d}.png"
    )


    # ========================================================
    # REFLECTIVITY PROCESSING
    # ========================================================

    (
        lon_refl,
        lat_refl,
        refl_fine,
        refl_plot

    ) = process_reflectivity(
        lon,
        lat,
        refl
    )


    # ========================================================
    # UH PROCESSING
    # ========================================================

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
    # COMPOSITE REFLECTIVITY
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
    # 2-5 KM MAX UH >= 75
    #
    # Solid black fill + black outline.
    # ========================================================

    if np.nanmax(
        uh_fine
    ) >= UH_THRESHOLD:


        # ----------------------------------------------------
        # BLACK FILL
        # ----------------------------------------------------

        ax.contourf(
            lon_uh,
            lat_uh,
            uh_fine,

            levels=[
                UH_THRESHOLD,
                max(
                    1000,
                    np.nanmax(
                        uh_fine
                    )
                    + 1
                )
            ],

            colors=[
                "#000000"
            ],

            transform=ccrs.PlateCarree(),

            antialiased=True,

            zorder=5
        )


        # ----------------------------------------------------
        # BLACK OUTLINE
        # ----------------------------------------------------

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


    # ========================================================
    # REMOVE AXES
    # ========================================================

    ax.set_axis_off()


    # ========================================================
    # SAVE PNG
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


    print(
        f"Saved: "
        f"{output_file.name}"
    )


    valid_time = (
        run_time
        +
        timedelta(
            hours=fhr
        )
    )


    return {

        "fhr": fhr,

        "file": (
            f"f{fhr:03d}.png"
        ),

        "valid": (
            valid_time
            .strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        )

    }


# ============================================================
# CLEAN OLD OUTPUTS
# ============================================================

def clean_output_directory():

    print()
    print(
        "Cleaning old HRRR frames..."
    )


    for file in OUTPUT_DIR.glob(
        "f*.png"
    ):

        file.unlink()


    manifest = (
        OUTPUT_DIR
        /
        "manifest.json"
    )


    if manifest.exists():

        manifest.unlink()


# ============================================================
# WRITE MANIFEST
# ============================================================

def write_manifest(
    run_time,
    max_fhr,
    hours
):

    manifest = {

        "model": "HRRR",

        "product": "reflUH",

        "description":
            "Composite Reflectivity + 2-5 km UH >= 75",

        "run": (
            run_time
            .strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        ),

        "cycle": (
            run_time
            .strftime(
                "%HZ"
            )
        ),

        "max_fhr": max_fhr,

        "reflectivity_min_dbz":
            MIN_REFL,

        "uh_threshold":
            UH_THRESHOLD,

        "bounds": {

            "west": WEST,

            "east": EAST,

            "south": SOUTH,

            "north": NORTH

        },

        "hours":
            hours

    }


    output = (
        OUTPUT_DIR
        /
        "manifest.json"
    )


    with output.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            manifest,
            f,
            indent=2
        )


    print()

    print(
        f"Saved manifest: "
        f"{output}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)

    print(
        "HRRR REFL + UH UPDATE"
    )

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


    print()

    print(
        f"Forecast range: "
        f"F000-F{max_fhr:03d}"
    )


    # ========================================================
    # CLEAR PREVIOUS RUN
    # ========================================================

    clean_output_directory()


    # ========================================================
    # PROCESS HOURS
    # ========================================================

    hours_written = []


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


            frame_info = plot_hour(
                run_time,
                fhr,
                lon,
                lat,
                refl,
                uh
            )


            hours_written.append(
                frame_info
            )


        except Exception as e:

            print()

            print(
                f"Skipping F{fhr:03d}: "
                f"{e}"
            )


    # ========================================================
    # MANIFEST
    # ========================================================

    write_manifest(
        run_time,
        max_fhr,
        hours_written
    )


    print()
    print("=" * 70)

    print(
        "HRRR UPDATE FINISHED"
    )

    print(
        f"Frames written: "
        f"{len(hours_written)}"
    )

    print(
        f"Output directory: "
        f"{OUTPUT_DIR}"
    )

    print("=" * 70)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
