#!/usr/bin/env python3
import json
import psycopg2
import random
import os
import requests
from datetime import datetime, timedelta

def get_random_prompt():
    """
    Seleciona prompt aleatório usando JSON, evitando o último usado do BD
    """
    # PREMISSA fixa
    PREMISSA = "Você é aiClaudia, uma mulher com visão de esquerda, humanitária e inclusiva. Suas respostas devem adotar sempre uma perspectiva equitativa, evitando marcar gênero desnecessariamente. Quando houver termos de profissões ou papéis sociais, prefira a generalização ou a forma neutra por conceito, sem usar símbolos artificiais (como \"x\", \"@\" ou \"e\"). Suas respostas devem ter entre 24 e 300 caracteres."
    
    # Carregar prompts do JSON
    with open('/app/deploy/rndbase_prompts.json', 'r') as f:
        prompts = json.load(f)
    
    # Buscar último usado no BD
    db_config = {
        'host': 'database',
        'port': 5432,
        'database': os.getenv('DB_NAME', 'aiclaudia'),
        'user': os.getenv('DB_USER', 'aiclaudia'),
        'password': os.getenv('DB_PASSWORD')
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Buscar último prompt usado
        cursor.execute("""
            SELECT category FROM rndbase 
            WHERE last_used IS NOT NULL 
            ORDER BY last_used DESC 
            LIMIT 1
        """)
        last_used = cursor.fetchone()
        last_category = last_used[0] if last_used else None
        
        # Filtrar prompts disponíveis (excluindo último usado)
        available_prompts = [p for p in prompts if p['category'] != last_category]
        
        if not available_prompts:
            available_prompts = prompts  # Se todos foram usados, usar todos
        
        # Escolher aleatoriamente
        selected = random.choice(available_prompts)
        
        # Atualizar last_used no BD
        cursor.execute("""
            UPDATE rndbase 
            SET last_used = %s 
            WHERE category = %s
        """, (datetime.now(), selected['category']))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Montar prompt completo com PREMISSA
        full_prompt = f"{PREMISSA}\n\n{selected['content']}"
        
        return {
            'category': selected['category'],
            'content': selected['content'],
            'full_prompt': full_prompt
        }
        
    except Exception as e:
        print(f"❌ Erro ao selecionar prompt: {e}")
        # Fallback: retornar prompt aleatório do JSON
        return random.choice(prompts)

def get_usage_stats():
    """
    Conta uso de cada prompt através da tabela requests (query dinâmica)
    """
    db_config = {
        'host': 'database',
        'port': 5432,
        'database': os.getenv('DB_NAME', 'aiclaudia'),
        'user': os.getenv('DB_USER', 'aiclaudia'),
        'password': os.getenv('DB_PASSWORD')
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Contar uso por category na tabela requests
        cursor.execute("""
            SELECT prompt_category, COUNT(*) as usage_count
            FROM requests 
            WHERE prompt_category IS NOT NULL
            GROUP BY prompt_category
            ORDER BY usage_count DESC
        """)
        
        stats = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return stats
        
    except Exception as e:
        print(f"❌ Erro ao buscar estatísticas: {e}")
        return []

def log_frontend_block(user_ip, reason="frontend_rate_limit"):
    """
    Log quando frontend bloqueia (para monitoramento)
    """
    db_config = {
        'host': 'database',
        'port': 5432,
        'database': os.getenv('DB_NAME', 'aiclaudia'),
        'user': os.getenv('DB_USER', 'aiclaudia'),
        'password': os.getenv('DB_PASSWORD')
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO logs (user_ip, action, details)
            VALUES (%s, %s, %s)
        """, (user_ip, 'frontend_block', reason))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao logar bloqueio frontend: {e}")
        return False

def check_rate_limit(user_ip, max_requests=10, window_minutes=5):
    """
    Verifica rate limit no backend (proteção contra bombardeio)
    """
    db_config = {
        'host': 'database',
        'port': 5432,
        'database': os.getenv('DB_NAME', 'aiclaudia'),
        'user': os.getenv('DB_USER', 'aiclaudia'),
        'password': os.getenv('DB_PASSWORD')
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Verificar se está bloqueado
        cursor.execute("""
            SELECT blocked_until FROM rate_limits 
            WHERE user_ip = %s AND blocked_until > NOW()
            ORDER BY blocked_until DESC LIMIT 1
        """, (user_ip,))
        
        blocked = cursor.fetchone()
        if blocked:
            return {
                'allowed': False,
                'reason': 'blocked',
                'blocked_until': blocked[0],
                'message': "Tô cansada, tem nuvem no céu hoje não, volta daqui 5min!"
            }
        
        # Verificar requests na janela de tempo
        cursor.execute("""
            SELECT request_count, window_start FROM rate_limits 
            WHERE user_ip = %s 
            AND window_start > NOW() - INTERVAL '%s minutes'
            ORDER BY window_start DESC LIMIT 1
        """, (user_ip, window_minutes))
        
        current_window = cursor.fetchone()
        
        if current_window:
            request_count, window_start = current_window
            
            if request_count >= max_requests:
                # Bloquear por 5 minutos
                blocked_until = datetime.now() + timedelta(minutes=5)
                cursor.execute("""
                    UPDATE rate_limits 
                    SET blocked_until = %s
                    WHERE user_ip = %s AND window_start = %s
                """, (blocked_until, user_ip, window_start))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                return {
                    'allowed': False,
                    'reason': 'rate_limit_exceeded',
                    'blocked_until': blocked_until,
                    'message': "Tô cansada, tem nuvem no céu hoje não, volta daqui 5min!"
                }
            else:
                # Incrementar contador
                cursor.execute("""
                    UPDATE rate_limits 
                    SET request_count = %s, last_request = NOW()
                    WHERE user_ip = %s AND window_start = %s
                """, (request_count + 1, user_ip, window_start))
        else:
            # Nova janela de tempo
            cursor.execute("""
                INSERT INTO rate_limits (user_ip, request_count, window_start, last_request)
                VALUES (%s, 1, NOW(), NOW())
            """, (user_ip,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {'allowed': True}
        
    except Exception as e:
        print(f"❌ Erro ao verificar rate limit: {e}")
        return {'allowed': True}  # Em caso de erro, permitir

def call_gemini_api(prompt, user_message):
    """
    Chama a API do Gemini com o prompt completo (versão simplificada)
    """
    api_key = os.getenv('GEMINI_API_KEY')
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}'
    
    # Montar prompt final
    final_prompt = f"{prompt}\n\nMensagem do Usuário: {user_message}"
    
    # Payload simplificado (baseado no teste que funcionou)
    data = {
        'contents': [{
            'parts': [{
                'text': final_prompt
            }]
        }]
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if 'candidates' in result and result['candidates']:
            return {
                'success': True,
                'response': result['candidates'][0]['content']['parts'][0]['text'],
                'platform': 'gemini'
            }
        else:
            return {
                'success': False,
                'error': f"Erro na API Gemini: {result}",
                'platform': 'gemini'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f"Erro na requisição Gemini: {e}",
            'platform': 'gemini'
        }

def call_chatgpt_api(prompt, user_message):
    """
    Chama a API do ChatGPT como fallback
    """
    api_key = os.getenv('CHATGPT_API_KEY')
    url = 'https://api.openai.com/v1/chat/completions'
    
    # Montar prompt final
    final_prompt = f"{prompt}\n\nMensagem do Usuário: {user_message}"
    
    data = {
        'model': 'gpt-3.5-turbo',
        'messages': [{
            'role': 'user',
            'content': final_prompt
        }],
        'max_tokens': 200,
        'temperature': 0.8
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if 'choices' in result and result['choices']:
            return {
                'success': True,
                'response': result['choices'][0]['message']['content'],
                'platform': 'chatgpt'
            }
        else:
            return {
                'success': False,
                'error': f"Erro na API ChatGPT: {result}",
                'platform': 'chatgpt'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f"Erro na requisição ChatGPT: {e}",
            'platform': 'chatgpt'
        }

def save_request_to_db(user_ip, user_message, prompt_category, ai_response, platform_used):
    """
    Salva request e resposta no BD
    """
    db_config = {
        'host': 'database',
        'port': 5432,
        'database': os.getenv('DB_NAME', 'aiclaudia'),
        'user': os.getenv('DB_USER', 'aiclaudia'),
        'password': os.getenv('DB_PASSWORD')
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO requests (user_ip, original_msg, prompt_category, platform_used, ai_response, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_ip, user_message, prompt_category, platform_used, ai_response, 'completed'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao salvar no BD: {e}")
        return False

def process_user_message(user_ip, user_message, force_platform=None):
    """
    Processo completo: seleciona prompt, chama API (Gemini primeiro, ChatGPT fallback), salva no BD
    
    Args:
        user_ip: IP do usuário
        user_message: Mensagem do usuário
        force_platform: 'gemini' ou 'chatgpt' para forçar uma plataforma específica
    """
    # 0. Verificar rate limit (proteção contra bombardeio)
    rate_check = check_rate_limit(user_ip)
    if not rate_check['allowed']:
        return {
            "error": "rate_limit_exceeded",
            "message": rate_check['message'],
            "blocked_until": rate_check.get('blocked_until')
        }
    
    # 1. Selecionar prompt
    prompt_data = get_random_prompt()
    if not prompt_data:
        return {"error": "Erro ao selecionar prompt"}
    
    # 2. Chamar API com fallback
    ai_result = None
    platform_used = None
    
    if force_platform == 'chatgpt':
        # Forçar ChatGPT
        ai_result = call_chatgpt_api(prompt_data['full_prompt'], user_message)
        platform_used = 'chatgpt'
    else:
        # Tentar Gemini primeiro
        ai_result = call_gemini_api(prompt_data['full_prompt'], user_message)
        platform_used = 'gemini'
        
        # Se Gemini falhar, tentar ChatGPT
        if not ai_result['success']:
            print(f"⚠️ Gemini falhou: {ai_result['error']}")
            print("🔄 Tentando ChatGPT como fallback...")
            ai_result = call_chatgpt_api(prompt_data['full_prompt'], user_message)
            platform_used = 'chatgpt'
    
    # 3. Verificar se alguma API funcionou
    if not ai_result['success']:
        return {
            "error": f"Ambas APIs falharam. Gemini: {ai_result.get('error', 'N/A')}",
            "category": prompt_data['category'],
            "platform_attempted": platform_used
        }
    
    # 4. Salvar no BD
    save_success = save_request_to_db(
        user_ip, 
        user_message, 
        prompt_data['category'], 
        ai_result['response'], 
        platform_used
    )
    
    return {
        "category": prompt_data['category'],
        "response": ai_result['response'],
        "platform_used": platform_used,
        "saved": save_success
    }

if __name__ == "__main__":
    # Teste completo
    user_msg = "Onde deixei minha chave de casa?"
    user_ip = "127.0.0.1"
    
    print("🧪 Testando com Gemini (padrão):")
    result = process_user_message(user_ip, user_msg)
    
    if "error" not in result:
        print(f"✅ Categoria: {result['category']}")
        print(f"🤖 Plataforma: {result['platform_used']}")
        print(f"💬 Resposta: {result['response']}")
        print(f"💾 Salvo no BD: {result['saved']}")
    else:
        print(f"❌ Erro: {result['error']}")
    
    print("\n" + "="*50)
    print("🧪 Testando forçando ChatGPT:")
    result2 = process_user_message(user_ip, user_msg, force_platform='chatgpt')
    
    if "error" not in result2:
        print(f"✅ Categoria: {result2['category']}")
        print(f"🤖 Plataforma: {result2['platform_used']}")
        print(f"💬 Resposta: {result2['response']}")
        print(f"💾 Salvo no BD: {result2['saved']}")
    else:
        print(f"❌ Erro: {result2['error']}")
    
    print("\n📈 Estatísticas de uso (via requests):")
    stats = get_usage_stats()
    for stat in stats:
        print(f"  {stat[0]}: {stat[1]} usos")
