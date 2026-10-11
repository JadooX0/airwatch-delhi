"""Synthetic data generator - lets the whole pipeline run offline (and gives you a demo fallback).

The generating process is deliberately physical-ish (ventilation = wind x mixing height, rush-hour
emissions, upwind fire influence) so the ML model has real structure to learn. It is NOT real Delhi
data: never present synthetic output as real.
"""
import numpy as np
import pandas as pd

from config import FIRE_BEARING, KIND_CODE, STATIONS
from ingest import finalize


def _ar1(rng, n, phi, sd):
    x = np.zeros(n)
    e = rng.normal(0, sd, n)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


def generate(now, days=60, future_days=4, seed=7):
    rng = np.random.default_rng(seed)
    t = pd.date_range(now - pd.Timedelta(days=days), now + pd.Timedelta(days=future_days), freq="h")
    n = len(t)
    hr = t.hour.values

    ws = np.clip(2.4 + _ar1(rng, n, 0.96, 0.12) * 3 + 0.8 * np.sin(2 * np.pi * (hr - 13) / 24), 0.3, 9)
    wd = (300 + 70 * _ar1(rng, n, 0.985, 0.1)) % 360
    blh = np.clip(150 + 900 * np.clip(np.sin(np.pi * (hr - 6) / 12), 0, None) + rng.normal(0, 40, n), 80, 2000)
    temp = 24 + 7 * np.sin(2 * np.pi * (hr - 9) / 24) + _ar1(rng, n, 0.97, 0.15)
    rh = np.clip(55 - 20 * np.sin(2 * np.pi * (hr - 9) / 24) + _ar1(rng, n, 0.97, 0.5), 15, 100)

    # daily regional fire counts: stubble season ramps up through October
    dates = pd.DatetimeIndex(t.normalize().unique())
    ramp = np.linspace(80, 1700, len(dates)) * rng.lognormal(0, 0.35, len(dates))
    fires = {d: int(v) for d, v in zip(dates, ramp)}
    fire_cnt = pd.Series((t - pd.Timedelta(hours=24)).normalize()).map(fires).fillna(80).values
    align = np.clip(np.cos(np.radians(wd - FIRE_BEARING)), 0, None)

    vent = 0.25 + ws * blh / 2500.0
    rush = 1 + 0.6 * (((hr >= 7) & (hr <= 10)) | ((hr >= 18) & (hr <= 22)))
    target = (25 + 55 * rush + 0.045 * fire_cnt * align) / vent ** 0.7
    mult = {"traffic": 1.15, "industrial": 1.25, "residential": 0.95, "mixed": 1.0}

    frames = []
    for st in STATIONS:
        pm = np.zeros(n)
        pm[0] = target[0]
        noise = rng.lognormal(0, 0.08, n)
        for i in range(1, n):
            pm[i] = 0.82 * pm[i - 1] + 0.18 * target[i] * mult[st.kind] * noise[i]
        pm = np.clip(pm, 5, 650)
        ratio = np.clip(0.6 + 0.05 * align * fire_cnt / 1500 - 0.08 * (ws > 4) + rng.normal(0, 0.03, n), 0.3, 0.85)
        traffic_k = 1.0 if st.kind == "traffic" else 0.6
        no2 = np.clip(12 + 22 * (rush > 1) * traffic_k + 14 / vent + rng.normal(0, 3, n), 5, 220)
        jitter = 1 + 0.05 * rng.normal(size=n)
        frames.append(pd.DataFrame(dict(
            time=t, station=st.id, pm25=pm, pm10=pm / ratio, no2=no2,
            temp=temp, rh=rh, ws=ws * jitter, wd=wd, blh=blh, precip=0.0)))
    sources = {s.id: "synthetic" for s in STATIONS}
    df = pd.concat(frames, ignore_index=True)
    df["pm25_fc"] = np.nan  # no external model forecast in synthetic mode (generated future is hidden)
    return finalize(df, now), fires, sources
