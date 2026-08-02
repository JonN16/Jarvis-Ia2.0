"""
Screenshot Tool - Tira print da tela usando 'mss'.
Não depende do Pillow/pyscreeze (que o pyautogui.screenshot() usa por baixo
e que costuma ter problemas de compatibilidade em versões novas do Python).
"""

import os
import time
import mss
import mss.tools

PASTA_SCREENSHOTS = os.path.join(os.path.expanduser("~"), "Pictures", "Jarvis Screenshots")


def tirar_screenshot(args: dict = None) -> str:
    try:
        os.makedirs(PASTA_SCREENSHOTS, exist_ok=True)

        nome_arquivo = f"print_{time.strftime('%Y%m%d_%H%M%S')}.png"
        caminho = os.path.join(PASTA_SCREENSHOTS, nome_arquivo)

        with mss.mss() as sct:
            monitor_principal = sct.monitors[1]  # [0] = todos os monitores combinados
            captura = sct.grab(monitor_principal)
            mss.tools.to_png(captura.rgb, captura.size, output=caminho)

        return f"Print salvo: {nome_arquivo}"
    except Exception as e:
        return f"Não consegui tirar o print: {e}"