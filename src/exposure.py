"""Exposure map: interpolate station PM2.5 to a grid and weight by a population surface.

The population surface here is a PLACEHOLDER built from station population weights (gaussian kernels,
total ~20 million). For a credible demo replace `population()` with a WorldPop / GHSL raster
sampled onto the same grid.
"""
import numpy as np

from config import BBOX, CAT_NAMES, STATIONS, aqi_cat

COS_LAT = float(np.cos(np.radians(28.6)))
N_LAT, N_LON = 30, 34
SNAP_HOURS = [0, 24, 48, 72]


def make_grid():
    lats = np.linspace(BBOX["south"], BBOX["north"], N_LAT)
    lons = np.linspace(BBOX["west"], BBOX["east"], N_LON)
    LON, LAT = np.meshgrid(lons, lats)
    return lats, lons, np.c_[LAT.ravel(), LON.ravel()]


def _dist(pts, spts):
    dy = pts[:, None, 0] - spts[None, :, 0]
    dx = (pts[:, None, 1] - spts[None, :, 1]) * COS_LAT
    return np.sqrt(dx ** 2 + dy ** 2)


def idw(pts, spts, vals, power=2.0):
    w = 1.0 / (_dist(pts, spts) + 1e-3) ** power
    return (w * np.asarray(vals)[None, :]).sum(1) / w.sum(1)


def population(pts, total=2.0e7, sigma=0.04):
    spts = np.array([[s.lat, s.lon] for s in STATIONS])
    wts = np.array([s.pop for s in STATIONS])
    k = (wts[None, :] * np.exp(-(_dist(pts, spts) ** 2) / (2 * sigma ** 2))).sum(1) + 0.02
    return k / k.sum() * total


def station_value_at(series72, now_val, hour):
    if hour == 0:
        return now_val
    lo, hi = max(0, hour - 4), min(72, hour + 2)  # +-3h smoothing around the target hour
    return float(np.mean(series72[lo:hi]))


def build(forecasts, now_vals):
    lats, lons, pts = make_grid()
    spts = np.array([[s.lat, s.lon] for s in STATIONS])
    pop = population(pts)
    pm_by_hour, summary = {}, {}
    for h in SNAP_HOURS:
        vals = [station_value_at(forecasts[s.id], now_vals[s.id], h) for s in STATIONS]
        pm = idw(pts, spts, vals)
        pm_by_hour[str(h)] = np.round(pm, 1).tolist()
        cats = np.array([aqi_cat(v) for v in pm])
        by_cat = {CAT_NAMES[c]: float(pop[cats == c].sum()) for c in range(6)}
        summary[str(h)] = dict(
            pop_weighted_pm25=round(float((pm * pop).sum() / pop.sum()), 1),
            population_by_category={k: int(round(v, -3)) for k, v in by_cat.items()},
            pop_poor_or_worse=int(round(float(pop[cats >= 3].sum()), -3)),
        )
    grid = dict(lats=np.round(lats, 4).tolist(), lons=np.round(lons, 4).tolist(),
                pop=np.round(pop, 0).astype(int).tolist(), pm=pm_by_hour)
    return grid, summary
