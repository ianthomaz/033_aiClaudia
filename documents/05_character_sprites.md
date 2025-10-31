# 🎨 Sistema de Sprites da Claudia

## ✅ Status Atual

Sistema básico implementado com **emojis como placeholder**.

**Funcionalidades:**
- Claudia aparece em 7 posições diferentes
- Muda de posição a cada 10 segundos
- Muda aparência baseado na personalidade
- Animação suave de transição

---

## 📁 Arquivos

**HTML:** `index.html` - Contém `<div id="claudiaCharacter">`
**CSS:** `front/style.css` - Estilos `.claudia-scene` e `.claudia-character`
**JS:** `front/main.js` - Funções `moveClaudia()` e `updateClaudiaAppearance()`

---

## 🔄 Como Trocar por Sprites PNG

### 1. Preparar Sprites

Criar arquivos PNG:
```
img/claudia/
  ├── default.png
  ├── gata_oraculo.png
  ├── gata_rainha.png
  ├── nuvem_preguicosa.png
  └── ...
```

**Tamanho recomendado:** 128x128px ou 256x256px (PNG transparente)

---

### 2. Modificar JavaScript

**Trocar em `front/main.js`:**

```javascript
// ANTES (emojis):
const CLAUDIA_APPEARANCES = {
    'default': '👩‍💻',
    'gata_oraculo': '🐱',
    // ...
};

// DEPOIS (caminhos de imagem):
const CLAUDIA_APPEARANCES = {
    'default': 'img/claudia/default.png',
    'gata_oraculo': 'img/claudia/gata_oraculo.png',
    'gata_rainha': 'img/claudia/gata_rainha.png',
    'nuvem_preguicosa': 'img/claudia/nuvem_preguicosa.png',
    // ...
};

// Modificar função:
function updateClaudiaAppearance(category) {
    const character = document.getElementById('claudiaCharacter');
    if (!character) return;

    let appearance = CLAUDIA_APPEARANCES[category] || CLAUDIA_APPEARANCES['default'];

    // TROCAR de textContent para background-image:
    character.style.backgroundImage = `url('${appearance}')`;
    character.textContent = ''; // Limpar emoji

    moveClaudia();
}
```

---

### 3. Modificar CSS

**Adicionar em `front/style.css`:**

```css
.claudia-character {
    position: absolute;
    width: 128px;      /* Tamanho do sprite */
    height: 128px;
    background-size: contain;
    background-repeat: no-repeat;
    background-position: center;
    transition: all 0.5s ease-in-out;
    cursor: pointer;
    filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2));
}
```

---

### 4. Modificar HTML

**Trocar em `index.html`:**

```html
<!-- ANTES: -->
<div id="claudiaCharacter" class="claudia-character">
    👩‍💻
</div>

<!-- DEPOIS: -->
<div id="claudiaCharacter" class="claudia-character"
     style="background-image: url('img/claudia/default.png')">
</div>
```

---

## 🎨 Onde Conseguir Sprites

### Opção 1: Contratar Designer
- **Fiverr**: $20-50 por sprite set
- **99designs**: $30-100
- **Upwork**: $50-200

### Opção 2: Assets Prontos
- **Itch.io**: sprites grátis
- **OpenGameArt**: CC0 (domínio público)
- **Kenney**: assets free

### Opção 3: Gerar com IA
- **Midjourney**: $10/mês
- **Stable Diffusion**: grátis (rodar local)
- **DALL-E**: pay-per-use

---

## 📋 Checklist para Contratar Designer

**Brief para o designer:**

```
Preciso de sprites 2D para personagem "Claudia" (assistente virtual brasileira)

Estilo: [pixel art / cartoon / realista]
Tamanho: 256x256px
Formato: PNG transparente
Quantidade: 10-15 variações

Variações necessárias:
1. Default (trabalhando no PC)
2. Gata/Oráculo (mística)
3. Gata Rainha (elegante)
4. Nuvem Preguiçosa (dormindo)
5. Editorial (lendo jornal)
6. Horóscopo (com bola de cristal)
7. Cansada (exausta)
8. Pensativa
9. Feliz
10. [outras personalidades...]

Referências:
- Humor: Sarcástica, brasileira, cansada
- Cores: Roxo (#7209B7), Rosa (#F72585), Ciano (#23B5D3)
```

---

## 🔮 Futuras Melhorias

- Animações frame-by-frame (spritesheet)
- Idle animations (piscar, respirar)
- Transições entre estados
- Interações (click na Claudia)
- Cenário completo com elementos decorativos

---

**Status:** ✅ Sistema básico funcionando com emojis
**Próximo:** Substituir por sprites profissionais
