import gc
from core.brain import pensar
from tools.voice_input import ouvir_microfone
from tools.voice_output import falar

MODO_VOZ = True  # True = tenta usar o microfone; cai pro teclado se não conseguir


def obter_entrada() -> str:
    if MODO_VOZ:
        texto = ouvir_microfone()
        if texto:
            return texto
        print("[Jarvis] Não consegui usar o microfone agora — digite sua mensagem:")

    return input("Você: ")


def main():
    print("=== Jarvis v2 (voz + texto) ===")
    print("Fale ou digite 'sair' para encerrar.\n")

    # Guarda o que você já começou a falar quando interrompe o Jarvis no meio
    # da fala — assim a próxima volta do loop usa isso direto, sem perguntar
    # de novo nem passar pelos prints normais de "aguardando microfone".
    entrada_pendente = None

    while True:
        texto = entrada_pendente if entrada_pendente else obter_entrada()
        entrada_pendente = None

        if not texto:
            continue
        if texto.strip().lower() == "sair":
            falar("Até logo!", permitir_interrupcao=False)
            break

        resposta = pensar(texto)
        if resposta:
            foi_interrompido = falar(resposta)
            if foi_interrompido:
                # Você começou a falar por cima — escuta agora o que você
                # disse e processa na próxima volta do loop.
                entrada_pendente = ouvir_microfone()

    gc.collect()  # limpeza final explícita, antes do interpretador encerrar


if __name__ == "__main__":
    main()