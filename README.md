# AirWatch Delhi

### From air-quality data to environmental action.

> **Track:** Air
> **Built with:** AWS Lambda · Amazon S3 · Amazon EventBridge · Python · Leaflet · NASA FIRMS · Open-Meteo/CAMS · OpenAQ

**AirWatch Delhi** is an environmental decision-support platform that goes beyond telling people *how bad the air is*.

It combines air-quality measurements, weather conditions and satellite fire detections to help answer four more useful questions:

**Where is the pollution worst? → What may be contributing to it? → What happens next? → What can we do about it?**

---

## The Problem

Delhi already has plenty of AQI numbers.

Knowing that the AQI is *"Severe"* is important, but that number alone does not tell citizens or decision-makers:

* Which areas are experiencing the highest pollution?
* How could PM2.5 change over the next few days?
* What environmental signals may explain the pollution?
* Which communities may experience the greatest exposure?
* What interventions could potentially reduce that exposure?

Most air-quality dashboards stop at **monitoring**.

AirWatch Delhi is designed to move from:

**Monitoring → Understanding → Forecasting → Action**

---

## Our Solution

AirWatch Delhi brings multiple environmental signals into one interactive platform.

It provides:

### Hyperlocal Pollution Map

Explore PM2.5 conditions across monitoring locations in Delhi instead of relying on one city-wide AQI number.

###  72-Hour Forecast

AirWatch uses historical pollution and meteorological conditions to estimate how PM2.5 could evolve over the next 72 hours.

### Pollution Source Signals

Weather, temporal patterns, pollution measurements and NASA FIRMS satellite fire detections are combined to estimate signals associated with potential pollution sources such as:

* biomass burning
* traffic
* dust
* industry
* other sources

These are **decision-support indicators**, not a replacement for chemical source-apportionment studies.

### Exposure Intelligence

AirWatch connects pollution concentrations with population information to communicate environmental risk in terms of **people and places**, not just pollutant measurements.

### Citizen & Authority Recommendations

Instead of stopping at *"air quality is poor,"* the platform translates environmental conditions into understandable actions for citizens and decision-makers.

###  What-If Intervention Simulator

Decision-makers can explore scenarios such as reducing:

* traffic emissions
* dust-generating activities
* biomass-burning influence
* industrial emissions

AirWatch estimates how those changes could affect PM2.5 and exposure.

The simulator is intended for **comparative decision support**, rather than as a full atmospheric chemistry or dispersion model.

---

# Built on AWS

AWS powers the automated data-to-dashboard workflow behind AirWatch Delhi.

```text
      AIR-QUALITY DATA
            +
        WEATHER DATA
            +
 NASA FIRMS FIRE DETECTIONS
            │
            ▼
     ┌──────────────┐
     │  AWS Lambda  │
     │              │
     │ Data cleaning│
     │ Forecasting  │
     │ Attribution  │
     │ Exposure     │
     │ Simulation   │
     └──────┬───────┘
            │
            ▼
      ┌───────────┐
      │ Amazon S3 │
      │ data.json │
      └─────┬─────┘
            │
            ▼
     AIRWATCH DELHI
        DASHBOARD


 Amazon EventBridge
        │
        │ scheduled trigger
        ▼
     AWS Lambda
```

## AWS Services

### AWS Lambda

Runs the AirWatch environmental data pipeline without requiring a continuously running server.

The pipeline collects the latest available environmental data, processes it and generates the data consumed by the dashboard.

### Amazon S3

Stores the generated AirWatch dataset (`data.json`) and can host the static web dashboard.

### Amazon EventBridge

Schedules the Lambda pipeline so environmental data and forecasts can be refreshed automatically.

Together:

**EventBridge → Lambda → S3 → AirWatch**

turns AirWatch from a static visualization into an automatically updating environmental intelligence system.

---

# How AirWatch Works

```text
OpenAQ ───────────────┐
                      │
Open-Meteo / CAMS ────┼──► Data Collection
                      │
NASA FIRMS ────────────┘
                              │
                              ▼
                       Clean & Process
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
             PM2.5 Forecast      Source Signals
                    │                   │
                    └─────────┬─────────┘
                              ▼
                       Exposure Model
                              │
                              ▼
                      Recommendations
                              │
                              ▼
                    What-If Simulator
                              │
                              ▼
                       AirWatch UI
```

---

#  Environmental Data

AirWatch combines multiple data sources because no single dataset explains urban air pollution.

