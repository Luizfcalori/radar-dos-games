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


## Capa vertical do Short — padrão oficial aprovado em 06/10/2026

A capa do Short é separada do layout interno do vídeo. Para as capas verticais, a identidade visual é fixa e deve seguir o modelo aprovado pelo usuário:

- Resolução obrigatória: 1080 × 1920.
- Badge `RADAR DOS GAMES` no topo.
- Verde neon Radar como cor dominante de branding e destaque.
- Headline muito grande, pesada, de alto impacto, combinando branco + verde.
- Fundo com ação forte e arte oficial do jogo.
- Painel metálico/tech escuro na região inferior para headline/subheadline.
- Visual gamer premium, dramático, agressivo e otimizado para clique.
- Adaptar personagens, cenário e atmosfera ao jogo atual sem alterar a linguagem visual da marca.
- Não usar vermelho como cor dominante do branding da capa.
- Gerador oficial: `src/short_cover.py`.
- Arquivos esperados: `output/shorts/short_1_cover.jpg`, `short_2_cover.jpg`, `short_3_cover.jpg`.
- As capas devem ser referenciadas automaticamente nos respectivos `short-1-youtube.json`, `short-2-youtube.json` e `short-3-youtube.json`.

A regra de cor contextual descrita acima continua valendo somente para elementos internos do vídeo Short; não substitui a identidade verde fixa das capas.


## Padrão cinematográfico oficial — aprovado em 08/10/2026

Masters e os três Shorts passam a usar `RADAR_CINEMATIC_V1` por padrão.
- Trilha Five Armies, de Kevin MacLeod, incluída no repositório, CC BY 4.0, com créditos automáticos nos metadados e no envio ao YouTube.
- Música normalizada, baixa sob a voz, com ducking e fades; impactos discretos do diretor V4. Voz Thalita mantida, alvo -16 LUFS e limiter sem ganho automático.
- Tratamento sutil de cor (contraste 1.025, saturação 0.94, brilho +0.008), aplicado à mídia antes dos textos. Não acrescentar faixas de cinema ou recortes destrutivos.
- Intro oficial integral primeiro, com áudio original; a trilha começa no corpo do Master. Cards, sincronismo, identidade, formatos e agenda continuam os aprovados.
- Shorts V4 recebem mixagem própria a partir da voz e mídias originais. O fallback legado recorta o Master já tratado, sem aplicar uma segunda trilha ou uma segunda correção de cor.
- Trilha ausente bloqueia o render; gate V4 exige trilha com ducking e perfil cinematográfico nos dois formatos.
- Módulo compartilhado: `src/cinematic.py`.
