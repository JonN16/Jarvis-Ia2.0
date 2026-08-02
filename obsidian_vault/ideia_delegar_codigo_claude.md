# Ideia futura: ferramenta pro Jarvis delegar código pro Claude

## O problema
O cérebro do Jarvis hoje é um modelo local pequeno (`qwen2.5:7b` via Ollama).
Ele já tem dificuldade em tarefas relativamente simples de tool-calling (ver
`ideia_bibliotecas_ia.md`) — pedir pra ele **escrever ou corrigir código**
seria pedir demais. Só que trocar o cérebro inteiro por um modelo mais forte
(API paga) rodaria caro, já que ele processaria toda conversa comum (tocar
música, WhatsApp, etc), não só as tarefas de código.

## A ideia
Em vez de trocar o cérebro inteiro, adicionar **uma ferramenta nova e
específica** que só entra em ação quando o pedido é sobre código — o resto
continua no modelo local rápido/grátis. Basicamente: uma tool a mais no
`tools/registry.py`, do mesmo jeito que `controlar_spotify` ou
`controlar_whatsapp`.

## Como funcionaria (fluxo)
1. Você fala: "Jarvis, melhora o código desse arquivo" ou "corrige o bug no
   `spotify_service.py`".
2. Uma função nova (ex: `tools/code_assistant.py` → `consultar_claude_codigo`)
   lê o conteúdo do arquivo em disco.
3. Monta uma mensagem com o conteúdo do arquivo + a instrução, e manda pra
   API do Claude (biblioteca `anthropic`, é o mesmo padrão de chamada HTTP
   que a biblioteca `openai` — ver `ideia_bibliotecas_ia.md`).
4. Extrai só o bloco de código da resposta (o Claude normalmente escreve
   explicação junto do código — precisa parsear e separar).
5. Salva o resultado.

## Esqueleto de código (ponto de partida, não testado)

```python
# tools/code_assistant.py
import os
import re
import anthropic

_cliente = anthropic.Anthropic()  # pega a API key da variável de ambiente ANTHROPIC_API_KEY

def consultar_claude_codigo(caminho_arquivo: str, instrucao: str) -> str:
    if not os.path.exists(caminho_arquivo):
        return f"Não encontrei o arquivo '{caminho_arquivo}'"

    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        codigo_original = f.read()

    prompt = (
        f"Aqui está o conteúdo do arquivo '{os.path.basename(caminho_arquivo)}':\n\n"
        f"```python\n{codigo_original}\n```\n\n"
        f"Instrução: {instrucao}\n\n"
        f"Responda APENAS com o código completo do arquivo já corrigido/melhorado, "
        f"dentro de um bloco de código, sem explicação antes ou depois."
    )

    resposta = _cliente.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    texto_resposta = resposta.content[0].text

    # Extrai o conteúdo de dentro do bloco ```...```
    match = re.search(r"```(?:python)?\n(.*?)```", texto_resposta, re.DOTALL)
    codigo_novo = match.group(1) if match else texto_resposta

    caminho_novo = caminho_arquivo.replace(".py", "_novo.py")
    with open(caminho_novo, "w", encoding="utf-8") as f:
        f.write(codigo_novo)

    return f"Pronto, salvei a versão nova em '{os.path.basename(caminho_novo)}'. Quer que eu substitua o original?"
```

## Pontos importantes a resolver antes de usar de verdade

- **Nunca sobrescrever o arquivo original direto.** Sempre salvar como cópia
  (`arquivo_novo.py`) e perguntar antes de substituir — sobrescrever código
  que funciona sem revisão é risco alto de perder algo que estava certo.
- **Confirmação de duas etapas**: o Jarvis devia perguntar "quer que eu
  substitua o original?" e só sobrescrever depois de um "sim" explícito —
  parecido com o padrão de confirmação que já existe pra ações destrutivas.
- **Custo**: como só roda quando o pedido é claramente sobre código, o gasto
  com a API fica bem menor do que trocar o cérebro inteiro. Vale colocar um
  limite de tamanho de arquivo (ex: não mandar arquivos gigantes) pra não
  estourar custo/tokens à toa.
- **Diff antes de aceitar**: seria ótimo mostrar as diferenças (`difflib` no
  Python tem isso pronto) entre o arquivo original e o novo, em vez de só
  falar "pronto" — assim dá pra revisar o que mudou antes de aceitar.
- **Detectar quando é "pedido de código"**: precisa de um jeito confiável do
  modelo local saber quando chamar essa tool em vez de tratar como conversa
  normal — provavelmente vale a pena ser bem explícito no prompt do sistema
  sobre quando usar essa ferramenta (nome de arquivo `.py` mencionado, palavras
  como "corrige", "melhora o código", etc.).

## Nota
Isso é, na prática, uma versão caseira e simplificada do que o **Claude
Code** já faz de forma bem mais robusta (histórico de mudanças, diff,
execução de testes automático). Vale a pena como projeto de aprendizado,
mas não substitui a ferramenta de verdade pra uso sério.
