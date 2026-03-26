"""
CVI-HazardFusion — Google Earth Engine Data Ingestion
======================================================
Provides functions for authenticating with Google Earth Engine and fetching
district-level satellite hazard indicators for Bangladesh.

Each function returns an ee.FeatureCollection containing district polygons
annotated with zonal mean statistics for the relevant satellite variable.

Data Sources
------------
    Flood       : Sentinel-1 SAR GRD (COPERNICUS/S1_GRD)
                  VV backscatter anomaly vs. 5-year calendar-month median
    Drought     : MODIS Terra MOD13A1 (MODIS/061/MOD13A1)
                  NDVI deficit vs. 5-year calendar-week baseline
    Landslide   : SRTM (USGS/SRTMGL1_003) × CHIRPS (UCSB-CHG/CHIRPS/DAILY)
                  Slope angle (°) × 30-day cumulative rainfall (mm)
    CVI Proxy   : WorldPop (WorldPop/GP/100m/pop)
                  + Inverse VIIRS Nighttime Lights (NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG)
                  + JRC Historical Flood Frequency (JRC/GSW1_4/GlobalSurfaceWater)

Pipeline Integration
--------------------
    This module is called by src/model.py and the Makefile `make risk-score` target.
    Typical usage:

        from src.ingest import authenticate_gee, get_sentinel1_flood, ...
        authenticate_gee()
        district_fc = ee.FeatureCollection("FAO/GAUL/2015/level2").filter(
            ee.Filter.eq("ADM0_NAME", "Bangladesh")
        )
        flood_fc = get_sentinel1_flood(district_fc, "2026-02-23", "2026-03-25")

Authors
-------
    CVI-HazardFusion Contributors
    RIMES Regional Innovation Challenge 2026
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try importing Earth Engine SDK
# ---------------------------------------------------------------------------
try:
    import ee  # type: ignore
    _EE_AVAILABLE = True
except ImportError:
    _EE_AVAILABLE = False
    logger.warning(
        "earthengine-api is not installed. Install with: pip install earthengine-api==0.1.390"
    )

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FLOOD_THRESHOLD_DB: float = -3.5       # dB anomaly for flood detection (Wagner et al. 2026)
NDVI_SCALE: float = 0.0001             # MODIS NDVI scale factor
BASELINE_START_YEAR: int = 2019        # 5-year climatological baseline start
BASELINE_END_YEAR: int = 2023          # 5-year climatological baseline end
ZONAL_SCALE: int = 500                 # meters — native GEE zonal statistics resolution
MAX_PIXELS: int = 1_000_000_000        # maxPixels for GEE reduceRegions


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
def authenticate_gee(project: Optional[str] = None) -> None:
    """Authenticate and initialize the Google Earth Engine Python API.

    Calls ee.Authenticate() if credentials do not exist, then ee.Initialize().
    For non-interactive environments (e.g., CI/CD), ensure credentials are
    pre-configured via `earthengine authenticate` CLI or service account JSON.

    Args:
        project (Optional[str]): GEE Cloud project ID. If None, uses the
            default project configured during authentication.

    Raises:
        ImportError: If the earthengine-api package is not installed.
        ee.EEException: If authentication or initialization fails.

    Example:
        >>> authenticate_gee(project="my-gee-project-id")
    """
    if not _EE_AVAILABLE:
        raise ImportError(
            "earthengine-api is required. Install with: pip install earthengine-api==0.1.390"
        )

    logger.info("Authenticating with Google Earth Engine...")
    try:
        ee.Initialize(project=project)
        logger.info("GEE initialized successfully (project=%s).", project or "default")
    except Exception:
        logger.info("No existing credentials found. Running interactive authentication...")
        ee.Authenticate()
        ee.Initialize(project=project)
        logger.info("GEE authenticated and initialized (project=%s).", project or "default")


# ---------------------------------------------------------------------------
# Sentinel-1 Flood Detection
# ---------------------------------------------------------------------------
def get_sentinel1_flood(
    district_fc: "ee.FeatureCollection",
    start_date: str,
    end_date: str,
    polarization: str = "VV",
    flood_threshold_db: float = FLOOD_THRESHOLD_DB,
) -> "ee.FeatureCollection":
    """Compute district-level Sentinel-1 SAR flood fraction.

    For each district, computes the fraction of pixels classified as flooded
    based on the VV backscatter anomaly versus a 5-year (2019–2023)
    calendar-month median composite. A pixel is classified as flooded if:

        backscatter_current − backscatter_5yr_median < flood_threshold_db

    This method follows Wagner et al. (2026), who demonstrate >92% accuracy
    for C-band SAR open water detection over South Asian floodplains using a
    −3.5 dB anomaly threshold.

    Args:
        district_fc (ee.FeatureCollection): GEE FeatureCollection of Bangladesh
            district polygons (e.g., from FAO/GAUL or custom boundary asset).
        start_date (str): Analysis window start date in "YYYY-MM-DD" format.
        end_date (str): Analysis window end date in "YYYY-MM-DD" format.
        polarization (str): SAR polarization band to use. Default: "VV".
            "VH" may be used as an alternative in vegetated areas.
        flood_threshold_db (float): Backscatter anomaly threshold (dB) below
            which a pixel is classified as flooded. Default: -3.5.

    Returns:
        ee.FeatureCollection: Input district_fc with an added property
            ``flood_mean`` (float, range [0, 1]) representing the fraction of
            district pixels classified as flooded during the analysis window.

    Example:
        >>> district_fc = ee.FeatureCollection("FAO/GAUL/2015/level2").filter(
        ...     ee.Filter.eq("ADM0_NAME", "Bangladesh")
        ... )
        >>> flood_fc = get_sentinel1_flood(district_fc, "2026-02-23", "2026-03-25")
    """
    logger.info(
        "Fetching Sentinel-1 flood data: %s to %s (threshold=%.1f dB, band=%s).",
        start_date, end_date, flood_threshold_db, polarization,
    )

    s1 = ee.ImageCollection("COPERNICUS/S1_GRD") \
        .filter(ee.Filter.eq("instrumentMode", "IW")) \
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", polarization)) \
        .filter(ee.Filter.eq("orbitProperties_pass", "DESCENDING")) \
        .select(polarization)

    # Current period composite (mean of all S1 images in analysis window)
    current = s1.filterDate(start_date, end_date).mean()

    # Build 5-year baseline: same calendar months, years 2019–2023
    start_month = ee.Date(start_date).get("month")
    end_month = ee.Date(end_date).get("month")

    def _get_baseline_image(year: int) -> "ee.Image":
        baseline_start = ee.Date.fromYMD(year, start_month, 1)
        baseline_end = baseline_start.advance(
            ee.Date(end_date).difference(ee.Date(start_date), "day"), "day"
        )
        return s1.filterDate(baseline_start, baseline_end).mean()

    baseline_images = ee.ImageCollection([
        _get_baseline_image(y) for y in range(BASELINE_START_YEAR, BASELINE_END_YEAR + 1)
    ])
    baseline_median = baseline_images.median()

    # Backscatter anomaly and flood mask
    anomaly = current.subtract(baseline_median)
    flood_mask = anomaly.lt(flood_threshold_db).rename("flood_mask")

    # Zonal statistics: mean flood fraction per district
    flood_fc = flood_mask.reduceRegions(
        collection=district_fc,
        reducer=ee.Reducer.mean(),
        scale=ZONAL_SCALE,
        crs="EPSG:4326",
    ).map(lambda f: f.set("flood_mean", f.get("mean")))

    logger.info("Sentinel-1 flood zonal statistics computed.")
    return flood_fc


# ---------------------------------------------------------------------------
# MODIS Drought Detection
# ---------------------------------------------------------------------------
def get_modis_drought(
    district_fc: "ee.FeatureCollection",
    start_date: str,
    end_date: str,
) -> "ee.FeatureCollection":
    """Compute district-level MODIS NDVI drought deficit.

    Computes the mean NDVI deficit relative to a 5-year (2019–2023)
    calendar-week baseline. Positive deficit values indicate vegetation
    stress (drought). Negative values (greener than baseline) are clipped
    to zero.

    Args:
        district_fc (ee.FeatureCollection): GEE FeatureCollection of Bangladesh
            district polygons.
        start_date (str): Analysis window start date in "YYYY-MM-DD" format.
        end_date (str): Analysis window end date in "YYYY-MM-DD" format.

    Returns:
        ee.FeatureCollection: Input district_fc with an added property
            ``drought_mean`` (float, ≥ 0) representing mean NDVI deficit.
            Higher values indicate greater drought stress.

    Example:
        >>> drought_fc = get_modis_drought(district_fc, "2026-02-23", "2026-03-25")
    """
    logger.info("Fetching MODIS NDVI drought data: %s to %s.", start_date, end_date)

    modis = ee.ImageCollection("MODIS/061/MOD13A1").select("NDVI")

    # Current NDVI (scaled)
    current_ndvi = modis.filterDate(start_date, end_date).mean().multiply(NDVI_SCALE)

    # 5-year baseline NDVI (same DOY range)
    start_doy = ee.Date(start_date).getRelative("day", "year")
    end_doy = ee.Date(end_date).getRelative("day", "year")

    def _get_baseline_ndvi(year: int) -> "ee.Image":
        year_start = ee.Date.fromYMD(year, 1, 1).advance(start_doy, "day")
        year_end = ee.Date.fromYMD(year, 1, 1).advance(end_doy, "day")
        return modis.filterDate(year_start, year_end).mean().multiply(NDVI_SCALE)

    baseline_ndvi = ee.ImageCollection([
        _get_baseline_ndvi(y) for y in range(BASELINE_START_YEAR, BASELINE_END_YEAR + 1)
    ]).mean()

    # NDVI deficit: positive = drought stress; clip negative to 0
    ndvi_deficit = baseline_ndvi.subtract(current_ndvi).max(ee.Image(0)).rename("ndvi_deficit")

    # Zonal statistics
    drought_fc = ndvi_deficit.reduceRegions(
        collection=district_fc,
        reducer=ee.Reducer.mean(),
        scale=ZONAL_SCALE,
        crs="EPSG:4326",
    ).map(lambda f: f.set("drought_mean", f.get("mean")))

    logger.info("MODIS drought zonal statistics computed.")
    return drought_fc


# ---------------------------------------------------------------------------
# Landslide Susceptibility (SRTM × CHIRPS)
# ---------------------------------------------------------------------------
def get_landslide_proxy(
    district_fc: "ee.FeatureCollection",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> "ee.FeatureCollection":
    """Compute district-level landslide susceptibility proxy.

    Combines SRTM slope angle (°) with 30-day cumulative CHIRPS rainfall (mm)
    to produce a dimensionless landslide susceptibility index:

        Landslide_raw = slope_degrees × rainfall_30day_mm

    This approach is consistent with the rainfall-triggered landslide
    susceptibility framework validated for the Chittagong Hill Tracts by
    Sultana & Tan (2021).

    Args:
        district_fc (ee.FeatureCollection): GEE FeatureCollection of Bangladesh
            district polygons.
        start_date (Optional[str]): Start of the 30-day rainfall window
            ("YYYY-MM-DD"). If None, defaults to 30 days before today.
        end_date (Optional[str]): End of the rainfall window ("YYYY-MM-DD").
            If None, defaults to today.

    Returns:
        ee.FeatureCollection: Input district_fc with an added property
            ``landslide_mean`` (float, ≥ 0) representing mean landslide
            susceptibility. Higher values indicate greater susceptibility.

    Example:
        >>> landslide_fc = get_landslide_proxy(district_fc, "2026-02-23", "2026-03-25")
    """
    if end_date is None:
        end_date = datetime.utcnow().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")

    logger.info(
        "Computing landslide susceptibility proxy: SRTM slope × CHIRPS rainfall (%s to %s).",
        start_date, end_date,
    )

    # SRTM slope
    srtm = ee.Image("USGS/SRTMGL1_003")
    slope = ee.Terrain.slope(srtm)  # degrees

    # CHIRPS 30-day cumulative rainfall
    chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY") \
        .filterDate(start_date, end_date) \
        .sum() \
        .rename("rainfall_30day")

    # Landslide proxy: slope × rainfall
    landslide_proxy = slope.multiply(chirps).rename("landslide_proxy")

    # Zonal statistics
    landslide_fc = landslide_proxy.reduceRegions(
        collection=district_fc,
        reducer=ee.Reducer.mean(),
        scale=ZONAL_SCALE,
        crs="EPSG:4326",
    ).map(lambda f: f.set("landslide_mean", f.get("mean")))

    logger.info("Landslide susceptibility zonal statistics computed.")
    return landslide_fc


# ---------------------------------------------------------------------------
# Proxy CVI (WorldPop + VIIRS + JRC)
# ---------------------------------------------------------------------------
def get_proxy_cvi(
    district_fc: "ee.FeatureCollection",
    pop_weight: float = 0.35,
    poverty_weight: float = 0.35,
    flood_freq_weight: float = 0.30,
) -> "ee.FeatureCollection":
    """Compute district-level proxy Climate Vulnerability Index (CVI).

    Combines three freely available satellite/census datasets as proxies for
    the three UNDP LoGIC CVI pillars:

        CVI_proxy = 0.35 × Pop_norm + 0.35 × (1 − NTL_norm) + 0.30 × FloodFreq_norm

    Pillar mapping:
        - Exposure        → WorldPop 2020 population density
        - Sensitivity     → Inverse VIIRS nighttime light intensity (poverty proxy)
        - Adaptive Cap.   → JRC historical flood occurrence frequency

    Note: Component normalization (MinMax) is applied locally in src/model.py,
    not in this GEE function, so raw zonal means are returned.

    Args:
        district_fc (ee.FeatureCollection): GEE FeatureCollection of Bangladesh
            district polygons.
        pop_weight (float): Weight for population exposure component. Default: 0.35.
        poverty_weight (float): Weight for poverty proxy (inverse NTL). Default: 0.35.
        flood_freq_weight (float): Weight for historical flood frequency. Default: 0.30.

    Returns:
        ee.FeatureCollection: Input district_fc with added properties:
            - ``pop_mean`` (float): Mean population density (persons/pixel)
            - ``ntl_mean`` (float): Mean VIIRS nighttime light radiance
            - ``flood_freq_mean`` (float): Mean JRC occurrence fraction [0, 100]
            - ``cvi_proxy`` (float): Placeholder for post-normalization fusion
              (set to 0.0; actual fusion happens in model.py after normalization)

    Example:
        >>> cvi_fc = get_proxy_cvi(district_fc)
    """
    logger.info("Computing proxy CVI (WorldPop + VIIRS + JRC)...")

    # WorldPop 2020 population
    worldpop = ee.ImageCollection("WorldPop/GP/100m/pop") \
        .filter(ee.Filter.eq("year", 2020)) \
        .filter(ee.Filter.eq("country", "BGD")) \
        .first() \
        .select("population")

    # VIIRS Nighttime Lights (latest available month)
    viirs = ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG") \
        .sort("system:time_start", False) \
        .first() \
        .select("avg_rad")

    # JRC Global Surface Water — occurrence band (% of time water is present)
    jrc = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence")

    # Zonal statistics for each component
    pop_fc = worldpop.reduceRegions(
        collection=district_fc,
        reducer=ee.Reducer.mean(),
        scale=100,
        crs="EPSG:4326",
    ).map(lambda f: f.set("pop_mean", f.get("mean")))

    ntl_fc = viirs.reduceRegions(
        collection=pop_fc,
        reducer=ee.Reducer.mean(),
        scale=500,
        crs="EPSG:4326",
    ).map(lambda f: f.set("ntl_mean", f.get("mean")))

    flood_freq_fc = jrc.reduceRegions(
        collection=ntl_fc,
        reducer=ee.Reducer.mean(),
        scale=30,
        crs="EPSG:4326",
    ).map(lambda f: f.set("flood_freq_mean", f.get("mean")))

    # Add a placeholder cvi_proxy column (actual computation in model.py)
    cvi_fc = flood_freq_fc.map(lambda f: f.set("cvi_proxy", 0.0))

    logger.info("Proxy CVI zonal statistics computed (WorldPop + VIIRS + JRC).")
    return cvi_fc


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------
def run_ingestion_pipeline(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    gee_project: Optional[str] = None,
) -> dict:
    """Run the full GEE ingestion pipeline and return district-level data as a dict.

    This function orchestrates authenticate_gee(), get_sentinel1_flood(),
    get_modis_drought(), get_landslide_proxy(), and get_proxy_cvi() into a
    single call, returning a Python dictionary suitable for constructing a
    pandas DataFrame.

    Args:
        start_date (Optional[str]): Analysis window start ("YYYY-MM-DD").
            Defaults to 30 days before today.
        end_date (Optional[str]): Analysis window end ("YYYY-MM-DD").
            Defaults to today.
        gee_project (Optional[str]): GEE Cloud project ID.

    Returns:
        dict: Keys are column names; values are lists of per-district values.
            Includes: district_name, flood_mean, drought_mean,
            landslide_mean, pop_mean, ntl_mean, flood_freq_mean.

    Example:
        >>> data = run_ingestion_pipeline("2026-02-23", "2026-03-25")
        >>> import pandas as pd
        >>> df = pd.DataFrame(data)
    """
    if end_date is None:
        end_date = datetime.utcnow().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")

    authenticate_gee(project=gee_project)

    logger.info("Loading Bangladesh district boundaries from FAO/GAUL...")
    district_fc = ee.FeatureCollection("FAO/GAUL/2015/level2").filter(
        ee.Filter.eq("ADM0_NAME", "Bangladesh")
    )
    logger.info("Boundary collection loaded.")

    # Run each ingestion function
    flood_fc = get_sentinel1_flood(district_fc, start_date, end_date)
    drought_fc = get_modis_drought(district_fc, start_date, end_date)
    landslide_fc = get_landslide_proxy(district_fc, start_date, end_date)
    cvi_fc = get_proxy_cvi(district_fc)

    logger.info("Merging district-level results...")

    # Extract to Python (triggers GEE computation)
    flood_info = flood_fc.getInfo()
    drought_info = drought_fc.getInfo()
    landslide_info = landslide_fc.getInfo()
    cvi_info = cvi_fc.getInfo()

    def _extract(fc_info: dict, col: str) -> dict:
        return {
            f["properties"].get("ADM2_NAME", f["properties"].get("district", f"District_{i}")):
            f["properties"].get(col, 0.0)
            for i, f in enumerate(fc_info["features"])
        }

    flood_by_district = _extract(flood_info, "flood_mean")
    drought_by_district = _extract(drought_info, "drought_mean")
    landslide_by_district = _extract(landslide_info, "landslide_mean")
    pop_by_district = _extract(cvi_info, "pop_mean")
    ntl_by_district = _extract(cvi_info, "ntl_mean")
    flood_freq_by_district = _extract(cvi_info, "flood_freq_mean")

    districts = list(flood_by_district.keys())
    result = {
        "district": districts,
        "flood_mean": [flood_by_district[d] for d in districts],
        "drought_mean": [drought_by_district.get(d, 0.0) for d in districts],
        "landslide_mean": [landslide_by_district.get(d, 0.0) for d in districts],
        "pop_mean": [pop_by_district.get(d, 0.0) for d in districts],
        "ntl_mean": [ntl_by_district.get(d, 0.0) for d in districts],
        "flood_freq_mean": [flood_freq_by_district.get(d, 0.0) for d in districts],
    }

    logger.info(
        "Ingestion complete. %d districts retrieved for window %s – %s.",
        len(districts), start_date, end_date,
    )
    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json
    import os

    logger.info("Running CVI-HazardFusion ingestion pipeline (last 30 days)...")

    data = run_ingestion_pipeline()

    os.makedirs("outputs", exist_ok=True)
    out_path = "outputs/ingested_data.json"
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)

    logger.info("Ingested data written to %s", out_path)
    logger.info("Districts retrieved: %d", len(data["district"]))
