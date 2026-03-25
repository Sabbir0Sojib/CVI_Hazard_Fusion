# Pilot Study Results — 23 Feb to 25 Mar 2026

## Risk Classification Summary

| Risk Level | DRS Range | Districts | Top Districts |
|---|---|---|---|
| Critical | ≥75 | 2 | Dhaka (100.0), Rangamati (84.4) |
| High | 50–74 | 3 | Sirajganj (68.3), Manikganj (59.1), Bogra (57.6) |
| Moderate | 25–49 | 12 | Narayanganj (39.9), Barguna (39.1), Munshiganj (38.7)... |
| Low | <25 | 47 | Barisal (22.4), Chittagong (12.3), Sylhet (9.6)... |

## Full District Rankings

| Rank | District | DRS | Risk Level |
|------|----------|-----|------------|
| 1 | Dhaka | 100.00 | Critical |
| 2 | Rangamati | 84.39 | Critical |
| 3 | Sirajganj | 68.25 | High |
| 4 | Manikganj | 59.06 | High |
| 5 | Bogra | 57.58 | High |
| 6 | Narayanganj | 39.94 | Moderate |
| 7 | Barguna | 39.14 | Moderate |
| 8 | Munshiganj | 38.75 | Moderate |
| 9 | Pirojpur | 36.79 | Moderate |
| 10 | Rajbari | 36.39 | Moderate |
| 11 | Satkhira | 34.30 | Moderate |
| 12 | Rajshahi | 33.94 | Moderate |
| 13 | Jhalokati | 33.29 | Moderate |
| 14 | Pabna | 28.97 | Moderate |
| 15 | Shariatpur | 27.63 | Moderate |
| 16 | Khulna | 26.00 | Moderate |
| 17 | Kushtia | 25.68 | Moderate |
| 18 | Naogaon | 24.62 | Low |
| 19 | Nawabganj | 22.90 | Low |
| 20 | Barisal | 22.44 | Low |
| 21 | Chandpur | 21.66 | Low |
| 22 | Tangail | 19.83 | Low |
| 23 | Jamalpur | 19.29 | Low |
| 24 | Bagerhat | 19.28 | Low |
| 25 | Sunamganj | 18.78 | Low |
| 26 | Gaibandha | 18.71 | Low |
| 27 | Dinajpur | 18.40 | Low |
| 28 | Cox's Bazar | 18.04 | Low |
| 29 | Faridpur | 17.49 | Low |
| 30 | Magura | 16.97 | Low |
| 31 | Narsingdi | 14.86 | Low |
| 32 | Brahamanbaria | 14.50 | Low |
| 33 | Lakshmipur | 14.40 | Low |
| 34 | Patuakhali | 13.68 | Low |
| 35 | Kurigram | 12.79 | Low |
| 36 | Madaripur | 12.45 | Low |
| 37 | Chittagong | 12.35 | Low |
| 38 | Joypurhat | 11.85 | Low |
| 39 | Maulvibazar | 11.65 | Low |
| 40 | Bhola | 10.94 | Low |
| 41 | Nilphamari | 10.13 | Low |
| 42 | Gazipur | 9.56 | Low |
| 43 | Sylhet | 9.56 | Low |
| 44 | Kishoreganj | 9.27 | Low |
| 45 | Narail | 8.31 | Low |
| 46 | Jessore | 7.99 | Low |
| 47 | Jhenaidah | 7.98 | Low |
| 48 | Noakhali | 7.81 | Low |
| 49 | Khagrachhari | 7.16 | Low |
| 50 | Habiganj | 6.74 | Low |
| 51 | Rangpur | 5.60 | Low |
| 52 | Natore | 5.49 | Low |
| 53 | Netrakona | 4.40 | Low |
| 54 | Panchagarh | 4.37 | Low |
| 55 | Comilla | 4.05 | Low |
| 56 | Bandarban | 3.65 | Low |
| 57 | Lalmonirhat | 2.40 | Low |
| 58 | Mymensingh | 2.38 | Low |
| 59 | Sherpur | 2.35 | Low |
| 60 | Gopalganj | 1.92 | Low |
| 61 | Chuadanga | 1.81 | Low |
| 62 | Feni | 1.03 | Low |
| 63 | Meherpur | 0.50 | Low |
| 64 | Thakurgaon | 0.00 | Low |

## Key Observations

1. **Multiplicative model validation**: Joypurhat achieves the highest raw flood score (1.00 normalized) and near-maximum drought score (1.00), yet its final DRS is only 11.85 (Low). Its proxy CVI (0.042) is the lowest in the dataset — confirming that the multiplicative design correctly suppresses high-hazard outcomes in genuinely low-vulnerability districts, preventing false alarm escalation.

2. **Urban vulnerability dominance**: Dhaka's DRS of 100.0 (maximum) is driven primarily by the highest proxy CVI in the dataset (0.451), reflecting dense informal settlement exposure and limited adaptive capacity — even though its raw hazard scores are moderate. This highlights that vulnerability amplification is the dominant risk driver in Dhaka, not hazard intensity alone.

3. **Chittagong Hill Tracts landslide risk**: Rangamati achieves Critical status (DRS=84.4) with a normalized landslide score of 1.00 — the highest in the dataset. Its proximity to the Chittagong Hill Tracts, steep SRTM slopes, and CHIRPS rainfall accumulation produce a landslide hazard far exceeding all other districts, a risk pattern invisible to flood-only early warning systems.

4. **River-island (char) district clustering**: The High-risk cluster (Sirajganj, Manikganj, Bogra) corresponds geographically to the Brahmaputra-Jamuna floodplain char districts, where high Sentinel-1 flood signals combine with moderate-to-high CVI values from seasonal displacement vulnerability. This clustering validates the spatial coherence of the DRS model.

5. **Coastal delta underperformance**: Southern coastal districts (Barisal, Pirojpur, Barguna, Patuakhali) that carry high administrative disaster risk perceptions show only Moderate or Low DRS values for this 30-day window, indicating that during the dry-season analysis period (February–March 2026) active hazard signals were suppressed — the system correctly distinguishes seasonal risk from chronic structural vulnerability.

## Validation Note

Joypurhat presents the most instructive validation case for the multiplicative model design. It records the highest normalized flood score (1.00) and highest normalized drought score (1.00) in the entire dataset — yet its final DRS is only **11.85 (Low)**. This outcome is not an error: Joypurhat's proxy CVI is 0.042, the lowest of all 64 districts, reflecting low population density, relatively lower poverty exposure, and minimal historical surface water accumulation. Under the multiplicative formula `DRS = CVI × Compound Hazard`, a near-zero CVI correctly suppresses even maximum hazard signals. This validates that the model avoids the false escalation that would result from an additive or purely hazard-based approach — ensuring that emergency resources are directed toward districts where high hazard intersects high human vulnerability, not simply where satellite signals are strongest.
