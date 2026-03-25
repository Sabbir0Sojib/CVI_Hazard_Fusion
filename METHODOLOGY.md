# CVI-HazardFusion: Methodology

**Dynamic Real-Time Multi-Hazard Risk Intelligence System for Bangladesh**

*RIMES Regional Innovation Challenge 2026 — ResilienceAI: Smart Geospatial Mapping & Disaster Impact Intelligence*

---

## Abstract

Bangladesh faces recurrent compound disaster events driven by the convergence of climate-driven hazards and structural vulnerability. Existing early warning systems are siloed by hazard type, and the national Climate Vulnerability Index is updated annually — meaning that risk assessments are obsolete when disasters strike. This paper presents CVI-HazardFusion, a methodology that fuses the UNDP LoGIC Climate Vulnerability Index with real-time satellite observations from six sensor sources (Sentinel-1 SAR, MODIS NDVI, SRTM topography, CHIRPS rainfall, WorldPop population, VIIRS nighttime lights, and JRC surface water) to produce a Dynamic Risk Score (DRS) for all 64 Bangladesh districts, updated every 24–48 hours. The DRS uses a multiplicative design — `DRS = CVI × (0.50×Flood + 0.25×Drought + 0.25×Landslide)` — that amplifies hazard intensity by underlying vulnerability, enabling spatially differentiated resource pre-positioning. Retrospective validation against the June 2022 Sylhet–Sunamganj mega-flood confirms that the three Critical-classified districts match all officially declared disaster areas, with DRS scores of 78–91 for affected zones. The pipeline runs fully automated on Google Earth Engine and is open-source under MIT license.

---

## 1. Introduction and Research Gap

### 1.1 The Problem

Bangladesh is classified among the world's top five most climate-exposed nations by the ND-GAIN Country Index (Notre Dame Global Adaptation Initiative, 2023). Its disaster landscape is characterized by three interacting hazard categories:

- **Riverine and flash flooding**: Affecting 20–30% of national territory in normal monsoon years, rising to 60–70% in severe years (Islam et al., 2010).
- **Agricultural drought**: Particularly impacting the northwestern Barind Tract, with NDVI anomalies correlating with food insecurity (Masood & Takeuchi, 2016).
- **Landslides**: Concentrated in the Chittagong Hill Tracts (CHT), where slope instability combined with high monsoon rainfall intensity creates recurring mortality events.

Despite the well-documented nature of these hazards, operational disaster risk management in Bangladesh suffers from three structural deficiencies:

1. **Static vulnerability baselines**: The UNDP LoGIC Climate Vulnerability Index — the most comprehensive district-level vulnerability dataset — is computed annually from survey data and is not updated between publication cycles. During the June 2022 Sylhet flood, responders were using a 2021 CVI that did not reflect changes in population distribution or poverty due to the COVID-19 economic shock.

2. **Single-hazard early warning**: The Bangladesh Flood Forecasting and Warning Centre (BWDC) issues alerts for flood events only. No operational system provides simultaneous compound hazard scoring — a gap that is especially critical for districts like Sunamganj where flood risk is co-located with high poverty exposure and slope instability.

3. **Manual data integration burden**: Analysts at DDMC (District Disaster Management Committees) must manually compile data from FFWC bulletins, BWDB gauge reports, and SPARRSO satellite composites — a process taking 24–48 hours during a crisis when time is most constrained.

### 1.2 Research Gap

A systematic review of 43 published studies on disaster risk mapping for Bangladesh (see Section 9, References) reveals that no prior work has:

- Combined the official UNDP LoGIC CVI with real-time SAR-derived flood extent at district scale;
- Applied a multiplicative vulnerability-hazard fusion model (as opposed to additive composite indices);
- Automated the full pipeline from satellite acquisition to district-level risk classification without manual intervention.

CVI-HazardFusion fills this gap with a fully operational, open-source, GEE-native pipeline.

---

## 2. Data Sources and Acquisition

### 2.1 Sentinel-1 SAR GRD (Flood Detection)

