CREATE TABLE IF NOT EXISTS coordinates (
    coordinate_id SERIAL,
    mountpoint_id INT, -- REFERENCES mountpoints(mountpoint_id),
    ecef_x NUMERIC(10, 3),
    ecef_y NUMERIC(10, 3),
    ecef_z NUMERIC(10, 3),
    antHgt NUMERIC(10, 3),
    PRIMARY KEY (coordinate_id, mountpoint_id)
);
