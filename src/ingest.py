"""Data ingestion.

Keyless mode  : Open-Meteo weather + Open-Meteo air-quality (CAMS *model* data, coarse grid).
Optional keys : OPENAQ_API_KEY -> real ground sensors override the CAMS PM2.5/PM10/NO2.
                FIRMS_MAP_KEY  -> NASA FIRMS fire detections (stubble burning signal).

Every function degrades gracefully: a failure for one source prints a warning and the
pipeline carries on with what it has.
"""
import io
import os
import time

import numpy as np
import pandas as pd
import requests

from config import FIRE_BBOX, STATIONS, TZ

OM_WEATHER = "https://api.open-meteo.com/v1/forecast"
OM_AQ = "https://air-quality-api.open-meteo.com/v1/air-quality"
OPENAQ = "https://api.openaq.org/v3"


def _get(url, params=None, headers=None, retries=3, timeout=40):
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 429:
                time.sleep(2 * (i + 1))
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as e:  # do not print URL: may contain API key
            last = type(e).__name__
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"request failed after {retries} tries ({last})")


# --------------------------------------------------------------------------- shared cleanup
def finalize(df: pd.DataFrame, now: pd.Timestamp) -> pd.DataFrame:
    """Regular hourly index per station, gap-filled weather, observations masked after `now`."""
    meta = {s.id: s for s in STATIONS}
    out = []
    for sid, g in df.groupby("station"):
        g = g.sort_values("time").drop_duplicates("time").set_index("time")
        g = g.reindex(pd.date_range(g.index.min(), g.index.max(), freq="h"))
        for c in ("temp", "rh", "ws", "wd", "blh", "precip"):
            g[c] = g[c].interpolate(limit=3).bfill(limit=3).ffill(limit=3)
        g["precip"] = g["precip"].fillna(0.0)
        if "pm25_fc" not in g:
            g["pm25_fc"] = g["pm25"].where(g.index > now)
        for c in ("pm25", "pm10", "no2"):
            if c not in g:
                g[c] = np.nan
            obs = g[c].where(g.index <= now).ffill(limit=6)
            g[c] = obs.where(g.index <= now)
        g["station"] = sid
        g["lat"], g["lon"] = meta[sid].lat, meta[sid].lon
        g.index.name = "time"
        out.append(g.reset_index())
    return pd.concat(out, ignore_index=True)


# --------------------------------------------------------------------------- Open-Meteo
def _openmeteo_station(st, past_days, forecast_days):
    common = dict(latitude=st.lat, longitude=st.lon, past_days=past_days,
                  forecast_days=forecast_days, timezone=TZ)
    w = _get(OM_WEATHER, dict(
        hourly="temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,"
               "boundary_layer_height,precipitation", wind_speed_unit="ms", **common)).json()["hourly"]
    a = _get(OM_AQ, dict(hourly="pm2_5,pm10,nitrogen_dioxide", **common)).json()["hourly"]
    df = pd.DataFrame(w).merge(pd.DataFrame(a), on="time", how="left")
    df["time"] = pd.to_datetime(df["time"])
    df = df.rename(columns={
        "temperature_2m": "temp", "relative_humidity_2m": "rh", "wind_speed_10m": "ws",
        "wind_direction_10m": "wd", "boundary_layer_height": "blh", "precipitation": "precip",
        "pm2_5": "pm25", "nitrogen_dioxide": "no2"})
    df["station"] = st.id
    return df


