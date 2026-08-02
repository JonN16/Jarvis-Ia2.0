import subprocess
import gc
from datetime import datetime
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

APPS_CONHECIDOS = {
    "chrome": "chrome",
    "spotify": "spotify",
    "calculadora": "calc",
    "bloco de notas": "notepad",
}


def abrir_app(args: dict) -> str:
    nome = args["nome"].lower()
    comando = APPS_CONHECIDOS.get(nome)

    if not comando:
        return f"Ainda não sei abrir '{nome}' — preciso que você me diga o comando certo pra ele."

    try:
        subprocess.Popen(
            comando,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return f"Abrindo {nome}..."
    except Exception as e:
        return f"Não consegui abrir {nome}: {e}"


def hora_atual(args: dict = None) -> str:
    agora = datetime.now().strftime("%H:%M")
    return f"Agora são {agora}."


def _volume_interface():
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


def controlar_volume(args: dict) -> str:
    acao = args.get("acao")
    vol = _volume_interface()

    try:
        if acao == "mutar":
            vol.SetMute(1, None)
            return "Volume mutado."
        elif acao == "desmutar":
            vol.SetMute(0, None)
            return "Volume ativado."
        elif acao == "aumentar":
            atual = vol.GetMasterVolumeLevelScalar()
            novo = min(1.0, atual + 0.1)
            vol.SetMasterVolumeLevelScalar(novo, None)
            return f"Volume em {int(novo * 100)}%"
        elif acao == "diminuir":
            atual = vol.GetMasterVolumeLevelScalar()
            novo = max(0.0, atual - 0.1)
            vol.SetMasterVolumeLevelScalar(novo, None)
            return f"Volume em {int(novo * 100)}%"
        else:
            return f"Não entendi a ação de volume '{acao}'."
    finally:
        # Libera o objeto COM AGORA, em vez de deixar acumular até o
        # shutdown do programa — evita o access violation no encerramento.
        del vol
        gc.collect()