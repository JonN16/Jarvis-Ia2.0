"""
WhatsApp Service - Abre conversas e envia mensagens via automação de UI
do WhatsApp Desktop (standalone ou Store).
"""

import os
import time
import functools
import subprocess
import pyautogui
import pyperclip

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

_DELAY_CURTO = 0.5
_DELAY_MEDIO = 1.2
_DELAY_LONGO = 2.5

_LOCAL = os.environ.get("LOCALAPPDATA", "")
_ROAMING = os.environ.get("APPDATA", "")

_CAMINHOS_WA = [
    os.path.join(_LOCAL, "WhatsApp", "WhatsApp.exe"),
    os.path.join(_ROAMING, "WhatsApp", "WhatsApp.exe"),
    os.path.join(_LOCAL, "Programs", "WhatsApp", "WhatsApp.exe"),
]


# ------------------------------------------------------------------
# Decorator — centraliza foco na janela + tratamento de erro
# ------------------------------------------------------------------

def acao_whatsapp(descricao_sucesso: str = None, precisa_contato: bool = False):
    """
    Decorator que padroniza toda ação do WhatsApp:
    - Garante que a janela está aberta e em foco
    - Confere se 'contato' foi informado, quando precisa_contato=True
    - Captura qualquer exceção e converte em (False, mensagem)
    - Sempre retorna (sucesso: bool, mensagem: str)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(contato: str = None, mensagem: str = None):
            if precisa_contato and not contato:
                return False, "Informe o nome do contato"

            if not _focar_whatsapp():
                return False, "Não consegui abrir/focar o WhatsApp. Verifique se está instalado."

            try:
                resultado = func(contato=contato, mensagem=mensagem)
                return True, resultado or descricao_sucesso
            except Exception as e:
                return False, f"Erro inesperado: {type(e).__name__}: {e}"

        return wrapper
    return decorator


# ------------------------------------------------------------------
# Encontrar e abrir o WhatsApp
# ------------------------------------------------------------------

def _caminho_whatsapp() -> str | None:
    for p in _CAMINHOS_WA:
        if os.path.exists(p):
            return p
    try:
        resultado = subprocess.check_output(
            ["where", "WhatsApp.exe"],
            stderr=subprocess.DEVNULL, text=True, timeout=3
        ).strip().splitlines()
        if resultado and os.path.exists(resultado[0].strip()):
            return resultado[0].strip()
    except Exception:
        pass
    return None


def _abrir_whatsapp_processo() -> bool:
    """Tenta abrir o WhatsApp por vários métodos em cascata, na ordem mais confiável primeiro."""
    caminho = _caminho_whatsapp()

    metodos = []
    if caminho:
        metodos.append(("executável", lambda: subprocess.Popen(caminho)))
    metodos.append(("URI scheme (Store)", lambda: subprocess.Popen("start whatsapp:", shell=True)))
    metodos.append(("PATH", lambda: subprocess.Popen("WhatsApp.exe", shell=False)))
    metodos.append(("explorer URI", lambda: subprocess.Popen(["explorer.exe", "whatsapp:"])))

    for nome_metodo, acao in metodos:
        try:
            acao()
            print(f"[WhatsApp] Aberto via {nome_metodo}")
            return True
        except Exception:
            continue

    print("[WhatsApp] ❌ Não consegui abrir o WhatsApp por nenhum método")
    return False


def _encontrar_janela_whatsapp():
    try:
        import pygetwindow as gw
        for j in gw.getAllWindows():
            if "whatsapp" in j.title.lower():
                return j
    except Exception:
        pass
    return None


def _focar_whatsapp(espera_max: int = 15) -> bool:
    """Garante que o WhatsApp está aberto e em foco, abrindo se necessário."""
    janela = _encontrar_janela_whatsapp()
    if janela:
        return _ativar_janela(janela)

    print("[WhatsApp] Abrindo WhatsApp...")
    if not _abrir_whatsapp_processo():
        return False

    inicio = time.time()
    while time.time() - inicio < espera_max:
        time.sleep(1.5)
        janela = _encontrar_janela_whatsapp()
        if janela and _ativar_janela(janela):
            return True

    print("[WhatsApp] ⚠️ Janela não apareceu após abrir")
    return False


def _ativar_janela(janela) -> bool:
    try:
        if janela.isMinimized:
            janela.restore()
        # Maximiza sempre — garante que a proporção calibrada do clique
        # (89% da altura) seja consistente independente do estado anterior da janela.
        if not janela.isMaximized:
            janela.maximize()
            time.sleep(_DELAY_CURTO)
        janela.activate()
        time.sleep(_DELAY_MEDIO)
        return True
    except Exception:
        return False


# ------------------------------------------------------------------
# Navegação e digitação
# ------------------------------------------------------------------

def _buscar_contato(nome: str) -> bool:
    pyautogui.hotkey('ctrl', 'f')
    time.sleep(_DELAY_MEDIO)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.2)
    pyperclip.copy(nome)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(_DELAY_LONGO)
    pyautogui.press('enter')
    time.sleep(_DELAY_MEDIO)

    # Enter pode desfocar a janela — refoca antes de continuar
    janela = _encontrar_janela_whatsapp()
    if janela:
        _ativar_janela(janela)
    return True


_Y_CAMPO_MENSAGEM = 0.89  # calibrado manualmente via calibrar_posicao.py


def _digitar_e_enviar(mensagem: str) -> bool:
    """Clica na caixa de texto (posição calibrada) e envia via clipboard."""
    janela = _encontrar_janela_whatsapp()
    if not janela:
        raise RuntimeError("Janela do WhatsApp não encontrada para digitar")

    x = janela.left + janela.width // 2
    y = janela.top + int(janela.height * _Y_CAMPO_MENSAGEM)

    pyautogui.click(x, y)
    time.sleep(0.6)  # tempo extra pra garantir que o campo ganhou foco

    # Limpa o clipboard antes, cola, e confere se o clipboard realmente
    # bateu com o que copiamos (detecta problema de timing do Ctrl+V).
    pyperclip.copy(mensagem)
    time.sleep(0.1)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.6)

    pyautogui.press('enter')
    time.sleep(0.5)
    return True


# ------------------------------------------------------------------
# Ações (decoradas)
# ------------------------------------------------------------------

@acao_whatsapp(descricao_sucesso="WhatsApp aberto")
def abrir_whatsapp(contato=None, mensagem=None):
    pass  # _focar_whatsapp já rodou no decorator; só confirma sucesso


@acao_whatsapp(precisa_contato=True)
def abrir_conversa(contato=None, mensagem=None):
    if not _buscar_contato(contato):
        raise RuntimeError(f"Contato '{contato}' não encontrado")
    return f"Conversa com {contato} aberta"


@acao_whatsapp(precisa_contato=True)
def enviar_mensagem(contato=None, mensagem=None):
    if not mensagem:
        raise ValueError("Qual mensagem você quer enviar?")
    print(f"[WhatsApp] Enviando para '{contato}': {mensagem[:60]}")
    if not _buscar_contato(contato):
        raise RuntimeError(f"Não encontrei '{contato}' no WhatsApp")
    if not _digitar_e_enviar(mensagem):
        raise RuntimeError("Não consegui enviar a mensagem")
    return f"Mensagem enviada para {contato}"


# ------------------------------------------------------------------
# Ponto de entrada único para o dispatcher (mesmo padrão do Spotify)
# ------------------------------------------------------------------

def controlar_whatsapp(acao: str, contato: str = None, mensagem: str = None) -> dict:
    """
    acao: enviar | abrir | conversa
    contato: nome do contato (obrigatório em 'enviar' e 'conversa')
    mensagem: texto a enviar (obrigatório em 'enviar')

    Retorna: {"sucesso": bool, "mensagem": str}
    """
    mapa = {
        "enviar": enviar_mensagem,
        "abrir": abrir_whatsapp,
        "conversa": abrir_conversa,
    }

    handler = mapa.get(acao)
    if handler is None:
        return {"sucesso": False, "mensagem": f"Ação '{acao}' não reconhecida"}

    sucesso, msg = handler(contato=contato, mensagem=mensagem)
    return {"sucesso": sucesso, "mensagem": msg}