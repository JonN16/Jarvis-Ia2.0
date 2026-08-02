"""
Voice Input - Captura e transcreve fala do microfone via Google Speech
Recognition (gratuito, requer internet).

Grava com DETECÇÃO DE SILÊNCIO em vez de duração fixa: calibra o ruído
ambiente por ~0.4s, depois grava até você ficar ~1.2s em silêncio (ou até
o limite máximo de segurança). Assim a gravação para sozinha quando você
termina de falar, sem esperar um tempo fixo desnecessário.
"""

import queue
import threading
import numpy as np
import sounddevice as sd
import speech_recognition as sr

_SAMPLE_RATE = 16000
_TAMANHO_BLOCO = int(_SAMPLE_RATE * 0.05)  # blocos de 50ms

_DURACAO_CALIBRACAO = 0.4      # segundos medindo o ruído ambiente
_SILENCIO_PARA_PARAR = 1.2     # segundos de silêncio contínuo pra parar
_DURACAO_MINIMA = 0.5          # nunca para antes disso, mesmo em silêncio
_DURACAO_MAXIMA = 15           # trava de segurança

_MARGEM_RUIDO = 2.5   # o quanto acima do ruído ambiente já conta como "fala"
_PISO_MINIMO = 150    # nunca deixa o limiar cair abaixo disso (evita falso positivo)

# Limiar usado só pra detectar INTERRUPÇÃO enquanto o Jarvis está falando.
# É fixo (não calibra ambiente) porque precisa reagir rápido no meio da fala
# do Jarvis — calibrar custaria tempo de reação e o próprio áudio do TTS
# tocando no ambiente atrapalharia a calibração.
_LIMIAR_INTERRUPCAO = 700

_reconhecedor = sr.Recognizer()


def _rms(bloco: np.ndarray) -> float:
    return float(np.sqrt(np.mean(bloco.astype(np.float64) ** 2)))


def _calibrar_ruido_ambiente(fila: queue.Queue) -> float:
    """Mede o volume médio do ambiente antes de começar a detectar fala."""
    amostras = []
    n_blocos = int(_DURACAO_CALIBRACAO / 0.05)
    for _ in range(n_blocos):
        amostras.append(_rms(fila.get()))
    media = sum(amostras) / len(amostras) if amostras else 0
    return max(media * _MARGEM_RUIDO, _PISO_MINIMO)


def _gravar_com_deteccao_silencio() -> bytes:
    fila = queue.Queue()

    def callback(indata, frames, time_info, status):
        fila.put(indata.copy())

    with sd.InputStream(
        samplerate=_SAMPLE_RATE, channels=1, dtype="int16",
        blocksize=_TAMANHO_BLOCO, callback=callback
    ):
        limiar = _calibrar_ruido_ambiente(fila)

        blocos = []
        tempo_total = 0.0
        silencio_acumulado = 0.0
        ja_falou = False

        while tempo_total < _DURACAO_MAXIMA:
            bloco = fila.get()
            blocos.append(bloco)
            tempo_total += 0.05

            volume = _rms(bloco)

            if volume > limiar:
                ja_falou = True
                silencio_acumulado = 0.0
            else:
                silencio_acumulado += 0.05

            parar_por_silencio = (
                ja_falou
                and silencio_acumulado >= _SILENCIO_PARA_PARAR
                and tempo_total >= _DURACAO_MINIMA
            )
            if parar_por_silencio:
                break

    if not blocos:
        return b""

    audio = np.concatenate(blocos, axis=0)
    return audio.tobytes()


def ouvir_microfone() -> str | None:
    try:
        print("[Jarvis] 🎤 Ouvindo... (fale, eu paro sozinho quando você terminar)")
        pcm_bytes = _gravar_com_deteccao_silencio()

        if not pcm_bytes:
            print("[Jarvis] Não ouvi nada.")
            return None

        audio_data = sr.AudioData(pcm_bytes, _SAMPLE_RATE, 2)

        print("[Jarvis] Processando fala...")
        texto = _reconhecedor.recognize_google(audio_data, language="pt-BR")
        print(f"[Você disse] {texto}")
        return texto

    except sr.UnknownValueError:
        print("[Jarvis] Não consegui entender o que você disse.")
        return None
    except sr.RequestError as e:
        print(f"[Jarvis] ⚠️ Sem internet ou serviço de voz indisponível: {e}")
        return None
    except sd.PortAudioError as e:
        print(f"[Jarvis] ⚠️ Microfone não encontrado/disponível: {e}")
        return None
    except Exception as e:
        print(f"[Jarvis] Erro inesperado no microfone: {e}")
        return None


def monitorar_interrupcao(
    evento_interrompido: threading.Event,
    evento_parar: threading.Event,
    limiar: float = _LIMIAR_INTERRUPCAO,
):
    """
    Escuta o microfone em paralelo ENQUANTO o Jarvis está falando (usado pelo
    voice_output.py pra permitir "falar por cima" e interromper).

    - Se detectar volume acima do limiar, marca `evento_interrompido` e para.
    - Para sozinho, sem marcar nada, quando `evento_parar` é ativado (ou seja,
      a fala do Jarvis terminou normalmente, sem interrupção).

    Roda num stream de microfone próprio e separado do usado em
    ouvir_microfone() — os dois nunca ficam abertos ao mesmo tempo na prática,
    já que um só começa depois que o outro fecha.
    """
    try:
        with sd.InputStream(
            samplerate=_SAMPLE_RATE, channels=1, dtype="int16",
            blocksize=_TAMANHO_BLOCO
        ) as stream:
            while not evento_parar.is_set():
                bloco, _overflow = stream.read(_TAMANHO_BLOCO)
                if _rms(bloco) > limiar:
                    evento_interrompido.set()
                    return
    except Exception:
        # Best-effort: se o microfone não puder ser aberto (ex: já em uso),
        # simplesmente não há interrupção por voz nessa fala — sem quebrar nada.
        return