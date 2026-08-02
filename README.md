# Jarvis v2

Assistente pessoal por voz e texto, rodando localmente com um modelo LLM via Ollama e integrando Spotify, WhatsApp Desktop, sistema Windows, arquivos e memória em Obsidian.

## O que o projeto faz

- Escuta fala pelo microfone e transforma em texto.
- Responde com voz sintetizada via Edge TTS.
- Usa um modelo local do Ollama para decidir quando chamar ferramentas.
- Pode:
  - controlar Spotify
  - abrir aplicativos
  - ajustar volume
  - tirar screenshots
  - buscar arquivos no PC
  - enviar/abrir WhatsApp Desktop
  - guardar e recuperar informações na pasta de memória do Obsidian

## Requisitos

- Windows
- Python 3.10+ (recomendado 3.11)
- Ollama instalado e rodando localmente
- Microfone e alto-falante ou fones
- Internet para:
  - reconhecimento de fala via Google Speech Recognition
  - síntese de voz via Edge TTS
  - integração com Spotify e serviços externos

## Instalação

### 1) Clone o projeto

```powershell
git clone <seu-repositorio>
cd jarvis_v2
```

### 2) Crie um ambiente virtual

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3) Instale as dependências

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Ou use o script pronto para Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
```

### 4) Instale o Ollama

Baixe e instale o Ollama em: https://ollama.com/

Depois rode:

```powershell
ollama pull qwen2.5:7b
```

### 5) Configure o Spotify

Crie um app no Spotify Developer Dashboard:

- https://developer.spotify.com/dashboard
- defina a redirect URI como:
  - http://localhost:8888/callback

Copie o exemplo do ambiente:

```powershell
Copy-Item .env.example .env
```

Edite o arquivo .env com suas credenciais:

```env
SPOTIFY_CLIENT_ID=seu_client_id
SPOTIFY_CLIENT_SECRET=seu_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
```

## Uso

### Iniciar o assistente

```powershell
python main.py
```

### Comandos exemplos

- "toca uma música boa"
- "abre o spotify"
- "qual hora é?"
- "pula a música"
- "tira um print"
- "procura um arquivo no downloads"
- "envia uma mensagem para João"

## Estrutura do projeto

```text
main.py                 # ponto de entrada
core/
  brain.py              # conversa com o Ollama e histórico
  dispatcher.py         # executa as ferramentas escolhidas
tools/
  registry.py           # lista de ferramentas disponíveis
  voice_input.py        # captura de áudio do microfone
  voice_output.py       # síntese de voz
  spotify_service.py    # integração com Spotify
  whatsapp_service.py   # integração com WhatsApp Desktop
  memory_service.py     # memória em Obsidian
  system_tools.py       # volume, hora e abertura de apps
  screenshot_tool.py    # captura de tela
  file_finder.py        # busca de arquivos
scripts/
  setup_windows.ps1     # instalação rápida no Windows
```

## Observações importantes

- O reconhecimento de voz depende de internet.
- A síntese de voz também depende de internet.
- Algumas ações do Spotify podem falhar em contas grátis ou sem dispositivo ativo.
- A pasta obsidian_vault/ é usada como memória persistente e pode ser aberta diretamente no Obsidian.

## Arquivos de apoio

- .env.example: modelo de configuração do ambiente
- scripts/setup_windows.ps1: script de instalação para Windows

## Futuro do projeto

As ideias de evolução, melhorias e próximos passos do Jarvis estão organizadas na pasta [obsidian_vault](obsidian_vault). Quem abrir o README já consegue ver alguns exemplos do que está sendo pensado:

- [obsidian_vault/ideias_futuras_jarvis.md](obsidian_vault/ideias_futuras_jarvis.md): visão geral das próximas melhorias e expansões do projeto.
- [obsidian_vault/ideia_bibliotecas_ia.md](obsidian_vault/ideia_bibliotecas_ia.md): ideias sobre uso de bibliotecas e ferramentas de IA.
- [obsidian_vault/ideia_delegar_codigo_claude.md](obsidian_vault/ideia_delegar_codigo_claude.md): propostas para delegar parte do código para modelos externos.
- [obsidian_vault/ideia_whatsapp_waha.md](obsidian_vault/ideia_whatsapp_waha.md): ideias para integrar o Jarvis com WhatsApp via WAHA.

Esses documentos servem como um espaço de planejamento para o crescimento do projeto e podem ser abertos diretamente no Obsidian.

## Notas de desenvolvimento

Para validar a sintaxe do projeto:

```powershell
python -m compileall .
```