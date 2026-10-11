"""What-if impact simulator.

new_pm = pm * (1 - sum_i share_i * cut_i * controllable_i)

This is a first-order SCENARIO ESTIMATE built on (a) the indicative attribution shares and (b) the
CONTROLLABLE assumptions in config.py. It is not a validated chemical-transport simulation. The
dashboard applies the same formula in JavaScript for the interactive sliders.
"""
from config import CONTROLLABLE, SOURCES, SOURCE_LABELS, aqi_cat, CAT_NAMES

PRESETS = [
    ("Traffic restrictions (-30%)", {"traffic": 0.30}),
    ("Dust control drive (-40%)", {"dust": 0.40}),
    ("Industrial curbs (-30%)", {"industry": 0.30}),
    ("Combined local package", {"traffic": 0.30, "dust": 0.40, "industry": 0.30}),
]


def estimate(pm, shares, cuts):
    frac = sum(shares.get(s, 0) / 100.0 * cuts.get(s, 0.0) * CONTROLLABLE[s] for s in SOURCES)
    new = pm * (1 - frac)
    return dict(before=round(pm, 1), after=round(new, 1), reduction_pct=round(100 * frac, 1),
                cat_before=CAT_NAMES[aqi_cat(pm)], cat_after=CAT_NAMES[aqi_cat(new)])


def build(city_peak_pm, city_shares):
    return dict(
        controllable=CONTROLLABLE,
        source_labels=SOURCE_LABELS,
        presets=[dict(name=n, cuts=c, result=estimate(city_peak_pm, city_shares, c)) for n, c in PRESETS],
        note="First-order scenario estimate from indicative attribution shares and stated controllability "
             "assumptions. Not a validated dispersion simulation.",
    )
