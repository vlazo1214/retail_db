CREATE TABLE IF NOT EXISTS statements (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255),
    actor_name VARCHAR(255),
    verb VARCHAR(100),
    activity VARCHAR(255),
    score FLOAT,
    timestamp TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS emails (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255)
);