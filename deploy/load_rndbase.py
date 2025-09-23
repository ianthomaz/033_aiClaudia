#!/usr/bin/env python3
import json
import psycopg2
import os
from datetime import datetime

def load_rndbase_prompts():
    # Configurações do banco
    db_config = {
        'host': 'database',
        'port': 5432,
        'database': os.getenv('DB_NAME', 'aiclaudia'),
        'user': os.getenv('DB_USER', 'aiclaudia'),
        'password': os.getenv('DB_PASSWORD')
    }
    
    try:
        # Conectar ao banco
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Ler o arquivo JSON
        with open('/app/deploy/rndbase_prompts.json', 'r') as f:
            prompts = json.load(f)
        
        # Atualizar ou inserir prompts (UPSERT)
        for prompt in prompts:
            cursor.execute("""
                INSERT INTO rndbase (category, content, created_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (category) 
                DO UPDATE SET 
                    content = EXCLUDED.content,
                    created_at = EXCLUDED.created_at
            """, (prompt['category'], prompt['content'], datetime.now()))
        
        # Commit e fechar
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ {len(prompts)} prompts carregados com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao carregar prompts: {e}")

if __name__ == "__main__":
    load_rndbase_prompts()
