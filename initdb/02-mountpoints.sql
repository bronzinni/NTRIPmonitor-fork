CREATE TABLE IF NOT EXISTS mountpoints (
    mountpoint_id SERIAL PRIMARY KEY,
    caster_id INT REFERENCES casters(caster_id) ON DELETE CASCADE,
    sitename VARCHAR(50),
    city VARCHAR(50),
    countrycode VARCHAR(50),
    latitude DECIMAL(7,4),
    longitude DECIMAL(7,4),
    receiver VARCHAR(50),
    rtcm_version VARCHAR(50),
    UNIQUE (caster_id, sitename)
);