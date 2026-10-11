"""Rule-based recommendations. Advisory only: defer to official CPCB / CAQM / GRAP orders."""
from config import CAT_NAMES

SOURCE_ACTIONS = {
    "biomass_burning": [
        "Escalate upwind fire hotspots to the Punjab/Haryana agencies through the inter-state coordination channel",
        "Pre-announce expected smoke-arrival windows so schools and hospitals can plan",
    ],
    "traffic": [
        "Deploy traffic police at congestion choke-points near the worst-hit stations during rush hours",
        "Step up PUC and old-vehicle enforcement; push park-and-ride / extra metro and bus frequency",
    ],
    "dust": [
        "Run mechanical sweeping and water sprinkling on arterial roads near the hotspots",
        "Inspect construction sites for dust-control compliance (covers, barricades, wheel-wash)",
    ],
    "industry": [
        "Inspect industrial clusters near hotspots for emission-norm and fuel compliance",
        "Check that diesel generator use and open burning in industrial areas are being stopped",
    ],
    "other": [
        "No single controllable source dominates - prioritise public advisories and health-system readiness",
    ],
}


def build(city_peak_pm, peak_cat, peak_time, top_key, top_label, hotspots, pop_poor):
    cat = CAT_NAMES[peak_cat]
    citizens, authorities = [], []

    if peak_cat <= 1:
        headline = f"Air stays {cat.lower()} over the next 72 h - routine precautions only."
        citizens = ["No special restrictions expected. Sensitive groups should still check the daily outlook."]
        authorities = ["Continue routine monitoring; no escalation indicated by the forecast."]
    else:
        headline = (f"Peak PM2.5 of ~{city_peak_pm:.0f} ug/m3 ({cat}) expected around {peak_time}. "
                    f"Main indicated driver: {top_label.lower()}.")
        citizens = [
            "Plan outdoor exercise outside the peak window; prefer midday when mixing height is highest",
            "Children, older adults and people with heart or lung conditions: limit time outdoors",
            "Keep windows closed during the evening/night peak; use a purifier in one room if you have one",
            "If you must be outside, a well-fitted N95/FFP2 mask helps; cloth and surgical masks do little for PM2.5",
        ]
        if peak_cat >= 4:
            citizens += ["Avoid strenuous outdoor activity altogether; schools should move activities indoors",
                         "Seek medical care early for breathlessness, chest tightness or persistent cough"]
        authorities = list(SOURCE_ACTIONS.get(top_key, []))
        authorities.append("Review readiness for the next GRAP stage; follow the official CAQM/CPCB triggers")
        if peak_cat >= 3:
            authorities.append(f"~{pop_poor / 1e6:.1f} million residents forecast in 'Poor' or worse air at some point - "
                               "alert hospitals and issue public advisories ahead of the peak")
        if hotspots:
            authorities.append("Focus field teams on: " + ", ".join(hotspots))
    return dict(headline=headline, citizens=citizens, authorities=authorities, hotspots=hotspots,
                disclaimer="Advisory generated from a model forecast. Follow official orders.")
