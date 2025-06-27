CREATE OR REPLACE FUNCTION public.insert_rtcm_messages(decodedframes json, OUT rtcm_ids BIGINT[])
 RETURNS BIGINT[]
 LANGUAGE plpgsql
AS $$
BEGIN
    -- Insert into rtcm_messages and get the IDs
    WITH insertion AS (
        INSERT INTO rtcm_messages (mountpoint_id, time_received, msg_type, msg_size)
        SELECT (json_array_elements->>'mountpoint_id')::integer,
               (json_array_elements->>'time_received')::timestamp without time zone,
               (json_array_elements->>'msg_type')::integer,
               (json_array_elements->>'msg_size')::integer
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
           (json_array_elements->>4)::timestamp with time zone,
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


CREATE OR REPLACE FUNCTION public.insert_caster(casterData JSON, OUT casterId INT)
RETURNS INT
LANGUAGE plpgsql
AS $$
BEGIN
    -- Insert into casters and get the ID
    INSERT INTO casters(caster, host, username)
    VALUES (
        (casterData->>0)::text, 
        (casterData->>1)::text,
        (casterData->>2)::text
    )
    ON CONFLICT (caster, host, username) DO UPDATE 
    SET caster = EXCLUDED.caster -- Nødvendig for at få returneret den eksisterende casters id
    RETURNING caster_id INTO casterId;
END;
$$;


CREATE OR REPLACE FUNCTION public.insert_mountpoints(mountpointTable JSON, OUT mountpoint_ids INT[])
RETURNS INT[]
LANGUAGE plpgsql
AS $$
BEGIN
    WITH insertion AS (
        INSERT INTO mountpoints (caster_id, sitename, city, countrycode, latitude, longitude, receiver, rtcm_version)
        SELECT (json_array_elements->>'caster_id')::INT,
            (json_array_elements->>'sitename')::TEXT,
            (json_array_elements->>'city')::TEXT,
            (json_array_elements->>'countrycode')::TEXT,
            (json_array_elements->>'latitude')::DECIMAL(7,4),
            (json_array_elements->>'longitude')::DECIMAL(7,4),
            (json_array_elements->>'receiver')::TEXT,
            (json_array_elements->>'rtcm_version')::TEXT
        FROM json_array_elements(mountpointTable)
        ON CONFLICT (caster_id, sitename) DO UPDATE
        SET caster_id = EXCLUDED.caster_id -- Necessary for procedure to return existing mountpoint_id
        RETURNING mountpoint_id
    )
    SELECT array_agg(mountpoint_id) FROM insertion INTO mountpoint_ids;
END;
$$;


CREATE OR REPLACE FUNCTION public.insert_disconnect_log(logData JSON, OUT log_id INT)
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

CREATE OR REPLACE FUNCTION public.update_reconnect_log(logData JSON)
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

CREATE OR REPLACE FUNCTION public.upsert_coordinates(decodedObsFrame JSON)
 RETURNS VOID
 LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO coordinates
    (rtcm_id, mountpoint_id, ecef_x, ecef_y, ecef_z, antHgt)
    SELECT (json_array_elements->>0)::bigint, 
           (json_array_elements->>1)::int, 
           (json_array_elements->>2)::numeric(10, 3),
           (json_array_elements->>3)::numeric(10, 3),
           (json_array_elements->>4)::numeric(10, 3),
           (json_array_elements->>5)::numeric(10, 3)
    FROM json_array_elements(decodedObsFrame)
    ON CONFLICT (mountpoint_id) DO UPDATE SET
        rtcm_package_id = EXCLUDED.rtcm_package_id,
        mountpoint_id = EXCLUDED.mountpoint_id,
        ecef_x = EXCLUDED.ecef_x,
        ecef_y = EXCLUDED.ecef_y,
        ecef_z = EXCLUDED.ecef_z,
        antHgt = EXCLUDED.antHgt;
END;
$$;