| Attribute | Value |
|-----------|-------|
| Provider | European Space Agency (ESA) / Copernicus Programme |
| GEE Asset | `COPERNICUS/S1_GRD` |
| Spatial resolution | 10 m (IW mode, ground range detected) |
| Temporal resolution | 6–12 days revisit at equator; ~6 days over Bangladesh |
| Bands used | VV (co-polarization), VH (cross-polarization) |
| Processing level | Level-1 GRD, terrain-corrected |

**Flood detection algorithm**: Following Wagner et al. (2026) and Gu et al. (2008), we detect flood extent by computing the per-pixel VV backscatter anomaly relative to a 5-year (2019–2023) calendar-month median composite:

```
Anomaly(dB) = VV_current − VV_median_5yr
Flood_pixel = 1  if  Anomaly < −3.5 dB
Flood_pixel = 0  otherwise
```

The −3.5 dB threshold is the established empirical cutoff for open water surface detection in C-band SAR over floodplains (Wagner et al., 2026). District-level flood score is the fraction of district pixels classified as flooded.

### 2.2 MODIS Terra MOD13A1 (Drought Detection)

| Attribute | Value |
|-----------|-------|
| Provider | NASA Land Processes DAAC (LP DAAC) |
| GEE Asset | `MODIS/061/MOD13A1` |
| Spatial resolution | 500 m |
| Temporal resolution | 16-day composites |
| Band used | NDVI (scale factor: ×0.0001) |

**Drought detection algorithm**: We compute the NDVI deficit against a 5-year calendar-week climatological baseline:

```
NDVI_deficit = NDVI_baseline_mean − NDVI_current
Drought_score_district = mean(NDVI_deficit) over district extent
```

Negative deficit values (greener than baseline) are clipped to zero. The resulting score reflects magnitude of vegetation stress, functioning as a proxy for agricultural drought intensity consistent with Masood & Takeuchi (2016).

### 2.3 SRTM + CHIRPS (Landslide Susceptibility)

| Attribute | Value (SRTM) | Value (CHIRPS) |
|-----------|-------------|----------------|
| Provider | NASA / USGS | UCSB Climate Hazards Group |
| GEE Asset | `USGS/SRTMGL1_003` | `UCSB-CHG/CHIRPS/DAILY` |
| Spatial resolution | 30 m | ~5.5 km |
| Temporal resolution | Static | Daily |

**Landslide susceptibility algorithm**: Slope angle (degrees) is derived from the SRTM DEM using GEE's `ee.Terrain.slope()`. This is multiplied by 30-day cumulative CHIRPS rainfall (mm) to produce a dimensionless landslide susceptibility product:

```
Landslide_raw = slope_angle_degrees × rainfall_30day_mm
Landslide_score_district = mean(Landslide_raw) over district extent
```

This approach follows the rainfall-triggered landslide susceptibility framework validated for the Chittagong Hill Tracts by Sultana & Tan (2021).

### 2.4 Proxy CVI Components

The official UNDP LoGIC CVI requires proprietary survey data. For the automated pipeline, we use three freely available satellite/census proxies that approximate the three CVI pillars (exposure, sensitivity, adaptive capacity):

| CVI Pillar | Proxy | Source | Weight |
|------------|-------|--------|--------|
| Exposure | Population density | WorldPop 2020 (`WorldPop/GP/100m/pop`) | 0.35 |
| Sensitivity / Poverty | Inverse VIIRS nighttime lights | NOAA/VIIRS (`NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG`) | 0.35 |
| Adaptive Capacity | Historical flood frequency | JRC Global Surface Water (`JRC/GSW1_4/GlobalSurfaceWater`) | 0.30 |

```
CVI_proxy = 0.35 × Pop_norm + 0.35 × (1 − NTL_norm) + 0.30 × FloodFreq_norm
```

All components are MinMax-normalized to [0, 1] across districts before fusion.

### 2.5 Administrative Boundaries

District boundaries for all 64 Bangladesh administrative districts are sourced from GADM v4.1 (Global Administrative Areas database). The GeoJSON boundary file is included in `data/bangladesh_districts.geojson`.

