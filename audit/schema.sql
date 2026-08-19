CREATE TABLE IF NOT EXISTS ticket_workflows (
    ticket_id INTEGER PRIMARY KEY,
    current_state VARCHAR(50) NOT NULL,
    category VARCHAR(50),
    confidence_score FLOAT,
    clarification_rounds INTEGER DEFAULT 0,
    raw_title TEXT,
    sanitized_content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workflow_audit_logs (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    from_state VARCHAR(50),
    to_state VARCHAR(50),
    agent_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
