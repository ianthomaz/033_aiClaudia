#!/usr/bin/env python3
"""
☁️👜 aiClaudia - API Server
Servidor Flask para receber chamadas do frontend
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
from datetime import datetime

# Adicionar o diretório deploy ao path para importar o simple_prompt_selector
sys.path.append('/app/deploy')

# Importar as funções do backend
from simple_prompt_selector import process_user_message, log_frontend_block
import psycopg2

app = Flask(__name__)
CORS(app)  # Permitir CORS para o frontend

@app.route('/api/process-message', methods=['POST'])
def process_message():
    """
    Endpoint principal: processa mensagem do usuário com suporte a sessões
    """
    try:
        data = request.get_json()

        if not data or 'user_message' not in data:
            return jsonify({
                'error': 'missing_user_message',
                'message': 'Mensagem do usuário é obrigatória'
            }), 400

        user_message = data['user_message'].strip()

        if not user_message:
            return jsonify({
                'error': 'empty_message',
                'message': 'Mensagem não pode estar vazia'
            }), 400

        # Pegar IP do usuário
        user_ip = request.remote_addr or '127.0.0.1'

        # Pegar session_id se enviado pelo frontend
        session_id = data.get('session_id', None)

        # Processar mensagem usando o backend (com sessão)
        result = process_user_message(user_ip, user_message, session_id)

        if 'error' in result:
            return jsonify(result), 400

        return jsonify({
            'success': True,
            'session_id': result['session_id'],
            'response': result['response'],
            'category': result['category'],
            'platform_used': result['platform_used'],
            'is_new_session': result.get('is_new_session', False)
        })

    except Exception as e:
        print(f"❌ Erro no processamento: {e}")
        return jsonify({
            'error': 'internal_error',
            'message': 'Erro interno do servidor'
        }), 500

@app.route('/api/log-block', methods=['POST'])
def log_block():
    """
    Endpoint para logar bloqueios do frontend
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'no_data'}), 400
        
        # Pegar IP do usuário
        user_ip = request.remote_addr or '127.0.0.1'
        
        # Logar no backend
        reason = data.get('reason', 'frontend_rate_limit')
        success = log_frontend_block(user_ip, reason)
        
        return jsonify({
            'success': success,
            'message': 'Log registrado'
        })
        
    except Exception as e:
        print(f"❌ Erro no log: {e}")
        return jsonify({
            'error': 'log_error',
            'message': 'Erro ao registrar log'
        }), 500

@app.route('/api/msgs', methods=['GET'])
def get_messages():
    """
    Endpoint para buscar mensagens do banco de dados
    """
    try:
        # Parâmetros de query
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Conectar ao banco
        db_config = {
            'host': 'database',
            'port': 5432,
            'database': os.getenv('DB_NAME', 'aiclaudia'),
            'user': os.getenv('DB_USER', 'aiclaudia'),
            'password': os.getenv('DB_PASSWORD')
        }
        
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Buscar mensagens
        query = """
        SELECT 
            request_id,
            user_ip,
            original_msg,
            date_time_request,
            status,
            prompt_category,
            platform_used,
            ai_response,
            response_title
        FROM requests 
        ORDER BY date_time_request DESC 
        LIMIT %s OFFSET %s
        """
        
        cursor.execute(query, (limit, offset))
        rows = cursor.fetchall()
        
        # Converter para dicionários
        messages = []
        for row in rows:
            messages.append({
                'id': row[0],
                'user_ip': row[1],
                'original_msg': row[2],
                'date_time': row[3].isoformat() if row[3] else None,
                'status': row[4],
                'prompt_category': row[5],
                'platform_used': row[6],
                'ai_response': row[7],
                'response_title': row[8]
            })
        
        # Contar total
        cursor.execute("SELECT COUNT(*) FROM requests")
        total = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'messages': messages,
            'total': total,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        print(f"❌ Erro ao buscar mensagens: {e}")
        return jsonify({
            'error': 'database_error',
            'message': 'Erro ao buscar mensagens do banco'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Endpoint de health check
    """
    return jsonify({
        'status': 'healthy',
        'service': '☁️👜 aiClaudia API',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/', methods=['GET'])
def root():
    """
    Endpoint raiz
    """
    return jsonify({
        'service': '☁️👜 aiClaudia API',
        'version': '1.0.0',
        'endpoints': [
            'POST /api/process-message',
            'POST /api/log-block',
            'GET /api/msgs',
            'GET /api/health'
        ]
    })

if __name__ == '__main__':
    # Carregar variáveis de ambiente
    from dotenv import load_dotenv
    load_dotenv('config.env')
    
    # Configurações
    port = int(os.getenv('API_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Iniciando ☁️👜 aiClaudia API na porta {port}")
    print(f"📡 Endpoints disponíveis:")
    print(f"   POST /api/process-message")
    print(f"   POST /api/log-block")
    print(f"   GET /api/msgs")
    print(f"   GET /api/health")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
