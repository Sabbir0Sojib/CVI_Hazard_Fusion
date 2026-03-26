"""
CVI-HazardFusion — Dynamic Risk Score Model
============================================
Computes the Dynamic Risk Score (DRS) for Bangladesh districts by fusing
the Climate Vulnerability Index (CVI) with multi-hazard satellite indicators
derived from Sentinel-1 (flood), MODIS (drought), and SRTM+CHIRPS (landslide).

Formula
-------
    DRS = CVI × (0.50 × Flood + 0.25 × Drought + 0.25 × Landslide)

All component inputs are MinMax-normalized to [0, 1] before fusion.
The output DRS is scaled to [0, 100] for interpretability.

Risk Classification
-------------------
    Critical  : DRS ≥ 75   — Immediate emergency response
    High      : DRS ≥ 50   — Pre-position resources
    Moderate  : DRS ≥ 25   — Enhanced monitoring
    Low       : DRS  < 25  — Routine operations

Authors
-------
    CVI-HazardFusion Contributors
    RIMES Regional Innovation Challenge 2026

Usage
-----
    from src.model import compute_drs
    results_gdf = compute_drs(union_gdf, ...)
"""

from __future__ import annotations

import logging
from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

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
# Constants
# ---------------------------------------------------------------------------
FLOOD_WEIGHT: float = 0.50
DROUGHT_WEIGHT: float = 0.25
LANDSLIDE_WEIGHT: float = 0.25

CRITICAL_THRESHOLD: float = 75.0
HIGH_THRESHOLD: float = 50.0
MODERATE_THRESHOLD: float = 25.0

RISK_LEVELS: list[str] = ["Critical", "High", "Moderate", "Low"]

