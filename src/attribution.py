"""INDICATIVE source attribution.

This is a transparent rule-based score, NOT receptor modelling or chemical source apportionment
(that needs speciation data you will not have in a hackathon). Each source gets a score from
observable signals; scores are normalised to shares. Say "indicative" in the demo and show the
evidence strings - judges will respect that more than a claimed-exact breakdown.
"""
import numpy as np

from config import FIRE_BEARING, FIRE_SATURATION, SOURCE_LABELS, SOURCES


def _clip01(x):
    return float(np.clip(x, 0.0, 1.0))


def attribute(pm25, pm10, no2, ws, wd, precip, hour, fire_cnt, kind):
    ratio = pm25 / pm10 if pm10 and pm10 > 0 else 0.55
    align = max(0.0, float(np.cos(np.radians(wd - FIRE_BEARING)))) if wd == wd else 0.0
    fire_known = fire_cnt == fire_cnt and fire_cnt is not None
    fire_f = _clip01((fire_cnt if fire_known else 0.0) / FIRE_SATURATION)
    n = _clip01(((no2 if no2 == no2 else 20.0) - 20.0) / 80.0)
    rush = 1.0 if (7 <= hour <= 11 or 17 <= hour <= 22) else 0.4

    score = {
        "biomass_burning": 3.0 * fire_f * align * (0.6 + 0.4 * _clip01((ratio - 0.4) / 0.3)),
        "traffic": 1.5 * n * rush + (0.5 if kind == "traffic" else 0.0),
        "dust": 1.5 * _clip01((0.55 - ratio) / 0.25) * (0.4 + 0.6 * _clip01(ws / 5.0)) * (1.0 if precip < 0.1 else 0.3),
        "industry": (0.9 if kind == "industrial" else 0.2) + 0.3 * n,
        "other": 0.8,
    }
    total = sum(score.values())
    shares = {k: round(100.0 * v / total, 1) for k, v in score.items()}

    ev = []
    if not fire_known:
        ev.append("No fire-detection data available - biomass share is a lower bound")
    elif fire_f * align > 0.25:
        ev.append(f"~{int(fire_cnt)} fire detections upwind region in last day, wind from {wd:.0f} deg "
                  f"(alignment {align:.2f})")
    if n > 0.35:
        ev.append(f"NO2 elevated ({no2:.0f} ug/m3){' in rush hours' if rush == 1.0 else ''} - combustion/traffic")
    if ratio < 0.45:
        ev.append(f"PM2.5/PM10 ratio low ({ratio:.2f}) with wind {ws:.1f} m/s - coarse dust likely")
    if kind == "industrial":
        ev.append("Station sits in an industrial cluster - industry weighted up")
    if not ev:
        ev.append("No single dominant signal - regional background dominates")
    return dict(shares=shares, evidence=ev[:4], ratio=round(ratio, 2))


def top_source(shares):
    k = max(shares, key=shares.get)
    return k, SOURCE_LABELS[k], shares[k]
