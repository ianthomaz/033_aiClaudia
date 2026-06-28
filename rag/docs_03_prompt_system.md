# Como o “género” da resposta é escolhido (sistema de prompts)

## Aleatório por categoria

O backend escolhe **uma categoria** de um ficheiro JSON (`rndbase_prompts.json`) com instruções do tipo: “fala como nuvem preguiçosa”, “horóscopo surreal”, “editorial de revista”, etc. Há rotação para **não repetir** a mesma categoria em sequência quando possível.

## O que é enviado ao modelo

1. Um **prefixo curto** com regras de voz e tamanho (sempre presente).
2. O **bloco de instruções** da categoria sorteada (o “modo” da resposta).
3. Se existir **sessão**, um **contexto** das últimas trocas para manter fio narrativo.

A pergunta do utilizador vai separada como **mensagem do utilizador**; o resto orienta o **estilo** da resposta, não o conteúdo factual da pergunta (que pode ser absurda de propósito).

## Sessões

Um `session_id` mantém a mesma “personalidade” (categoria) ao longo de várias mensagens, até o fluxo expirar ou o utilizador reiniciar. Isto evita que cada pergunta pare de um género completamente diferente sem ligação.
