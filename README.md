# BUEEF — Building Utility & Energy Efficiency Fine-Tuner

*A Python-based energy analytics and optimisation tool that simulates a 14-zone school building, analyses its energy use, predicts hourly consumption, compares energy-saving scenarios, and displays results on a Flask dashboard.*

## Problem

Schools waste significant electricity in empty rooms, after-hours, and via always-on equipment. They need to know where energy goes, and how to reduce consumption, cost, and emissions without compromising classroom comfort or essential operations.

## Features

- Synthetic data generator — 14 zones × 48 half-hour slots × 7 days = 4,704 readings, with realistic ±8% variation
- SQL analysis — energy by zone, floor, and hour; cost and CO₂ estimates; after-hours waste detection
- Validation — 8 automated checks on data integrity (row count, gaps, ranges, foreign keys)
- Machine learning — RandomForestRegressor vs a naive baseline, with time-based train/test split and MAE/RMSE evaluation
- Anomaly detection — flags readings exceeding 2 standard deviations of training residuals
- Optimisation — three scenarios (motion sensors, server setback, lab shutdown) with an enforced comfort constraint
- Dashboard — Flask app with KPI cards, zone bar chart, hourly line chart, and optimisation table

## Tech Stack

Python 3.10+, SQLite, pandas, numpy, scikit-learn, Flask, Chart.js

## How to Run

```text
pip install -r requirements.txt
python generator.py     # generate 7 days of data into bueef.db
python validate.py      # verify data integrity
python analysis.py      # print SQL analysis report
python predict.py       # train models + detect anomalies
python optimize.py      # simulate energy-saving scenarios
python app.py           # launch dashboard at http://localhost:5000
```

## Project Structure

```text
BUEEF/
├── generator.py       # synthetic data generator
├── validate.py        # 8 data integrity checks
├── analysis.py        # SQL analysis report
├── predict.py         # ML prediction + anomaly detection
├── optimize.py        # optimisation scenarios
├── app.py             # Flask web app
├── templates/         # HTML for dashboard
├── static/            # CSS for dashboard
├── requirements.txt
└── README.md
```

## Key Results

Weekly figures from the 7-day simulation:

- Total consumption: 595.94 kWh
- After-hours waste: 28% of total consumption
- Prediction: RandomForest MAE 0.0077 kWh vs baseline 0.0257 kWh
- Optimisation: 19.40% savings — 115.58 kWh, ₹982.47, 82.07 kg CO₂ avoided
- Comfort constraint: verified — no occupied reading was modified by any rule

## Limitations

- Uses a simulated dataset, not real sensor readings
- Tariff (₹8.50/kWh) and grid emission factor (0.71 kg CO₂/kWh) are fixed constants
- Occupancy model is simplified (weekday/weekend + hour-of-day)
- Does not control real building systems; scenarios are simulated estimates

## Author

Skand Gokarmo Tiwari
