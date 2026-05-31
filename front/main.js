// ☁️👜 aiClaudia — chat

/* ---------- Config ---------- */
const RATE_LIMIT_KEY = 'aiclaudia_rate_limit';
const MAX_REQUESTS = 3;
const WINDOW_MINUTES = 3;
const SESSION_KEY = 'aiclaudia_session_id';

const PLACEHOLDERS = [
    "Pergunta qualquer coisa pra nuvem…",
    "Perdeu algo na memória? Conta pra mim.",
    "Manda tua dúvida mais existencial.",
    "O que tu quer descobrir hoje?",
    "Fala comigo, eu guardo (quase) tudo."
];

const SUGGESTIONS = [
    "Onde foi parar minha chave?",
    "Me dá um conselho de vida",
    "Como vai ser meu dia?",
    "Por que eu esqueço as senhas?"
];

/* ---------- Personas ----------
 * Chaves em ASCII puro (sem ç/ã). A categoria vinda do backend é normalizada
 * (sem acento, minúscula) antes da busca — assim "nuvem_preguiçosa" e
 * "claudia_guardiã" casam mesmo vindo com acento, evitando bug de encoding.
 */
const PERSONAS = {
    'default':              { name: 'aiClaudia',           emoji: '👩‍💻', accent: '#4361EE' },
    'nuvem_preguicosa':     { name: 'Nuvem Preguiçosa',    emoji: '☁️',  accent: '#279AF1' },
    'discurso_heroico':     { name: 'Discurso Heroico',    emoji: '🦸',  accent: '#4361EE' },
    'haicai_sistema':       { name: 'Haicai do Sistema',   emoji: '🍃',  accent: '#23B5D3' },
    'assistente_cansada':   { name: 'Assistente Cansada',  emoji: '😴',  accent: '#6a6385' },
    'sermao_epico':         { name: 'Sermão Épico',        emoji: '📢',  accent: '#3A0CA3' },
    'profecia_mistica':     { name: 'Profecia Mística',    emoji: '🔮',  accent: '#7209B7' },
    'slogan_publicitario':  { name: 'Slogan Publicitário', emoji: '📣',  accent: '#EA526F' },
    'heroi_cansado':        { name: 'Herói Cansado',       emoji: '🛡️',  accent: '#4361EE' },
    'carta_poetica':        { name: 'Carta Poética',       emoji: '✉️',  accent: '#F72585' },
    'motivacional_absurdo': { name: 'Motivacional Absurdo',emoji: '🌈',  accent: '#F72585' },
    'icloudia_consciente':  { name: 'Nuvem Consciente',    emoji: '🌫️',  accent: '#279AF1' },
    'claudia_guardia':      { name: 'Cláudia Guardiã',     emoji: '🌥️',  accent: '#23B5D3' },
    'auditorio_absurdo':    { name: 'Auditório Absurdo',   emoji: '🎤',  accent: '#F72585' },
    'diario_secreto':       { name: 'Diário Secreto',      emoji: '📔',  accent: '#7209B7' },
    'entidade_dissimulada': { name: 'Entidade Dissimulada',emoji: '🌀',  accent: '#3A0CA3' },
    'revista_editorial':    { name: 'Coluna Editorial',    emoji: '📰',  accent: '#3A0CA3' },
    'revista_horoscopo':    { name: 'Horóscopo Surreal',   emoji: '🌙',  accent: '#7209B7' },
    'revista_dicas':        { name: 'Dicas de Bem-Estar',  emoji: '💡',  accent: '#23B5D3' },
    'revista_moda':         { name: 'Repórter de Moda',    emoji: '👗',  accent: '#EA526F' },
    'revista_cartas':       { name: 'Cartas das Leitoras', emoji: '💌',  accent: '#F72585' },
    'tigresa_oraculo':      { name: 'Tigresa-Oráculo',     emoji: '🐯',  accent: '#7209B7' },
    'gata_rainha':          { name: 'Gata Rainha',         emoji: '👑',  accent: '#7209B7' },
    'gata_bugada':          { name: 'Gata Bugada',         emoji: '🙀',  accent: '#EA526F' },
    'gata_memes':           { name: 'Gata dos Memes',      emoji: '😹',  accent: '#F72585' },
    'felina_psicanalista':  { name: 'Felina Psicanalista', emoji: '😼',  accent: '#4361EE' },
    // estado auxiliar (erro/rate-limit)
    'tired':                { name: 'Claudia Cansada',     emoji: '😴',  accent: '#6a6385' }
};

