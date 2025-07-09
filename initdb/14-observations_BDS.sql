CREATE TABLE IF NOT EXISTS observations_BDS(
    obs_id BIGSERIAL,
    rtcm_id BIGINT, -- REFERENCES rtcm_messages(rtcm_id) ON DELETE CASCADE,
    obs_epoch TIMESTAMPTZ,
    sat_id CHAR(3),
    sat_signal CHAR(3),
    obs_code DOUBLE PRECISION,
    obs_phase DOUBLE PRECISION,
    obs_doppler DOUBLE PRECISION,
    obs_snr DOUBLE PRECISION,
    obs_lock_time_indicator INTEGER,
    PRIMARY KEY (obs_id, rtcm_id)
);

CREATE INDEX ON observations_BDS(rtcm_id);