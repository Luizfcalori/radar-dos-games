# RADAR PREMIUM CONVERSÃO — segundo padrão oficial (V1)

**Status:** padrão oficial de todos os Shorts do Radar dos Games desde 10/10/2026, aprovado pelo usuário.

## Modelos do canal

1. **RADAR_PREMIUM_CONVERSAO_V1**: padrão visual obrigatório para todos os Shorts — notícias, lançamentos, análises, conteúdo recorrente, convites e campanhas.
2. **RADAR_SHORTS_CLASSIC_V1**: legado histórico; não usar em novas produções sem aprovação explícita do usuário.

## Composição aprovada

- Vídeo em 1080x1920, 30fps, H.264 + AAC, português brasileiro.
- Cabeçalho RADAR DOS GAMES em azul-escuro, acentos verde neon e títulos claros, com forte contraste.
- Gameplay centralizada dentro de moldura e destaque à identidade da marca; evitar recorte que deixa imagem acima/abaixo da moldura.
- Fundo tech escurecido, bloco visual grande para inscrição, rodapé limpo e assinatura 'RADAR DOS GAMES'.
- Trilha e tratamento cinematográfico equivalentes ao padrão Radar; narradora Thalita Multilingual PT-BR. Nomes e empréstimos ingleses com pronúncia adequada.
- Aplicar o layout Premium automaticamente em toda nova produção de três Shorts, mantendo a mídia completa e sem recortes destrutivos.

## CTA aprovado para todas as redes

- CTA principal: **INSCREVA-SE AGORA**.
- CTA secundário: **DEIXE O LIKE**.
- Assinatura: **RADAR DOS GAMES**.
- **Não colocar** 'ATIVE O SININHO' nem '@radardosgamesbr', inclusive na voz e nos textos sobrepostos.
- Não colocar marcas de plataforma como 'YOUTUBE' no vídeo, pois a mesma produção é publicada em múltiplas redes.
- A palavra 'INSCREVA-SE' foi preservada por ser o texto aprovado anteriormente; não a trocar por outro CTA sem solicitação do usuário.

## Aplicação prática

- O convite exclusivo atual é renderizado por `specials/once_radar_channel_invite_2026_10_09.py` e `.github/workflows/once-radar-channel-invite-2026-10-09.yml`.
- O renderer comum `src/shorts_v4.py` aplica `RADAR_PREMIUM_CONVERSAO_V1` a cada beat e o gate `src/premium_v4_qa.py` bloqueia qualquer produção que use o layout legado.
- QA exige formato vertical, duração válida, locução e presença do CTA aprovado sem sininho nem arroba.
- Não ativar publicação automática de material institucional sem revisão explícita.
