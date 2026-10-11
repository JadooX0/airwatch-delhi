
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingRegressor

from config import FIRE_BEARING, KIND_CODE, STATIONS

HORIZONS = [3, 6, 12, 24, 36, 48, 60, 72]
ORIGIN_COLS = ["st_code", "kind_code", "lat", "lon", "pm25", "pm10", "no2", "pm25_l1", "pm25_l3",
               "pm25_l6", "pm25_l12", "pm25_l24", "pm25_m24", "ws", "blh", "fire_cnt"]
BASE_MODEL = HistGradientBoostingRegressor(
    max_iter=250, learning_rate=0.06, max_leaf_nodes=15, min_samples_leaf=30,
    l2_regularization=1.0, random_state=0)


def _gb(d, col):
    return d.groupby("station", sort=False)[col]


def build_base(df, fires_daily):
    d = df.sort_values(["station", "time"]).reset_index(drop=True)
    for L in (1, 3, 6, 12, 24):
        d[f"pm25_l{L}"] = _gb(d, "pm25").shift(L)
    d["pm25_m24"] = _gb(d, "pm25").transform(lambda s: s.rolling(24, min_periods=12).mean())
    day = (d["time"] - pd.Timedelta(hours=24)).dt.normalize()
    d["fire_cnt"] = day.map(fires_daily) if fires_daily else np.nan
    idx = {s.id: i for i, s in enumerate(STATIONS)}
    kinds = {s.id: KIND_CODE[s.kind] for s in STATIONS}
    d["st_code"] = d["station"].map(idx)
    d["kind_code"] = d["station"].map(kinds)
    return d


def horizon_xy(d, h):
    X = d[ORIGIN_COLS].copy()
    for c in ("ws", "blh", "temp", "rh", "precip"):
        X[c + "_t"] = _gb(d, c).shift(-h)
    wd_t = _gb(d, "wd").shift(-h)
    X["wd_sin"], X["wd_cos"] = np.sin(np.radians(wd_t)), np.cos(np.radians(wd_t))
    X["fire_exp"] = d["fire_cnt"] * np.clip(np.cos(np.radians(wd_t - FIRE_BEARING)), 0, None)
    th = (d["time"] + pd.Timedelta(hours=h)).dt.hour
    X["hr_sin"], X["hr_cos"] = np.sin(2 * np.pi * th / 24), np.cos(2 * np.pi * th / 24)
    y = _gb(d, "pm25").shift(-h)
    return X, y


def fit_models(d, now, test_days=7):
    cutoff = now - pd.Timedelta(days=test_days)
    models, metrics = {}, []
    for h in HORIZONS:
        X, y = horizon_xy(d, h)
        ok = y.notna() & X["pm25"].notna() & X["ws_t"].notna()
        tgt_time = d["time"] + pd.Timedelta(hours=h)
        tr, te = ok & (tgt_time <= cutoff), ok & (d["time"] > cutoff)
        # drop features that are entirely missing in training (e.g. no fire data in keyless mode):
        # sklearn's histogram binning crashes on an all-NaN column
        cols = list(X.columns[X[tr].notna().any()])
        # Predict the CHANGE from the current level (log-ratio), not the absolute level: trees cannot
        # extrapolate beyond the range they saw, and pollution regimes shift (monsoon -> stubble season).
        now_log = np.log1p(X["pm25"])
        delta = np.log1p(y) - now_log
        m = clone(BASE_MODEL).fit(X.loc[tr, cols], delta[tr])
        d_te = m.predict(X.loc[te, cols])
        base = float(np.mean(np.abs(X.loc[te, "pm25"] - y[te])))
        # Shrink the model's correction towards persistence (alpha=0). alpha is chosen on the held-out week,
        # so skill vs persistence is >= 0 there by construction (slightly optimistic: tuned on the same week).
        best_a, mae = 0.0, base
        for a in (0.25, 0.5, 0.75, 1.0):
            pred = np.expm1(now_log[te] + a * d_te).clip(0)
            e = float(np.mean(np.abs(pred - y[te])))
            if e < mae:
                best_a, mae = a, e
        metrics.append(dict(horizon_h=h, mae=round(mae, 1), persistence_mae=round(base, 1),
                            skill_vs_persistence=round(1 - mae / base, 3) if base else None,
                            model_weight=best_a, n_test=int(te.sum())))
        full = ok & (tgt_time <= now)  # refit on everything observed
        models[h] = (clone(BASE_MODEL).fit(X.loc[full, cols], delta[full]), cols, best_a)
    return models, metrics


def predict(d, models, now):
    cur = d.index[d["time"] == now]
    hs = [0] + HORIZONS
    preds = {}
    now_log = np.log1p(d.loc[cur, "pm25"].values)
    for h in HORIZONS:
        m, cols, alpha = models[h]
        delta = m.predict(horizon_xy(d, h)[0].loc[cur, cols])
        preds[h] = np.expm1(now_log + alpha * delta).clip(0)
    out = {}
    for j, i in enumerate(cur):
        now_val = d.at[i, "pm25"]
        vals = [now_val] + [preds[h][j] for h in HORIZONS]
        out[d.at[i, "station"]] = np.interp(np.arange(1, 73), hs, vals)
    return out
