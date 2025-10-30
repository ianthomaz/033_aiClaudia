-- ☁️👜 aiClaudia - Migration: Add Sessions Support
-- Este script adiciona suporte a sessões em bancos de dados existentes
-- Execute apenas UMA vez em bancos que já existem

-- 1. Criar tabela sessions se não existir
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_ip VARCHAR(45) NOT NULL,
    current_personality VARCHAR(100) REFERENCES rndbase(category),
    message_history JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- 2. Adicionar coluna session_id na tabela requests se não existir
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='requests' AND column_name='session_id'
    ) THEN
        ALTER TABLE requests ADD COLUMN session_id VARCHAR(255) REFERENCES sessions(session_id);
        RAISE NOTICE 'Coluna session_id adicionada à tabela requests';
    ELSE
        RAISE NOTICE 'Coluna session_id já existe na tabela requests';
    END IF;
END $$;

-- 3. Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_sessions_user_ip ON sessions(user_ip);
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity);
CREATE INDEX IF NOT EXISTS idx_requests_session_id ON requests(session_id);

-- 4. Feedback
DO $$
BEGIN
    RAISE NOTICE '✅ Migração concluída! Sistema de sessões configurado.';
END $$;