# --------------------------------------------------------------------------- OpenAQ (UNTESTED here)
def _openaq_series(key, st, now, days):
    """Return {param: Series(hourly local-naive)} for the nearest sensors, or {} if none found."""
    h = {"X-API-Key": key}
    locs = _get(f"{OPENAQ}/locations", dict(coordinates=f"{st.lat},{st.lon}", radius=6000, limit=20),
                headers=h).json().get("results", [])
    best, best_d = None, 1e9
    for loc in locs:
        names = {s["parameter"]["name"] for s in loc.get("sensors", [])}
        if "pm25" not in names:
            continue
        c = loc["coordinates"]
        d = (c["latitude"] - st.lat) ** 2 + (c["longitude"] - st.lon) ** 2
        if d < best_d:
            best, best_d = loc, d
    if best is None:
        return {}
    out = {}
    start = (now - pd.Timedelta(days=days)).tz_localize(TZ).tz_convert("UTC")
    end = now.tz_localize(TZ).tz_convert("UTC")
    for s in best["sensors"]:
        name = s["parameter"]["name"]
        if name not in ("pm25", "pm10", "no2"):
            continue
        rows, page = [], 1
        while True:
            res = _get(f"{OPENAQ}/sensors/{s['id']}/hours", dict(
                datetime_from=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                datetime_to=end.strftime("%Y-%m-%dT%H:%M:%SZ"), limit=1000, page=page),
                headers=h).json().get("results", [])
            rows += [(r["period"]["datetimeFrom"]["utc"], r["value"]) for r in res]
            if len(res) < 1000:
                break
            page += 1
        if rows:
            ts = pd.to_datetime([r[0] for r in rows], utc=True).tz_convert(TZ).tz_localize(None)
            out[name] = pd.Series([r[1] for r in rows], index=ts).groupby(level=0).mean()
    return out


def overlay_openaq(df, key, now, days, sources):
    for st in STATIONS:
        try:
            series = _openaq_series(key, st, now, days)
        except Exception as e:
            print(f"[openaq] {st.id}: {e}")
            continue
        if "pm25" not in series:
            print(f"[openaq] {st.id}: no PM2.5 sensor within 6 km - keeping CAMS model data")
            continue
        m = df["station"] == st.id
        for param, col in (("pm25", "pm25"), ("pm10", "pm10"), ("no2", "no2")):
            if param in series:
                df.loc[m, col] = df.loc[m, "time"].map(series[param]).values
            else:
                # don't mix a sensor PM2.5 with a coarse-model PM10/NO2 (different scale -> misleading ratios)
                df.loc[m, col] = np.nan
        sources[st.id] = "openaq_sensor"
        time.sleep(0.3)
    return df, sources


# --------------------------------------------------------------------------- NASA FIRMS (UNTESTED here)
def fetch_fires(map_key, now, days=30, source="VIIRS_SNPP_NRT"):
    """Daily fire-detection counts over the Punjab/Haryana box -> {Timestamp(date): count}."""
    if not map_key:
        print("[firms] FIRMS_MAP_KEY not set - stubble-burning signal unavailable")
        return {}
    west, south, east, north = FIRE_BBOX
    today = now.normalize()
    d0 = today - pd.Timedelta(days=days - 1)
    counts = {}
    while d0 <= today:
        n = min(10, (today - d0).days + 1)
        url = (f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/{source}/"
               f"{west},{south},{east},{north}/{n}/{d0:%Y-%m-%d}")
        try:
            txt = _get(url).text
            if txt.startswith("latitude"):
                f = pd.read_csv(io.StringIO(txt))
                by_day = f.groupby("acq_date").size()
                for k in range(n):
                    day = d0 + pd.Timedelta(days=k)
                    counts[day] = int(by_day.get(day.strftime("%Y-%m-%d"), 0))
        except Exception as e:
            print(f"[firms] chunk starting {d0:%Y-%m-%d} failed: {e}")
        d0 += pd.Timedelta(days=10)
    return counts


# --------------------------------------------------------------------------- entry point
def load_live(now, past_days=60, forecast_days=4):
    frames = []
    for st in STATIONS:
        frames.append(_openmeteo_station(st, past_days, forecast_days))
        time.sleep(0.3)
    df = pd.concat(frames, ignore_index=True)
    sources = {s.id: "cams_model" for s in STATIONS}
    # keep the CAMS model forecast (future hours) as a comparison baseline before sensors overwrite PM2.5
    df["pm25_fc"] = df["pm25"].where(df["time"] > now)
    key = os.getenv("OPENAQ_API_KEY")
    if key:
        df, sources = overlay_openaq(df, key, now, past_days, sources)
    else:
        print("[openaq] OPENAQ_API_KEY not set - using coarse CAMS model data, NOT ground sensors")
    fires = fetch_fires(os.getenv("FIRMS_MAP_KEY"), now)
    return finalize(df, now), fires, sources
