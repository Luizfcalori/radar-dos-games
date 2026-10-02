# Padrão oficial dos Shorts — Radar dos Games

Referência aprovada em 02/10/2026: `THE SIFT VAI CHEGAR AO MINECRAFT NORMAL! JAVA + BEDROCK #Shorts - Radar dos Games`.

## Especificação técnica

- Formato: 9:16
- Resolução: 1080 × 1920
- Frame rate: 30 fps
- Vídeo: H.264 / yuv420p
- Áudio: AAC estéreo, normalizado em -16 LUFS
- Duração-alvo: aproximadamente 22 segundos por Short
- Quantidade por Master: exatamente 3
- Origem: sempre derivados do Master correspondente

## Layout visual obrigatório

1. Cabeçalho superior escuro com `RADAR DOS GAMES` em branco.
2. Headline principal em caixa alta, centralizada, branca, dentro de uma área preta no topo.
3. Fundo vertical contextual derivado da própria mídia, desfocado e escurecido.
4. Gameplay/imagem contextual no centro, preservando enquadramento; não usar crop vertical destrutivo.
5. Moldura/acento ao redor da mídia principal usando uma cor contextual retirada do próprio vídeo/jogo.
6. Faixa contextual curta logo abaixo da mídia usando a mesma cor de destaque contextual.
7. CTA inferior em duas linhas:
   - `VÍDEO COMPLETO NO CANAL` em branco.
   - `RADAR DOS GAMES` em destaque.
8. Nada de logos de terceiros, templates pagos ou elementos visuais que dependam de créditos.

## Regra de cor

- **Ciano NÃO é uma cor fixa do padrão.** Ele apareceu na referência aprovada porque combinava com aquele corte específico.
- A estrutura/composição é fixa; a cor de destaque é variável e deve acompanhar a identidade visual do jogo ou do trecho.
- O gerador deve extrair localmente uma cor forte da própria mídia usando FFmpeg/Python.
- Se não houver uma cor útil no trecho, usar branco neutro como fallback em vez de impor ciano ou qualquer outra cor fixa.

## Conteúdo

- Cada Short deve usar um trecho diferente do Master.
- Quando existir `output/qa.json`, usar os títulos/subtítulos das cenas do Master para preencher headline e faixa contextual.
- Seleção padrão de trechos: aproximadamente 12%, 42% e 72% do Master.
- Gameplay contextual tem prioridade sobre imagem estática quando disponível no Master.

## Regra do projeto

Este é o padrão oficial dos Shorts até nova aprovação explícita. O gerador em `src/shorts.py` deve permanecer compatível com `python src/shorts.py <master.mp4>` e produzir exatamente três arquivos em `output/shorts/`.
