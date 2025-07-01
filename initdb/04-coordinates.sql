CREATE TABLE IF NOT EXISTS coordinates (
    coordinate_id SERIAL,
    rtcm_id BIGINT,
    mountpoint_id INT UNIQUE, -- REFERENCES mountpoints(mountpoint_id),
    ecef_x NUMERIC(11, 4),
    ecef_y NUMERIC(11, 4),
    ecef_z NUMERIC(11, 4),
    antHgt NUMERIC(6, 4),
    PRIMARY KEY (coordinate_id, mountpoint_id)
);
