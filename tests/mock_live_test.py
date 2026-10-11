"""Exercises the LIVE code path (Open-Meteo + OpenAQ + FIRMS parsing, pagination, NaN handling)
against mocked HTTP responses shaped like the real APIs, so it runs offline.

    python tests/mock_live_test.py

Passing means: our parsing/plumbing is self-consistent. It does NOT prove the real APIs still return
exactly these shapes - the first real run is the real test.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import ingest  # noqa: E402
import pipeline  # noqa: E402
import synthetic  # noqa: E402
from config import STATIONS, TZ  # noqa: E402

NOW = pd.Timestamp.now(tz=TZ).floor("h").tz_localize(None)
TRUTH, _, _ = synthetic.generate(NOW)
BY_LL = {(round(s.lat, 4), round(s.lon, 4)): s for s in STATIONS}


class Resp:
    def __init__(self, payload=None, text=""):
        self._p, self.text, self.status_code = payload, text, 200

    def json(self):
        return self._p


def _station_frame(lat, lon):
    st = BY_LL[(round(float(lat), 4), round(float(lon), 4))]
    return st, TRUTH[TRUTH["station"] == st.id].sort_values("time")


def fake_get(url, params=None, headers=None, **kw):
    if url.startswith("https://api.open-meteo.com"):
        _, g = _station_frame(params["latitude"], params["longitude"])
        return Resp({"hourly": {
            "time": g["time"].dt.strftime("%Y-%m-%dT%H:%M").tolist(),
            "temperature_2m": g["temp"].tolist(), "relative_humidity_2m": g["rh"].tolist(),
            "wind_speed_10m": g["ws"].tolist(), "wind_direction_10m": g["wd"].tolist(),
            "boundary_layer_height": g["blh"].tolist(), "precipitation": g["precip"].tolist()}})
    if url.startswith("https://air-quality-api.open-meteo.com"):
        _, g = _station_frame(params["latitude"], params["longitude"])
        pm = g["pm25"].ffill()  # CAMS-style: values also for the future
        return Resp({"hourly": {
            "time": g["time"].dt.strftime("%Y-%m-%dT%H:%M").tolist(),
            "pm2_5": (pm * 0.6).tolist(), "pm10": (g["pm10"].ffill() * 0.6).tolist(),
            "nitrogen_dioxide": g["no2"].ffill().tolist()}})
    if "api.openaq.org/v3/locations" in url:
        lat, lon = [float(x) for x in params["coordinates"].split(",")]
        return Resp({"results": [{"id": 1, "coordinates": {"latitude": lat, "longitude": lon},
                                  "sensors": [{"id": 11, "parameter": {"name": "pm25"}},
                                              {"id": 12, "parameter": {"name": "pm10"}},
                                              {"id": 13, "parameter": {"name": "no2"}},
                                              {"id": 14, "parameter": {"name": "so2"}}]}]})
    if "api.openaq.org/v3/sensors" in url:
        # NB: station lookup by sensor is not possible in this mock -> use city mean of truth
        col = {"11": "pm25", "12": "pm10", "13": "no2"}[url.split("/sensors/")[1].split("/")[0]]
        g = TRUTH[TRUTH["time"] <= NOW].groupby("time")[col].mean()
        rows = [{"value": float(v), "period": {"datetimeFrom": {
            "utc": (t.tz_localize(TZ).tz_convert("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")}}}
            for t, v in g.items()]
        lim, page = params["limit"], params["page"]
        return Resp({"results": rows[(page - 1) * lim: page * lim]})
    if "firms.modaps" in url:
        parts = url.split("/")
        n, d0 = int(parts[-2]), pd.Timestamp(parts[-1])
        lines = ["latitude,longitude,acq_date"]
        for k in range(n):
            day = d0 + pd.Timedelta(days=k)
            lines += [f"30.1,75.2,{day:%Y-%m-%d}"] * (20 + 10 * k)
        return Resp(text="\n".join(lines))
    raise AssertionError(f"unexpected url {url}")


def main():
    ingest._get = fake_get
    ingest.time.sleep = lambda *_: None
    for variant, env in (("keyless (CAMS only, no fires)", {}),
                         ("with OpenAQ + FIRMS keys", {"OPENAQ_API_KEY": "x", "FIRMS_MAP_KEY": "y"})):
        for k in ("OPENAQ_API_KEY", "FIRMS_MAP_KEY"):
            os.environ.pop(k, None)
        os.environ.update(env)
        out = pipeline.run("live", "/tmp/mock_live.json")
        srcs = set(out["meta"]["sources"].values())
        s = out["stations"][0]
        assert len(s["forecast"]) == 72 and len(s["history_24h"]) == 24, "shape"
        assert np.isfinite(s["forecast"]).all() and np.isfinite(out["city"]["forecast"]).all(), "nan forecast"
        assert s["cams_baseline"] is not None and len(s["cams_baseline"]) == 72, "cams baseline"
        print(f"OK [{variant}] sources={srcs} city_now={out['city']['pm25_now']} "
              f"top_shares={out['city']['shares']} notes={out['meta']['notes']}")


if __name__ == "__main__":
    main()
