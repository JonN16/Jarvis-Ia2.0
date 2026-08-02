"""
File Finder - Busca arquivos no PC. Suporta escolher a pasta (desktop,
documentos, downloads, ou todas) separadamente do termo de busca — assim
"procure em downloads" não confunde "downloads" com o nome do arquivo.

Se não houver termo específico, lista os arquivos mais recentes da pasta.
"""

import os
from tools.screenshot_tool import PASTA_SCREENSHOTS

PASTAS_NOMEADAS = {
    "desktop": [
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.path.expanduser("~"), "OneDrive", "Área de Trabalho"),
    ],
    "documentos": [
        os.path.join(os.path.expanduser("~"), "Documents"),
        os.path.join(os.path.expanduser("~"), "OneDrive", "Documentos"),
    ],
    "downloads": [
        os.path.join(os.path.expanduser("~"), "Downloads"),
    ],
    "prints": [PASTA_SCREENSHOTS],
}

TODAS_PASTAS = [p for lista in PASTAS_NOMEADAS.values() for p in lista]

PASTAS_IGNORADAS = {
    "node_modules", "venv", ".venv", ".git", "__pycache__",
    ".vscode", "AppData", "$RECYCLE.BIN",
}

MAX_PROFUNDIDADE = 6
MAX_RESULTADOS = 8

# Termos genéricos que significam "qualquer arquivo", não um nome de verdade
_TERMOS_GENERICOS = {
    "", "algum", "alguma", "algum arquivo", "alguma coisa",
    "qualquer", "qualquer arquivo", "arquivo", "um arquivo", "arquivos",
}


def _listar_diretorios(pasta_pedida: str) -> list:
    chave = (pasta_pedida or "").strip().lower()
    return PASTAS_NOMEADAS.get(chave, TODAS_PASTAS)


def _todos_arquivos(diretorios: list) -> list:
    """Retorna lista de (mtime, caminho) de todos os arquivos nas pastas dadas."""
    arquivos = []
    vistos = set()

    for base in diretorios:
        base_real = os.path.realpath(base)
        if not os.path.isdir(base_real) or base_real in vistos:
            continue
        vistos.add(base_real)

        for raiz, pastas, nomes in os.walk(base_real):
            pastas[:] = [p for p in pastas if p not in PASTAS_IGNORADAS]

            profundidade = raiz[len(base_real):].count(os.sep)
            if profundidade > MAX_PROFUNDIDADE:
                pastas[:] = []
                continue

            for nome in nomes:
                caminho = os.path.join(raiz, nome)
                try:
                    mtime = os.path.getmtime(caminho)
                except OSError:
                    mtime = 0
                arquivos.append((mtime, caminho))

    return arquivos


def _buscar_por_nome(termo: str, diretorios: list) -> list:
    termo = termo.lower()
    encontrados = []
    for _, caminho in _todos_arquivos(diretorios):
        if termo in os.path.basename(caminho).lower():
            encontrados.append(caminho)
            if len(encontrados) >= MAX_RESULTADOS:
                break
    return encontrados


def buscar_arquivo(args: dict) -> str:
    termo = (args.get("nome") or "").strip()
    termo = termo.replace("*", "").replace("?", "").strip()  # remove wildcards — busca é substring literal
    diretorios = _listar_diretorios(args.get("pasta"))

    # Sem termo específico: lista os arquivos mais recentes da pasta
    if termo.lower() in _TERMOS_GENERICOS:
        arquivos = _todos_arquivos(diretorios)
        if not arquivos:
            return "Não achei nenhum arquivo nessa pasta."
        arquivos.sort(key=lambda x: x[0], reverse=True)
        nomes = [os.path.basename(c) for _, c in arquivos[:5]]
        return f"Os arquivos mais recentes são: {', '.join(nomes)}"

    resultados = _buscar_por_nome(termo, diretorios)

    if not resultados:
        return f"Não encontrei nenhum arquivo com '{termo}' nessa pasta."

    if len(resultados) == 1:
        caminho = resultados[0]
        try:
            os.startfile(caminho)
            return f"Encontrei e abri: {os.path.basename(caminho)}"
        except Exception as e:
            return f"Encontrei {os.path.basename(caminho)}, mas não consegui abrir: {e}"

    nomes = [os.path.basename(c) for c in resultados]
    lista = ", ".join(nomes[:6])
    extra = f" e mais {len(nomes) - 6}" if len(nomes) > 6 else ""
    return f"Encontrei {len(resultados)} arquivos com '{termo}': {lista}{extra}. Pode especificar melhor?"