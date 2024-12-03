-- Create the user and database
CREATE USER f1_user WITH PASSWORD 'admin';
CREATE DATABASE f1_db OWNER f1_user;

-- Connect to the newly created database
\connect f1_db;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE f1_db TO f1_user;


-- Core tables
CREATE TABLE IF NOT EXISTS seasons (
    year INT PRIMARY KEY,
    url VARCHAR(255) UNIQUE
);

CREATE TABLE IF NOT EXISTS circuits (
    circuit_id SERIAL PRIMARY KEY,
    circuit_ref VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    country VARCHAR(255),
    lat FLOAT,
    lng FLOAT,
    alt INT,
    url VARCHAR(255) UNIQUE
);

CREATE TABLE IF NOT EXISTS constructors (
    constructor_id SERIAL PRIMARY KEY,
    constructor_ref VARCHAR(255) NOT NULL,
    name VARCHAR(255) UNIQUE NOT NULL,
    nationality VARCHAR(255),
    url VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS drivers (
    driver_id SERIAL PRIMARY KEY,
    driver_ref VARCHAR(255) NOT NULL,
    number INT,
    code VARCHAR(3),
    forename VARCHAR(255) NOT NULL,
    surname VARCHAR(255) NOT NULL,
    dob DATE,
    nationality VARCHAR(255),
    url VARCHAR(255) UNIQUE
);

CREATE TABLE IF NOT EXISTS status (
    status_id SERIAL PRIMARY KEY,
    status VARCHAR(255) NOT NULL
);

-- Races and related tables
CREATE TABLE IF NOT EXISTS races (
    race_id SERIAL PRIMARY KEY,
    year INT NOT NULL REFERENCES seasons(year),
    round INT NOT NULL,
    circuit_id INT REFERENCES circuits(circuit_id),
    name VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    time TIME,
    url VARCHAR(255) UNIQUE,
    fp1_date DATE,
    fp1_time TIME,
    fp2_date DATE,
    fp2_time TIME,
    fp3_date DATE,
    fp3_time TIME,
    quali_date DATE,
    quali_time TIME,
    sprint_date DATE,
    sprint_time TIME
);

CREATE TABLE IF NOT EXISTS constructor_results (
    constructor_results_id SERIAL PRIMARY KEY,
    race_id INT REFERENCES races(race_id),
    constructor_id INT REFERENCES constructors(constructor_id),
    points FLOAT,
    status VARCHAR(255),
    UNIQUE(race_id, constructor_id)
);

CREATE TABLE IF NOT EXISTS constructor_standings (
    constructor_standings_id SERIAL PRIMARY KEY,
    race_id INT REFERENCES races(race_id),
    constructor_id INT REFERENCES constructors(constructor_id),
    points FLOAT NOT NULL,
    position INT,
    position_text VARCHAR(255),
    wins INT NOT NULL,
    UNIQUE(race_id, constructor_id)
);

CREATE TABLE IF NOT EXISTS driver_standings (
    driver_standings_id SERIAL PRIMARY KEY,
    race_id INT REFERENCES races(race_id),
    driver_id INT REFERENCES drivers(driver_id),
    points FLOAT NOT NULL,
    position INT,
    position_text VARCHAR(255),
    wins INT NOT NULL,
    UNIQUE(race_id, driver_id)
);

CREATE TABLE IF NOT EXISTS qualifying (
    qualify_id SERIAL PRIMARY KEY,
    race_id INT REFERENCES races(race_id),
    driver_id INT REFERENCES drivers(driver_id),
    constructor_id INT REFERENCES constructors(constructor_id),
    number INT NOT NULL,
    position INT,
    q1 VARCHAR(255),
    q2 VARCHAR(255),
    q3 VARCHAR(255),
    UNIQUE(race_id, driver_id)
);

CREATE TABLE IF NOT EXISTS results (
    result_id SERIAL PRIMARY KEY,
    race_id INT REFERENCES races(race_id),
    driver_id INT REFERENCES drivers(driver_id),
    constructor_id INT REFERENCES constructors(constructor_id),
    number INT,
    grid INT NOT NULL,
    position INT,
    position_text VARCHAR(255) NOT NULL,
    position_order INT NOT NULL,
    points FLOAT NOT NULL,
    laps INT NOT NULL,
    time VARCHAR(255),
    milliseconds INT,
    fastest_lap INT,
    rank INT,
    fastest_lap_time VARCHAR(255),
    fastest_lap_speed VARCHAR(255),
    status_id INT REFERENCES status(status_id),
    UNIQUE(race_id, driver_id)
);

CREATE TABLE IF NOT EXISTS lap_times (
    race_id INT REFERENCES races(race_id),
    driver_id INT REFERENCES drivers(driver_id),
    lap INT NOT NULL,
    position INT,
    time VARCHAR(255),
    milliseconds INT,
    PRIMARY KEY (race_id, driver_id, lap)
);

CREATE TABLE IF NOT EXISTS pit_stops (
    race_id INT REFERENCES races(race_id),
    driver_id INT REFERENCES drivers(driver_id),
    stop INT NOT NULL,
    lap INT NOT NULL,
    time TIME NOT NULL,
    duration VARCHAR(255),
    milliseconds INT,
    PRIMARY KEY (race_id, driver_id, stop)
); 