-- Tabela de usuários (anotada para futuro uso)
-- CREATE TABLE users (
--     user_id SERIAL PRIMARY KEY,
--     google_login VARCHAR(255) UNIQUE NOT NULL,
--     token TEXT,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- Tabela de sessões (anotada para futuro uso)
-- CREATE TABLE sessions (
--     session_id SERIAL PRIMARY KEY,
--     user_id INTEGER REFERENCES users(user_id),
--     session_token VARCHAR(255) UNIQUE NOT NULL,
--     date_time_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     expires_at TIMESTAMP NOT NULL,
--     is_active BOOLEAN DEFAULT TRUE
-- );

-- Tabela de prompts para o Gemini (rndbase) - DEVE SER CRIADA PRIMEIRO
CREATE TABLE rndbase (
    phrase_id SERIAL PRIMARY KEY,
    category VARCHAR(100) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de requests (principal para testes)
CREATE TABLE requests (
    request_id SERIAL PRIMARY KEY,
    user_ip VARCHAR(45) NOT NULL,
    original_msg TEXT NOT NULL,
    date_time_request TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',
    prompt_category VARCHAR(100) REFERENCES rndbase(category),
    platform_used VARCHAR(20) DEFAULT 'gemini', -- gemini, chatgpt, etc
    ai_response TEXT,
    response_title TEXT
);

-- Tabela de imagens (anotada para futuro uso)
-- CREATE TABLE images (
--     image_id SERIAL PRIMARY KEY,
--     request_id INTEGER REFERENCES requests(request_id),
--     user_id INTEGER REFERENCES users(user_id),
--     context TEXT,
--     tags TEXT,
--     image_url TEXT,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- Tabela de logs
CREATE TABLE logs (
    log_id SERIAL PRIMARY KEY,
    user_ip VARCHAR(45),
    action VARCHAR(100) NOT NULL,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de rate limiting
CREATE TABLE rate_limits (
    limit_id SERIAL PRIMARY KEY,
    user_ip VARCHAR(45) NOT NULL,
    request_count INTEGER DEFAULT 1,
    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_request TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    blocked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de categorias (anotada para futuro uso)
-- CREATE TABLE categories (
--     category_id SERIAL PRIMARY KEY,
--     name VARCHAR(100) UNIQUE NOT NULL,
--     description TEXT
-- );

-- Tabela de AI helpers (GPT, Gemini, etc.)
CREATE TABLE ai_helpers (
    helper_id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    api_key TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    type VARCHAR(50) DEFAULT 'text' -- text, image, etc.
);

-- Prompts serão carregados via JSON (rndbase_prompts.json)

-- Inserir AI helpers (chaves serão carregadas via config.env)
INSERT INTO ai_helpers (name, api_key, is_active, type) VALUES
('gemini', 'GEMINI_API_KEY_FROM_ENV', TRUE, 'text'),
('chatgpt', 'CHATGPT_API_KEY_FROM_ENV', TRUE, 'text');
