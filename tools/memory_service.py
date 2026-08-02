"""
Memory Service - Memória de longo prazo do Jarvis usando um vault Obsidian
(arquivos Markdown simples). Pode ser aberto no app do Obsidian pra
visualizar/editar manualmente também.

Estrutura:
    obsidian_vault/
        Perfil.md              -> fatos estáveis sobre o usuário
        Memorias/AAAA-MM-DD.md  -> notas do dia (timestamped)

Busca por palavra-chave: sem embeddings, sem dependência pesada — conta
sobreposição de palavras entre a consulta e cada entrada salva.
"""

import os
import re
from datetime import datetime

VAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "obsidian_vault")
PASTA_MEMORIAS = os.path.join(VAULT_PATH, "Memorias")
ARQUIVO_PERFIL = os.path.join(VAULT_PATH, "Perfil.md")

_STOPWORDS = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "que", "e", "é",
    "um", "uma", "para", "com", "em", "no", "na", "nos", "nas", "eu", "você",
    "meu", "minha", "seu", "sua", "isso", "isso", "ser", "estou", "está",
}


def _garantir_estrutura():
    os.makedirs(PASTA_MEMORIAS, exist_ok=True)
    if not os.path.exists(ARQUIVO_PERFIL):
        with open(ARQUIVO_PERFIL, "w", encoding="utf-8") as f:
            f.write("# Perfil\n\nFatos estáveis sobre o usuário, mantidos pelo Jarvis.\n\n")


def _arquivo_do_dia() -> str:
    hoje = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(PASTA_MEMORIAS, f"{hoje}.md")


def _tokenizar(texto: str) -> set:
    palavras = re.findall(r"\w+", texto.lower())
    return {p for p in palavras if p not in _STOPWORDS and len(p) > 2}


def salvar_memoria(texto: str, categoria: str = "geral") -> str:
    _garantir_estrutura()

    arquivo_dia = _arquivo_do_dia()
    novo = not os.path.exists(arquivo_dia)

    # Evita duplicar a mesma anotação várias vezes no mesmo dia (o modelo
    # às vezes re-salva o mesmo fato em turnos seguidos).
    if not novo:
        with open(arquivo_dia, "r", encoding="utf-8") as f:
            conteudo_hoje = f.read().lower()
        if texto.strip().lower() in conteudo_hoje:
            return "Já tinha anotado isso."

    agora = datetime.now().strftime("%H:%M")
    linha = f"- [{agora}] {texto}\n"

    with open(arquivo_dia, "a", encoding="utf-8") as f:
        if novo:
            f.write(f"# {datetime.now().strftime('%d/%m/%Y')}\n\n")
        f.write(linha)

    if categoria == "perfil":
        with open(ARQUIVO_PERFIL, "r", encoding="utf-8") as f:
            conteudo_atual = f.read()

        linha_perfil = f"- {texto}\n"
        if texto.strip().lower() not in conteudo_atual.lower():
            with open(ARQUIVO_PERFIL, "a", encoding="utf-8") as f:
                f.write(linha_perfil)

    return "Anotado."


def buscar_memoria(consulta: str, max_resultados: int = 5) -> str:
    _garantir_estrutura()

    palavras_consulta = _tokenizar(consulta)
    if not palavras_consulta:
        return "Não entendi bem o que buscar."

    candidatos = []  # (score, texto_da_linha)

    arquivos = [ARQUIVO_PERFIL]
    if os.path.isdir(PASTA_MEMORIAS):
        arquivos += [
            os.path.join(PASTA_MEMORIAS, nome)
            for nome in os.listdir(PASTA_MEMORIAS)
            if nome.endswith(".md")
        ]

    for caminho in arquivos:
        if not os.path.exists(caminho):
            continue
        with open(caminho, "r", encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if not linha.startswith("-"):
                    continue
                palavras_linha = _tokenizar(linha)
                score = len(palavras_consulta & palavras_linha)
                if score > 0:
                    candidatos.append((score, linha.lstrip("- ")))

    if not candidatos:
        return "Não encontrei nada relevante sobre isso nas minhas memórias."

    candidatos.sort(key=lambda x: x[0], reverse=True)
    melhores = [texto for _, texto in candidatos[:max_resultados]]

    return "Encontrei isso: " + " | ".join(melhores)


def controlar_memoria(acao: str, texto: str = None, categoria: str = "geral") -> dict:
    """
    acao: salvar | buscar
    texto: conteúdo a salvar, ou consulta de busca
    categoria: "perfil" (fato estável) ou "geral" (só no diário do dia) — usado em 'salvar'

    Retorna: {"sucesso": bool, "mensagem": str}
    """
    if not texto:
        return {"sucesso": False, "mensagem": "Preciso saber o que salvar ou buscar."}

    if acao == "salvar":
        msg = salvar_memoria(texto, categoria)
        return {"sucesso": True, "mensagem": msg}

    if acao == "buscar":
        msg = buscar_memoria(texto)
        return {"sucesso": True, "mensagem": msg}

    return {"sucesso": False, "mensagem": f"Ação '{acao}' não reconhecida"}