### NASA FIRMS

Satellite-derived active-fire detections provide signals for regional biomass-burning activity.

### OpenAQ

Provides access to air-quality monitoring observations where available.

### Open-Meteo / CAMS

Provides meteorological and atmospheric information used by the forecasting and source-signal pipeline.

Combining these datasets allows AirWatch to examine the relationship between **pollution + weather + fire activity + location + time**.

---

#  Who Is AirWatch For?

## Citizens

A resident should not need to understand atmospheric science to make sense of the air around them.

AirWatch presents environmental information visually and translates technical measurements into understandable risk information and recommendations.

## Decision-Makers

Authorities can use the platform to identify high-risk locations, examine possible pollution-source signals, inspect upcoming conditions and compare potential interventions.

---

# Why AirWatch Is Different

Traditional AQI dashboard:

```text
PM2.5 = 180 µg/m³
        ↓
     "Severe"
```

AirWatch:

```text
What is happening?
        ↓
Where is it happening?
        ↓
What may be contributing?
        ↓
What could happen next?
        ↓
Who could be exposed?
        ↓
What can we do?
```

AirWatch is therefore designed around **decisions**, not just measurements.

---

# Tech Stack

| Layer             | Technology                        |
| ----------------- | --------------------------------- |
| Cloud             | AWS                               |
| Compute           | AWS Lambda                        |
| Storage / Hosting | Amazon S3                         |
| Scheduling        | Amazon EventBridge                |
| Data processing   | Python                            |
| Data analysis     | Pandas / NumPy                    |
| Forecasting       | Python-based forecasting pipeline |
| Maps              | Leaflet                           |
| Frontend          | HTML / CSS / JavaScript           |
| Fire intelligence | NASA FIRMS                        |
| Air quality       | OpenAQ / CAMS                     |
| Weather           | Open-Meteo                        |

---

# Running Locally

Clone the repository:

```bash
git clone https://github.com/JadooX0/airwatch-delhi.git
cd airwatch-delhi
```

Create a Python virtual environment:

```bash
python -m venv .venv
```

### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# Environment Variables

Create a `.env` file using `.env.example` as the template.

```env
OPENAQ_API_KEY=your_key_here
FIRMS_MAP_KEY=your_key_here
```

**Never commit `.env` or API keys to GitHub.**

---

# Generate Live Data

Run:

```bash
python src/pipeline.py --mode live --out dashboard/data.json
```

The pipeline collects available environmental information and generates the dataset consumed by the dashboard.

---

#  Run the Dashboard

```bash
python -m http.server 8000 --directory dashboard
```

Then visit:

```text
http://localhost:8000
```

---

#  AWS Deployment

The production workflow is:

```text
Amazon EventBridge
        ↓
    AWS Lambda
        ↓
Environmental pipeline
        ↓
     Amazon S3
        ↓
    data.json
        ↓
AirWatch Dashboard
```

A Lambda deployment package can be prepared using:

```bash
python scripts/build_lambda_zip.py
```

Configure the Lambda environment variables:

```text
OPENAQ_API_KEY
FIRMS_MAP_KEY
S3_BUCKET
```

The Lambda execution role should have permission to write the generated output to the project's S3 bucket.

EventBridge can then trigger the function on a schedule.

---

# Scientific Scope & Limitations

AirWatch is a **hackathon prototype and decision-support system**, not a regulatory air-quality or atmospheric-chemistry model.

In particular:

**Source attribution** represents indicative signals inferred from available environmental variables. Definitive pollution-source attribution normally requires techniques such as chemical speciation and validated atmospheric modelling.

**What-if scenarios** are comparative estimates and should not be interpreted as guaranteed real-world reductions.

**Forecast accuracy** depends on the quality and availability of input measurements and meteorological data.

**Exposure estimates** depend on the resolution and reliability of the population data available to the system.

These limitations are surfaced deliberately rather than presenting uncertain environmental estimates as ground truth.

---

# What's Next?

With additional time and data, AirWatch could be extended with:

* validated high-resolution population datasets
* additional CPCB monitoring observations
* satellite aerosol products
* traffic-intensity datasets
* higher-resolution meteorological modelling
* calibrated ML forecasting
* atmospheric dispersion modelling
* uncertainty intervals
* intervention-cost modelling
* personalized low-exposure routing

The long-term goal is to move from simply **observing pollution** toward helping communities make **better environmental decisions before exposure occurs**.

---

