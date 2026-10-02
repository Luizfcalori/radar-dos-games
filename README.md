# Radar dos Games — Automação diária

Pipeline gratuito para produzir o vídeo diário e 3 Shorts do canal Radar dos Games.

## Regras editoriais
- O mesmo jogo/tema pode voltar quando existir novidade relevante.
- Nunca republicar o mesmo vídeo: cada produção recebe `content_id` único e hash do arquivo final.
- Vídeo principal: alvo normal de 4–5 minutos, PT-BR, intro, B-roll/gameplay relevante, cards, CTA e áudio sincronizado.
- **Padrão visual oficial:** Master final corrigido de Ace Combat 8 aprovado em 02/10/2026.
- Gameplay/vídeo contextual tem prioridade quando existir; imagem oficial/contextual é o fallback.
- Cards usam o bloco inferior aprovado, com sombra/faixa sempre presa ao título e subtítulo — nunca deslocada para o topo.
- Shorts: exatamente 3 por produção, 9:16, derivados do vídeo do dia e com CTA para o vídeo completo.
- Nunca usar créditos pagos automaticamente.
- Confirmar o canal e a versão final antes do upload.

Especificação completa: [`docs/VIDEO_STANDARD_RADAR_DOS_GAMES.md`](docs/VIDEO_STANDARD_RADAR_DOS_GAMES.md).

## Pipeline
`research -> script -> voice -> media -> render -> shorts -> quality gate -> YouTube`

O workflow pode ser disparado manualmente e, após validação completa, diariamente por cron.
