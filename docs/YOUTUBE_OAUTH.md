# Conectar o YouTube ao Radar dos Games

Estado em 02/10/2026: o projeto tem módulos iniciais, mas src/pipeline.py ainda
gera apenas um manifesto. Validar OAuth não significa que a produção ou publicação
de vídeos já esteja funcionando. Não há upload no workflow de validação.

## Preparação pelo navegador, inclusive celular

1. Abra https://console.cloud.google.com/ e selecione/crie o projeto Radar dos Games.
2. Habilite **YouTube Data API v3** em APIs e serviços.
3. Configure Google Auth Platform: nome Radar dos Games, seu email de suporte,
   audiência externa e seus dados de contato. Se estiver em Testing, adicione
   como testador a conta que administra o canal.
4. Crie cliente OAuth do tipo **Aplicativo da Web**, nome Radar dos Games.
   Cadastre exatamente este URI de redirecionamento autorizado:
   https://developers.google.com/oauthplayground
5. Abra https://developers.google.com/oauthplayground. Na engrenagem, marque
   **Use your own OAuth credentials** e insira o Client ID e Client Secret desse cliente.
   Use acesso offline e consentimento explícito.
6. Autorize somente os escopos:
   - https://www.googleapis.com/auth/youtube.upload
   - https://www.googleapis.com/auth/youtube.readonly
7. Na autorização Google, escolha **Radar dos Games**, incluindo a conta de marca
   quando aplicável. Conclua o consentimento pessoalmente.
8. No Step 2 do Playground, troque o código pelos tokens e obtenha o refresh token.
   Não envie códigos ou tokens pelo chat, nem os salve no repositório.
9. Pelo próprio Playground, consulte
   https://www.googleapis.com/youtube/v3/channels?part=id,snippet&mine=true
   e confirme que o título corresponde a Radar dos Games. Copie o ID UC... retornado.
10. Em https://github.com/Luizfcalori/radar-dos-games/settings/secrets/actions,
    salve os quatro Repository Secrets:

| Secret | Valor |
| --- | --- |
| YT_CLIENT_ID | Client ID do seu cliente Google |
| YT_CLIENT_SECRET | Client Secret do mesmo cliente |
| YT_REFRESH_TOKEN | Refresh token da autorização desse cliente |
| YT_CHANNEL_ID | ID UC... do canal confirmado |

11. Em Actions, execute **YouTube - Validar OAuth**. Sucesso exige token renovado
    e o canal exato confirmado. Nenhum vídeo é enviado por esse teste.

Use credenciais OAuth próprias: as credenciais padrão do Playground não servem
como configuração durável. Em apps externos no estado Testing, refresh tokens
com esses escopos expiram em sete dias. Para operação contínua, configure o estado
In production conforme as exigências aplicáveis do Google e refaça a autorização.
Produção OAuth não substitui eventual verificação/auditoria da API para publicar
vídeos; restrições do projeto YouTube precisam ser verificadas antes de ativar uploads.

## Diagnóstico

- Secrets ausentes: preencher apenas os nomes indicados no GitHub.
- Token recusado: refazer consentimento com o mesmo cliente e canal.
- HTTP 403: verificar API habilitada, escopos, permissões e quota.
- Canal diferente: corrigir a seleção durante o OAuth; não mudar o ID esperado
  apenas para fazer o teste passar.

## Próxima etapa

Após OAuth validado: integrar roteiro, voz aprovada, mídia, renderização,
três Shorts, controle de duplicidade e revisão do resultado. O workflow diário
ainda não publica. O mesmo tema pode reaparecer, mas o mesmo vídeo não pode ser
republicado. A verificação de histórico deve incluir os vídeos já existentes
no canal antes do primeiro upload automatizado.

Referências oficiais:
- https://developers.google.com/youtube/v3/guides/auth/server-side-web-apps
- https://developers.google.com/identity/protocols/oauth2
- https://developers.google.com/oauthplayground
