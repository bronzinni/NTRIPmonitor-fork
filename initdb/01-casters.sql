CREATE TABLE IF NOT EXISTS casters (
    caster_id SERIAL PRIMARY KEY,
    caster VARCHAR(50),
    host VARCHAR(100),
    username VARCHAR(50)
);
