#!/usr/bin/env python3
import json
import os
import random
import psycopg2
import requests
import time
import uuid
from datetime import datetime, timedelta

# Short prefix on every reply; long-form world-building is in rag/*.md for ai2tcs ingest.
CORE_VOICE_PREFIX = (
    "Voz aiClaudia (BR): esquerda, humanitarismo, inclusão linguística "
    "(evita marcar género em papéis sociais sem necessidade). "
    "Responda DIRECTO à pergunta do usuário em 1–3 frases curtas (máx. ~280 caracteres). "
    "Humor surreal/leve; sem ódio nem incitação. "
    "PROIBIDO: meta-texto ('vamos tecer', 'a nuvem significa', listar rótulos do prompt, "
    "enumerar palavras-chave, explicar o truque cénico). "
    "Pode usar **negrito** Markdown em no máximo uma expressão. "
    "Se o RAG trouxer trechos, use-os sem recitar literalmente."
)


def get_random_prompt():
    """
    Seleciona prompt aleatório usando JSON, evitando o último usado do BD
    """
    
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
        
        # Montar prompt completo com prefixo fixo + instrução de categoria
        full_prompt = f"{CORE_VOICE_PREFIX}\n\n{selected['content']}"
        
        return {
            'category': selected['category'],
            'content': selected['content'],
            'full_prompt': full_prompt
        }
        
    except Exception as e:
        print(f"❌ Erro ao selecionar prompt: {e}")
        p = random.choice(prompts)
        return {
            "category": p["category"],
            "content": p["content"],
            "full_prompt": f"{CORE_VOICE_PREFIX}\n\n{p['content']}",
        }

def create_session(user_ip, personality_category):
    """
    Cria nova sessão com personalidade escolhida
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

        # Gerar UUID único
        session_id = str(uuid.uuid4())

        # Inserir sessão
        cursor.execute("""
            INSERT INTO sessions (session_id, user_ip, current_personality)
            VALUES (%s, %s, %s)
        """, (session_id, user_ip, personality_category))

        conn.commit()
        cursor.close()
        conn.close()

        return {
            'success': True,
            'session_id': session_id,
            'personality': personality_category
        }

    except Exception as e:
        print(f"❌ Erro ao criar sessão: {e}")
        return {'success': False, 'error': str(e)}

def get_session(session_id):
    """
    Recupera sessão existente
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

        # Buscar sessão
        cursor.execute("""
            SELECT session_id, user_ip, current_personality, message_history,
                   created_at, last_activity, is_active
            FROM sessions
            WHERE session_id = %s AND is_active = TRUE
        """, (session_id,))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            return {
                'success': True,
                'session_id': row[0],
                'user_ip': row[1],
                'personality': row[2],
                'message_history': row[3] or [],
                'created_at': row[4],
                'last_activity': row[5],
                'is_active': row[6]
            }
        else:
            return {'success': False, 'error': 'session_not_found'}

    except Exception as e:
        print(f"❌ Erro ao buscar sessão: {e}")
        return {'success': False, 'error': str(e)}

def update_session_activity(session_id):
    """
    Atualiza timestamp de última atividade da sessão
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
            UPDATE sessions
            SET last_activity = NOW()
            WHERE session_id = %s
        """, (session_id,))

        conn.commit()
        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"❌ Erro ao atualizar atividade: {e}")
        return False

def add_message_to_history(session_id, user_msg, ai_response, max_messages=5):
    """
    Adiciona mensagem ao histórico da sessão (mantém últimas max_messages)
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

        # Buscar histórico atual
        cursor.execute("""
            SELECT message_history FROM sessions WHERE session_id = %s
        """, (session_id,))

        row = cursor.fetchone()
        history = row[0] if row and row[0] else []

        # Adicionar nova mensagem
        new_entry = {
            'user': user_msg,
            'assistant': ai_response,
            'timestamp': datetime.now().isoformat()
        }

        history.append(new_entry)

        # Manter apenas últimas max_messages
        if len(history) > max_messages:
            history = history[-max_messages:]

        # Atualizar no banco
        cursor.execute("""
            UPDATE sessions
            SET message_history = %s::jsonb
            WHERE session_id = %s
        """, (json.dumps(history), session_id))

        conn.commit()
        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"❌ Erro ao adicionar mensagem ao histórico: {e}")
        return False

def get_session_prompt(session_id, user_ip):
    """
    Pega prompt da sessão existente ou cria nova sessão com prompt aleatório
    Retorna: (session_id, prompt_data, is_new_session)
    """
    # Tentar recuperar sessão existente
    if session_id:
        session = get_session(session_id)

        if session['success']:
            # Sessão existe - usar personalidade da sessão
            personality = session['personality']

            # Buscar conteúdo do prompt
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
                    SELECT category, content FROM rndbase WHERE category = %s
                """, (personality,))

                row = cursor.fetchone()
                cursor.close()
                conn.close()

                if row:
                    # Adicionar contexto da conversa
                    context_str = ""
                    if session['message_history']:
                        context_str = "\n\nContexto da conversa anterior:\n"
                        for msg in session['message_history'][-2:]:  # últimas 2 trocas no system prompt
                            context_str += f"Usuário: {msg['user']}\n"
                            context_str += f"Você: {msg['assistant']}\n"

                    return (
                        session_id,
                        {
                            'category': row[0],
                            'content': row[1],
                            'full_prompt': f"{CORE_VOICE_PREFIX}\n\n{row[1]}{context_str}"
                        },
                        False  # não é nova sessão
                    )

            except Exception as e:
                print(f"❌ Erro ao buscar prompt da sessão: {e}")

    # Sessão não existe ou erro - criar nova
    prompt_data = get_random_prompt()
    new_session = create_session(user_ip, prompt_data['category'])

    if new_session['success']:
        return (new_session['session_id'], prompt_data, True)
    else:
        # Fallback: sem sessão
        return (None, prompt_data, True)

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


