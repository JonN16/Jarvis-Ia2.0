import json
import re
from tools.system_tools import abrir_app, hora_atual, controlar_volume
from tools.spotify_service import controlar_spotify
from tools.whatsapp_service import controlar_whatsapp
from tools.memory_service import controlar_memoria
from tools.screenshot_tool import tirar_screenshot
from tools.file_finder import buscar_arquivo


def conversar(args: dict) -> str:
    return args.get("resposta", "")


DESPACHO = {
    "abrir_app": abrir_app,
    "conversar": conversar,
    "hora_atual": hora_atual,
    "controlar_volume": controlar_volume,
    "controlar_spotify": lambda args: controlar_spotify(
        args.get("acao"), args.get("parametro")
    )["mensagem"],
    "controlar_whatsapp": lambda args: controlar_whatsapp(
        args.get("acao"), args.get("contato"), args.get("mensagem")
    )["mensagem"],
    "controlar_memoria": lambda args: controlar_memoria(
        args.get("acao"), args.get("texto"), args.get("categoria", "geral")
    )["mensagem"],
    "tirar_screenshot": tirar_screenshot,
    "buscar_arquivo": buscar_arquivo,
}

# Detecta chamadas tipo: nome_funcao("a", "b") escritas em texto puro quando
# o modelo falha em emitir um tool_call estruturado.
PADRAO_PSEUDO_CHAMADA = re.compile(r"(\w+)\(([^)]*)\)")

NOMES_FUNCOES = set(DESPACHO.keys())

# 'conversar' fica de fora dessa checagem: é o nome da ferramenta de bate-papo,
# mas também é uma palavra comum do português ("podemos conversar sobre...").
# Se deixássemos ela aqui, qualquer resposta de conversa normal que usasse essa
# palavra seria rejeitada como "menção fantasma" de função — mesmo sendo só
# uma resposta de texto legítima, sem nenhuma tentativa de fingir uma ação.
NOMES_FUNCOES_SUSPEITAS = NOMES_FUNCOES - {"conversar"}


def _menciona_funcao_sem_executar(conteudo: str) -> bool:
    """
    Detecta se o texto menciona o nome de uma função conhecida (em QUALQUER
    formato — parênteses, dois-pontos, maiúscula/minúscula, etc) sem que ela
    tenha sido realmente executada. Sinal de que o modelo tentou "chamar" a
    ferramenta escrevendo texto em vez de usar tool_calls de verdade.
    """
    if not conteudo:
        return False
    return any(
        re.search(rf"\b{re.escape(nome)}\b", conteudo, re.IGNORECASE)
        for nome in NOMES_FUNCOES_SUSPEITAS
    )


# Detecta pares chave='valor' ou chave="valor" — usado quando o modelo escreve
# controlar_memoria(acao='buscar', texto='...') em vez de posicional ou JSON.
PADRAO_KWARGS = re.compile(r"(\w+)\s*=\s*['\"]([^'\"]*)['\"]")


def _parsear_argumentos_posicionais(nome_funcao: str, bruto: str) -> dict:
    bruto = bruto.strip()

    # Tenta primeiro como JSON de verdade: controlar_spotify({"acao": "pause"})
    if bruto.startswith("{"):
        try:
            args_json = json.loads(bruto)
            if isinstance(args_json, dict):
                return args_json
        except (json.JSONDecodeError, ValueError):
            pass  # não era JSON válido, cai pros parsings abaixo

    # Tenta como kwargs: acao='buscar', texto='qual é meu nome'
    pares_kwargs = PADRAO_KWARGS.findall(bruto)
    if pares_kwargs:
        return {chave: valor for chave, valor in pares_kwargs}

    # Por último, posicional simples: "buscar", "qual é meu nome"
    valores = [v.strip().strip("'\"") for v in bruto.split(",") if v.strip()]

    mapa_chaves = {
        "controlar_spotify": ["acao", "parametro"],
        "controlar_whatsapp": ["acao", "contato", "mensagem"],
        "controlar_memoria": ["acao", "texto", "categoria"],
        "controlar_volume": ["acao"],
        "abrir_app": ["nome"],
        "buscar_arquivo": ["nome", "pasta"],
    }
    chaves = mapa_chaves.get(nome_funcao)
    if not chaves:
        return {}

    return dict(zip(chaves, valores))


