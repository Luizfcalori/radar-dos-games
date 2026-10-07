# Radar Social Bot v1

Bot central para tratar comentários do Radar dos Games sem depender de API paga de IA.

## Política de resposta

- Elogios, agradecimentos, saudações e reações curtas podem receber resposta automática.
- Perguntas, críticas e comentários ambíguos entram em `pending.json` para aprovação.
- Spam e comentários já respondidos são ignorados.
- Há limite de respostas por execução para evitar comportamento de spam.
- Curtidas não são usadas para disparar DM automática.
- TikTok e Kwai permanecem somente como status/placeholder até existir uma rota oficial compatível para responder comentários.

## YouTube

Leitura usa os secrets já adotados no projeto:

- `YT_CLIENT_ID`
- `YT_CLIENT_SECRET`
- `YT_REFRESH_TOKEN`

Para publicar respostas, o refresh token precisa ter o escopo:

`https://www.googleapis.com/auth/youtube.force-ssl`

Pode-se guardar um token separado em `YT_SOCIAL_REFRESH_TOKEN`. Quando presente, ele tem prioridade no bot e não altera o token usado pelo pipeline de upload.

## Instagram e Facebook

Configuração esperada:

- `META_ACCESS_TOKEN`
- `META_GRAPH_VERSION`
- `INSTAGRAM_USER_ID`
- `INSTAGRAM_USERNAME`
- `FACEBOOK_PAGE_ID`

A versão do Graph fica em secret/variável em vez de fixa no código para evitar obsolescência.

## Execução

Modo seguro, apenas coleta/propostas:

```bash
SOCIAL_BOT_NETWORKS=youtube SOCIAL_BOT_AUTO_REPLY=false python -m social_bot.bot
```

Modo automático, depois de validar as permissões:

```bash
SOCIAL_BOT_NETWORKS=youtube SOCIAL_BOT_AUTO_REPLY=true SOCIAL_BOT_MAX_REPLIES=5 python -m social_bot.bot
```

Saídas:

- `social_bot/out/report.json`
- `social_bot/out/pending.json`
