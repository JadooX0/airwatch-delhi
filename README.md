# AirWatch Delhi

**A 72-hour PM2.5 forecast for Delhi that also answers: where is the pollution coming from, who will be exposed, and what should people and authorities do?**

Built for the [Environmental Hacks](https://www.wemakedevs.org/aws/env) hackathon (WeMakeDevs × AWS, Bharat Builds Tour, Oct 2026).

| | |
|---|---|
| Live demo | **TODO: paste your S3 website URL** |
| Demo video | **TODO: paste your YouTube link** |
| Team | **TODO: names** |

**TODO: add 2–3 screenshots of the real-data dashboard here** (`docs/screenshots/*.png`).

## What it does

1. **Forecasts** PM2.5 for 12 Delhi stations out to 72 hours (gradient-boosted model per horizon, trained on station history + weather forecasts + an upwind stubble-fire index).
2. **Attributes sources (indicative)**: biomass burning, traffic, dust, industry, other, from transparent rules on wind direction, upwind fire counts, NO₂ and the PM2.5/PM10 ratio, with the evidence shown.
3. **Maps exposure**: interpolates the forecast onto a grid and weights by population ("people exposed" view, Now → +72 h).
4. **Recommends actions** for citizens and for authorities, driven by the forecast and the dominant source.
5. **Simulates what-ifs**: first-order estimate of how much a traffic / dust / industry intervention would lower the forecast peak.

## Architecture

```
Open-Meteo (weather + CAMS air quality) ┐
OpenAQ ground sensors  (API key)        ├──► AWS Lambda (Python 3.12) ──► Amazon S3 ──► Dashboard
NASA FIRMS fire detections (API key)    ┘     ▲  ingest → forecast →      data.json     (S3 static website,
                                              │  attribute → exposure →                  Leaflet + OSM)
                                  Amazon EventBridge (hourly)  recommend → simulate
```

### How AWS is used
- **AWS Lambda** runs the whole pipeline (ingest, model training and inference, analysis) on every invocation.
- **Amazon EventBridge** triggers it every hour.
- **Amazon S3** stores the generated `data.json` and hosts the static dashboard.

## Quick start (local, no AWS needed)

```bash
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                     # optional: add your API keys
python src/pipeline.py --mode synthetic --out dashboard/data.json   # offline demo data
python src/pipeline.py --mode live --out dashboard/data.json        # real data (needs internet)
python -m http.server 8000 --directory dashboard         # open http://localhost:8000
```

`--mode synthetic` generates **made-up** data for development; the dashboard shows a banner whenever it is used.

### API keys (free, optional but strongly recommended)
| Key | Where | Effect if missing |
|---|---|---|
| `OPENAQ_API_KEY` | openaq.org | Falls back to coarse CAMS model data; stations look nearly identical |
| `FIRMS_MAP_KEY` | firms.modaps.eosdis.nasa.gov/api | No stubble-burning signal |

## Deploy to AWS (no Docker needed)

Use region `ap-south-1`. Everything below can be done in the AWS console.

1. **S3 bucket**: create `airwatch-delhi-<unique>`. Under *Permissions* untick "Block all public access"; add this bucket policy (replace the bucket name); under *Properties → Static website hosting* enable it with index document `index.html`. Upload `dashboard/index.html`.
   ```json
   {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":"arn:aws:s3:::YOUR-BUCKET/*"}]}
   ```
2. **Build the Lambda package** (works on Windows/macOS/Linux; downloads Linux wheels, ~1 min):
   ```bash
   python scripts/build_lambda_zip.py        # → build/airwatch-lambda.zip (~63 MB)
   ```
   Upload that zip into your bucket (for example under `deploy/`). It is above the console's 50 MB direct-upload limit, so Lambda must pull it from S3.
3. **Lambda function**: *Create function → Author from scratch*, runtime **Python 3.12**, architecture **x86_64**. Then *Code → Upload from → Amazon S3 location* and paste the zip's S3 URL. *Runtime settings → Edit → Handler* = `lambda_handler.handler`.
   - *Configuration → General*: memory 3008 MB (or your account's maximum), timeout 5 min.
   - *Environment variables*: `BUCKET` = your bucket, `OPENAQ_API_KEY`, `FIRMS_MAP_KEY`.
   - *Permissions → execution role → add inline policy* allowing `s3:PutObject` on `arn:aws:s3:::YOUR-BUCKET/data.json`.
   - Click **Test** once. `data.json` should appear in the bucket.
4. **Schedule**: *Add trigger → EventBridge (CloudWatch Events) → new rule → Schedule expression* `rate(1 hour)`.
5. Open the bucket's website endpoint (S3 → Properties → Static website hosting).

## Data sources
Open-Meteo (weather, CAMS air-quality model) · OpenAQ (ground sensors) · NASA FIRMS (fire detections) · OpenStreetMap tiles · Leaflet. Licences and credits: [CREDITS.md](CREDITS.md).

## Limitations (please read)
- **Source attribution is a heuristic**, not chemical source apportionment. Shares are indicative; the evidence behind each is shown.
- **The what-if simulator is a first-order scenario estimate** built from those shares and stated controllability assumptions (`src/config.py → CONTROLLABLE`). It is not a dispersion model.
- **Station coordinates** are approximate and **the population surface is a placeholder** (smooth blobs, ~20 M people), not a census raster. **TODO: update this line if you replace either.**
- **Forecast accuracy**: the dashboard's *About* tab shows hold-out error vs a "same as now" baseline. The model is trained on analysed weather but run on forecast weather, so 48–72 h skill is somewhat optimistic.
- Advisory only. Follow official CPCB / CAQM orders.

## Tests
```bash
python tests/mock_live_test.py     # exercises the live-data code path against mocked API responses (offline)
```

## Built with AI assistance
The initial scaffold of the pipeline, dashboard and docs was written with Claude (Anthropic) during the hackathon. **TODO: edit this to describe what you changed or added yourself.** See [CREDITS.md](CREDITS.md).

## Project layout
```
src/            pipeline, ingest, forecast, attribution, exposure, recommend, simulate, synthetic, lambda_handler
dashboard/      index.html (Leaflet UI); data.json is generated, not committed
scripts/        build_lambda_zip.py (Docker-free Lambda package)
tests/          mock_live_test.py
```

## License
MIT, see [LICENSE](LICENSE).
