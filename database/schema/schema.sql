CREATE DATABASE IF NOT EXISTS bueef;

USE bueef;


-- 1. BUILDINGS
CREATE TABLE buildings (
    building_id INT PRIMARY KEY AUTO_INCREMENT,
    building_name VARCHAR(100),
    building_type VARCHAR(60),
    total_area_m2 DECIMAL(8,2),
    number_of_floors INT,
    location VARCHAR(100)
);


-- 2. ZONES
CREATE TABLE zones (
    zone_id INT PRIMARY KEY AUTO_INCREMENT,
    building_id INT,
    zone_name VARCHAR(100),
    floor_number INT,
    zone_type VARCHAR(50),
    area_m2 DECIMAL(8,2),
    max_occupancy INT,

    FOREIGN KEY (building_id)
        REFERENCES buildings(building_id)
);


-- 3. ENERGY READINGS
CREATE TABLE energy_readings (
    reading_id INT PRIMARY KEY AUTO_INCREMENT,
    zone_id INT,
    reading_timestamp DATETIME,

    tr_power_kw DECIMAL(10,3),
    lighting_power_kw DECIMAL(10,3),
    equipment_power_kw DECIMAL(10,3),
    other_power_kw DECIMAL(10,3),

    total_energy_kwh DECIMAL(10,3),

    FOREIGN KEY (zone_id)
        REFERENCES zones(zone_id)
);


-- 4. OCCUPANCY READINGS
CREATE TABLE occupancy_readings (
    occupancy_id INT PRIMARY KEY AUTO_INCREMENT,
    zone_id INT,
    reading_timestamp DATETIME,
    occupancy INT,

    FOREIGN KEY (zone_id)
        REFERENCES zones(zone_id)
);


-- 5. ENVIRONMENT READINGS
CREATE TABLE environment_readings (
    environment_id INT PRIMARY KEY AUTO_INCREMENT,
    building_id INT,
    reading_timestamp DATETIME,

    outdoor_temperature_c DECIMAL(5,2),
    outdoor_humidity_percent DECIMAL(5,2),
    solar_irradiance_w_m2 DECIMAL(8,2),
    wind_speed_m_s DECIMAL(5,2),
    solar_generation_kwh DECIMAL(10,3),

    FOREIGN KEY (building_id)
        REFERENCES buildings(building_id)
);


-- 6. INDOOR ENVIRONMENT READINGS
CREATE TABLE indoor_environment_readings (
    indoor_environment_id INT PRIMARY KEY AUTO_INCREMENT,
    zone_id INT,
    reading_timestamp DATETIME,

    indoor_temperature_c DECIMAL(5,2),
    indoor_humidity_percent DECIMAL(5,2),

    FOREIGN KEY (zone_id)
        REFERENCES zones(zone_id)
);


-- 7. OPTIMISATION RESULTS
CREATE TABLE optimisation_results (
    result_id INT PRIMARY KEY AUTO_INCREMENT,
    building_id INT,

    scenario VARCHAR(100),
    baseline_energy_kwh DECIMAL(10,3),
    optimised_energy_kwh DECIMAL(10,3),
    energy_saved_kwh DECIMAL(10,3),

    cost_saved DECIMAL(10,2),
    carbon_reduction_kg DECIMAL(10,3),

    comfort_maintained BOOLEAN,
    recommendation TEXT,

    result_timestamp DATETIME,

    FOREIGN KEY (building_id)
        REFERENCES buildings(building_id)
);