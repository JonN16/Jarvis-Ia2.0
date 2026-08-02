# Ideia futura: trocar o WhatsApp do Jarvis pra WAHA

## Por que
Hoje o `whatsapp_service.py` usa `pyautogui` (clique simulado, coordenada
calibrada na tela) pra abrir conversa e enviar mensagem no WhatsApp Desktop.
Isso tem dois problemas que eu queria resolver:

1. **Rouba o foco da tela** — abre/maximiza a janela do WhatsApp e clica nela,
   interrompendo o que eu estou fazendo no PC.
2. **Só envia, nunca recebe** — não tem como o Jarvis saber que chegou uma
   mensagem nova, porque ele não "escuta" o WhatsApp, só simula cliques.

A troca é pro **WAHA** (WhatsApp HTTP API, open-source, grátis, roda em
Docker local). Ele conecta com meu WhatsApp como um "dispositivo vinculado"
(igual WhatsApp Web) e vira uma API HTTP de verdade — sem clique, sem
depender de coordenada de tela, e com **webhook** pra avisar quando chega
mensagem nova.

## O que decidi (na conversa com o Claude)
- Quero manter simples por enquanto: o Jarvis só verifica mensagens **quando
  eu perguntar** ("tenho mensagem nova?") — não fala sozinho quando chega.
- Não tenho Docker instalado ainda — é pré-requisito.

## Importante sobre "perder o WhatsApp"
Não perde nada. O WAHA funciona exatamente como o WhatsApp Web: escaneia um
QR Code, vira mais um "dispositivo vinculado" na lista do celular
(Configurações → Dispositivos conectados), e dá pra desconectar a qualquer
momento pelo celular. Não cria conta nova, não migra número.

**Risco real:** usar WhatsApp automatizado fora da API oficial paga da Meta
tecnicamente viola os termos de uso. Pra uso pessoal e baixo volume o risco
de ban é baixo, mas existe — vale ter em mente antes de decidir seguir.

## Arquitetura da solução
- `tools/whatsapp_service.py` (reescrito): chama a API do WAHA via `requests`
  pra **enviar** mensagens (`POST /api/sendText`) e resolver contato → chat_id.
- `tools/whatsapp_inbox.py` (novo): sobe um servidor HTTP leve (FastAPI +
  uvicorn) numa thread em segundo plano, dentro do mesmo processo do Jarvis.
  O WAHA chama esse servidor (`/webhook`) toda vez que chega mensagem nova; o
  servidor guarda em memória até eu perguntar, aí `verificar_mensagens()`
  devolve o que chegou e limpa a fila.
- `main.py`: chama `iniciar_servidor_webhook()` uma vez, no começo, antes do
  loop principal.
- `controlar_whatsapp(acao, contato, mensagem)`: ação passa a ser só
  `enviar | verificar` (antes era `enviar | abrir | conversa`, que só fazia
  sentido pro jeito antigo via UI).

## Passo a passo pra retomar
1. Instalar Docker Desktop (https://www.docker.com/products/docker-desktop/).
2. Subir o WAHA já com o webhook configurado:
   ```powershell
   docker run -it -p 3000:3000 --name waha ^
     -e WHATSAPP_HOOK_URL=http://host.docker.internal:5001/webhook ^
     -e WHATSAPP_HOOK_EVENTS=message ^
     devlikeapro/waha
   ```
   (repara em `host.docker.internal`, não `localhost` — é assim que o
   container consegue chamar de volta o Python rodando fora do Docker.)
3. Abrir `http://localhost:3000/dashboard`, iniciar a sessão `default` e
   escanear o QR Code com o WhatsApp do celular.
4. `pip install fastapi uvicorn` no venv do projeto.
5. Substituir `tools/whatsapp_service.py` e adicionar `tools/whatsapp_inbox.py`
   pelos arquivos que o Claude já deixou prontos naquela conversa (pedir pra
   gerar de novo se precisar).
6. Atualizar `tools/registry.py`: o schema da ferramenta `controlar_whatsapp`
   precisa que o campo `acao` aceite `enviar` e `verificar` (tirando `abrir`
   e `conversa`, que não existem mais nessa versão).
7. Testar: pedir pro Jarvis mandar uma mensagem de teste, mandar uma mensagem
   pro próprio número de outro chip/WhatsApp Web, e perguntar "tenho mensagem
   nova?" pro Jarvis.

## Se no futuro eu quiser evoluir
- Fazer o Jarvis avisar sozinho, na hora, quando chega mensagem (em vez de só
  responder quando eu pergunto) — trocar a "verificação sob demanda" por uma
  notificação automática via `falar()` direto dentro do webhook.
- Guardar as mensagens em disco (SQLite) em vez de só em memória, pra não
  perder o histórico se o Jarvis reiniciar.
- Adicionar suporte a responder mensagens específicas por contato, não só ver
  a lista geral.
