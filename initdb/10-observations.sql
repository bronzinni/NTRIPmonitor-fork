CREATE TABLE IF NOT EXISTS observations(
    obs_id BIGSERIAL,
    rtcm_id BIGINT, -- REFERENCES rtcm_messages(rtcm_id) ON DELETE CASCADE,
    obs_epoch TIMESTAMPTZ,
    sat_sys CHAR(1),
    sat_id INT,
    sat_signal CHAR(2),
    obs_code DOUBLE PRECISION,
    obs_phase DOUBLE PRECISION,
    obs_doppler DOUBLE PRECISION,
    obs_snr DOUBLE PRECISION,
    obs_lock_time_indicator INTEGER,
    PRIMARY KEY (obs_id, rtcm_id)
);

CREATE INDEX ON observations(rtcm_id);