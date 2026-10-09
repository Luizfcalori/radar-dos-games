# Padrão oficial de vídeo — Radar dos Games

Referência aprovada: **Master final corrigido de Ace Combat 8, aprovado em 02/10/2026**.

Este padrão é o default obrigatório para os vídeos principais do canal, salvo mudança explícita futura.

## Estrutura visual

- Resolução: **1920×1080**.
- Frame rate: **30 fps**.
- Intro: usar a **intro oficial real do Radar dos Games**, com o áudio original preservado.
- Depois da intro, entrar diretamente no conteúdo do vídeo.
- Watermark `RADAR DOS GAMES` discreto no canto superior direito.
- Não colocar elementos aleatórios ou sobreposições sem função editorial.

## Cards contextuais — padrão travado

O card aprovado é um bloco único: **sombra/faixa, título, subtítulo e barra de destaque devem permanecer juntos**.

Valores de referência em 1920×1080:

- Fundo: `x=62`, `y=850`, `w=1240`, `h=138`, `black@0.68`.
- Barra lateral: `x=62`, `y=850`, `w=10`, `h=138`, `0x00DCC8@0.96`.
- Título: `x=102`, `y=869`, tamanho `40`, branco, borda preta.
- Subtítulo: `x=102`, `y=927`, tamanho `25`, `0x7FE8FF`.
- Entrada do card: `0.45s` após o começo do primeiro corte do bloco.
- Duração máxima visível: `5.8s`, respeitando margem final do corte.
- A sombra/faixa **nunca pode aparecer no topo do vídeo nem separada do texto**.

## Mídia do conteúdo

Ordem de preferência por bloco narrativo:

1. **Gameplay/vídeo contextual**, quando existir e for relevante ao trecho narrado.
2. **Imagem oficial/contextual**, quando não houver gameplay adequado.

Regras:

- Não usar gameplay genérico só para preencher tempo.
- Não usar imagem desconectada da narração.
- Quando houver apenas imagem, aplicar movimento suave de câmera para evitar quadro estático.
- Para artes verticais ou estreitas, manter a arte integral sobre preenchimento de fundo adequado, evitando cortar o conteúdo principal.
- Cada bloco narrativo usa cadência padrão de **quatro cortes**, ciclando as mídias contextuais disponíveis.

## Texto e edição

- O título do card resume a ideia do bloco.
- O subtítulo complementa o título com informação curta e contextual.
- Texto deve permanecer legível sem cobrir o foco principal da imagem/gameplay.
- O card aparece apenas no primeiro corte do bloco; os cortes seguintes ficam limpos.
- A edição deve parecer contínua e editorial, não uma sequência de slides.

## Áudio

- Narração padrão atual: **Thalita Multilingual PT-BR V3** quando o roteiro pedir a voz oficial do canal.
- Corpo da narração normalizado com alvo `I=-16`, `LRA=7`, `TP=-1.5`.
- Intro mantém o próprio áudio.
- Voz deve ficar clara, sem clipping e sem saltos perceptíveis de volume.

## Quality gate

Antes de liberar qualquer Master:

- intro correta e com áudio;
- resolução 1920×1080 e 30 fps;
- card no bloco inferior aprovado;
- sombra/faixa alinhada atrás do título/subtítulo;
- nenhum retângulo escuro perdido no topo;
- gameplay priorizado quando existir;
- imagens contextuais quando gameplay não existir;
- watermark discreto;
- áudio da narração normalizado;
- revisão visual de intro, primeiro card, trecho intermediário e encerramento.

O renderizador `src/render.py` contém os mesmos valores como constantes para reduzir regressões visuais.


## Premium V3 — padrão oficial a partir de 07/10/2026

O Premium V3 evolui o padrão Fortnite V2 sem descartar sua base visual. Regras obrigatórias:

- direção semântica antes do render: cada cena recebe somente assets aprovados e compatíveis com o assunto narrado;
- cadência visual guiada pela fala, com alvo de ~4,2 s por corte e faixa operacional de 3–6 s quando a duração permitir;
- vídeo/gameplay contextual tem prioridade, sem preencher trechos com gameplay de outro assunto;
- imagens estáticas recebem movimento sutil e não destrutivo, preservando 100% do conteúdo principal;
- evitar começar cenas consecutivas com o mesmo asset quando houver alternativa aprovada;
- o card entra uma única vez por cena e não deve competir com o gameplay;
- os 3 Shorts são escolhidos por força de hook e limites semânticos completos de fala;
- o gate `src/premium_v3_qa.py` é bloqueante: sem aprovação semântica, cadência, movimento e Shorts, não há publicação.

