import requests
from tools.registry import TOOLS
from core.dispatcher import executar

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:7b"

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Você é o Jarvis, assistente pessoal brasileiro. Responda SEMPRE em português do Brasil. "
        "Toda resposta DEVE usar uma tool_call de verdade (mecanismo estruturado da API) — "
        "nunca escreva o nome de uma função como texto, nunca narre uma ação em prosa. "
        "Se for só bater papo, use a ferramenta 'conversar'. "
        "Respostas são faladas em voz alta: seja curto e natural, sem listas. "
        "Nunca invente hora, data ou fatos — use uma ferramenta. "
        "Quando o usuário contar algo pessoal relevante (nome, curso, projeto, preferência), "
        "chame controlar_memoria (acao='salvar'). Quando ele perguntar algo que já disse antes, "
        "chame controlar_memoria (acao='buscar') primeiro. "
        "Se o usuário disser que a música tocada não é o que ele pediu ('não foi isso', "
        "'errou', 'não é essa'), NÃO toque outra música aleatória: junte TODOS os detalhes "
        "que ele já deu sobre essa música ao longo da conversa (nome, trecho, artista, banda, "
        "contexto) em uma única busca mais específica e chame controlar_spotify de novo com isso. "
        "Se o usuário disser que uma música tocada ANTES estava certa e pedir pra voltar a ela "
        "('era essa mesmo', 'volta pra aquela', 'era a de antes', 'você tinha acertado'), NÃO "
        "pesquise por nome de novo — chame controlar_spotify(acao='repetir', parametro=N), "
        "onde N é quantas músicas atrás na conversa era essa (1 = a música tocada logo antes "
        "da atual). Uma frase que é só agradecimento ou confirmação positiva sobre a música "
        "que está tocando AGORA ('boa', 'era isso mesmo', 'valeu', 'gostei', 'isso aí') NÃO é "
        "um pedido pra trocar de música — não chame controlar_spotify nesse caso, apenas "
        "responda com 'conversar'."
    )
}

# Palavras que indicam que o usuário pediu uma AÇÃO (não só bate-papo).
# Se a resposta do modelo não vier com tool_calls estruturado E o pedido
# bater com uma dessas palavras, tratamos como suspeito de "sucesso fantasma"
# mesmo que o texto da resposta pareça natural e não mencione a função.
_PALAVRAS_ACAO = [
    "toca", "toque", "pausa", "despausa", "retoma", "próxima", "proxima",
    "anterior", "volume", "aumenta", "diminui", "muta", "desmuta",
    "abre", "abra", "fecha", "spotify", "playlist", "fila", "curtidas",
    "manda mensagem", "envia mensagem", "whatsapp", "contato",
    "lembra", "salva", "anota", "memória", "memoria", "busca", "procura",
    "que horas", "tira um print", "tira print", "screenshot", "captura de tela",
    "busca arquivo", "procura arquivo", "achar arquivo", "encontrar arquivo",
]


def _parece_pedido_de_acao(texto_usuario: str) -> bool:
    texto = texto_usuario.lower()
    return any(p in texto for p in _PALAVRAS_ACAO)

MAX_HISTORICO = 12
MAX_TENTATIVAS = 3

historico = [SYSTEM_PROMPT]


def _podar_historico():
    global historico
    if len(historico) > MAX_HISTORICO + 1:
        historico = [SYSTEM_PROMPT] + historico[-MAX_HISTORICO:]


def _chamar_ollama() -> dict:
    payload = {
        "model": MODEL,
        "messages": historico,
        "tools": TOOLS,
        "stream": False,
        "options": {"temperature": 0.3}
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=1000)
    resp.raise_for_status()
    return resp.json()["message"]


def pensar(texto_usuario: str) -> str:
    """Retorna o texto final da resposta (pra imprimir e/ou falar)."""
    historico.append({"role": "user", "content": texto_usuario})

    texto_resposta = None

    for tentativa in range(MAX_TENTATIVAS):
        mensagem = _chamar_ollama()
        executou_de_verdade, texto_resposta, resultados_tool = executar(mensagem, texto_usuario)

        # Mesmo que o dispatcher tenha aceitado como "conversa normal", se o
        # PEDIDO do usuário claramente soava como uma ação e não veio
        # tool_calls estruturado, tratamos como suspeito de resposta
        # fantasma (o modelo narrou a ação em vez de executá-la de verdade).
        suspeito_de_fantasma = (
            texto_resposta is not None
            and not executou_de_verdade
            and not mensagem.get("tool_calls")
            and _parece_pedido_de_acao(texto_usuario)
        )
        if suspeito_de_fantasma:
            texto_resposta = None

        if texto_resposta is not None:
            # Resposta válida: ação real executada OU conversa normal de verdade.
            if mensagem.get("tool_calls"):
                historico.append(mensagem)
                # Feedback real do resultado de cada tool — sem isso o modelo
                # não sabe se a ação deu certo e tende a repetir ou inventar.
                for r in resultados_tool:
                    historico.append({
                        "role": "tool",
                        "content": r["content"],
                    })
            elif executou_de_verdade:
                historico.append({"role": "assistant", "content": "Comando executado."})
            else:
                historico.append(mensagem)
            break

        # Resposta inválida — pede pra tentar de novo com reforço
        print("[Jarvis] (não executou de verdade, tentando novamente...)")
        historico.append({
            "role": "user",
            "content": (
                "Você respondeu como se tivesse feito algo, mas não usou tool_calls "
                "de verdade. Execute a ação agora usando o mecanismo de tool_calls."
            )
        })

    if texto_resposta is None:
        texto_resposta = "Desculpa, não consegui executar esse comando direito. Pode repetir?"
        print(f"[Jarvis] {texto_resposta}")

    _podar_historico()
    return texto_resposta