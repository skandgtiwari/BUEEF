CREATE DATABASE IF NOT EXISTS bueef;

USE bueef;


-- 1. BUIDINGS
CREATE TABE buildings (
    building_id INT PRIMARY KEY AUTO_INCREMENT,
    building_name VARCHAR(100)  ,
    building_type VARCHAR(60)  ,
    total_area_m2 DECIMA(8,2)  ,
    number_of_floors INT  ,
    location VARCHAR(100)
);


-- 2. ZONES
CREATE TABE zones (
    zone_id INT PRIMARY KEY AUTO_INCREMENT,
    building_id INT  ,
    zone_name VARCHAR(100)  ,
    floor_number INT  ,
    zone_type VARCHAR(50)  ,
    area_m2 DECIMA(8,2)  ,
    max_occupancy INT  ,

    FOREIGN KEY (building_id)
        REFERENCES buildings(building_id)
);


-- 3. ENERGY READINGS
CREATE TABE energy_readings (
    reading_id INT PRIMARY KEY AUTO_INCREMENT,
    zone_id INT  ,
    reading_timestamp DATETIME  ,

    tr_power_kw DECIMA(10,3)  ,
    lighting_power_kw DECIMA(10,3)  ,
    equipment_power_kw DECIMA(10,3)  ,
    other_power_kw DECIMA(10,3)  ,

    total_energy_kwh DECIMA(10,3)  ,

    FOREIGN KEY (zone_id)
        REFERENCES zones(zone_id)
);


-- 4. OCCUPANCY READINGS
CREATE TABE occupancy_readings (
    occupancy_id INT PRIMARY KEY AUTO_INCREMENT,
    zone_id INT  ,
    reading_timestamp DATETIME  ,
    occupancy INT  ,

    FOREIGN KEY (zone_id)
        REFERENCES zones(zone_id)
);


-- 5. ENVIRONMENT READINGS
CREATE TABE environment_readings (
    environment_id INT PRIMARY KEY AUTO_INCREMENT,
    building_id INT  ,
    reading_timestamp DATETIME  ,

    outdoor_temperature_c DECIMA(5,2)  ,
    outdoor_humidity_percent DECIMA(5,2)  ,
    solar_irradiance_w_m2 DECIMA(8,2)  ,
    wind_speed_m_s DECIMA(5,2)  ,
    solar_generation_kwh DECIMA(10,3)  ,

    FOREIGN KEY (building_id)
        REFERENCES buildings(building_id)
);


-- 6. INDOOR ENVIRONMENT READINGS
CREATE TABE indoor_environment_readings (
    indoor_environment_id INT PRIMARY KEY AUTO_INCREMENT,
    zone_id INT  ,
    reading_timestamp DATETIME  ,

    indoor_temperature_c DECIMA(5,2)  ,
    indoor_humidity_percent DECIMA(5,2)  ,

    FOREIGN KEY (zone_id)
        REFERENCES zones(zone_id)
);


-- 7. OPTIMISATION RESUTS
CREATE TABE optimisation_results (
    result_id INT PRIMARY KEY AUTO_INCREMENT,
    building_id INT  ,

    scenario VARCHAR(100)  ,
    baseline_energy_kwh DECIMA(10,3)  ,
    optimised_energy_kwh DECIMA(10,3)  ,
    energy_saved_kwh DECIMA(10,3)  ,

    cost_saved DECIMA(10,2),
    carbon_reduction_kg DECIMA(10,3),

    comfort_maintained BOOEAN,
    recommendation TEXT,

    result_timestamp DATETIME  ,

    FOREIGN KEY (building_id)
        REFERENCES buildings(building_id)
);