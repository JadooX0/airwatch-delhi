"""End-to-end pipeline:  ingest -> features/model -> forecast -> attribution -> exposure ->
recommendations -> simulator -> one JSON file for the dashboard.

  python src/pipeline.py --mode synthetic --out dashboard/data.json
  python src/pipeline.py --mode live      --out dashboard/data.json
"""
import argparse
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import attribution
import exposure
import forecast
import ingest
import recommend
import simulate
import synthetic
from config import SOURCE_LABELS, SOURCES, STATIONS, TZ, aqi_cat, CAT_NAMES


def run(mode="synthetic", out_path="dashboard/data.json"):
    now = pd.Timestamp.now(tz=TZ).floor("h").tz_localize(None)
    if mode == "synthetic":
        df, fires, sources = synthetic.generate(now)
    elif mode == "live":
        df, fires, sources = ingest.load_live(now)
    else:
        raise ValueError("mode must be 'synthetic' or 'live'")

    d = forecast.build_base(df, fires)
    models, metrics = forecast.fit_models(d, now)
    fc = forecast.predict(d, models, now)

    cur = d[d["time"] == now].set_index("station")
    pop_w = {s.id: s.pop for s in STATIONS}
    W = sum(pop_w.values())
    times = [(now + pd.Timedelta(hours=i)).strftime("%Y-%m-%d %H:%M") for i in range(1, 73)]

    stations_out, now_vals, shares_by_st, peak_by_st = [], {}, {}, {}
    for s in STATIONS:
        r = cur.loc[s.id]
        series = fc[s.id]
        now_vals[s.id] = float(r["pm25"])
        peak_i = int(np.argmax(series))
        peak_by_st[s.id] = float(series[peak_i])
        att = attribution.attribute(
            r["pm25"], r["pm10"], r["no2"], r["ws"], r["wd"], r["precip"], now.hour,
            r["fire_cnt"] if "fire_cnt" in r and r["fire_cnt"] == r["fire_cnt"] else None, s.kind)
        shares_by_st[s.id] = att["shares"]
        hist = d[(d["station"] == s.id) & (d["time"] > now - pd.Timedelta(hours=24)) & (d["time"] <= now)]
        stations_out.append(dict(
            id=s.id, name=s.name, lat=s.lat, lon=s.lon, kind=s.kind, source=sources.get(s.id),
            pm25_now=round(now_vals[s.id], 1), cat_now=CAT_NAMES[aqi_cat(now_vals[s.id])],
            peak=dict(pm25=round(float(series[peak_i]), 1), time=times[peak_i],
                      cat=CAT_NAMES[aqi_cat(float(series[peak_i]))]),
            history_24h=np.round(hist["pm25"].values, 1).tolist(),
            forecast=np.round(series, 1).tolist(),
            cams_baseline=(np.round(d[(d["station"] == s.id) & (d["time"] > now)]["pm25_fc"].values[:72], 1).tolist()
                           if d["pm25_fc"].notna().any() else None),
            attribution=att))

    # city-wide (population-weighted) roll-up
    city_fc = sum(fc[s.id] * s.pop for s in STATIONS) / W
    city_now = sum(now_vals[s.id] * s.pop for s in STATIONS) / W
    city_shares = {k: round(sum(shares_by_st[s.id][k] * s.pop for s in STATIONS) / W, 1) for k in SOURCES}
    ci = int(np.argmax(city_fc))
    city = dict(pm25_now=round(float(city_now), 1), peak=dict(pm25=round(float(city_fc[ci]), 1), time=times[ci]),
                forecast=np.round(city_fc, 1).tolist(), shares=city_shares)

    grid, exp_summary = exposure.build(fc, now_vals)
    hot = sorted(STATIONS, key=lambda s: peak_by_st[s.id] * s.pop, reverse=True)[:3]
    hot_names = [f"{s.name} (peak ~{peak_by_st[s.id]:.0f})" for s in hot]
    top_key = max(city_shares, key=city_shares.get)
    pop_poor = max(v["pop_poor_or_worse"] for v in exp_summary.values())
    recs = recommend.build(city["peak"]["pm25"], aqi_cat(city["peak"]["pm25"]), city["peak"]["time"],
                           top_key, SOURCE_LABELS[top_key], hot_names, pop_poor)
    sim = simulate.build(city["peak"]["pm25"], city_shares)

    notes = []
    if mode == "synthetic":
        notes.append("SYNTHETIC DATA - generated for development/demo, not real measurements.")
    if "cams_model" in sources.values():
        notes.append("Some stations use coarse CAMS model data (tens of km grid), not ground sensors.")
    if not fires:
        notes.append("No fire-detection data: stubble-burning contribution is not estimated from fires.")

    out = dict(
        meta=dict(generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  now_local=now.strftime("%Y-%m-%d %H:%M"), mode=mode, notes=notes,
                  sources=sources, source_labels=SOURCE_LABELS),
        model=dict(type="HistGradientBoosting, direct multi-horizon, pooled across stations",
                   holdout="last 7 days", metrics=metrics),
        city=city, stations=stations_out, grid=grid, exposure_summary=exp_summary,
        recommendations=recs, simulation=sim)
    with open(out_path, "w") as f:
        json.dump(out, f, default=float, separators=(",", ":"))
    return out


def load_dotenv(path=".env"):
    """Tiny .env reader (KEY=VALUE per line) so keys need not be exported by hand. Existing env vars win."""
    import os
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


if __name__ == "__main__":
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="synthetic", choices=["synthetic", "live"])
    ap.add_argument("--out", default="dashboard/data.json")
    a = ap.parse_args()
    res = run(a.mode, a.out)
    print(f"wrote {a.out}: {len(res['stations'])} stations, city now {res['city']['pm25_now']}, "
          f"peak {res['city']['peak']['pm25']} at {res['city']['peak']['time']}")
    for m in res["model"]["metrics"]:
        print(m)
    sys.exit(0)
