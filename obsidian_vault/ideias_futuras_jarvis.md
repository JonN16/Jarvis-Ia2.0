# Ideias futuras pro Jarvis (antes do hiato da faculdade)

Lista de ideias levantadas numa sessão de brainstorm, pra não perder o fio
quando eu voltar a mexer no projeto depois da faculdade.

## Funcionalidades novas

### Wake word ("Jarvis", "Ei Jarvis")
Hoje o loop principal fica sempre ouvindo e tentando interpretar qualquer
fala como comando — inclusive ruído/conversa de fundo. Um detector de wake
word faria ele só "acordar" quando eu chamar pelo nome.
- Opções: `openWakeWord` (open-source) ou `Porcupine` da Picovoice (tem tier
  grátis).
- Resolveria o problema de STT captando ruído e tentando responder coisa
  sem sentido.

### Calendário e lembretes
Integração com Google Calendar API — "que compromissos eu tenho hoje", "me
lembra às 15h de ligar pro fulano".
- Combina com o que já existe: `memory_service.py` já lida com "lembrar
  coisas", só falta o lado de horário/notificação de verdade.

### Visão via screenshot
Já existe `screenshot_tool.py`. Próximo passo natural: mandar a imagem pra
um modelo com visão (GPT-4o-mini, ou Llava local) e perguntar "o que tá
acontecendo nessa tela" / "resume esse erro que apareceu".

### Resumo de e-mail
Ler e resumir e-mails novos via Gmail API — mesmo espírito do que já foi
feito pro WhatsApp com o WAHA (ver `ideia_whatsapp_waha.md`).

## Engenharia / robustez

### Poda de histórico mais inteligente
Hoje o `core/brain.py` corta o histórico só por quantidade de mensagens
(`MAX_HISTORICO`), sem critério de conteúdo. Ideia: resumir automaticamente
as mensagens antigas (o próprio LLM resumindo) antes de descartar, em vez
de simplesmente truncar — evita perder contexto importante no meio de uma
conversa longa (relevante pro caso de "correção de música" que já vi
falhar por perda de contexto).

### Logging estruturado
Hoje é tudo `print()`. Trocar por `logging` com níveis (INFO/WARNING/ERROR)
e salvar em arquivo — dá histórico real pra debugar depois, sem precisar
copiar o terminal na mão toda vez que algo dá errado.

### Testes automatizados
`tools/dispatcher.py` é particularmente testável (funções puras, regex bem
definidos). Uns 15-20 testes cobrindo os casos de "sucesso fantasma"
(modelo narrando ação em vez de executar) seriam uma boa prova de robustez
e evitariam regressão quando eu mexer em algo.

### Rodar como serviço
Usar `NSSM` ou Task Scheduler no Windows pra o Jarvis subir sozinho no
boot e reiniciar sozinho se cair, em vez de precisar abrir o terminal
manualmente toda vez.

## Bibliotecas de IA a considerar

Ver nota separada: `ideia_bibliotecas_ia.md` — cobre OpenAI API, LangChain,
Hugging Face (Whisper + embeddings) e CrewAI, com avaliação de prioridade
pra cada uma.

## WhatsApp via WAHA

Ver nota separada: `ideia_whatsapp_waha.md` — trocar a automação por
`pyautogui` por uma API HTTP de verdade (WAHA), com envio sem roubar foco
da tela e verificação de mensagens novas sob demanda.

## Portfólio (quando for retomar/publicar)

- README com diagrama de arquitetura (brain → dispatcher → tools).
- Contar a história dos bugs resolvidos (ex: "sucesso fantasma", correção
  de música ignorada) — mostra raciocínio de debugging, não só integração
  de API.
- Testes automatizados (ver acima) — muda a percepção de "script pessoal"
  pra "projeto de engenharia".
- Separar segredos/dados pessoais (token Spotify, vínculo WhatsApp, vault
  do Obsidian) antes de deixar o repositório público — um "modo demo" sem
  essas dependências ajuda quem for avaliar/rodar.
