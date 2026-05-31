// ☁️👜 aiClaudia - Main JavaScript (chat)

// Rate limiting (frontend)
const RATE_LIMIT_KEY = 'aiclaudia_rate_limit';
const MAX_REQUESTS = 3;
const WINDOW_MINUTES = 3; // 3 minutos, mas texto mantém "5min"

// Session management
const SESSION_KEY = 'aiclaudia_session_id';

// Placeholders aleatórios (também usados ao limpar o input)
const PLACEHOLDERS = [
    "Tá na dúvida? Eu sou a nuvem que guarda tudo. Pergunte qualquer coisa!",
    "Perdeu na memória? A aiClaudia é seu achados e perdidos digital.",
    "Precisa de ajuda? Eu sou sua assistente pessoal, pronta pra informar.",
    "Confie na nuvem: aqui sua dúvida vira resposta.",
    "Dependência digital? Deixe comigo, eu sou a aiClaudia."
];

// Claudia character positions and appearances
const CLAUDIA_POSITIONS = [
    'position-left',
    'position-center',
    'position-right',
    'position-top-left',
    'position-top-right',
    'position-bottom-left',
    'position-bottom-right'
];

const CLAUDIA_APPEARANCES = {
    'default': '👩‍💻',
    'gata_oraculo': '🐱',
    'gata_rainha': '👑',
    'gata_psicanalista': '😺',
    'nuvem_preguicosa': '☁️',
    'nuvem_guarda': '🌥️',
    'coluna_editorial': '📰',
    'horoscopo': '🔮',
    'reporter_moda': '👗',
    'coluna_querida_claudia': '💌',
    'tired': '😴',
    'thinking': '🤔',
    'happy': '😊'
};

// Nome amigável da persona (rótulo do balão). Fallback: "aiClaudia".
const CLAUDIA_PERSONA_NAMES = {
    'gata_oraculo': 'Gata Oráculo',
    'gata_rainha': 'Gata Rainha',
    'gata_psicanalista': 'Gata Psicanalista',
    'nuvem_preguicosa': 'Nuvem Preguiçosa',
    'nuvem_guarda': 'Nuvem Guardiã',
    'coluna_editorial': 'Coluna Editorial',
    'horoscopo': 'Horóscopo Surreal',
    'reporter_moda': 'Repórter de Moda',
    'coluna_querida_claudia': 'Querida Cláudia'
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function () {
    console.log('☁️👜 aiClaudia');

    // Posicionar Claudia inicialmente e mudar a cada 10s
    moveClaudia();
    setInterval(moveClaudia, 10000);

    // Enter envia, Shift+Enter quebra linha; textarea cresce com o conteúdo
    const textarea = document.getElementById('userInput');
    if (textarea) {
        textarea.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendToClaudia();
            }
        });
        textarea.addEventListener('input', autoGrow);
    }

    // Saudação inicial da Claudia
    greet();
});

function sendToClaudia() {
    const input = document.getElementById('userInput');
    const button = document.getElementById('sendButton');
    const userMessage = input.value.trim();

    if (!userMessage) {
        showAlert('Digite algo primeiro!', 'warning');
        return;
    }

    // Check rate limit
    if (!checkRateLimit()) {
        showAlert('Tô cansada, tem nuvem no céu hoje não, volta daqui 5min!', 'info');
        return;
    }

    // Mostra a mensagem do usuário no thread e limpa o input
    appendUserMessage(userMessage);
    input.value = '';
    autoGrow.call(input);

    // Desabilita botão e mostra "digitando..."
    button.disabled = true;
    const typingEl = appendTyping();

    callAPI(userMessage)
        .then(response => {
            if (response.error) {
                if (response.error === 'rate_limit_exceeded') {
                    return { text: 'Tô cansada, tem nuvem no céu hoje não, volta daqui 5min!', category: 'tired' };
                }
                return { text: 'O céu aqui tá azul e não tem nenhuma nuvem; tô na sombra, descansando e lendo uma revista. Volta mais tarde?', category: null };
            }
            return { text: response.response, category: response.category };
        })
        .catch(error => {
            console.error('Erro:', error);
            return { text: 'O céu aqui tá azul e não tem nenhuma nuvem; tô na sombra, descansando e lendo uma revista. Volta mais tarde?', category: null };
        })
        .then(({ text, category }) => {
            removeTyping(typingEl);
            appendClaudiaMessage(text, category);
        })
        .finally(() => {
            button.disabled = false;
            // Novo placeholder aleatório
            input.placeholder = PLACEHOLDERS[Math.floor(Math.random() * PLACEHOLDERS.length)];
            input.focus();
        });
}

