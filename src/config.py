
from dataclasses import dataclass

TZ = "Asia/Kolkata"


@dataclass(frozen=True)
class Station:
    id: str
    name: str
    lat: float
    lon: float
    kind: str   # traffic | industrial | residential | mixed
    pop: float  # relative population weight (placeholder)


STATIONS = [
    Station("anand_vihar", "Anand Vihar", 28.6469, 77.3152, "traffic", 1.3),
    Station("ito", "ITO", 28.6286, 77.2410, "traffic", 1.0),
    Station("rk_puram", "R.K. Puram", 28.5633, 77.1869, "residential", 1.0),
    Station("punjabi_bagh", "Punjabi Bagh", 28.6742, 77.1310, "mixed", 1.1),
    Station("dwarka_s8", "Dwarka Sec-8", 28.5710, 77.0712, "residential", 1.2),
    Station("rohini", "Rohini", 28.7324, 77.1177, "residential", 1.2),
    Station("okhla_p2", "Okhla Phase-2", 28.5308, 77.2712, "industrial", 1.0),
    Station("jahangirpuri", "Jahangirpuri", 28.7330, 77.1700, "industrial", 1.4),
    Station("bawana", "Bawana", 28.7762, 77.0511, "industrial", 0.8),
    Station("mundka", "Mundka", 28.6819, 77.0306, "industrial", 0.9),
    Station("vivek_vihar", "Vivek Vihar", 28.6723, 77.3152, "mixed", 1.3),
    Station("wazirpur", "Wazirpur", 28.6996, 77.1654, "industrial", 1.2),
]
KIND_CODE = {"traffic": 0, "industrial": 1, "residential": 2, "mixed": 3}

# Map extent for the exposure grid
BBOX = dict(south=28.40, west=76.84, north=28.88, east=77.35)

# Stubble-burning region (Punjab / Haryana) for NASA FIRMS: west, south, east, north
FIRE_BBOX = (73.8, 28.4, 77.6, 32.6)
FIRE_BEARING = 315.0       # approx. compass bearing Delhi -> burning region (north-west)
FIRE_SATURATION = 1500.0   # daily detections at which the biomass signal saturates (tunable)

# India NAQI PM2.5 categories (upper bounds in ug/m3)
CAT_NAMES = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
CAT_UPPER = [30, 60, 90, 120, 250]


def aqi_cat(pm: float) -> int:
    for i, u in enumerate(CAT_UPPER):
        if pm <= u:
            return i
    return 5


SOURCES = ["biomass_burning", "traffic", "dust", "industry", "other"]
SOURCE_LABELS = {
    "biomass_burning": "Stubble / biomass burning",
    "traffic": "Traffic & combustion",
    "dust": "Road / construction dust",
    "industry": "Industry & power",
    "other": "Other / regional background",
}

# Assumed share of each source that local action can cut within ~72h.
# These are ASSUMPTIONS for the what-if simulator, not measured values. Tune and state them in your pitch.
CONTROLLABLE = {
    "biomass_burning": 0.10,  # regional - Delhi can barely influence it directly
    "traffic": 0.60,
    "dust": 0.70,
    "industry": 0.60,
    "other": 0.20,
}
