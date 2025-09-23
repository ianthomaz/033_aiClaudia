-- Adicionar colunas faltantes na tabela requests
ALTER TABLE requests 
ADD COLUMN promptUsed TEXT,
ADD COLUMN geminiResponse TEXT,
ADD COLUMN responseTitle TEXT;

-- Verificar a estrutura atualizada
\d requests;
