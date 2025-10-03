// ☁️👜 aiClaudia - Main JavaScript

// Rate limiting (frontend)
const RATE_LIMIT_KEY = 'aiclaudia_rate_limit';
const MAX_REQUESTS = 3;
const WINDOW_MINUTES = 3; // 3 minutos, mas texto mantém "5min"

// Placeholders aleatórios
const placeholders = [
    "Tá na dúvida? Eu sou a nuvem que guarda tudo. Pergunte qualquer coisa!",
    "Perdeu na memória? A aiClaudia é seu achados e perdidos digital.",
    "Precisa de ajuda? Eu sou sua assistente pessoal, pronta pra informar.",
    "Confie na nuvem: aqui sua dúvida vira resposta.",
    "Dependência digital? Deixe comigo, eu sou a aiClaudia."
];

let clippyAgent;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('☁️👜 aiClaudia');
    setRandomPlaceholder();

    // Load Clippy
    clippy.load('Peedy', function(agent) {
        clippyAgent = agent;
        clippyAgent.show();
        clippyAgent.speak('Saudações! Sou a aiClaudia, no corpo de um papagaio. Pode perguntar o que quiser!');
    }, undefined, 'front/lib/clippyjs/agents/');
    
    // Add enter key support for textarea
    const textarea = document.getElementById('userInput');
    if (textarea) {
        textarea.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault(); // Previne quebra de linha
                sendToClaudia();
            }
        });
    }
});

function sendToClaudia() {
    const input = document.getElementById('userInput');
    const button = document.getElementById('sendButton');
    const userMessage = input.value.trim();
    
    if (!userMessage) {
        showAlert('Digite algo primeiro!', 'warning');
        if (clippyAgent) clippyAgent.speak('Você precisa digitar algo para eu poder te ajudar!');
        return;
    }
    
    // Check rate limit
    if (!checkRateLimit()) {
        const msg = 'Tô cansada, tem nuvem no céu hoje não, volta daqui 5min!';
        showAlert(msg, 'info');
        if (clippyAgent) clippyAgent.speak(msg);
        return;
    }
    
    // Disable button and show loading
    button.disabled = true;
    button.innerHTML = '<span class="material-icons">hourglass_empty</span> Consultando...';
    
    // Animate Peedy while processing
    if (clippyAgent) clippyAgent.animate();

    // Show modal with loading
    showModal();
    showLoading();
    
    // Call API
    callAPI(userMessage)
        .then(response => {
            let claudiaResponseText;
            let claudiaResponseTitle = '<span class="material-icons">cloud_done</span> | aiClaudia';

            if (response.error) {
                if (response.error === 'rate_limit_exceeded') {
                    claudiaResponseText = 'Tô cansada, tem nuvem no céu hoje não, volta daqui 5min!';
                    claudiaResponseTitle = 'Claudia Cansada';
                } else {
                    claudiaResponseText = 'O céu aqui tá azul e não tem nenhuma nuvem; tô na sombra, descansando e lendo uma revista. Volta mais tarde?';
                    claudiaResponseTitle = 'De pernas pro ar!';
                }
            } else {
                claudiaResponseText = response.response;
            }

            // Peedy speaks the response
            if (clippyAgent) {
                clippyAgent.speak(claudiaResponseText);
            }
            showResponse(claudiaResponseText, claudiaResponseTitle);
        })
        .catch(error => {
            console.error('Erro:', error);
            const errorMsg = 'O céu aqui tá azul e não tem nenhuma nuvem; tô na sombra, descansando e lendo uma revista. Volta mais tarde?';
            if (clippyAgent) clippyAgent.speak(errorMsg);
            showResponse(errorMsg, 'De pernas pro ar!');
        })
        .finally(() => {
            // Re-enable button
            button.disabled = false;
            button.innerHTML = '<span class="material-icons">send</span> consultar';
            
            // Limpar campo e definir novo placeholder
            clearInputAndSetNewPlaceholder();
        });
}

function checkRateLimit() {
    const now = Date.now();
    const windowMs = WINDOW_MINUTES * 60 * 1000;
    
    // Get stored data
    const stored = localStorage.getItem(RATE_LIMIT_KEY);
    let requests = stored ? JSON.parse(stored) : [];
    
    // Remove old requests outside the window
    requests = requests.filter(time => now - time < windowMs);
    
    // Check if limit exceeded
    if (requests.length >= MAX_REQUESTS) {
        return false;
    }
    
    // Add current request
    requests.push(now);
    localStorage.setItem(RATE_LIMIT_KEY, JSON.stringify(requests));
    
    return true;
}

async function callAPI(userMessage) {
    const response = await fetch('/api/process-message', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            user_message: userMessage
        })
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
}

function showModal() {
    const modal = new bootstrap.Modal(document.getElementById('modal'));
    modal.show();
}

function showLoading() {
    const responseDiv = document.getElementById('claudiaResponse');
    responseDiv.innerHTML = `
        <div class="loading">
            <span class="material-icons">card_travel</span>
            <div class="rainbow-arrows">> > > > ></div>
            <span class="material-icons">cloud</span>
            <p>Consultando...</p>
        </div>
    `;
}

function showResponse(responseText, title) {
    const responseDiv = document.getElementById('claudiaResponse');
    const modalTitle = document.getElementById('modalTitle');
    
    // Atualizar título do modal
    modalTitle.innerHTML = title;
    
    // Mostrar apenas o texto da resposta
    responseDiv.innerHTML = `<div class="response-text">${responseText}</div>`;
}

function showAlert(message, type = 'info') {
    // Create Bootstrap alert
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

function setRandomPlaceholder() {
    const input = document.getElementById('userInput');
    if (input) {
        const randomPlaceholder = placeholders[Math.floor(Math.random() * placeholders.length)];
        input.placeholder = randomPlaceholder;
    }
}

function clearInputAndSetNewPlaceholder() {
    const input = document.getElementById('userInput');
    if (input) {
        input.value = '';
        setRandomPlaceholder();
    }
}

// TODO: Implementar random de cores de fundo (desenvolvimento futuro)
// function randomizeBackground() { ... }