// Normaliza a chave: tira acento, minúscula, espaços->_. Robusto a encoding.
function normCat(cat) {
    if (!cat) return 'default';
    return String(cat)
        .normalize('NFD').replace(/[̀-ͯ]/g, '') // remove diacríticos
        .toLowerCase().trim().replace(/\s+/g, '_');
}

function persona(cat) {
    return PERSONAS[normCat(cat)] || PERSONAS.default;
}

const POSITIONS = [
    'position-left', 'position-center', 'position-right',
    'position-top-left', 'position-top-right',
    'position-bottom-left', 'position-bottom-right'
];

let currentCategory = 'default';

/* ---------- Init ---------- */
document.addEventListener('DOMContentLoaded', function () {
    console.log('☁️👜 aiClaudia');

    const character = document.getElementById('claudiaCharacter');
    if (character) character.classList.add('bob');
    moveClaudia();
    setInterval(moveClaudia, 7000);

    const textarea = document.getElementById('userInput');
    if (textarea) {
        textarea.placeholder = pick(PLACEHOLDERS);
        textarea.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendToClaudia();
            }
        });
        textarea.addEventListener('input', autoGrow);
    }

    renderSuggestions();
    greet();
});

/* ---------- Envio ---------- */
function sendToClaudia() {
    const input = document.getElementById('userInput');
    const button = document.getElementById('sendButton');
    const userMessage = input.value.trim();

    if (!userMessage) { showToast('Escreve algo primeiro 😉'); return; }
    if (!checkRateLimit()) {
        showToast('Tô cansada, tem nuvem no céu hoje não — volta daqui 5min!');
        return;
    }

    clearSuggestions();
    appendUserMessage(userMessage);
    input.value = '';
    autoGrow.call(input);

    button.disabled = true;
    const typingEl = appendTyping();

    callAPI(userMessage)
        .then(response => {
            if (response.error) {
                if (response.error === 'rate_limit_exceeded') {
                    return { text: 'Tô cansada, tem nuvem no céu hoje não — volta daqui 5min!', category: 'tired' };
                }
                return { text: 'O céu aqui tá azul e sem nuvem; tô na sombra, lendo uma revista. Volta mais tarde?', category: 'tired' };
            }
            return { text: response.response, category: response.category };
        })
        .catch(err => {
            console.error('Erro:', err);
            return { text: 'O céu aqui tá azul e sem nuvem; tô na sombra, lendo uma revista. Volta mais tarde?', category: 'tired' };
        })
        .then(({ text, category }) => {
            removeTyping(typingEl);
            appendClaudiaMessage(text, category);
        })
        .finally(() => {
            button.disabled = false;
            input.placeholder = pick(PLACEHOLDERS);
            input.focus();
        });
}

/* ---------- Rate limit ---------- */
function checkRateLimit() {
    const now = Date.now();
    const windowMs = WINDOW_MINUTES * 60 * 1000;
    let requests = JSON.parse(localStorage.getItem(RATE_LIMIT_KEY) || '[]');
    requests = requests.filter(t => now - t < windowMs);
    if (requests.length >= MAX_REQUESTS) return false;
    requests.push(now);
    localStorage.setItem(RATE_LIMIT_KEY, JSON.stringify(requests));
    return true;
}

/* ---------- Sessão ---------- */
const getSessionId = () => localStorage.getItem(SESSION_KEY);
const setSessionId = (id) => localStorage.setItem(SESSION_KEY, id);
const clearSession  = () => localStorage.removeItem(SESSION_KEY);

async function callAPI(userMessage) {
    const sessionId = getSessionId();
    const response = await fetch('/api/process-message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_message: userMessage, session_id: sessionId })
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    if (data.session_id) {
        setSessionId(data.session_id);
        if (data.is_new_session && data.category) {
            revealPersona(data.category);
        }
    }
    if (data.category) applyPersona(data.category);
    return data;
}

/* ---------- Render ---------- */
const thread = () => document.getElementById('chatThread');
const scrollDown = () => { const t = thread(); if (t) t.scrollTop = t.scrollHeight; };
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str == null ? '' : String(str);
    return d.innerHTML;
}

/** Markdown leve para respostas da Claudia: **negrito**, *itálico*, quebras de linha. */
function formatResponseText(str) {
    let s = escapeHtml(str);
    s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');
    return s.replace(/\n/g, '<br>');
}