# Extrai intenção de tocar música quando o modelo NARRA em prosa em vez de
# emitir tool_call ou pseudo-chamada de função — ex: o modelo escreveu
# 'Controlando o Spotify para tocar "Izo" da banda King Gaijins.' ao invés de
# realmente chamar a ferramenta. Exige aspas ao redor do nome da música pra
# evitar disparar em frases genéricas que só mencionam a palavra "tocar".
PADRAO_TOCAR_NATURAL = re.compile(
    r"(?:toc(?:ar|ando|a)|reproduz(?:ir|indo)|coloc(?:ar|ando|a))\s+"
    r"(?:a\s+m[uú]sica\s+)?[\"']([^\"']{2,60})[\"']"
    r"(?:\s+(?:da\s+banda|do\s+artista|de)\s+([^\.\n,]{2,60}))?",
    re.IGNORECASE,
)


# Segundo padrão de narração: o modelo às vezes não usa "tocar/colocar", e sim
# algo como 'Controlando Spotify com a música "X"' ou 'Controlando Spotify com
# o trecho "X" e "Y"' (quando o usuário deu um trecho de letra em vez do nome).
# Aceita até 2 trechos entre aspas, que são combinados numa busca só.
PADRAO_CONTROLANDO_SPOTIFY = re.compile(
    r"controlando\s+(?:o\s+)?spotify\s+com\s+(?:a\s+m[uú]sica|o\s+trecho)\s+"
    r"[\"']([^\"']{2,80})[\"']"
    r"(?:\s+e\s+[\"']([^\"']{2,80})[\"'])?"
    r"(?:\s+(?:da\s+banda|do\s+artista|de)\s+([^\.\n,]{2,60}))?",
    re.IGNORECASE,
)

# Ações simples do Spotify (sem parâmetro) narradas em vez de executadas —
# ex: "A próxima música será tocada agora." ou "Próxima música. Pronto!".
_ACOES_SIMPLES_SPOTIFY = [
    (re.compile(r"pr[oó]xima\s*m[uú]sica", re.IGNORECASE), "next"),
    (re.compile(r"m[uú]sica\s*anterior", re.IGNORECASE), "previous"),
    (re.compile(r"pausa(r|ndo|da)?\s*(a\s*)?(m[uú]sica|reprodu[çc][ãa]o|spotify)", re.IGNORECASE), "pause"),
    (re.compile(r"retoma(r|ndo|da)?\s*(a\s*)?(m[uú]sica|reprodu[çc][ãa]o|spotify)", re.IGNORECASE), "resume"),
]


def _tentar_fallback_linguagem_natural(conteudo: str) -> tuple:
    """
    Rede de segurança nível 2 (depois da pseudo-chamada de função): quando o
    modelo narra em português puro que vai fazer algo no Spotify em vez de
    executar de verdade, extrai a intenção da frase e EXECUTA — em vez de
    descartar a resposta e fazer o modelo tentar de novo do zero (o que pode
    esgotar as tentativas e falhar mesmo o modelo já sabendo o que fazer).
    """
    if not conteudo:
        return False, ""

    m = PADRAO_TOCAR_NATURAL.search(conteudo)
    if m:
        musica = m.group(1).strip()
        artista = (m.group(2) or "").strip()
        if musica:
            query = f"{musica} {artista}".strip()
            return True, controlar_spotify("play", query)["mensagem"]

    m = PADRAO_CONTROLANDO_SPOTIFY.search(conteudo)
    if m:
        trecho1 = m.group(1).strip()
        trecho2 = (m.group(2) or "").strip()
        artista = (m.group(3) or "").strip()
        query = " ".join(p for p in (trecho1, trecho2, artista) if p)
        if query:
            return True, controlar_spotify("play", query)["mensagem"]

    for padrao, acao in _ACOES_SIMPLES_SPOTIFY:
        if padrao.search(conteudo):
            return True, controlar_spotify(acao)["mensagem"]

    return False, ""


