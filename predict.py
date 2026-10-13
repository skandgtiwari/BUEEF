import sqlite3
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

from generator import BASE_LOAD, START, ZONES, occupancy_for


DATABASE = Path(__file__).resolve().with_name("bueef.db")
INTEGER_ENCODING_FOR_COMPARISON = {
    "classroom": 0,
    "lab": 1,
    "library": 2,
    "office": 3,
    "hall": 4,
    "server": 5,
}
FEATURES = [
    "hour",
    "day_of_week",
    "is_weekend",
    "occupancy",
    "is_classroom",
    "is_lab",
    "is_library",
    "is_office",
    "is_hall",
    "is_server",
]
INTEGER_FEATURES = [
    "hour",
    "day_of_week",
    "is_weekend",
    "occupancy",
    "zone_type_integer",
]
HALF_HOUR_SLOTS_PER_DAY = 48
DAYS_TO_GENERATE = 7
TRAINING_DAYS = 6


def regenerate_seven_day_dataset(connection):
    """Create a fresh week of half-hour readings using generator.py's zones."""
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS zones (
            id INTEGER PRIMARY KEY,
            name TEXT,
            floor INTEGER,
            type TEXT,
            capacity INTEGER
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id INTEGER,
            timestamp TEXT,
            energy_kwh REAL,
            occupancy REAL,
            FOREIGN KEY(zone_id) REFERENCES zones(id)
        )
        """
    )

    # Replace previous readings so each run trains on exactly this generated week.
    connection.execute("DELETE FROM readings")
    connection.executemany(
        """
        INSERT OR REPLACE INTO zones (id, name, floor, type, capacity)
        VALUES (:id, :name, :floor, :type, :capacity)
        """,
        ZONES,
    )

    readings = []
    for day in range(DAYS_TO_GENERATE):
        for zone in ZONES:
            for slot in range(HALF_HOUR_SLOTS_PER_DAY):
                timestamp = START + timedelta(
                    days=day,
                    minutes=30 * slot,
                )
                occupancy = occupancy_for(zone["type"], timestamp)
                watts = BASE_LOAD[zone["type"]] * (0.3 + 0.7 * occupancy)
                energy_kwh = round(watts * 0.5 / 1000, 4)
                readings.append(
                    (
                        zone["id"],
                        timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        energy_kwh,
                        occupancy,
                    )
                )

    connection.executemany(
        """
        INSERT INTO readings (zone_id, timestamp, energy_kwh, occupancy)
        VALUES (?, ?, ?, ?)
        """,
        readings,
    )
    return len(readings)


def load_hourly_readings(connection):
    """Fetch raw rows with SQLite, then combine two half-hour rows into an hour."""
    raw = pd.read_sql_query(
        """
        SELECT
            readings.zone_id,
            zones.name AS zone_name,
            zones.floor,
            zones.type AS zone_type,
            readings.timestamp,
            readings.energy_kwh,
            readings.occupancy
        FROM readings
        JOIN zones ON zones.id = readings.zone_id
        ORDER BY readings.timestamp, readings.zone_id
        """,
        connection,
    )
    if raw.empty:
        raise ValueError("No readings were loaded from bueef.db.")

    raw["timestamp"] = pd.to_datetime(raw["timestamp"], errors="raise")
    # Combine the two half-hour samples: sum energy and average occupancy.
    raw["hour_timestamp"] = raw["timestamp"].dt.floor("h")
    hourly = (
        raw.groupby(
            ["zone_id", "zone_name", "floor", "zone_type", "hour_timestamp"],
            as_index=False,
            sort=True,
        )
        .agg(
            energy_kwh=("energy_kwh", "sum"),
            occupancy=("occupancy", "mean"),
        )
        .rename(columns={"hour_timestamp": "timestamp"})
    )

    # Derive time features, then represent zone type with separate binary features.
    hourly["hour"] = hourly["timestamp"].dt.hour
    hourly["day_of_week"] = hourly["timestamp"].dt.dayofweek
    hourly["is_weekend"] = (hourly["day_of_week"] >= 5).astype(int)

    zone_type_columns = {
        "classroom": "is_classroom",
        "lab": "is_lab",
        "library": "is_library",
        "office": "is_office",
        "hall": "is_hall",
        "server": "is_server",
    }
    # Integer category codes imply a false order and equal spacing between zone types.
    for zone_type, column in zone_type_columns.items():
        hourly[column] = (hourly["zone_type"] == zone_type).astype(int)

    hourly["zone_type_integer"] = hourly["zone_type"].map(
        INTEGER_ENCODING_FOR_COMPARISON
    )
    if hourly[["zone_type_integer", *FEATURES[4:]]].isna().any().any():
        raise ValueError("A zone has a type that is missing from the encoding map.")

    return hourly


def mean_absolute_error(actual, predicted):
    return float(np.mean(np.abs(actual - predicted)))


def root_mean_squared_error(actual, predicted):
    return float(np.sqrt(np.mean(np.square(actual - predicted))))


def evaluate_models(hourly):
    """Train on the first six days and evaluate on the seventh day."""
    test_start = pd.Timestamp(START + timedelta(days=TRAINING_DAYS))
    test_end = pd.Timestamp(START + timedelta(days=DAYS_TO_GENERATE))
    training = hourly[hourly["timestamp"] < test_start].copy()
    testing = hourly[
        (hourly["timestamp"] >= test_start)
        & (hourly["timestamp"] < test_end)
    ].copy()

    expected_training_rows = len(ZONES) * 24 * TRAINING_DAYS
    expected_test_rows = len(ZONES) * 24
    if len(training) != expected_training_rows or len(testing) != expected_test_rows:
        raise ValueError(
            "Expected "
            f"{expected_training_rows} hourly training rows and "
            f"{expected_test_rows} test rows; got "
            f"{len(training)} and {len(testing)}."
        )

    # A random split would let later readings appear in training and leak future data.
    x_train = training[FEATURES]
    y_train = training["energy_kwh"].to_numpy()
    x_test = testing[FEATURES]
    y_test = testing["energy_kwh"].to_numpy()

    # The baseline uses each zone's historical mean for the matching hour.
    baseline_by_zone_hour = (
        training.groupby(["zone_id", "hour"])["energy_kwh"].mean().to_dict()
    )
    baseline_predictions = np.array(
        [
            baseline_by_zone_hour[(zone_id, hour)]
            for zone_id, hour in zip(testing["zone_id"], testing["hour"])
        ]
    )

    # Fit the regression only on training rows, then predict the later test day.
    integer_model = LinearRegression()
    integer_model.fit(training[INTEGER_FEATURES], y_train)
    integer_predictions = integer_model.predict(testing[INTEGER_FEATURES])

    baseline_mae = mean_absolute_error(y_test, baseline_predictions)
    baseline_rmse = root_mean_squared_error(y_test, baseline_predictions)
    integer_mae = mean_absolute_error(y_test, integer_predictions)
    integer_rmse = root_mean_squared_error(y_test, integer_predictions)

    one_hot_model = LinearRegression()
    one_hot_model.fit(x_train, y_train)
    one_hot_predictions = one_hot_model.predict(x_test)
    one_hot_mae = mean_absolute_error(y_test, one_hot_predictions)
    one_hot_rmse = root_mean_squared_error(y_test, one_hot_predictions)

    forest_model = RandomForestRegressor(n_estimators=100, random_state=42)
    forest_model.fit(x_train, y_train)
    # Energy targets are stored to four decimals; match that precision to avoid
    # treating floating-point residue as a real prediction error.
    forest_predictions = np.round(forest_model.predict(x_test), 4)
    forest_mae = mean_absolute_error(y_test, forest_predictions)
    forest_rmse = root_mean_squared_error(y_test, forest_predictions)

    # Use the forest's training residuals to set its anomaly alert threshold.
    training_predictions = np.round(forest_model.predict(x_train), 4)
    training_residuals = y_train - training_predictions
    residual_std_dev = float(np.std(training_residuals))
    anomaly_threshold = 2 * residual_std_dev

    testing["forest_prediction"] = forest_predictions
    testing["absolute_error"] = np.abs(y_test - forest_predictions)
    anomalies = testing[testing["absolute_error"] > anomaly_threshold].copy()

    return {
        "training": training,
        "testing": testing,
        "baseline_mae": baseline_mae,
        "baseline_rmse": baseline_rmse,
        "integer_mae": integer_mae,
        "integer_rmse": integer_rmse,
        "one_hot_mae": one_hot_mae,
        "one_hot_rmse": one_hot_rmse,
        "forest_mae": forest_mae,
        "forest_rmse": forest_rmse,
        "residual_std_dev": residual_std_dev,
        "anomaly_threshold": anomaly_threshold,
        "anomalies": anomalies,
    }


def print_report(result, reading_count):
    print("=" * 72)
    print("BUEEF HOURLY ENERGY PREDICTION & ANOMALY REPORT")
    print("=" * 72)
    print("\nDataset and split")
    print("-" * 72)
    print(
        f"Generated {reading_count:,} half-hour readings over "
        f"{DAYS_TO_GENERATE} days."
    )
    print(
        f"Training: first {TRAINING_DAYS} days "
        f"({len(result['training']):,} hourly zone readings)"
    )
    print(
        f"Testing: day 7 "
        f"({len(result['testing']):,} hourly zone readings)"
    )

    print("\nModel comparison (test day)")
    print("-" * 72)
    print(f"{'Model':<24} {'MAE (kWh)':>16} {'RMSE (kWh)':>18}")
    models = [
        ("Baseline (zone/hour)", "baseline"),
        ("Linear (integer encoding)", "integer"),
        ("Linear (one-hot)", "one_hot"),
        ("Random Forest", "forest"),
    ]
    for label, key in models:
        print(
            f"{label:<24} "
            f"{result[f'{key}_mae']:>16.4f} "
            f"{result[f'{key}_rmse']:>18.4f}"
        )

    best_model = min(models, key=lambda item: result[f"{item[1]}_mae"])
    print(f"Verdict: {best_model[0]} has the lowest MAE.")

    print("\nAnomaly detection (Random Forest, test day)")
    print("-" * 72)
    print(f"Training residual standard deviation: {result['residual_std_dev']:.4f} kWh")
    print(f"Flag threshold (2x standard deviation): {result['anomaly_threshold']:.4f} kWh")

    anomalies = result["anomalies"]
    if anomalies.empty:
        print("No readings exceeded the anomaly threshold.")
    else:
        print(
            f"{'Zone':<22} {'Timestamp':<19} "
            f"{'Actual':>10} {'Predicted':>10} {'Error':>10}"
        )
        for row in anomalies.itertuples(index=False):
            print(
                f"{row.zone_name:<22} {row.timestamp:%Y-%m-%d %H:%M} "
                f"{row.energy_kwh:>10.4f} "
                f"{row.forest_prediction:>10.4f} "
                f"{row.absolute_error:>10.4f}"
            )

    print("\nWhy this matters")
    print("-" * 72)
    print(
        "Baselines are often strong because they use relevant historical "
        "patterns. Linear models cannot easily capture step-function "
        "occupancy patterns, while tree models such as Random Forest can."
    )


def main():
    with sqlite3.connect(DATABASE) as connection:
        reading_count = regenerate_seven_day_dataset(connection)
        hourly = load_hourly_readings(connection)

    result = evaluate_models(hourly)
    print_report(result, reading_count)


if __name__ == "__main__":
    main()