RISK_COLORS: dict[str, str] = {
    "Critical": "#d62728",
    "High": "#ff7f0e",
    "Moderate": "#FFCC00",
    "Low": "#2ca02c",
}


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------
def compute_drs(
    union_gdf: gpd.GeoDataFrame,
    flood_col: str = "flood_mean",
    drought_col: str = "drought_mean",
    landslide_col: str = "landslide_mean",
    cvi_col: str = "cvi_proxy",
) -> gpd.GeoDataFrame:
    """Compute the Dynamic Risk Score (DRS) and classify risk level for each district.

    Applies MinMax normalization to all hazard components and the CVI, then
    computes the multiplicative DRS formula:

        DRS = CVI × (0.50 × Flood + 0.25 × Drought + 0.25 × Landslide)

    The output DRS is scaled to [0, 100].

    Args:
        union_gdf (gpd.GeoDataFrame): GeoDataFrame with one row per district,
            containing raw (un-normalized) hazard and CVI columns.
        flood_col (str): Column name for flood intensity (from Sentinel-1 SAR).
            Default: "flood_mean".
        drought_col (str): Column name for drought intensity (from MODIS NDVI deficit).
            Default: "drought_mean".
        landslide_col (str): Column name for landslide susceptibility (slope × rainfall).
            Default: "landslide_mean".
        cvi_col (str): Column name for proxy Climate Vulnerability Index.
            Default: "cvi_proxy".

    Returns:
        gpd.GeoDataFrame: Input GeoDataFrame augmented with the following columns:
            - ``flood_n`` (float): MinMax-normalized flood score [0, 1]
            - ``drought_n`` (float): MinMax-normalized drought score [0, 1]
            - ``landslide_n`` (float): MinMax-normalized landslide score [0, 1]
            - ``cvi_n`` (float): MinMax-normalized CVI score [0, 1]
            - ``compound_hazard`` (float): Weighted sum of normalized hazard scores [0, 1]
            - ``drs_score`` (float): Dynamic Risk Score scaled to [0, 100]
            - ``risk_level`` (str): One of "Critical", "High", "Moderate", "Low"

    Raises:
        KeyError: If any of the specified column names are not found in union_gdf.
        ValueError: If union_gdf is empty or contains fewer than 2 rows (normalization
            requires at least a min and max value).

    Example:
        >>> import geopandas as gpd
        >>> gdf = gpd.read_file("data/bangladesh_districts.geojson")
        >>> # Assume gdf already has flood_mean, drought_mean, landslide_mean, cvi_proxy
        >>> results = compute_drs(gdf)
        >>> print(results[["district", "drs_score", "risk_level"]].head())
          district  drs_score risk_level
        0   Dhaka      42.3   Moderate
        1   Sylhet     84.7   Critical
    """
    # -----------------------------------------------------------------------
    # Input validation
    # -----------------------------------------------------------------------
    required_cols = [flood_col, drought_col, landslide_col, cvi_col]
    missing = [c for c in required_cols if c not in union_gdf.columns]
    if missing:
        raise KeyError(
            f"The following required columns are missing from the GeoDataFrame: {missing}. "
            f"Available columns: {list(union_gdf.columns)}"
        )
    if len(union_gdf) < 2:
        raise ValueError(
            f"GeoDataFrame must contain at least 2 rows for MinMax normalization. "
            f"Got {len(union_gdf)} rows."
        )

    logger.info("Starting DRS computation for %d districts.", len(union_gdf))

    # -----------------------------------------------------------------------
    # Work on a copy to avoid mutating the input
    # -----------------------------------------------------------------------
    gdf = union_gdf.copy()

    # -----------------------------------------------------------------------
    # MinMax normalization
    # -----------------------------------------------------------------------
    scaler = MinMaxScaler(feature_range=(0, 1))
    cols_to_normalize = [flood_col, drought_col, landslide_col, cvi_col]
    normalized_array = scaler.fit_transform(gdf[cols_to_normalize].fillna(0).values)

    gdf["flood_n"] = normalized_array[:, 0]
    gdf["drought_n"] = normalized_array[:, 1]
    gdf["landslide_n"] = normalized_array[:, 2]
    gdf["cvi_n"] = normalized_array[:, 3]

    logger.info(
        "Normalization complete. Flood range: [%.3f, %.3f], Drought range: [%.3f, %.3f], "
        "Landslide range: [%.3f, %.3f], CVI range: [%.3f, %.3f].",
        gdf["flood_n"].min(), gdf["flood_n"].max(),
        gdf["drought_n"].min(), gdf["drought_n"].max(),
        gdf["landslide_n"].min(), gdf["landslide_n"].max(),
        gdf["cvi_n"].min(), gdf["cvi_n"].max(),
    )

    # -----------------------------------------------------------------------
    # Compound hazard score (weighted sum)
    # -----------------------------------------------------------------------
    gdf["compound_hazard"] = (
        FLOOD_WEIGHT * gdf["flood_n"]
        + DROUGHT_WEIGHT * gdf["drought_n"]
        + LANDSLIDE_WEIGHT * gdf["landslide_n"]
    )

    # -----------------------------------------------------------------------
    # DRS — multiplicative fusion, scaled to [0, 100]
    # -----------------------------------------------------------------------
    gdf["drs_score"] = (gdf["cvi_n"] * gdf["compound_hazard"] * 100).round(2)

    logger.info(
        "DRS computed. Mean=%.1f, Max=%.1f, Min=%.1f.",
        gdf["drs_score"].mean(),
        gdf["drs_score"].max(),
        gdf["drs_score"].min(),
    )

    # -----------------------------------------------------------------------
    # Risk classification
    # -----------------------------------------------------------------------
    gdf["risk_level"] = pd.cut(
        gdf["drs_score"],
        bins=[-np.inf, MODERATE_THRESHOLD, HIGH_THRESHOLD, CRITICAL_THRESHOLD, np.inf],
        labels=["Low", "Moderate", "High", "Critical"],
        right=False,
    ).astype(str)

    # Log classification summary
    counts = gdf["risk_level"].value_counts()
    for level in RISK_LEVELS:
        n = counts.get(level, 0)
        logger.info("  %s: %d districts", level, n)

    return gdf


