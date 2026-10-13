import sqlite3
import sys
from pathlib import Path

import pandas as pd


DATABASE = Path(__file__).resolve().with_name("bueef.db")
RATE_PER_KWH = 8.50
CO2_KG_PER_KWH = 0.71

SCENARIOS = (
    ("Motion-sensor lighting", ("motion_sensor",)),
    ("Server Room night setback", ("server_setback",)),
    ("Lab equipment auto-shutdown", ("lab_shutdown",)),
)
COMBINED_RULES = ("motion_sensor", "server_setback", "lab_shutdown")


def load_readings(connection):
    """Fetch actual readings and zone types from SQLite for simulation."""
    readings = pd.read_sql_query(
        """
        SELECT
            readings.zone_id,
            zones.name AS zone_name,
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
    if readings.empty:
        raise ValueError("No readings found in bueef.db.")

    readings["timestamp"] = pd.to_datetime(readings["timestamp"], errors="raise")
    return readings


def simulate_scenario(readings, rules):
    """Apply optimization rules in order and return the updated frame and total."""
    optimized = readings.copy()
    optimized["energy_kwh_optimized"] = optimized["energy_kwh"]
    occupied = optimized["occupancy"] > 0

    for rule in rules:
        if rule == "motion_sensor":
            # Motion sensors dim lighting only when a zone is empty.
            comfort_energy_before = optimized.loc[occupied, "energy_kwh_optimized"].copy()
            empty = optimized["occupancy"] == 0.0
            optimized.loc[empty, "energy_kwh_optimized"] *= 0.6
            if not optimized.loc[occupied, "energy_kwh_optimized"].equals(
                comfort_energy_before
            ):
                raise RuntimeError(
                    "Motion-sensor lighting changed energy in an occupied zone."
                )
        elif rule == "server_setback":
            hour = optimized["timestamp"].dt.hour
            night = (hour >= 22) | (hour < 6)
            server_night = (optimized["zone_type"] == "server") & night
            optimized.loc[server_night, "energy_kwh_optimized"] *= 0.85
        elif rule == "lab_shutdown":
            # Lab equipment is reduced only when its lab has zero occupancy.
            comfort_energy_before = optimized.loc[occupied, "energy_kwh_optimized"].copy()
            empty_lab = (
                (optimized["zone_type"] == "lab")
                & (optimized["occupancy"] == 0.0)
            )
            optimized.loc[empty_lab, "energy_kwh_optimized"] *= 0.3
            if not optimized.loc[occupied, "energy_kwh_optimized"].equals(
                comfort_energy_before
            ):
                raise RuntimeError(
                    "Lab auto-shutdown changed energy in an occupied zone."
                )
        else:
            raise ValueError(f"Unknown optimization rule: {rule}")

    return float(optimized["energy_kwh_optimized"].sum())


def print_scenario_report(title, baseline_kwh, optimized_kwh):
    savings_kwh = baseline_kwh - optimized_kwh
    reduction_percent = (
        savings_kwh / baseline_kwh * 100 if baseline_kwh else 0.0
    )
    cost_savings = savings_kwh * RATE_PER_KWH
    co2_avoided = savings_kwh * CO2_KG_PER_KWH

    print(f"\n{title}")
    print("-" * 58)
    print(f"Baseline total:  {baseline_kwh:>12.2f} kWh")
    print(f"Optimized total: {optimized_kwh:>12.2f} kWh")
    print(f"Energy savings:  {savings_kwh:>12.2f} kWh ({reduction_percent:.2f}%)")
    print(f"Cost savings:    ₹{cost_savings:>11,.2f}")
    print(f"CO₂ avoided:     {co2_avoided:>12.2f} kg")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with sqlite3.connect(DATABASE) as connection:
        readings = load_readings(connection)

    baseline_kwh = float(readings["energy_kwh"].sum())
    print("=" * 58)
    print("BUEEF WEEKLY ENERGY OPTIMIZATION REPORT")
    print("=" * 58)

    for title, rules in SCENARIOS:
        optimized_kwh = simulate_scenario(readings, rules)
        print_scenario_report(title, baseline_kwh, optimized_kwh)

    combined_kwh = simulate_scenario(readings, COMBINED_RULES)
    print_scenario_report("Combined policy", baseline_kwh, combined_kwh)
    print("\nComfort check: PASS — no occupied reading was changed by rules 1 or 3.")


if __name__ == "__main__":
    main()