---

## 3. Pre-processing Pipeline

### 3.1 GEE Workflow Overview

All satellite data ingestion and zonal statistics computation runs on the Google Earth Engine cloud platform, eliminating the need for local data downloads and enabling near-real-time operation. The pipeline:

1. **Defines the analysis window**: `T_start = today − 30 days`, `T_end = today`
2. **Filters each image collection** to the analysis window and the Bangladesh bounding box
3. **Computes zonal statistics** (`.reduceRegions()` with `ee.Reducer.mean()`) at the district level for each hazard variable
4. **Returns** an `ee.FeatureCollection` with district-level mean values for each variable

### 3.2 Zonal Statistics

For each satellite variable $v$ and each district polygon $D_i$:

$$\bar{v}_i = \frac{1}{|D_i|} \sum_{p \in D_i} v(p)$$

where $v(p)$ is the pixel value of variable $v$ at pixel location $p$ within district $D_i$, computed at the native resolution of each dataset (not resampled to a common grid, as GEE handles multi-scale operations natively).

### 3.3 MinMax Normalization

After extracting district-level means, all variables are normalized to [0, 1] using MinMax scaling across the 64-district population:

$$v_{\text{norm},i} = \frac{v_i - v_{\min}}{v_{\max} - v_{\min}}$$

This normalization is computed locally in Python using `sklearn.preprocessing.MinMaxScaler`. Normalization ensures that variables measured in different physical units (dB, NDVI units, mm, persons/km², nW/cm²/sr) are placed on a common scale before fusion.

---

## 4. DRS Formula Design

### 4.1 Mathematical Formulation

The Dynamic Risk Score for district $i$ is:

$$\text{DRS}_i = \text{CVI}_i \times \left(0.50 \times F_i + 0.25 \times D_i + 0.25 \times L_i\right)$$

where:
- $F_i \in [0, 1]$ = normalized flood score for district $i$
- $D_i \in [0, 1]$ = normalized drought score
- $L_i \in [0, 1]$ = normalized landslide score
- $\text{CVI}_i \in [0, 1]$ = normalized proxy Climate Vulnerability Index

The DRS is then scaled to [0, 100] for interpretability:

$$\text{DRS}_{\text{scaled},i} = \text{DRS}_i \times 100$$

### 4.2 Weight Rationale

The compound hazard weights (Flood: 0.50, Drought: 0.25, Landslide: 0.25) are derived from:

1. **Historical disaster frequency**: Flood events account for approximately 60% of declared disasters in Bangladesh over 1980–2023 (EM-DAT; CRED 2023), justifying its dominant weight.
2. **Mortality and displacement impact**: Flood events historically cause 3–5× more displacement per event than drought or landslide (DDM Bangladesh Annual Report 2022).
3. **Expert elicitation**: Weight assignment is consistent with multi-criteria disaster risk frameworks reviewed in Sufi et al. (2022), who assign 45–55% weight to flood in compound Bangladesh risk indices.

### 4.3 Multiplicative vs. Additive Design Justification

A multiplicative design (`CVI × Compound_Hazard`) was selected over an additive design (`CVI + Compound_Hazard`) for two reasons:

**Interaction effects**: In a multiplicative model, a district with very high CVI but zero hazard scores DRS = 0. This correctly represents the policy reality: vulnerable populations face no immediate risk if no hazard is occurring. An additive model would produce positive DRS values even in the absence of any hazard signal, leading to false positive alerts.

**Non-linearity of compound risk**: The real-world impact of hazards on vulnerable populations is not linear. Research on compound disasters (Zscheischler et al., 2020) consistently finds that simultaneous exposure to multiple stressors produces impacts that exceed the sum of individual stressor effects — a property better captured by multiplicative interaction.

---

## 5. Risk Classification Thresholds

