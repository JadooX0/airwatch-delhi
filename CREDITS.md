# Credits and third-party terms

The hackathon rules require crediting code and data you did not write. Licence summaries below are from general
knowledge; **TODO: confirm each against the provider's current terms before you submit.**

## Data and services
| Source | Used for | Attribution / terms (verify) |
|---|---|---|
| [Open-Meteo](https://open-meteo.com) | Weather forecast and history | Data CC BY 4.0, attribution required; free API tier is for non-commercial use |
| Copernicus Atmosphere Monitoring Service (CAMS), via Open-Meteo | Model PM2.5 / PM10 / NO₂ (fallback when no ground sensor) | Copernicus licence; attribute "Contains modified Copernicus Atmosphere Monitoring Service information" |
| [OpenAQ](https://openaq.org) | Ground-sensor PM2.5 / PM10 / NO₂ (CPCB and other providers) | Per-provider licences, mostly CC BY 4.0; credit OpenAQ and the original provider |
| [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov) | Active-fire detections (VIIRS) | Open NASA data; acknowledge NASA FIRMS |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | Map tiles | © OpenStreetMap contributors (ODbL); mind the tile usage policy |
| Amazon Web Services | Lambda, S3, EventBridge | n/a |

## Libraries
| Library | Licence |
|---|---|
| [Leaflet](https://leafletjs.com) 1.9.4 | BSD-2-Clause |
| NumPy, pandas, SciPy | BSD-3-Clause |
| scikit-learn | BSD-3-Clause |
| requests | Apache-2.0 |

## AI assistance
The initial scaffold of the pipeline, dashboard, build script and documentation was generated with Claude (Anthropic)
during the hackathon (9–10 Oct 2026). **TODO: replace this paragraph with what you personally changed, tested and added.**
