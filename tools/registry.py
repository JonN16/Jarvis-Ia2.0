TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "abrir_app",
            "description": "Abre um programa no computador pelo nome (ex: chrome, spotify, calculadora, bloco de notas)",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome do aplicativo a abrir"}
                },
                "required": ["nome"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "conversar",
            "description": "Usado quando o usuário só quer bater papo, perguntar algo, ou pedir opinião — não é um comando de ação",
            "parameters": {
                "type": "object",
                "properties": {
                    "resposta": {"type": "string", "description": "A resposta em texto para o usuário"}
                },
                "required": ["resposta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "hora_atual",
            "description": "Retorna a hora atual do sistema. Use sempre que perguntarem que horas são.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "controlar_volume",
            "description": "Aumenta, diminui, muta ou desmuta o volume do sistema",
            "parameters": {
                "type": "object",
                "properties": {
                    "acao": {
                        "type": "string",
                        "enum": ["aumentar", "diminuir", "mutar", "desmutar"]
                    }
                },
                "required": ["acao"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "controlar_spotify",
            "description": (
                "Controla o Spotify. Use para tocar música/playlist/curtidas, "
                "pausar, retomar, pular faixa, voltar faixa, ajustar volume, "
                "adicionar à fila ou ver a música atual."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "acao": {
                        "type": "string",
                        "enum": ["play", "pause", "resume", "next", "previous",
                                 "volume", "playlist", "liked", "queue", "current"],
                        "description": "A ação a executar no Spotify"
                    },
                    "parametro": {
                        "type": "string",
                        "description": (
                            "Depende da ação: nome da música (play/queue), "
                            "nome da playlist (playlist), número 0-100 (volume). "
                            "Deixe vazio para pause/resume/next/previous/liked/current."
                        )
                    }
                },
                "required": ["acao"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "controlar_whatsapp",
            "description": (
                "Controla o WhatsApp Desktop. Use para enviar mensagem para um contato, "
                "abrir a conversa com um contato, ou apenas abrir o WhatsApp."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "acao": {
                        "type": "string",
                        "enum": ["enviar", "abrir", "conversa"],
                        "description": "A ação a executar no WhatsApp"
                    },
                    "contato": {
                        "type": "string",
                        "description": "Nome do contato, obrigatório para 'enviar' e 'conversa'"
                    },
                    "mensagem": {
                        "type": "string",
                        "description": "Texto da mensagem, obrigatório para 'enviar'"
                    }
                },
                "required": ["acao"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "controlar_memoria",
            "description": (
                "Memória de longo prazo (vault Obsidian). 'salvar' guarda um fato "
                "pessoal do usuário. 'buscar' procura algo que ele mencionou antes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "acao": {
                        "type": "string",
                        "enum": ["salvar", "buscar"]
                    },
                    "texto": {
                        "type": "string",
                        "description": "O que salvar, ou o que buscar"
                    },
                    "categoria": {
                        "type": "string",
                        "enum": ["perfil", "geral"],
                        "description": "Só em 'salvar'. perfil=fato estável, geral=evento do dia. Padrão: geral."
                    }
                },
                "required": ["acao", "texto"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tirar_screenshot",
            "description": "Tira um print/screenshot da tela atual e salva no computador",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_arquivo",
            "description": (
                "Busca arquivos no PC. Se o usuário só disse a pasta sem nome "
                "específico (ex: 'algum arquivo em downloads'), deixe 'nome' vazio "
                "e use 'pasta' — isso lista os mais recentes dessa pasta. "
                "Abre automaticamente se achar só 1 resultado."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {
                        "type": "string",
                        "description": "Nome ou parte do nome do arquivo. Deixe vazio se o usuário não especificou um nome."
                    },
                    "pasta": {
                        "type": "string",
                        "enum": ["desktop", "documentos", "downloads", "prints", "todas"],
                        "description": "Pasta onde buscar. 'prints' = screenshots tirados pelo Jarvis. Padrão: todas."
                    }
                },
                "required": []
            }
        }
    }
]