# 7-day dataset (14 zones × 48 slots × 7 days = 4704 readings)
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


DAYS_TO_GENERATE = 7

ZONES = [
    {"id": 1, "name": "Classroom 101", "floor": 1, "type": "classroom", "capacity": 30},
    {"id": 2, "name": "Classroom 102", "floor": 1, "type": "classroom", "capacity": 30},
    {"id": 3, "name": "Classroom 103", "floor": 1, "type": "classroom", "capacity": 30},
    {"id": 4, "name": "Science Lab 1", "floor": 1, "type": "lab", "capacity": 24},
    {"id": 5, "name": "Library", "floor": 1, "type": "library", "capacity": 50},
    {"id": 6, "name": "Classroom 201", "floor": 2, "type": "classroom", "capacity": 30},
    {"id": 7, "name": "Classroom 202", "floor": 2, "type": "classroom", "capacity": 30},
    {"id": 8, "name": "Computer Lab 1", "floor": 2, "type": "lab", "capacity": 30},
    {"id": 9, "name": "Computer Lab 2", "floor": 2, "type": "lab", "capacity": 30},
    {"id": 10, "name": "Staff Room", "floor": 2, "type": "office", "capacity": 20},
    {"id": 11, "name": "Auditorium", "floor": 3, "type": "hall", "capacity": 200},
    {"id": 12, "name": "Art Room", "floor": 3, "type": "classroom", "capacity": 25},
    {"id": 13, "name": "Music Room", "floor": 3, "type": "classroom", "capacity": 30},
    {"id": 14, "name": "Server Room", "floor": 3, "type": "server", "capacity": 2},
]

BASE_LOAD = {
    "classroom": 200,
    "lab": 800,
    "library": 300,
    "office": 150,
    "hall": 500,
    "server": 1500,
}

DATABASE = Path(__file__).resolve().with_name("bueef.db")
START = datetime(2026, 1, 15, 0, 0, 0)


def occupancy_for(zone_type, timestamp):
    if zone_type == "server":
        return 1.0
    if timestamp.weekday() >= 5:
        return 0.0

    hour = timestamp.hour
    if 8 <= hour < 16:
        return 0.85 if zone_type == "classroom" else 0.7
    if 16 <= hour < 18:
        return 0.2
    return 0.0


def generate_readings(connection, days):
    """Replace readings with a seeded-range dataset and return inserted rows."""
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

    connection.execute("DELETE FROM readings")
    connection.execute("DELETE FROM sqlite_sequence WHERE name = 'readings'")
    connection.executemany(
        """
        INSERT OR REPLACE INTO zones (id, name, floor, type, capacity)
        VALUES (:id, :name, :floor, :type, :capacity)
        """,
        ZONES,
    )

    readings = []
    for day in range(days):
        for zone in ZONES:
            for interval in range(48):
                timestamp = START + timedelta(
                    days=day,
                    minutes=30 * interval,
                )
                occupancy = occupancy_for(zone["type"], timestamp)
                watts = BASE_LOAD[zone["type"]] * (0.3 + 0.7 * occupancy)
                # Noise makes energy use realistic and prevents trivial ML memorization.
                energy_kwh = round(
                    watts * 0.5 / 1000 * random.uniform(0.92, 1.08),
                    4,
                )
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
    return readings


def main():
    random.seed(42)
    with sqlite3.connect(DATABASE) as connection:
        readings = generate_readings(connection, DAYS_TO_GENERATE)
        total_energy = connection.execute(
            "SELECT SUM(energy_kwh) FROM readings"
        ).fetchone()[0]
        top_consumers = connection.execute(
            """
            SELECT zones.name, SUM(readings.energy_kwh) AS total_kwh
            FROM readings
            JOIN zones ON zones.id = readings.zone_id
            GROUP BY zones.id, zones.name
            ORDER BY total_kwh DESC, zones.id
            LIMIT 3
            """
        ).fetchall()

    print(f"Readings inserted: {len(readings)}")
    print(f"Total energy: {total_energy:.4f} kWh")
    print("Top 3 consumers:")
    for name, total_kwh in top_consumers:
        print(f"  {name}: {total_kwh:.4f} kWh")


if __name__ == "__main__":
    main()
