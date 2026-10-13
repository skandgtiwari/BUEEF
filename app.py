import sqlite3
from pathlib import Path

from flask import Flask, jsonify, render_template

from optimize import (
    CO2_KG_PER_KWH,
    RATE_PER_KWH,
    load_readings,
    simulate_scenario,
)


app = Flask(__name__)
DATABASE = Path(__file__).resolve().with_name("bueef.db")
# Fresh deployments have no persisted database, so generate the initial dataset.
if not DATABASE.exists():
    import generator
    generator.main()

COMBINED_RULES = ("motion_sensor", "server_setback", "lab_shutdown")


@app.route("/")
def dashboard():
    # Open SQLite in read-only mode so serving the dashboard cannot change the dataset.
    database_uri = f"file:{DATABASE.as_posix()}?mode=ro"
    with sqlite3.connect(database_uri, uri=True) as connection:
        # Ranked zone totals supply the dashboard bar chart.
        zone_rows = connection.execute(
            """
            SELECT zones.name, SUM(readings.energy_kwh) AS total_kwh
            FROM readings
            JOIN zones ON zones.id = readings.zone_id
            GROUP BY zones.id, zones.name
            ORDER BY total_kwh DESC, zones.id
            """
        ).fetchall()

        # Hourly totals use the timestamp's HH field, matching analysis.py.
        hour_rows = connection.execute(
            """
            SELECT
                CAST(substr(timestamp, 12, 2) AS INTEGER) AS hour,
                SUM(energy_kwh) AS total_kwh
            FROM readings
            GROUP BY hour
            ORDER BY hour
            """
        ).fetchall()

        # Compute energy, tariff cost, and grid emissions from actual readings.
        total_kwh = connection.execute(
            "SELECT COALESCE(SUM(energy_kwh), 0) FROM readings"
        ).fetchone()[0]

        # Reuse optimize.py's simulator for the combined savings estimate.
        readings = load_readings(connection)
        optimized_kwh = simulate_scenario(readings, COMBINED_RULES)

    savings_kwh = total_kwh - optimized_kwh
    data = {
        "energy_per_zone": [
            {"name": name, "kwh": round(kwh, 2)} for name, kwh in zone_rows
        ],
        "energy_by_hour": [
            {"hour": hour, "kwh": round(kwh, 2)} for hour, kwh in hour_rows
        ],
        "summary": {
            "total_kwh": round(total_kwh, 2),
            "total_cost": round(total_kwh * RATE_PER_KWH, 2),
            "total_co2_kg": round(total_kwh * CO2_KG_PER_KWH, 2),
        },
        "savings": {
            "baseline_kwh": round(total_kwh, 2),
            "optimized_kwh": round(optimized_kwh, 2),
            "savings_kwh": round(savings_kwh, 2),
            "savings_percent": (
                round(savings_kwh / total_kwh * 100, 2) if total_kwh else 0.0
            ),
            "cost_saved": round(savings_kwh * RATE_PER_KWH, 2),
            "co2_avoided_kg": round(savings_kwh * CO2_KG_PER_KWH, 2),
        },
    }
    return render_template("dashboard.html", data=data)


@app.route("/api/readings")
def api_readings():
    # Return the source rows needed by the browser-side optimization simulator.
    database_uri = f"file:{DATABASE.as_posix()}?mode=ro"
    with sqlite3.connect(database_uri, uri=True) as connection:
        rows = connection.execute(
            """
            SELECT
                readings.zone_id,
                zones.name AS zone_name,
                zones.type AS zone_type,
                CAST(substr(readings.timestamp, 12, 2) AS INTEGER) AS hour,
                readings.energy_kwh,
                readings.occupancy
            FROM readings
            JOIN zones ON zones.id = readings.zone_id
            ORDER BY readings.timestamp, readings.zone_id
            """
        ).fetchall()

    return jsonify(
        [
            {
                "zone_id": zone_id,
                "zone_name": zone_name,
                "zone_type": zone_type,
                "hour": hour,
                "energy_kwh": energy_kwh,
                "occupancy": occupancy,
            }
            for zone_id, zone_name, zone_type, hour, energy_kwh, occupancy in rows
        ]
    )


if __name__ == "__main__":
    app.run(host="localhost", port=5000)
