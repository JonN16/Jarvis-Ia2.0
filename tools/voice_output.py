"""
Voice Output - Fala respostas usando vozes neurais gratuitas da Microsoft
(edge-tts, o mesmo motor do "Ler em voz alta" do Edge). Muito mais natural
que a voz SAPI5 padrão do Windows. Requer internet.

Suporta INTERRUPÇÃO (barge-in): enquanto fala, escuta o microfone numa
thread separada (mesmo processo — sem precisar de servidor). Se você
começar a falar por cima, a reprodução para na hora em vez de terminar a
frase inteira.
"""

import asyncio
import os
import tempfile
import threading
import time
import edge_tts
from playsound3 import playsound

from tools.voice_input import monitorar_interrupcao

# Escolhida após teste real com testar_vozes.py — voz "Multilingual",
# geração mais recente e natural que as vozes clássicas do edge-tts.
VOZ = "pt-BR-ThalitaMultilingualNeural"


async def _gerar_audio(texto: str, caminho: str):
    comunicador = edge_tts.Communicate(texto, VOZ)
    await comunicador.save(caminho)


def falar(texto: str, permitir_interrupcao: bool = True) -> bool:
    """
    Fala o texto em voz alta.

    permitir_interrupcao: se True (padrão), escuta o microfone em paralelo
    e para de falar assim que detectar que você começou a falar por cima.

    Retorna True se a fala foi interrompida por você ter falado por cima,
    False caso tenha terminado normalmente (ou dado erro). O chamador pode
    usar esse retorno pra pular direto pra escutar o comando, sem esperar
    mais nada.
    """
    if not texto or not texto.strip():
        return False

    caminho = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            caminho = f.name

        asyncio.run(_gerar_audio(texto, caminho))

        if not permitir_interrupcao:
            playsound(caminho)  # bloqueia até terminar de tocar
            return False

        evento_interrompido = threading.Event()
        evento_parar_monitor = threading.Event()

        som = playsound(caminho, block=False)

        thread_monitor = threading.Thread(
            target=monitorar_interrupcao,
            args=(evento_interrompido, evento_parar_monitor),
            daemon=True,
        )
        thread_monitor.start()

        # Espera a reprodução terminar OU ser interrompida — checagem leve,
        # não trava o processo (a thread de monitor roda em paralelo de verdade).
        while som.is_alive() and not evento_interrompido.is_set():
            time.sleep(0.05)

        if evento_interrompido.is_set():
            try:
                som.stop()
            except Exception:
                pass
            print("[Jarvis] (interrompido — ouvindo você agora)")

        evento_parar_monitor.set()  # avisa a thread de monitor pra parar de escutar
        thread_monitor.join(timeout=0.5)

        return evento_interrompido.is_set()

    except Exception as e:
        print(f"[Jarvis] ⚠️ Erro ao falar (verifique sua internet): {e}")
        return False

    finally:
        if caminho and os.path.exists(caminho):
            try:
                os.remove(caminho)
            except Exception:
                pass