function nowTime() {
    return new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function appendUserMessage(text) {
    const el = document.createElement('div');
    el.className = 'chat-msg chat-msg-user';
    el.innerHTML = `<div class="bubble">${escapeHtml(text)}<span class="timestamp">${nowTime()}</span></div>`;
    thread().appendChild(el);
    scrollDown();
}

function appendClaudiaMessage(text, category) {
    const p = persona(category);
    const el = document.createElement('div');
    el.className = 'chat-msg chat-msg-claudia';
    el.innerHTML = `
        <div class="avatar">${p.emoji}</div>
        <div class="bubble">
            <div class="persona">${escapeHtml(p.name)}</div>
            <div class="response-text">${formatResponseText(text)}</div>
            <span class="timestamp">${nowTime()}</span>
        </div>`;
    thread().appendChild(el);
    scrollDown();
}

function appendTyping() {
    const character = document.getElementById('claudiaCharacter');
    const avatar = (character && character.textContent.trim()) || persona(currentCategory).emoji;
    const el = document.createElement('div');
    el.className = 'chat-msg chat-msg-claudia typing';
    el.innerHTML = `<div class="avatar">${avatar}</div>
        <div class="bubble"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>`;
    thread().appendChild(el);
    scrollDown();
    return el;
}

function removeTyping(el) { if (el && el.parentNode) el.parentNode.removeChild(el); }

function appendSystem(html) {
    const el = document.createElement('div');
    el.className = 'chat-system';
    el.innerHTML = html;
    thread().appendChild(el);
    scrollDown();
}

function greet() {
    appendClaudiaMessage(
        'Oi! Sou a nuvem que guarda tudo (e às vezes esquece). Manda tua dúvida que eu respondo no meu humor de hoje. ☁️',
        'default'
    );
}

/* ---------- Sugestões ---------- */
function renderSuggestions() {
    const box = document.getElementById('suggestions');
    if (!box) return;
    box.innerHTML = '';
    SUGGESTIONS.forEach(s => {
        const b = document.createElement('button');
        b.className = 'chip';
        b.type = 'button';
        b.textContent = s;
        b.onclick = () => {
            const input = document.getElementById('userInput');
            input.value = s;
            sendToClaudia();
        };
        box.appendChild(b);
    });
}
function clearSuggestions() {
    const box = document.getElementById('suggestions');
    if (box) box.innerHTML = '';
}

/* ---------- Persona / tema ---------- */
function applyPersona(category) {
    currentCategory = category;
    const p = persona(category);
    document.documentElement.style.setProperty('--accent', p.accent);
    document.documentElement.style.setProperty('--accent-soft', hexToSoft(p.accent, 0.13));
    updateClaudiaAppearance(category);
}

function revealPersona(category) {
    const p = persona(category);
    appendSystem(`✨ hoje quem te atende: <b>${escapeHtml(p.name)}</b> ${p.emoji}`);
    showPersonaBadge(p);
}

function showPersonaBadge(p) {
    const badge = document.getElementById('personaBadge');
    if (!badge) return;
    badge.textContent = `${p.emoji} ${p.name}`;
    badge.hidden = false;
}

function hexToSoft(hex, alpha) {
    const h = hex.replace('#', '');
    const r = parseInt(h.substring(0, 2), 16);
    const g = parseInt(h.substring(2, 4), 16);
    const b = parseInt(h.substring(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/* ---------- Nova conversa ---------- */
function startNewConversation() {
    clearSession();
    thread().innerHTML = '';
    applyPersona('default');
    const badge = document.getElementById('personaBadge');
    if (badge) badge.hidden = true;
    appendSystem('🔄 nova conversa — a próxima mensagem sorteia um perfil');
    greet();
    renderSuggestions();
    const input = document.getElementById('userInput');
    if (input) input.focus();
}
function resetSession() { startNewConversation(); } // atalho de console

/* ---------- Personagem ---------- */
function moveClaudia() {
    const c = document.getElementById('claudiaCharacter');
    if (!c) return;
    POSITIONS.forEach(pos => c.classList.remove(pos));
    c.classList.add(pick(POSITIONS));
}

function updateClaudiaAppearance(category) {
    const c = document.getElementById('claudiaCharacter');
    if (!c) return;
    c.textContent = persona(category).emoji;
    c.classList.remove('pop'); void c.offsetWidth; c.classList.add('pop');
    moveClaudia();
}

/* ---------- Util UI ---------- */
function autoGrow() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 140) + 'px';
}

function showToast(message) {
    const t = document.createElement('div');
    t.className = 'toast';
    t.textContent = message;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 4000);
}

function showAbout(e) {
    if (e) e.preventDefault();
    appendSystem('☁️ <b>aiClaudia</b> é uma paródia: a nuvem brasileira que guarda tudo e responde com humor surreal. Não é serviço real nem conselho profissional — é arte de boteco digital.');
}