Implementação de referência: `src/director_v3.py` -> `src/semantic_gate.py` -> `src/render.py` -> `src/shorts.py` -> `src/premium_v3_qa.py`.


## Premium V4 — Director Cut (padrão oficial a partir de 07/10/2026)

O Premium V4 mantém integralmente as regras de segurança visual e sincronismo do V3 e adiciona direção em nível de frase.

- A voz oficial continua **Thalita Multilingual PT-BR**; a síntese não é fragmentada para preservar naturalidade.
- `voice.py` registra limites estimados de sentenças dentro do áudio real de cada parágrafo.
- `director_v4.py` converte as sentenças em beats visuais com ritmo variável: frases de impacto recebem cortes mais rápidos; explicações respiram mais.
- O Master usa cold open curto antes da intro/sting quando existir um limite semântico seguro, sem repetir a fala.
- Palavras-chave são exibidas seletivamente, nunca como legenda permanente.
- Áudio passa por compressão leve, loudness, limiter e efeitos editoriais discretos. Música não é forçada sem asset previamente aprovado/licenciado.
- Shorts são **reconstruídos a partir das mídias originais aprovadas e da voz da própria cena**; não são crop do Master.
- `visual_frame_qa.py` amostra o Master em vários pontos e bloqueia quadros vazios/quase pretos ou tecnicamente degradados em excesso.
- `pro_score.py` soma sincronismo, direção, áudio, Shorts, frames, capas e identidade de voz; publicação exige **PRO_SCORE >= 85/100**.

Pipeline oficial: pesquisa -> roteiro -> Thalita + mapa de frases -> mídia -> Director V4 -> gate semântico -> Master V4 -> frame QA -> 3 Shorts independentes -> QA V4 -> capas premium -> PRO_SCORE -> publicação.


## Padrão cinematográfico oficial — aprovado em 08/10/2026

Masters e os três Shorts passam a usar `RADAR_CINEMATIC_V1` por padrão.
- Trilha Five Armies, de Kevin MacLeod, incluída no repositório, CC BY 4.0, com créditos automáticos nos metadados e no envio ao YouTube.
- Música normalizada, baixa sob a voz, com ducking e fades; impactos discretos do diretor V4. Voz Thalita mantida, alvo -16 LUFS e limiter sem ganho automático.
- Tratamento sutil de cor (contraste 1.025, saturação 0.94, brilho +0.008), aplicado à mídia antes dos textos. Não acrescentar faixas de cinema ou recortes destrutivos.
- Intro oficial integral primeiro, com áudio original; a trilha começa no corpo do Master. Cards, sincronismo, identidade, formatos e agenda continuam os aprovados.
- Shorts V4 recebem mixagem própria a partir da voz e mídias originais. O fallback legado recorta o Master já tratado, sem aplicar uma segunda trilha ou uma segunda correção de cor.
- Trilha ausente bloqueia o render; gate V4 exige trilha com ducking e perfil cinematográfico nos dois formatos.
- Módulo compartilhado: `src/cinematic.py`.

## Fluxo oficial media-first — 09/10/2026

Pesquisar e planejar mídia → baixar e verificar os arquivos reais → fazer a decupagem das cenas → finalizar roteiro → QA editorial → sintetizar Thalita PT-BR → Director V4 por frase → bloqueio semântico por beat → Master e 3 Shorts → QA e publicação conforme regras existentes.

`src/media_first.py` gera `output/media-first-storyboard.json` e somente então `output/auto-script.txt`. As cenas utilizam apenas índices de material efetivamente baixado. Se não houver um papel visual correspondente, a produção bloqueia — jamais substitui por material aleatório. As prévias são guardadas para revisão e a sinalização `source_level_only` não equivale a reconhecimento automático de ações/personagens na imagem. Roteiros manuais aprovados permanecem intactos.

Permanecem obrigatórios: intro integral, mixagem cinematográfica, Thalita, Master 1920×1080, 3 Shorts 1080×1920 no layout clássico aprovado, capas oficiais e qualidade bloqueante Premium V4. Nenhum serviço pago adicional.