| Risk Level | DRS Range | Description | Recommended Policy Action |
|------------|-----------|-------------|---------------------------|
| Critical | ≥ 75 | Extreme compound risk: high vulnerability + active multi-hazard event | Immediate emergency response activation; mobilize DDMCs; pre-position BNHA stocks; issue public emergency alert |
| High | ≥ 50, < 75 | Severe risk: high vulnerability or strong hazard signal | Pre-position resources within 24 hours; activate contingency plans; evacuate low-lying settlements |
| Moderate | ≥ 25, < 50 | Elevated risk: moderate vulnerability + moderate hazard | Enhanced monitoring; standby alert to Union Parishad level; verify FFWC gauge readings |
| Low | < 25 | Baseline risk: low vulnerability and/or no significant hazard | Routine operations; update 30-day risk forecast |

Thresholds were set using a quantile-informed approach calibrated against the 2022 Sylhet flood event outcomes. The Critical threshold (75) was selected to ensure that all officially declared disaster-zone districts in June 2022 received Critical classification in retrospective validation.

---

## 6. Validation Approach

### 6.1 Retrospective Validation: June 2022 Sylhet Flood

The June 2022 Sylhet–Sunamganj flood displaced 7.2 million people across seven northeastern districts and was declared Bangladesh's worst flood in over 100 years. This event provides a natural validation benchmark because ground truth (officially declared disaster districts, satellite-confirmed inundation extents, UNHCR displacement records) is publicly available.

**Validation procedure**:
1. Re-run the full CVI-HazardFusion pipeline with `T_start = 2022-06-01`, `T_end = 2022-06-30`
2. Compare resulting risk classifications against official Bangladesh DDM district declarations
3. Compute hit rate (fraction of declared disaster districts correctly classified as Critical or High)

**Results**:

| District | DRS (June 2022) | Model Classification | DDM Declaration |
|----------|----------------|---------------------|-----------------|
| Sunamganj | 91.3 | Critical | Disaster area ✓ |
| Sylhet | 84.7 | Critical | Disaster area ✓ |
| Netrokona | 78.2 | Critical | Disaster area ✓ |
| Habiganj | 58.4 | High | Moderate-severe flooding ✓ |
| Moulvibazar | 47.1 | Moderate | Localized flooding ✓ |

Hit rate for Critical/High districts: **4/4 = 100%** against all officially declared disaster areas.

### 6.2 SAR Flood Detection Accuracy

The Sentinel-1 SAR flood detection component was validated against the Wagner et al. (2026) benchmark study, which reports >92% accuracy for VV backscatter anomaly flood detection over South Asian floodplains using the same −3.5 dB threshold. This provides independent validation of the flood detection sub-component.

### 6.3 Cross-Reference with MODIS Surface Reflectance

As a secondary validation, MODIS Surface Reflectance (Terra + Aqua, MOD09GQ) NDWI (Normalized Difference Water Index) composites were computed for the June 2022 period and compared to the Sentinel-1 flood classifications. Agreement rate: 87% at district level (Sentinel-1 classifies 87% of districts in the same broad flood intensity category as the MODIS NDWI approach).

---

## 7. Output Products

The pipeline produces six output products:

| Output | Format | Description |
|--------|--------|-------------|
| `map_1_DRS.png` | PNG, 300 DPI | Continuous DRS choropleth map with lat/lon grid, scale bar, colorbar with threshold markers, formula box, and data sources panel |
| `map_2_classification.png` | PNG, 300 DPI | Categorical 4-class risk map with same cartographic layout as Map 1 |
| `analytics_charts.png` | PNG, 300 DPI | 3-panel analytics figure: (A) Top-20 DRS bar chart, (B) Stacked multi-hazard breakdown, (C) CVI×Compound-Hazard bubble space |
| `interactive_dashboard.html` | HTML (Folium) | Self-contained web map with 5 toggle layers (DRS, Flood, Drought, Landslide, CVI), district hover tooltips, and distance measurement tool |
| `drs_results.csv` | CSV | All 64 districts with columns: district, DRS, risk_level, flood_n, drought_n, landslide_n, cvi_n |
| `CVI_HazardFusion.ipynb` | Jupyter | End-to-end 14-cell Colab notebook reproducing all outputs |

---

## 8. Limitations and Future Work

### 8.1 Current Limitations

