CREATE TABLE IF NOT EXISTS coordinates (
    coordinate_id SERIAL,
    rtcm_id BIGINT,
    mountpoint_id INT UNIQUE, -- REFERENCES mountpoints(mountpoint_id),
    ecef_x DOUBLE PRECISION,
    ecef_y DOUBLE PRECISION,
    ecef_z DOUBLE PRECISION,
    antHgt DOUBLE PRECISION,
    PRIMARY KEY (coordinate_id, mountpoint_id)
);