def itcs_llm_configured() -> bool:
    """True when ai2tcs / itcs-webplace LLM API (POST /ask) should be tried first."""
    return bool(
        os.getenv("LLM_API_URL", "").strip()
        and os.getenv("LLM_API_TOKEN", "").strip()
        and os.getenv("LLM_PROJECT_ID", "").strip()
    )


def commercial_llm_allowed() -> bool:
    """Gemini/OpenAI only when not explicitly disabled (see LLM_DISABLE_COMMERCIAL)."""
    v = os.getenv("LLM_DISABLE_COMMERCIAL", "").strip().lower()
    return v not in ("1", "true", "yes", "on")


def call_itcs_llm_api(
    system_prompt: str,
    user_message: str,
    user_id: str | None = None,
    history: list[dict] | None = None,
):
    """
    Calls the ITCS-webplace LLM HTTP API (ai2tcs llm_api): POST /ask, poll /status, GET /result.
    Contract: ai2tcs docs/02-api-integration.md; overview and doc index: docs/01-overview.md.
    """
    base = os.getenv("LLM_API_URL", "").strip().rstrip("/")
    token = os.getenv("LLM_API_TOKEN", "").strip()
    project_id = os.getenv("LLM_PROJECT_ID", "").strip()
    if not base or not token or not project_id:
        return {
            "success": False,
            "error": "LLM_API_URL, LLM_API_TOKEN, LLM_PROJECT_ID required for ITCS",
            "platform": "itcs",
        }

    model = (os.getenv("LLM_MODEL_ALIAS") or os.getenv("LLM_MODEL") or "fast").strip()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload: dict = {
        "project_id": project_id,
        "question": user_message,
        "system_prompt": system_prompt,
        "model": model,
    }
    if user_id:
        payload["user_id"] = user_id
    if history:
        payload["history"] = history

    poll_timeout = int(os.getenv("LLM_ASK_TIMEOUT_SECONDS", "90"))
    poll_interval = float(os.getenv("LLM_ASK_POLL_INTERVAL", "0.35"))

    try:
        r = requests.post(f"{base}/ask", headers=headers, json=payload, timeout=60)
        if r.status_code not in (200, 202):
            return {
                "success": False,
                "error": f"ITCS /ask HTTP {r.status_code}: {r.text[:800]}",
                "platform": "itcs",
            }
        body = r.json()
        job_id = body.get("job_id")
        if not job_id:
            body_preview = repr(body)[:500]
            return {
                "success": False,
                "error": f"ITCS /ask missing job_id: {body_preview}",
                "platform": "itcs",
            }

        deadline = time.time() + poll_timeout
        last_status: dict = {}
        while time.time() < deadline:
            sr = requests.get(f"{base}/status/{job_id}", headers=headers, timeout=30)
            if sr.status_code != 200:
                time.sleep(poll_interval)
                continue
            last_status = sr.json()
            if last_status.get("client_status") != "processing":
                break
            time.sleep(poll_interval)
        else:
            return {
                "success": False,
                "error": "ITCS status poll timeout",
                "platform": "itcs",
            }

        rr = requests.get(f"{base}/result/{job_id}", headers=headers, timeout=30)
        if rr.status_code != 200:
            return {
                "success": False,
                "error": f"ITCS /result HTTP {rr.status_code}: {rr.text[:800]}",
                "platform": "itcs",
            }
        res = rr.json()
        status = (res.get("status") or "").lower()
        answer = (res.get("answer") or "").strip()

        if status == "done" and answer:
            return {"success": True, "response": answer, "platform": "itcs"}
        if answer and status not in ("failed", "cancelled"):
            return {"success": True, "response": answer, "platform": "itcs"}

        poll_preview = repr(last_status)[:400]
        return {
            "success": False,
            "error": (
                f"ITCS job status={status!r} last_poll={poll_preview} "
                f"answer_empty={not answer}"
            ),
            "platform": "itcs",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"ITCS request error: {e}",
            "platform": "itcs",
        }


def _history_for_itcs(session_id: str | None) -> list[dict] | None:
    """Map session message_history to ITCS /ask history format."""
    if not session_id:
        return None
    session = get_session(session_id)
    if not session.get("success") or not session.get("message_history"):
        return None
    turns: list[dict] = []
    for msg in session["message_history"][-4:]:
        turns.append({"role": "user", "text": msg.get("user", "")})
        turns.append({"role": "assistant", "text": msg.get("assistant", "")})
    return turns or None


