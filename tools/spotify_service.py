"""
Spotify Service - Integração com Spotify via Spotipy.
Controle de reprodução: play, pause, next/previous, volume, fila,
playlists e músicas curtidas — com wake-up automático de dispositivo
e fallback para teclas de mídia em contas Free ou sessões inativas.
"""

import os
import re
import time
import random
import functools
import unicodedata
import importlib
from difflib import SequenceMatcher
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

# Busca na internet é opcional — se o pacote não estiver instalado, o Jarvis
# simplesmente pula essa etapa (pip install ddgs).
try:
    from ddgs import DDGS
except ImportError:
    DDGS = None

CACHE_PATH = ".spotify_cache"

# Abaixo disso, o resultado do Spotify é considerado "não é bem o que o
# usuário pediu" — dispara a busca na internet pelo nome real da música.
LIMIAR_CONFIANCA = 0.45

SCOPE = (
    "streaming user-read-email user-read-private "
    "user-read-playback-state user-modify-playback-state user-read-currently-playing "
    "user-library-read user-top-read "
    "playlist-read-private playlist-modify-public playlist-modify-private"
)


def _abrir_app(nome: str):
    """
    Import tardio e best-effort — não quebra o serviço se não existir.
    Usa importlib (import dinâmico) em vez de 'from services.app_finder import
    abrir_app' pra não disparar reportMissingImports no Pylance quando esse
    módulo opcional não existir no projeto.
    """
    try:
        modulo = importlib.import_module("services.app_finder")
        modulo.abrir_app(nome)
    except Exception:
        pass