# ---------------------------------------------------------------------------
# Validation function
# ---------------------------------------------------------------------------
def validate_results(gdf: gpd.GeoDataFrame) -> bool:
    """Check the integrity of DRS output columns.

    Verifies that:
    - All required output columns are present.
    - DRS scores are in the range [0, 100].
    - Risk levels contain only valid category strings.
    - No NaN values exist in output columns.
    - The district count matches the expected 64 for Bangladesh.

    Args:
        gdf (gpd.GeoDataFrame): Output GeoDataFrame from compute_drs().

    Returns:
        bool: True if all checks pass, False if any check fails (with logged warnings).
    """
    passed = True
    required_output_cols = [
        "flood_n", "drought_n", "landslide_n", "cvi_n",
        "compound_hazard", "drs_score", "risk_level",
    ]

    logger.info("Running output validation checks...")

    # Check required columns
    missing = [c for c in required_output_cols if c not in gdf.columns]
    if missing:
        logger.warning("FAIL: Missing output columns: %s", missing)
        passed = False
    else:
        logger.info("PASS: All required output columns present.")

    # Check DRS range
    if "drs_score" in gdf.columns:
        out_of_range = gdf["drs_score"].dropna()
        out_of_range = out_of_range[(out_of_range < 0) | (out_of_range > 100)]
        if len(out_of_range) > 0:
            logger.warning(
                "FAIL: %d DRS scores are outside [0, 100]: %s",
                len(out_of_range),
                out_of_range.values,
            )
            passed = False
        else:
            logger.info("PASS: All DRS scores in [0, 100].")

    # Check risk level categories
    if "risk_level" in gdf.columns:
        invalid = ~gdf["risk_level"].isin(RISK_LEVELS)
        if invalid.any():
            logger.warning(
                "FAIL: Invalid risk_level values: %s",
                gdf.loc[invalid, "risk_level"].unique(),
            )
            passed = False
        else:
            logger.info("PASS: All risk_level values are valid.")

    # Check NaN values
    for col in required_output_cols:
        if col in gdf.columns and gdf[col].isna().any():
            logger.warning("FAIL: Column '%s' contains NaN values.", col)
            passed = False

    # Check district count
    if len(gdf) != 64:
        logger.warning(
            "WARN: Expected 64 districts for Bangladesh, got %d.", len(gdf)
        )

    if passed:
        logger.info("All validation checks passed.")
    else:
        logger.warning("One or more validation checks failed. Review logs above.")

    return passed


# ---------------------------------------------------------------------------
# Demo / __main__ block
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json
    import os

    logger.info("Running CVI-HazardFusion model demo with synthetic data...")

    # Generate 64 synthetic districts with random hazard and CVI values
    np.random.seed(42)
    n = 64
    synthetic_data = {
        "district": [f"District_{i:02d}" for i in range(1, n + 1)],
        "flood_mean": np.random.uniform(0.01, 0.85, n),
        "drought_mean": np.random.uniform(0.0, 0.6, n),
        "landslide_mean": np.random.uniform(0.0, 0.4, n),
        "cvi_proxy": np.random.uniform(0.1, 0.9, n),
        "geometry": gpd.points_from_xy(
            np.random.uniform(88.0, 92.7, n),   # Bangladesh lon range
            np.random.uniform(20.5, 26.7, n),   # Bangladesh lat range
        ),
    }

    demo_gdf = gpd.GeoDataFrame(synthetic_data, crs="EPSG:4326")

    # Compute DRS
    results = compute_drs(demo_gdf)

    # Validate
    validate_results(results)

    # Display top 10 highest-risk districts
    top10 = results.nlargest(10, "drs_score")[
        ["district", "drs_score", "risk_level", "flood_n", "drought_n", "landslide_n", "cvi_n"]
    ]
    print("\nTop 10 Highest-Risk Districts (Synthetic Demo):")
    print(top10.to_string(index=False))

    # Save to CSV
    os.makedirs("outputs", exist_ok=True)
    results[["district", "drs_score", "risk_level", "flood_n", "drought_n", "landslide_n", "cvi_n"]].to_csv(
        "outputs/drs_results_demo.csv", index=False
    )
    logger.info("Demo results written to outputs/drs_results_demo.csv")
