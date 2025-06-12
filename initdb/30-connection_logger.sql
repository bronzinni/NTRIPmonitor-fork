CREATE TABLE IF NOT EXISTS connection_logger (
    id SERIAL PRIMARY KEY,
    mountpoint_id SERIAL, -- REFERENCES mountpoints(mountpoint_id),
    disconnect_time TIMESTAMP WITHOUT TIME ZONE,
    reconnect_time TIMESTAMP WITHOUT TIME ZONE
);