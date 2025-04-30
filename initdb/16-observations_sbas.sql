CREATE TABLE IF NOT EXISTS observations_sbas (
    obs_id BIGSERIAL,
    rtcm_id BIGINT REFERENCES rtcm_messages(rtcm_id) ON DELETE CASCADE,
    sat_id CHAR(4),
    sat_signal CHAR(3),
    obs_code NUMERIC(13, 10),
    obs_phase NUMERIC(14, 11),
    obs_doppler NUMERIC(8, 4),
    obs_snr NUMERIC(6, 4),
    obs_lock_time_indicator INTEGER,
    PRIMARY KEY (obs_id, rtcm_id)
);

SELECT drop_chunks('observations_sbas', older_than => INTERVAL '2 months');
SELECT add_retention_policy('observations_sbas', INTERVAL '2 months');