def _tentar_fallback_regex(conteudo: str) -> tuple:
    """
    Rede de segurança: se o modelo escreveu a chamada como texto/código em vez
    de tool_call estruturado, detecta e EXECUTA de verdade em vez de só imprimir.
    Retorna (executou: bool, texto_resposta: str).
    """
    if not conteudo:
        return False, ""

    respostas = []
    for nome_funcao_bruto, args_brutos in PADRAO_PSEUDO_CHAMADA.findall(conteudo):
        nome_funcao = nome_funcao_bruto.lower()
        if nome_funcao not in DESPACHO:
            continue
        args = _parsear_argumentos_posicionais(nome_funcao, args_brutos)
        if not args and nome_funcao != "hora_atual":
            continue
        resultado = DESPACHO[nome_funcao](args) or ""
        respostas.append(resultado)

    if respostas:
        return True, " ".join(respostas)
    return False, ""


def executar(mensagem: dict, texto_usuario: str = None) -> tuple:
    """
    Executa a decisão do modelo, imprime o resultado UMA vez e retorna o
    texto final — usado tanto pro terminal quanto pra fala (TTS).

    texto_usuario: a fala/mensagem original do usuário nesse turno — usada
    como busca de reserva quando o modelo chama controlar_memoria(buscar)
    sem preencher o campo 'texto' (evita o loop de "preciso saber o que buscar").

    Retorna: (executou_de_verdade: bool, texto_resposta: str, resultados_tool: list)
    resultados_tool é uma lista de dicts {"tool_call_id", "name", "content"}
    usada pelo brain.py pra alimentar o modelo com o resultado real de cada
    chamada (sem isso, o modelo não sabe se a ação deu certo e tende a
    repetir ou inventar que funcionou).
    """
    tool_calls = mensagem.get("tool_calls")

    if tool_calls:
        respostas = []
        resultados_tool = []
        for chamada in tool_calls:
            nome_funcao = chamada["function"]["name"]
            args = chamada["function"]["arguments"]
            if isinstance(args, str):
                args = json.loads(args)

            # Fallback: busca de memória sem termo preenchido usa a fala do usuário
            if nome_funcao == "controlar_memoria" and args.get("acao") == "buscar" and not args.get("texto"):
                args["texto"] = texto_usuario

            if nome_funcao in DESPACHO:
                resultado = DESPACHO[nome_funcao](args) or ""
            else:
                resultado = f"Não sei executar '{nome_funcao}'"

            respostas.append(resultado)
            resultados_tool.append({
                "tool_call_id": chamada.get("id", nome_funcao),
                "name": nome_funcao,
                "content": resultado,
            })

        texto_final = " ".join(r for r in respostas if r)
        print(f"[Jarvis] {texto_final}")
        return True, texto_final, resultados_tool

    conteudo = mensagem.get("content", "")

    executou, texto = _tentar_fallback_regex(conteudo)
    if executou:
        print(f"[Jarvis] {texto}")
        return True, texto, []

    executou, texto = _tentar_fallback_linguagem_natural(conteudo)
    if executou:
        print(f"[Jarvis] {texto}")
        return True, texto, []

    if _menciona_funcao_sem_executar(conteudo):
        # O modelo mencionou uma ação mas não a executou de verdade —
        # não aceita isso como resposta válida (evita "sucesso fantasma").
        return False, None, []

    print(f"[Jarvis] {conteudo or '(sem resposta)'}")
    return False, conteudo or "", []