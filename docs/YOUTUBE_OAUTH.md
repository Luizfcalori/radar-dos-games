# Conectar o YouTube ao Radar dos Games

Estado em 02/10/2026: o canal oficial confirmado é `UCSZJZE-E10SVdx42wrDeWhw` (Radar dos Games). O ID do canal não é segredo e está travado no código para impedir upload acidental em outro canal.

## Preparação pelo navegador, inclusive celular

1. Abra https://console.cloud.google.com/ e selecione/crie o projeto Radar dos Games.
2. Habilite **YouTube Data API v3** em APIs e serviços.
3. Configure Google Auth Platform: nome Radar dos Games, seu email de suporte, audiência externa e seus dados de contato. Se estiver em Testing, adicione como testador a conta que administra o canal.
4. Crie cliente OAuth do tipo **Aplicativo da Web**, nome Radar dos Games.
   Cadastre exatamente este URI de redirecionamento autorizado:
   https://developers.google.com/oauthplayground
5. Abra https://developers.google.com/oauthplayground. Na engrenagem, marque **Use your own OAuth credentials** e insira o Client ID e Client Secret desse cliente.
   Use acesso offline e consentimento explícito.
6. Autorize somente os escopos:
   - https://www.googleapis.com/auth/youtube.upload
   - https://www.googleapis.com/auth/youtube.readonly
7. Na autorização Google, escolha a identidade que realmente administra o canal **Radar dos Games**. Não conclua se a API retornar outro canal.
8. No Step 2 do Playground, troque o código pelos tokens e obtenha o refresh token.
   Não envie códigos ou tokens pelo chat, nem os salve no repositório.
9. Pelo próprio Playground, consulte:
   https://www.googleapis.com/youtube/v3/channels?part=id,snippet&mine=true
   e confirme que o retorno é exatamente `Radar dos Games` com ID `UCSZJZE-E10SVdx42wrDeWhw`.
10. Em https://github.com/Luizfcalori/radar-dos-games/settings/secrets/actions, salve somente estes três Repository Secrets:

| Secret | Valor |
| --- | --- |
| YT_CLIENT_ID | Client ID do cliente Google |
| YT_CLIENT_SECRET | Client Secret do mesmo cliente |
| YT_REFRESH_TOKEN | Refresh token da autorização desse cliente |

11. Em Actions, execute **YouTube - Validar OAuth**. O workflow renova o token e confirma que a autorização pertence exatamente ao canal Radar dos Games. Nenhum vídeo é enviado por esse teste.

## Segurança

- `YT_CLIENT_SECRET` e `YT_REFRESH_TOKEN` nunca devem aparecer em commits, logs, issues ou chats.
- O canal esperado fica travado no código por **nome e ID**. Mesmo com um OAuth válido, upload para outro canal é bloqueado.
- O workflow de diagnóstico verifica apenas se os Secrets existem; não imprime os valores.
- Um eventual Secret antigo `YT_CHANNEL_ID` não é usado como fonte de verdade; o ID oficial está fixado no código.

Use credenciais OAuth próprias: as credenciais padrão do Playground não servem como configuração durável. Em apps externos no estado Testing, refresh tokens com esses escopos podem expirar conforme as regras do Google. Para operação contínua, mantenha o consentimento/configuração do projeto compatíveis com uso prolongado.

## Diagnóstico

- Secrets ausentes: preencher somente `YT_CLIENT_ID`, `YT_CLIENT_SECRET` e `YT_REFRESH_TOKEN` no GitHub.
- Token recusado: refazer consentimento com o mesmo cliente e canal.
- HTTP 403: verificar YouTube Data API v3 habilitada, escopos, permissões e quota.
- Canal diferente: refazer a seleção durante o OAuth. Não altere o ID esperado apenas para fazer o teste passar.

Referências oficiais:
- https://developers.google.com/youtube/v3/guides/auth/server-side-web-apps
- https://developers.google.com/identity/protocols/oauth2
- https://developers.google.com/oauthplayground
