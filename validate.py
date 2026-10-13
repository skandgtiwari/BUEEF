import sqlite3
import sys


DATABASE = "bueef.db"
EXPECTED_READING_COUNT = 672
READINGS_PER_ZONE = 48


def check_row_count(connection):
    count = connection.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    if count != EXPECTED_READING_COUNT:
        return [f"Expected {EXPECTED_READING_COUNT} readings, found {count}."]
    return []


def check_zone_coverage(connection):
    rows = connection.execute(
        """
        SELECT zones.id, zones.name, COUNT(readings.id)
        FROM zones
        LEFT JOIN readings ON readings.zone_id = zones.id
        GROUP BY zones.id, zones.name
        HAVING COUNT(readings.id) != ?
        ORDER BY zones.id
        """,
        (READINGS_PER_ZONE,),
    ).fetchall()
    return [
        f"Zone {zone_id} ({name}) has {count} readings; expected "
        f"{READINGS_PER_ZONE}."
        for zone_id, name, count in rows
    ]


def check_nonnegative_energy(connection):
    rows = connection.execute(
        """
        SELECT id, zone_id, timestamp, energy_kwh
        FROM readings
        WHERE energy_kwh < 0
        ORDER BY id
        """
    ).fetchall()
    return [
        f"Reading {reading_id} for zone {zone_id} at {timestamp} has "
        f"negative energy ({energy_kwh})."
        for reading_id, zone_id, timestamp, energy_kwh in rows
    ]


def check_occupancy_range(connection):
    rows = connection.execute(
        """
        SELECT id, zone_id, timestamp, occupancy
        FROM readings
        WHERE occupancy IS NULL OR occupancy NOT BETWEEN 0.0 AND 1.0
        ORDER BY id
        """
    ).fetchall()
    return [
        f"Reading {reading_id} for zone {zone_id} at {timestamp} has "
        f"occupancy outside [0.0, 1.0] ({occupancy})."
        for reading_id, zone_id, timestamp, occupancy in rows
    ]


def check_duplicate_readings(connection):
    rows = connection.execute(
        """
        SELECT zone_id, timestamp, COUNT(*)
        FROM readings
        GROUP BY zone_id, timestamp
        HAVING COUNT(*) > 1
        ORDER BY zone_id, timestamp
        """
    ).fetchall()
    return [
        f"Zone {zone_id} has {count} readings at duplicate timestamp {timestamp}."
        for zone_id, timestamp, count in rows
    ]


def check_timestamp_continuity(connection):
    rows = connection.execute(
        """
        WITH ordered_readings AS (
            SELECT
                id,
                zone_id,
                timestamp,
                LAG(timestamp) OVER (
                    PARTITION BY zone_id ORDER BY timestamp, id
                ) AS previous_timestamp
            FROM readings
        )
        SELECT id, zone_id, previous_timestamp, timestamp
        FROM ordered_readings
        WHERE timestamp IS NULL
           OR (
                previous_timestamp IS NOT NULL
                AND (
                    datetime(previous_timestamp, '+30 minutes') IS NULL
                    OR datetime(timestamp) IS NULL
                    OR datetime(timestamp) !=
                       datetime(previous_timestamp, '+30 minutes')
                )
           )
        ORDER BY zone_id, timestamp, id
        """
    ).fetchall()
    return [
        f"Zone {zone_id} has a timestamp gap or invalid timestamp between "
        f"{previous_timestamp} and {timestamp} (reading {reading_id})."
        for reading_id, zone_id, previous_timestamp, timestamp in rows
    ]


def check_plausible_energy(connection):
    rows = connection.execute(
        """
        SELECT id, zone_id, timestamp, energy_kwh
        FROM readings
        WHERE energy_kwh IS NULL OR energy_kwh <= 0 OR energy_kwh >= 5.0
        ORDER BY id
        """
    ).fetchall()
    return [
        f"Reading {reading_id} for zone {zone_id} at {timestamp} has "
        f"implausible energy ({energy_kwh}); expected 0 < energy_kwh < 5.0."
        for reading_id, zone_id, timestamp, energy_kwh in rows
    ]


def check_foreign_keys(connection):
    rows = connection.execute(
        """
        SELECT readings.id, readings.zone_id
        FROM readings
        LEFT JOIN zones ON zones.id = readings.zone_id
        WHERE zones.id IS NULL
        ORDER BY readings.id
        """
    ).fetchall()
    return [
        f"Reading {reading_id} references missing zone {zone_id}."
        for reading_id, zone_id in rows
    ]


def main():
    failures = []
    checks = (
        check_row_count,
        check_zone_coverage,
        check_nonnegative_energy,
        check_occupancy_range,
        check_duplicate_readings,
        check_timestamp_continuity,
        check_plausible_energy,
        check_foreign_keys,
    )

    try:
        with sqlite3.connect(DATABASE) as connection:
            for check in checks:
                failures.extend(check(connection))
    except sqlite3.Error as error:
        failures.append(f"Could not validate {DATABASE}: {error}")

    if failures:
        print(f"❌ {len(failures)} check(s) failed:")
        for failure in failures:
            print(f"- {failure}")
        sys.exit(1)

    print("✅ All validation checks passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
