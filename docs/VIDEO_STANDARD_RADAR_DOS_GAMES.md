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
