CREATE OR REPLACE FUNCTION public.insert_rtcm_messages(decodedframes json, OUT rtcm_ids bigint[])
 RETURNS bigint[]
 LANGUAGE plpgsql
AS $$
BEGIN
    -- Insert into rtcm_messages and get the IDs
    WITH insertion AS (
        INSERT INTO rtcm_messages (mountpoint_id, rtcm_msg_type, rtcm_msg_size, time_received, obs_epoch, sat_count)
        SELECT (json_array_elements->>0)::integer,
               (json_array_elements->>1)::integer,
               (json_array_elements->>2)::integer,
               (json_array_elements->>3)::timestamp without time zone,
               (json_array_elements->>4)::timestamp with time zone,
               (json_array_elements->>5)::integer
        FROM json_array_elements(decodedFrames) 
        RETURNING rtcm_id
    )
    SELECT array_agg(rtcm_id) FROM insertion INTO rtcm_ids;
END;
$$;

CREATE OR REPLACE FUNCTION public.insert_observations_gps(decodedObsFrame json)
 RETURNS VOID
 LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO observations_gps (rtcm_id, sat_id, sat_signal, obs_code, obs_phase, obs_doppler, obs_snr, obs_lock_time_indicator)
    SELECT (json_array_elements->>0)::bigint,
           (json_array_elements->>1)::char(4), 
           (json_array_elements->>2)::char(3), 
           (json_array_elements->>3)::numeric(13, 10), 
           (json_array_elements->>4)::numeric(14, 11), 
           (json_array_elements->>5)::numeric(8, 4), 
           (json_array_elements->>6)::numeric(6, 4), 
           (json_array_elements->>7)::integer
    FROM json_array_elements(decodedObsFrame);
END;
$$;


CREATE OR REPLACE FUNCTION public.insert_observations_glonass(decodedObsFrame json)
 RETURNS VOID
 LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO observations_glonass (rtcm_id, sat_id, sat_signal, obs_code, obs_phase, obs_doppler, obs_snr, obs_lock_time_indicator)
    SELECT (json_array_elements->>0)::bigint,
           (json_array_elements->>1)::char(4), 
           (json_array_elements->>2)::char(3), 
           (json_array_elements->>3)::numeric(13, 10), 
           (json_array_elements->>4)::numeric(14, 11), 
           (json_array_elements->>5)::numeric(8, 4), 
           (json_array_elements->>6)::numeric(6, 4), 
           (json_array_elements->>7)::integer
    FROM json_array_elements(decodedObsFrame);
END;
$$;


CREATE OR REPLACE FUNCTION public.insert_observations_galileo(decodedObsFrame json)
 RETURNS VOID
 LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO observations_galileo (rtcm_id, sat_id, sat_signal, obs_code, obs_phase, obs_doppler, obs_snr, obs_lock_time_indicator)
    SELECT (json_array_elements->>0)::bigint,
           (json_array_elements->>1)::char(4), 
           (json_array_elements->>2)::char(3), 
           (json_array_elements->>3)::numeric(13, 10), 
           (json_array_elements->>4)::numeric(14, 11), 
           (json_array_elements->>5)::numeric(8, 4), 
           (json_array_elements->>6)::numeric(6, 4), 
           (json_array_elements->>7)::integer
    FROM json_array_elements(decodedObsFrame);
END;
$$;


CREATE OR REPLACE FUNCTION public.insert_observations_beidou(decodedObsFrame json)
 RETURNS VOID
 LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO observations_beidou (rtcm_id, sat_id, sat_signal, obs_code, obs_phase, obs_doppler, obs_snr, obs_lock_time_indicator)
    SELECT (json_array_elements->>0)::bigint,
           (json_array_elements->>1)::char(4), 
           (json_array_elements->>2)::char(3), 
           (json_array_elements->>3)::numeric(13, 10), 
           (json_array_elements->>4)::numeric(14, 11), 
           (json_array_elements->>5)::numeric(8, 4), 
           (json_array_elements->>6)::numeric(6, 4), 
           (json_array_elements->>7)::integer
    FROM json_array_elements(decodedObsFrame);
END;
$$;


