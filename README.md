# Radar dos Games — Automação diária

Pipeline gratuito para produzir o vídeo diário e 3 Shorts do canal Radar dos Games.

## Regras editoriais
- O mesmo jogo/tema pode voltar quando existir novidade relevante.
- Nunca republicar o mesmo vídeo: cada produção recebe `content_id` único e hash do arquivo final.
- Vídeo principal: alvo normal de 4–5 minutos, PT-BR, intro, B-roll/gameplay relevante, cards, CTA e áudio sincronizado.
- Shorts: exatamente 3 por produção, 9:16, derivados do vídeo do dia e com CTA para o vídeo completo.
- Nunca usar créditos pagos automaticamente.
- Confirmar o canal e a versão final antes do upload.

## Pipeline
`research -> script -> voice -> media -> render -> shorts -> quality gate -> YouTube`

O workflow pode ser disparado manualmente e, após validação completa, diariamente por cron.
