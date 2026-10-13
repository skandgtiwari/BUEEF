import sqlite3


DATABASE = "bueef.db"
RATE_PER_KWH = 8.50
CO2_KG_PER_KWH = 0.71


def energy_per_zone(connection):
    print("\n1. Total energy per zone (ranked)")
    print("-" * 60)
    rows = connection.execute(
        """
        SELECT zones.name, zones.floor, SUM(readings.energy_kwh) AS total_kwh
        FROM readings
        JOIN zones ON zones.id = readings.zone_id
        GROUP BY zones.id, zones.name, zones.floor
        ORDER BY total_kwh DESC, zones.id
        """
    ).fetchall()
    print(f"{'Zone':<22} {'Floor':>5} {'Energy (kWh)':>15}")
    for name, floor, total_kwh in rows:
        print(f"{name:<22} {floor:>5} {total_kwh:>15.2f}")


def energy_by_floor(connection):
    print("\n2. Energy by floor")
    print("-" * 35)
    rows = connection.execute(
        """
        SELECT zones.floor, SUM(readings.energy_kwh) AS total_kwh
        FROM readings
        JOIN zones ON zones.id = readings.zone_id
        GROUP BY zones.floor
        ORDER BY zones.floor
        """
    ).fetchall()
    print(f"{'Floor':<10} {'Energy (kWh)':>15}")
    for floor, total_kwh in rows:
        print(f"{floor:<10} {total_kwh:>15.2f}")


def energy_by_hour(connection):
    print("\n3. Energy by hour of day")
    print("-" * 40)
    rows = connection.execute(
        """
        SELECT CAST(substr(timestamp, 12, 2) AS INTEGER) AS hour,
               SUM(energy_kwh) AS total_kwh
        FROM readings
        GROUP BY hour
        ORDER BY hour
        """
    ).fetchall()
    print(f"{'Hour':<10} {'Energy (kWh)':>15}")
    for hour, total_kwh in rows:
        print(f"{hour:02d}:00     {total_kwh:>15.2f}")


def cost_estimate(connection):
    print("\n4. Cost estimate (₹8.50 per kWh)")
    print("-" * 45)
    total_cost = connection.execute(
        "SELECT COALESCE(SUM(energy_kwh), 0) * ? FROM readings",
        (RATE_PER_KWH,),
    ).fetchone()[0]
    rows = connection.execute(
        """
        SELECT zones.name, SUM(readings.energy_kwh) * ? AS cost
        FROM readings
        JOIN zones ON zones.id = readings.zone_id
        GROUP BY zones.id, zones.name
        ORDER BY cost DESC, zones.id
        LIMIT 5
        """,
        (RATE_PER_KWH,),
    ).fetchall()
    print(f"Total estimated cost: ₹{total_cost:,.2f}")
    print("Top 5 zones by estimated cost:")
    for name, cost in rows:
        print(f"  {name:<22} ₹{cost:,.2f}")
    return total_cost


def co2_estimate(connection):
    print("\n5. CO₂ estimate (0.71 kg per kWh)")
    print("-" * 45)
    total_kg = connection.execute(
        "SELECT COALESCE(SUM(energy_kwh), 0) * ? FROM readings",
        (CO2_KG_PER_KWH,),
    ).fetchone()[0]
    print(f"Total estimated emissions: {total_kg:,.2f} kg CO₂")
    return total_kg


def after_hours_waste(connection):
    print("\n6. After-hours waste (occupancy = 0.0)")
    print("-" * 50)
    waste_kwh, total_kwh = connection.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN occupancy = ? THEN energy_kwh ELSE 0 END), 0),
            COALESCE(SUM(energy_kwh), 0)
        FROM readings
        """,
        (0.0,),
    ).fetchone()
    waste_percent = waste_kwh / total_kwh * 100 if total_kwh else 0.0
    print(f"Energy consumed in empty rooms: {waste_kwh:,.2f} kWh")
    print(f"Share of overall consumption: {waste_percent:.2f}%")

    rows = connection.execute(
        """
        SELECT zones.name, SUM(readings.energy_kwh) AS waste_kwh
        FROM readings
        JOIN zones ON zones.id = readings.zone_id
        WHERE readings.occupancy = ?
        GROUP BY zones.id, zones.name
        ORDER BY waste_kwh DESC, zones.id
        LIMIT 3
        """,
        (0.0,),
    ).fetchall()
    print("Top 3 zones by after-hours waste:")
    for name, zone_waste_kwh in rows:
        print(f"  {name:<22} {zone_waste_kwh:,.2f} kWh")


def main():
    with sqlite3.connect(DATABASE) as connection:
        energy_per_zone(connection)
        energy_by_floor(connection)
        energy_by_hour(connection)
        total_cost = cost_estimate(connection)
        total_co2 = co2_estimate(connection)
        after_hours_waste(connection)
        total_kwh = connection.execute(
            "SELECT COALESCE(SUM(energy_kwh), 0) FROM readings"
        ).fetchone()[0]

    print("\nSummary")
    print("-" * 35)
    print(
        f"Total: {total_kwh:,.2f} kWh | "
        f"₹{total_cost:,.2f} | {total_co2:,.2f} kg CO₂"
    )


if __name__ == "__main__":
    main()
