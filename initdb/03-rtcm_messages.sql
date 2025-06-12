CREATE TABLE IF NOT EXISTS rtcm_messages (
    rtcm_id BIGSERIAL,
    mountpoint_id INT, -- REFERENCES mountpoints(mountpoint_id),
    time_received TIMESTAMPTZ NOT NULL,
    msg_type SMALLINT NOT NULL,
    msg_size INTEGER
);

CREATE UNIQUE INDEX idx_time_id ON rtcm_messages(time_received, rtcm_id);

SELECT create_hypertable('rtcm_messages', by_range('time_received'));

CREATE INDEX ON rtcm_messages(time_received, mountpoint_id, rtcm_id);
CREATE INDEX ON rtcm_messages(time_received, mountpoint_id, rtcm_id, msg_type);

SELECT drop_chunks('rtcm_messages', older_than => INTERVAL '2 weeks');
SELECT add_retention_policy('rtcm_messages', INTERVAL '2 weeks');
