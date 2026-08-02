# Ideia futura: bibliotecas de IA pro Jarvis (OpenAI, LangChain, Hugging Face, CrewAI)

Contexto: essas 4 ferramentas apareceram como pergunta numa conversa onde a
gente passou boa parte do tempo consertando bugs do modelo local
(`qwen2.5:7b` via Ollama) confundindo pedidos, narrando ação em vez de
executar, ignorando correções etc. A avaliação abaixo é com esse pano de
fundo: o que cada ferramenta resolveria de verdade pro Jarvis.

## Resumo rápido

| Ferramenta | Resolve o quê | Urgência pro projeto |
|---|---|---|
| OpenAI (API) | Modelo mais confiável em tool-calling — ataca a causa raiz da maioria dos bugs | **Alta** — maior custo-benefício |
| Hugging Face | STT offline melhor (Whisper) + memória semântica de verdade | Média — dois upgrades bem concretos |
| LangChain / LangGraph | Framework pronto pro ciclo "modelo → tool → resultado" e memória com embeddings | Baixa/média — qualidade de vida, não urgente |
| CrewAI | Orquestrar vários agentes especializados | Baixa — complexidade sem necessidade real hoje |

## Biblioteca OpenAI (`openai`)

Troca o modelo local (`qwen2.5:7b`) por um modelo hospedado (GPT-4o, GPT-5,
etc.) através da API.

**Por que ajudaria:** praticamente todos os bugs que a gente consertou nessa
conversa vêm de o modelo local ser pequeno demais pra seguir instrução de
tool-calling de forma consistente:
- Narrar "Controlando Spotify com a música X" em vez de emitir tool_call de
  verdade (precisou de 3 camadas de fallback regex no `dispatcher.py` pra
  contornar isso).
- Confundir "boa, era isso mesmo" (confirmação) com pedido de trocar de
  música.
- Ignorar pedido de correção e tocar outra música quase aleatória.

Um modelo maior/mais capaz erra muito menos nisso — não elimina 100%, mas
reduz bastante a necessidade de toda a "rede de segurança" que foi construída
na unha no `dispatcher.py`/`brain.py`.

**Trade-offs:**
- Custa por requisição (mesmo que barato pro volume de um assistente pessoal).
- Precisa de internet (hoje o cérebro roda 100% local via Ollama).
- Manda dados pra fora da máquina — inclusive o conteúdo da memória pessoal
  salva no Obsidian (`memory_service.py`), que hoje nunca sai do PC.

**Alternativa intermediária:** antes de ir pra API paga, testar um modelo
Ollama local maior (`qwen2.5:14b` ou `32b`, se a máquina aguentar) — mantém
tudo local e grátis, só exige mais VRAM/RAM.

## LangChain (ou LangGraph)

Framework que padroniza o ciclo "modelo decide → chama ferramenta → recebe
resultado → decide de novo" — exatamente o que foi montado na mão no
`brain.py` (loop de `MAX_TENTATIVAS`, detecção de "sucesso fantasma",
alimentação do resultado da tool de volta pro modelo).

Também tem abstrações de memória com **embeddings de verdade**, que
substituiriam a busca por sobreposição de palavras (`_tokenizar` +
interseção de conjuntos) que tem hoje no `memory_service.py` — hoje ela não
entende sinônimo ("trabalho" vs "emprego", por exemplo).

**Vale a pena se:** você quiser parar de manter esse código de robustez na
mão e preferir usar algo testado pela comunidade. **Não é obrigatório** — o
sistema atual funciona, só dá mais trabalho de manutenção quando aparece um
caso novo de "sucesso fantasma".

## Hugging Face (`transformers`, `sentence-transformers`)

Duas aplicações concretas, independentes uma da outra:

1. **STT offline via Whisper** — troca o Google Speech Recognition
   (`voice_input.py`, grátis mas precisa de internet e erra bastante com
   sotaque/ruído — vimos "i z o" sendo soletrado letra por letra, "cerrou"
   em vez de "errou") por Whisper local. Roda sem internet, geralmente mais
   preciso.
2. **Memória semântica** — usar `sentence-transformers` pra gerar embeddings
   das anotações do Obsidian (`memory_service.py`) em vez da busca por
   palavra-chave atual. Mesmo ganho de "entender sinônimo" que o LangChain
   traria, mas sem precisar adotar o framework inteiro — só a peça de
   embeddings.

## CrewAI

Orquestra **vários agentes especializados** conversando entre si (ex: um
agente "pesquisador", outro "planejador", outro "executor").

**Avaliação:** complexidade desnecessária pro Jarvis hoje, que é um
assistente fazendo uma coisa de cada vez (tocar música, mandar mensagem,
buscar arquivo). Só faria sentido se o projeto crescesse pra tarefas de
múltiplas etapas coordenadas — tipo "planeje minha viagem: pesquise voos,
compare preços, monte um roteiro". Deixar de lado por enquanto.

## Se for retomar essa ideia no futuro

Ordem sugerida de prioridade, do maior pro menor impacto:

1. Testar um Ollama local maior (`14b`/`32b`) antes de decidir se compensa
   pagar API da OpenAI — ver se resolve boa parte dos bugs de tool-calling
   sem abrir mão de rodar local.
2. Se ainda precisar de mais confiabilidade, migrar `core/brain.py` pra
   usar a API da OpenAI (ou outro provedor) em vez do Ollama.
3. Trocar STT pra Whisper local (Hugging Face) — ganho direto de precisão,
   independente da decisão sobre o modelo de "cérebro".
4. Avaliar `sentence-transformers` pra melhorar a busca de memória, se a
   busca por palavra-chave atual começar a incomodar na prática.
5. LangChain/LangGraph só se, em algum desses pontos acima, a manutenção
   manual do sistema de tool-calling ficar cansativa demais.
6. CrewAI: só reconsiderar se o projeto crescer pra tarefas de múltiplas
   etapas coordenadas.