def call_gemini_api(prompt, user_message):
    """
    Chama a API do Gemini com o prompt completo (versão simplificada)
    """
    api_key = os.getenv('GEMINI_API_KEY')
    model = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}'
    
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

def save_request_to_db(user_ip, user_message, prompt_category, ai_response, platform_used, session_id=None):
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
            INSERT INTO requests (session_id, user_ip, original_msg, prompt_category, platform_used, ai_response, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (session_id, user_ip, user_message, prompt_category, platform_used, ai_response, 'completed'))

        conn.commit()
        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"❌ Erro ao salvar no BD: {e}")
        return False

def process_user_message(user_ip, user_message, session_id=None, force_platform=None):
    """
    Processo completo: gerencia sessão, seleciona/mantém prompt, chama API, salva no BD

    Args:
        user_ip: IP do usuário
        user_message: Mensagem do usuário
        session_id: ID da sessão (se existir)
        force_platform: 'itcs' | 'gemini' | 'chatgpt' to force one provider (commercial respect LLM_DISABLE_COMMERCIAL)
    """
    # 0. Verificar rate limit (proteção contra bombardeio)
    rate_check = check_rate_limit(user_ip)
    if not rate_check['allowed']:
        return {
            "error": "rate_limit_exceeded",
            "message": rate_check['message'],
            "blocked_until": rate_check.get('blocked_until')
        }

    # 1. Gerenciar sessão e selecionar prompt
    session_id, prompt_data, is_new_session = get_session_prompt(session_id, user_ip)

    if not prompt_data:
        return {"error": "Erro ao selecionar prompt"}

    # 2. Atualizar atividade da sessão
    if session_id:
        update_session_activity(session_id)

    # 3. LLM: ITCS only when LLM_* is set (no Gemini/GPT fallback). Commercial APIs only if ITCS is not configured.
    ai_result = None
    platform_used = None
    user_ref = session_id or f"aiclaudia:{user_ip}"
    hist = _history_for_itcs(session_id)

    if force_platform == "itcs":
        ai_result = call_itcs_llm_api(
            prompt_data["full_prompt"], user_message, user_id=user_ref, history=hist
        )
        platform_used = "itcs"
    elif force_platform == "chatgpt":
        if not commercial_llm_allowed():
            ai_result = {
                "success": False,
                "error": "Commercial LLM disabled (LLM_DISABLE_COMMERCIAL)",
                "platform": "chatgpt",
            }
        else:
            ai_result = call_chatgpt_api(prompt_data["full_prompt"], user_message)
        platform_used = "chatgpt"
    elif force_platform == "gemini":
        if not commercial_llm_allowed():
            ai_result = {
                "success": False,
                "error": "Commercial LLM disabled (LLM_DISABLE_COMMERCIAL)",
                "platform": "gemini",
            }
        else:
            ai_result = call_gemini_api(prompt_data["full_prompt"], user_message)
        platform_used = "gemini"
    elif itcs_llm_configured():
        ai_result = call_itcs_llm_api(
            prompt_data["full_prompt"], user_message, user_id=user_ref, history=hist
        )
        platform_used = "itcs"
    elif not commercial_llm_allowed():
        ai_result = {
            "success": False,
            "error": "Commercial LLM disabled; configure LLM_API_URL, LLM_API_TOKEN, LLM_PROJECT_ID for ITCS.",
            "platform": "none",
        }
        platform_used = "none"
    else:
        ai_result = call_gemini_api(prompt_data["full_prompt"], user_message)
        platform_used = "gemini"
        if not ai_result["success"]:
            print(f"⚠️ Gemini falhou: {ai_result['error']}")
            print("🔄 Tentando ChatGPT como fallback...")
            ai_result = call_chatgpt_api(prompt_data["full_prompt"], user_message)
            platform_used = "chatgpt"

    # 4. Verificar se alguma API funcionou
    if not ai_result["success"]:
        return {
            "error": ai_result.get("error", "All LLM backends failed"),
            "category": prompt_data["category"],
            "platform_attempted": platform_used,
            "session_id": session_id,
        }

    # 5. Adicionar mensagem ao histórico da sessão
    if session_id:
        add_message_to_history(session_id, user_message, ai_result['response'])

    # 6. Salvar no BD
    save_success = save_request_to_db(
        user_ip,
        user_message,
        prompt_data['category'],
        ai_result['response'],
        platform_used,
        session_id
    )

    return {
        "session_id": session_id,
        "category": prompt_data['category'],
        "response": ai_result['response'],
        "platform_used": platform_used,
        "is_new_session": is_new_session,
        "saved": save_success
    }

if __name__ == "__main__":
    # Teste completo
    user_msg = "Onde deixei minha chave de casa?"
    user_ip = "127.0.0.1"
    
    print("🧪 Testando LLM (ITCS se configurado, senão Gemini → ChatGPT):")
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