function checkRateLimit() {
    const now = Date.now();
    const windowMs = WINDOW_MINUTES * 60 * 1000;

    const stored = localStorage.getItem(RATE_LIMIT_KEY);
    let requests = stored ? JSON.parse(stored) : [];
    requests = requests.filter(time => now - time < windowMs);

    if (requests.length >= MAX_REQUESTS) {
        return false;
    }

    requests.push(now);
    localStorage.setItem(RATE_LIMIT_KEY, JSON.stringify(requests));
    return true;
}

// Session management functions
function getSessionId() {
    return localStorage.getItem(SESSION_KEY);
}

function setSessionId(sessionId) {
    localStorage.setItem(SESSION_KEY, sessionId);
}

function clearSession() {
    localStorage.removeItem(SESSION_KEY);
}

async function callAPI(userMessage) {
    const sessionId = getSessionId();

    const response = await fetch('/api/process-message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_message: userMessage,
            session_id: sessionId
        })
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    if (data.session_id) {
        setSessionId(data.session_id);
        if (data.is_new_session) {
            console.log(`✨ Nova sessão criada: ${data.session_id}`);
            console.log(`🎭 Personalidade: ${data.category}`);
        }
    }

    if (data.category) {
        updateClaudiaAppearance(data.category);
    }

    return data;
}

/* ---------- Chat thread ---------- */

function getThread() {
    return document.getElementById('chatThread');
}

function scrollThreadToBottom() {
    const thread = getThread();
    if (thread) thread.scrollTop = thread.scrollHeight;
}

// Escapa HTML para não injetar markup vindo da resposta/usuário
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
}

function appendUserMessage(text) {
    const thread = getThread();
    if (!thread) return;
    const msg = document.createElement('div');
    msg.className = 'chat-msg chat-msg-user';
    msg.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
    thread.appendChild(msg);
    scrollThreadToBottom();
}

function appendClaudiaMessage(text, category) {
    const thread = getThread();
    if (!thread) return;
    const avatar = CLAUDIA_APPEARANCES[category] || CLAUDIA_APPEARANCES['default'];
    const name = CLAUDIA_PERSONA_NAMES[category] || 'aiClaudia';
    const msg = document.createElement('div');
    msg.className = 'chat-msg chat-msg-claudia';
    msg.innerHTML = `
        <div class="avatar">${avatar}</div>
        <div class="bubble">
            <div class="persona">${escapeHtml(name)}</div>
            <div class="response-text">${escapeHtml(text)}</div>
        </div>
    `;
    thread.appendChild(msg);
    scrollThreadToBottom();
}

function appendTyping() {
    const thread = getThread();
    if (!thread) return null;
    const character = document.getElementById('claudiaCharacter');
    const avatar = (character && character.textContent.trim()) || CLAUDIA_APPEARANCES['default'];
    const msg = document.createElement('div');
    msg.className = 'chat-msg chat-msg-claudia typing';
    msg.innerHTML = `
        <div class="avatar">${avatar}</div>
        <div class="bubble">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </div>
    `;
    thread.appendChild(msg);
    scrollThreadToBottom();
    return msg;
}

function removeTyping(el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
}

function greet() {
    appendClaudiaMessage(
        'Oi! Sou a nuvem que guarda tudo (e às vezes esquece). Manda tua dúvida aí que eu respondo no meu humor de hoje. ☁️',
        'default'
    );
}

function startNewConversation() {
    clearSession();
    const thread = getThread();
    if (thread) thread.innerHTML = '';
    const character = document.getElementById('claudiaCharacter');
    if (character) character.textContent = CLAUDIA_APPEARANCES['default'];
    console.log('🔄 Nova conversa — próxima mensagem cria um novo perfil.');
    greet();
    const input = document.getElementById('userInput');
    if (input) input.focus();
}

function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);
    setTimeout(() => {
        if (alertDiv.parentNode) alertDiv.remove();
    }, 5000);
}

// textarea que cresce com o conteúdo (até um limite via CSS)
function autoGrow() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 140) + 'px';
}

// Mantido para uso avançado no console
function resetSession() {
    startNewConversation();
}

/* ---------- Personagem (cena no topo) ---------- */

function moveClaudia() {
    const character = document.getElementById('claudiaCharacter');
    if (!character) return;
    CLAUDIA_POSITIONS.forEach(pos => character.classList.remove(pos));
    const randomPos = CLAUDIA_POSITIONS[Math.floor(Math.random() * CLAUDIA_POSITIONS.length)];
    character.classList.add(randomPos);
}

function updateClaudiaAppearance(category) {
    const character = document.getElementById('claudiaCharacter');
    if (!character) return;
    character.textContent = CLAUDIA_APPEARANCES[category] || CLAUDIA_APPEARANCES['default'];
    moveClaudia();
}