CREATE OR REPLACE FUNCTION public.insert_observations_qzss(decodedObsFrame json)
 RETURNS VOID
 LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO observations_qzss (rtcm_id, sat_id, sat_signal, obs_code, obs_phase, obs_doppler, obs_snr, obs_lock_time_indicator)
    SELECT (json_array_elements->>0)::bigint,
           (json_array_elements->>1)::char(4), 
           (json_array_elements->>2)::char(3), 
           (json_array_elements->>3)::numeric(13, 10), 
           (json_array_elements->>4)::numeric(14, 11), 
           (json_array_elements->>5)::numeric(8, 4), 
           (json_array_elements->>6)::numeric(6, 4), 
           (json_array_elements->>7)::integer
    FROM json_array_elements(decodedObsFrame);
END;
$$;


CREATE OR REPLACE FUNCTION public.insert_observations_sbas(decodedObsFrame json)
 RETURNS VOID
 LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO observations_sbas (rtcm_id, sat_id, sat_signal, obs_code, obs_phase, obs_doppler, obs_snr, obs_lock_time_indicator)
    SELECT (json_array_elements->>0)::bigint,
           (json_array_elements->>1)::char(4), 
           (json_array_elements->>2)::char(3), 
           (json_array_elements->>3)::numeric(13, 10), 
           (json_array_elements->>4)::numeric(14, 11), 
           (json_array_elements->>5)::numeric(8, 4), 
           (json_array_elements->>6)::numeric(6, 4), 
           (json_array_elements->>7)::integer
    FROM json_array_elements(decodedObsFrame);
END;
$$;


CREATE OR REPLACE FUNCTION public.insert_caster(casterData json, OUT caster_id int)
RETURNS int
LANGUAGE plpgsql
AS $$
BEGIN
    -- Insert into casters and get the ID
    INSERT INTO casters(caster, host, username)
    VALUES (
        (logData->>0)::text, 
        (logData->>1)::text,
        (logData->>2)::text
    )
    RETURNING caster_id INTO caster_id;
END;
$$;

CREATE OR REPLACE FUNCTION public.insert_mountpoints(mountpointTable json)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO mountpoints
    (caster_id, sitename, city, countrycode, latitude, longitude, receiver, rtcm_version)
    SELECT (json_array_elements->>0)::int, 
           (json_array_elements->>1)::text, 
           (json_array_elements->>2)::text, 
           (json_array_elements->>3)::text,
           (json_array_elements->>4)::decimal(7,4), 
           (json_array_elements->>5)::decimal(7,4), 
           (json_array_elements->>6)::text,
           (json_array_elements->>7)::text
    FROM json_array_elements(mountpointTable);
END;
$$;

CREATE OR REPLACE FUNCTION public.insert_disconnect_log(logData json, OUT log_id int)
RETURNS int
LANGUAGE plpgsql
AS $$
BEGIN
    -- Insert into connection_logger and get the ID
    INSERT INTO connection_logger (mountpoint, disconnect_time)
    VALUES (
        (logData->>0)::text, 
        (logData->>1)::timestamp without time zone
    )
    RETURNING id INTO log_id;
END;
$$;

CREATE OR REPLACE FUNCTION public.update_reconnect_log(logData json)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    -- Update reconnect_time in connection_logger
    UPDATE connection_logger
    SET reconnect_time = (logData->>1)::timestamp without time zone
    WHERE id = (logData->>0)::int;
    RETURN;
END;
$$;

CREATE OR REPLACE FUNCTION public.upsert_coordinates(decodedObsFrame json)
 RETURNS VOID
 LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO coordinates
    (rtcm_id, ecef_x, ecef_y, ecef_z, antHgt)
    SELECT (json_array_elements->>0)::bigint, 
           (json_array_elements->>1)::numeric(10, 3),
           (json_array_elements->>2)::numeric(10, 3),
           (json_array_elements->>3)::numeric(10, 3),
           (json_array_elements->>4)::numeric(10, 3)
    FROM json_array_elements(decodedObsFrame)
    ON CONFLICT (mountpoint) DO UPDATE SET
        rtcm_package_id = EXCLUDED.rtcm_package_id,
        rtcm_msg_type = EXCLUDED.rtcm_msg_type,
        ecef_x = EXCLUDED.ecef_x,
        ecef_y = EXCLUDED.ecef_y,
        ecef_z = EXCLUDED.ecef_z,
        antHgt = EXCLUDED.antHgt;
END;
$$;