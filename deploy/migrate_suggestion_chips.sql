-- Suggestion chips pool (news-driven chat starters)
CREATE TABLE IF NOT EXISTS suggestion_chips (
    chip_id SERIAL PRIMARY KEY,
    text VARCHAR(280) NOT NULL,
    topic VARCHAR(50) NOT NULL,
    source_headline TEXT,
    source_url TEXT,
    batch_id UUID,
    is_active BOOLEAN DEFAULT TRUE,
    deactivated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_suggestion_chips_active ON suggestion_chips(is_active, created_at);
CREATE INDEX IF NOT EXISTS idx_suggestion_chips_topic ON suggestion_chips(topic);