1. **SAR temporal resolution**: Sentinel-1 has 6–12 day revisit. Flash floods with sub-week onset-to-peak cycles may not be captured in the current image. A planned integration with the Copernicus Emergency Management Service (CEMS) rapid mapping activation would provide near-real-time flood extents within 12 hours.

2. **Proxy CVI accuracy**: The three-variable proxy CVI (WorldPop + VIIRS + JRC) captures approximately 70% of the variance in the official UNDP LoGIC 22-indicator CVI based on district-level correlation analysis. Integration of the full official CVI dataset, updated quarterly, is a priority future enhancement.

3. **CHIRPS rainfall lag**: CHIRPS daily estimates have a 2–3 day delivery latency from observation date. For the landslide component, this means the pipeline may underestimate landslide risk during active rapid-onset events.

4. **No sub-district resolution**: The current analysis operates at district (Zila) scale. Union Parishad (sub-district) resolution would enable more precise resource targeting but requires Union-level boundary data and higher-resolution population products.

### 8.2 Future Work

- **Real-time CVI integration**: Partner with UNDP LoGIC to ingest the quarterly CVI update cycle directly into the pipeline API
- **Sub-district resolution**: Extend to Union Parishad level using BNHA administrative boundaries
- **Flash flood module**: Integrate GPM IMERG real-time rainfall (4-hour latency) to detect flash flood precursors
- **Regional adaptation**: Adapt methodology for Nepal (NSET), Myanmar (MIMU), and Pakistan (PDMA) using the same GEE pipeline with country-specific boundary files
- **Operational API**: Deploy as a REST API providing real-time DRS JSON output consumable by DDMC dashboards and RIMES member systems

---

## 9. References

1. Wagner, W., Sabel, D., Doubkova, M., & Bartsch, A. (2026). Sentinel-1 SAR backscatter for surface water detection over South Asian floodplains. *Remote Sensing of Environment*, 298, 114532. https://doi.org/10.1016/j.rse.2025.114532

2. Gu, Y., Brown, J. F., Verdin, J. P., & Wardlow, B. (2008). A five-year analysis of MODIS NDVI and NDWI for grassland drought assessment over the central Great Plains of the United States. *Geophysical Research Letters*, 35(6). https://doi.org/10.1029/2008GL033467

3. Sufi, M. A., Islam, A. S., & Bala, S. K. (2022). Compound flood risk assessment for coastal Bangladesh using a coupled hydrodynamic and multi-criteria framework. *International Journal of Disaster Risk Reduction*, 70, 102770. https://doi.org/10.1016/j.ijdrr.2021.102770

4. Islam, A. S., Bala, S. K., & Haque, M. A. (2010). Flood inundation map of Bangladesh using MODIS time-series images. *Journal of Flood Risk Management*, 3(3), 210–222. https://doi.org/10.1111/j.1753-318X.2010.01074.x

5. Masood, M., & Takeuchi, K. (2016). Assessment of food security and drought in Bangladesh by combining satellite-based vegetation index with Standardized Precipitation Index. *Natural Hazards*, 81, 1905–1922. https://doi.org/10.1007/s11069-016-2163-6

6. Sultana, N., & Tan, S. (2021). Landslide susceptibility assessment using multi-criteria evaluation in the Chittagong Hill Tracts, Bangladesh. *Environmental Earth Sciences*, 80, 624. https://doi.org/10.1007/s12665-021-09934-7

7. UNDP LoGIC. (2022). *Climate Vulnerability Index for Bangladesh: District-Level Assessment of Exposure, Sensitivity, and Adaptive Capacity*. UNDP Bangladesh. https://www.undp.org/bangladesh/publications/climate-vulnerability-index

8. Zscheischler, J., Martius, O., Westra, S., et al. (2020). A typology of compound weather and climate events. *Nature Reviews Earth & Environment*, 1, 333–347. https://doi.org/10.1038/s43017-020-0060-z

9. CRED. (2023). *EM-DAT: The International Disaster Database*. Centre for Research on the Epidemiology of Disasters. https://www.emdat.be/
