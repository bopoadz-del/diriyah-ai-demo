
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name TEXT,
    drive_id TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE chats (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id),
    user_message TEXT,
    ai_response TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id),
    category TEXT,
    message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE,
    role TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    name TEXT,
    drive_credentials TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);


-- New tables for AI services
CREATE TABLE IF NOT EXISTS summaries (
    id SERIAL PRIMARY KEY,
    meeting_id VARCHAR(100),
    summary TEXT,
    decisions TEXT,
    issues TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS actions (
    id SERIAL PRIMARY KEY,
    task TEXT,
    assignee VARCHAR(100),
    deadline DATE,
    status VARCHAR(50) DEFAULT 'pending',
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS anomalies (
    id SERIAL PRIMARY KEY,
    anomaly_type VARCHAR(100),
    source VARCHAR(100),
    details TEXT,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS forecasts (
    id SERIAL PRIMARY KEY,
    schedule_id VARCHAR(100),
    risk_score NUMERIC,
    estimated_completion DATE,
    forecast_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
