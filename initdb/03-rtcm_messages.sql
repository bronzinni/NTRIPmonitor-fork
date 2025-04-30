CREATE TABLE IF NOT EXISTS rtcm_messages (
    rtcm_id BIGSERIAL,
    mountpoint_id INT REFERENCES mountpoints(mountpoint_id),
    msg_type SMALLINT NOT NULL,
    msg_size INTEGER,
    time_received TIMESTAMPTZ NOT NULL,
    obs_epoch TIMESTAMPTZ,
    sat_count SMALLINT
);

CREATE UNIQUE INDEX idx_time_id ON rtcm_messages(time_received, rtcm_id);

SELECT create_hypertable('rtcm_messages', by_range('time_received'));

CREATE INDEX ON rtcm_messages(time_received, mountpoint_id, rtcm_id);
CREATE INDEX ON rtcm_messages(time_received, mountpoint_id, rtcm_id, msg_type);

SELECT drop_chunks('rtcm_messages', older_than => INTERVAL '2 months');
SELECT add_retention_policy('rtcm_messages', INTERVAL '2 months');