def acao_spotify(descricao_sucesso: str = None, precisa_dispositivo: bool = False):
    """
    Decorator que padroniza toda ação do Spotify:
    - Confere se está conectado
    - Garante dispositivo ativo, se precisa_dispositivo=True
    - Trata SpotifyException por status HTTP com fallback de tecla de mídia
    - Sempre retorna (sucesso: bool, mensagem: str)

    Elimina o try/except repetido que existia em cada método.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if not self.sp:
                return False, "Spotify não conectado. Configure as credenciais no .env."

            device_id = None
            if precisa_dispositivo:
                device_id = self._garantir_dispositivo()
                if device_id is None:
                    return False, (
                        "Não encontrei nenhum dispositivo Spotify. "
                        "Abra o Spotify em algum lugar e tente de novo."
                    )

            try:
                resultado = func(self, *args, device_id=device_id, **kwargs)
                return True, resultado or descricao_sucesso

            except spotipy.SpotifyException as e:
                if e.http_status == 401:
                    return False, "Token do Spotify expirado. Reautentique o aplicativo."
                if e.http_status in (403, 404):
                    # 403 = restrição de conta/dispositivo (comum em Free);
                    # 404 = sessão sumiu no meio do caminho.
                    # Nos dois casos, tenta a tecla de mídia como plano B
                    # antes de desistir de vez.
                    tecla = TECLA_FALLBACK.get(func.__name__)
                    if tecla:
                        return self._fallback_media_key(tecla, descricao_sucesso)
                    if e.http_status == 403:
                        return False, "Permissão negada — provavelmente exige Spotify Premium."
                    return False, "Sessão do Spotify inativa. Abra o app e comece a tocar algo manualmente."
                return False, f"Erro do Spotify ({e.http_status}): {e.msg}"

            except Exception as e:
                return False, f"Erro inesperado: {type(e).__name__}: {e}"

        return wrapper
    return decorator


def _normalizar(texto: str) -> str:
    """Minúsculas e sem acento, só pra comparar — não afeta o que é exibido/tocado."""
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def _similaridade(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalizar(a), _normalizar(b)).ratio()


# Sufixos comuns em títulos de busca/YouTube que atrapalham a extração do
# nome real da música (ex: "Fulano - Musica X (Official Video) - YouTube")
_SUFIXOS_RUIDO = re.compile(
    r"\s*[\|\-–]?\s*(official\s*(video|audio|music\s*video)?|lyrics?|letra"
    r"(\s*e\s*m[uú]sica)?|clipe\s*oficial|v[ií]deo\s*oficial|ouça|youtube"
    r"|hq|hd|4k)\s*.*$",
    re.IGNORECASE,
)


def _extrair_musica_do_titulo(titulo: str) -> str:
    """Tenta limpar um título de resultado de busca pra virar uma boa query de Spotify."""
    limpo = _SUFIXOS_RUIDO.sub("", titulo).strip(" -–|\"'")
    return limpo


def _buscar_nome_real_na_internet(query: str) -> str:
    """
    Pesquisa na internet pra descobrir o nome/artista real de uma música que
    o Spotify não achou com confiança (ex: usuário pediu de forma incompleta,
    apelido, trecho da letra, etc). Retorna uma query melhorada pro Spotify,
    ou None se não achar nada ou o pacote de busca não estiver instalado.
    """
    if DDGS is None:
        return None

    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(f"{query} música nome artista", max_results=5))
    except Exception:
        return None

    for r in resultados:
        titulo = (r.get("title") or "").strip()
        candidato = _extrair_musica_do_titulo(titulo)
        if candidato and len(candidato) > 3 and _normalizar(candidato) != _normalizar(query):
            return candidato

    return None


# Mapeia nome do método -> tecla de mídia usada como fallback quando a API falha
# (nomes no vocabulário da lib 'keyboard')
TECLA_FALLBACK = {
    "pause": "play/pause media",
    "resume": "play/pause media",
    "next_track": "next track",
    "previous_track": "previous track",
}


class SpotifyService:
    """Controle do Spotify via Web API."""

    def __init__(self):
        self.sp = None
        # Guarda as últimas músicas tocadas (uri, nome, artista) — permite
        # voltar com certeza pra uma delas quando o usuário disser algo como
        # "toca de novo a anterior", sem precisar pesquisar (e errar) de novo.
        self.historico_reproducao = []
        self._connect()

    def _registrar_reproducao(self, track: dict):
        entrada = {
            "uri": track["uri"],
            "nome": track["name"],
            "artista": track["artists"][0]["name"],
        }
        self.historico_reproducao.append(entrada)
        self.historico_reproducao = self.historico_reproducao[-10:]

    def _connect(self):
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")

        if not client_id or not client_secret:
            print("[Spotify] ⚠️  Credenciais ausentes no .env (SPOTIFY_CLIENT_ID/SECRET).")
            return

        try:
            self.sp = spotipy.Spotify(
                auth_manager=SpotifyOAuth(
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri=redirect_uri,
                    scope=SCOPE,
                    cache_path=CACHE_PATH,
                    open_browser=True,
                )
            )
            self.sp.current_user()
            print("[Spotify] ✅ Conectado.")
        except Exception as e:
            print(f"[Spotify] ❌ Erro ao conectar: {e}")
            self.sp = None

    # ------------------------------------------------------------------
    # Dispositivo
    # ------------------------------------------------------------------

    def _listar_dispositivos(self):
        try:
            return self.sp.devices().get("devices", [])
        except Exception:
            return []

    def _garantir_dispositivo(self, tentativas: int = 2):
        """
        Acha um dispositivo ativo; se não achar, abre o Spotify e tenta
        de novo, com fallback de tecla de mídia como último recurso.
        """
        dispositivos = self._listar_dispositivos()

        if not dispositivos and tentativas > 0:
            _abrir_app("spotify")
            time.sleep(3)
            return self._garantir_dispositivo(tentativas=tentativas - 1)

        if not dispositivos:
            return None

        device_id = next((d["id"] for d in dispositivos if d.get("is_active")), dispositivos[0]["id"])

        try:
            self.sp.transfer_playback(device_id=device_id, force_play=False)
            time.sleep(1)
        except Exception:
            pass  # já pode estar ativo; segue o jogo

        return device_id

    def _fallback_media_key(self, tecla: str, mensagem_sucesso: str):
        try:
            import keyboard
            keyboard.send(tecla)
            return True, mensagem_sucesso
        except Exception as e:
            return False, f"Fallback de tecla falhou: {e}"

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------

    def _pesquisar_e_rankear(self, query, limiar):
        """
        Busca até 10 candidatos no Spotify e escolhe o que tem o texto
        (música + artista) mais parecido com a query — em vez de simplesmente
        pegar o primeiro resultado, que nem sempre é o certo.
        """
        resultados = self.sp.search(q=query, type="track", limit=10)
        items = resultados["tracks"]["items"]
        if not items:
            return None

        def pontuar(track):
            texto = f"{track['name']} {track['artists'][0]['name']}"
            return _similaridade(query, texto)

        melhor = max(items, key=pontuar)
        return melhor if pontuar(melhor) >= limiar else None

    def _buscar_melhor_musica(self, query):
        """
        Primeiro tenta achar a música no Spotify com confiança razoável. Se
        não achar nada parecido o suficiente, pesquisa na internet o nome
        real da música e tenta de novo no Spotify com esse nome melhorado.
        """
        track = self._pesquisar_e_rankear(query, LIMIAR_CONFIANCA)
        if track:
            return track

        nome_real = _buscar_nome_real_na_internet(query)
        if nome_real:
            # Já veio da internet — aceita o melhor resultado do Spotify pra essa query,
            # mesmo com confiança menor, já que o nome em si já foi validado fora do Spotify.
            track = self._pesquisar_e_rankear(nome_real, limiar=0.2)
            if track:
                return track

        # Última tentativa: melhor resultado bruto do Spotify, sem exigir confiança.
        return self._pesquisar_e_rankear(query, limiar=0.0)

    @acao_spotify(precisa_dispositivo=True)
    def play_music(self, query, device_id=None):
        track = self._buscar_melhor_musica(query)
        if not track:
            raise ValueError(f"Nenhuma música encontrada para '{query}'")
        self.sp.start_playback(device_id=device_id, uris=[track["uri"]])
        self._registrar_reproducao(track)
        return f"Tocando '{track['name']}' de {track['artists'][0]['name']}"

    @acao_spotify(descricao_sucesso="Reprodução pausada")
    def pause(self, device_id=None):
        self.sp.pause_playback()

    @acao_spotify(descricao_sucesso="Reprodução retomada", precisa_dispositivo=True)
    def resume(self, device_id=None):
        self.sp.start_playback(device_id=device_id)

    @acao_spotify(descricao_sucesso="Próxima música")
    def next_track(self, device_id=None):
        self.sp.next_track()

    @acao_spotify(descricao_sucesso="Música anterior")
    def previous_track(self, device_id=None):
        self.sp.previous_track()

    @acao_spotify()
    def set_volume(self, volume_percent, device_id=None):
        volume = max(0, min(100, int(volume_percent)))
        self.sp.volume(volume)
        return f"Volume definido para {volume}%"

    @acao_spotify(precisa_dispositivo=True)
    def play_liked_songs(self, device_id=None):
        results = self.sp.current_user_saved_tracks(limit=50)
        items = results.get("items", [])
        if not items:
            raise ValueError("Nenhuma música curtida encontrada")
        uris = [item["track"]["uri"] for item in items if item.get("track")]
        random.shuffle(uris)
        self.sp.start_playback(device_id=device_id, uris=uris)
        return f"Tocando suas músicas curtidas ({len(uris)} músicas)"

    @acao_spotify(precisa_dispositivo=True)
    def play_playlist(self, nome, device_id=None):
        nome_lower = nome.lower()
        playlists = self.sp.current_user_playlists(limit=50).get("items", [])

        alvo = next((pl for pl in playlists if pl and nome_lower in pl["name"].lower()), None)

        if not alvo:
            resultados = self.sp.search(q=nome, type="playlist", limit=1)
            achados = resultados.get("playlists", {}).get("items", [])
            alvo = achados[0] if achados else None

        if not alvo:
            raise ValueError(f"Nenhuma playlist encontrada para '{nome}'")

        self.sp.start_playback(device_id=device_id, context_uri=alvo["uri"])
        return f"Tocando playlist '{alvo['name']}'"

    @acao_spotify(precisa_dispositivo=True)
    def tocar_do_historico(self, posicoes_atras=1, device_id=None):
        """
        Toca de novo uma música já tocada antes nessa sessão.
        posicoes_atras=1 -> a música tocada logo ANTES da atual (mais comum:
        "não, era a de antes"). posicoes_atras=2 -> duas antes, etc.
        """
        indice = -(posicoes_atras + 1)
        if len(self.historico_reproducao) < abs(indice):
            raise ValueError("Não tenho no histórico dessa sessão uma música tão antiga assim")
        alvo = self.historico_reproducao[indice]
        self.sp.start_playback(device_id=device_id, uris=[alvo["uri"]])
        self._registrar_reproducao({
            "uri": alvo["uri"],
            "name": alvo["nome"],
            "artists": [{"name": alvo["artista"]}],
        })
        return f"Tocando de novo '{alvo['nome']}' de {alvo['artista']}"

    @acao_spotify()
    def add_to_queue(self, query, device_id=None):
        track = self._buscar_melhor_musica(query)
        if not track:
            raise ValueError(f"Nenhuma música encontrada para '{query}'")
        self.sp.add_to_queue(track["uri"])
        return f"'{track['name']}' adicionada à fila"

    @acao_spotify()
    def get_current_track(self, device_id=None):
        current = self.sp.currently_playing()
        if not current or not current.get("item"):
            raise ValueError("Nenhuma música tocando no momento")
        track = current["item"]
        return f"Tocando agora: {track['name']} de {track['artists'][0]['name']}"


# ------------------------------------------------------------------
# Singleton e ponto de entrada único para o dispatcher
# ------------------------------------------------------------------

_spotify_service = None


def get_spotify_service() -> SpotifyService:
    global _spotify_service
    if _spotify_service is None:
        _spotify_service = SpotifyService()
    return _spotify_service


def controlar_spotify(acao: str, parametro=None) -> dict:
    """
    Ponto de entrada único chamado pelo dispatcher do LLM.

    acao: play | pause | resume | next | previous | volume | playlist | liked | queue | current | repetir
    parametro: nome da música/playlist, volume 0-100, ou (pra 'repetir') quantas
    posições atrás no histórico da sessão tocar de novo (default 1).

    Retorna: {"sucesso": bool, "mensagem": str}
    """
    service = get_spotify_service()

    if not service.sp:
        return {"sucesso": False, "mensagem": "Spotify não conectado. Configure as credenciais no .env."}

    mapa = {
        "play":     lambda: service.play_music(parametro) if parametro else service.resume(),
        "pause":    service.pause,
        "resume":   service.resume,
        "next":     service.next_track,
        "previous": service.previous_track,
        "volume":   lambda: service.set_volume(parametro) if parametro is not None else (False, "Informe o volume (0-100)"),
        "playlist": lambda: service.play_playlist(parametro) if parametro else (False, "Informe o nome da playlist"),
        "liked":    service.play_liked_songs,
        "queue":    lambda: service.add_to_queue(parametro) if parametro else (False, "Informe o nome da música"),
        "current":  service.get_current_track,
        # Toca de novo, com certeza, uma música já tocada nessa sessão — em vez
        # de pesquisar por nome de novo (o que pode errar). parametro = quantas
        # posições atrás (1 = a música tocada logo antes da atual; default 1).
        "repetir":  lambda: service.tocar_do_historico(int(parametro) if parametro else 1),
    }

    handler = mapa.get(acao)
    if handler is None:
        return {"sucesso": False, "mensagem": f"Ação '{acao}' não reconhecida"}

    sucesso, mensagem = handler()
    return {"sucesso": sucesso, "mensagem": mensagem}