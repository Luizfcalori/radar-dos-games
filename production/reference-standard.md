# Radar dos Games — padrão editorial oficial

Referências aprovadas pelo usuário: Masters finais de Gears of War: E-Day e Minecraft/The Sift fornecidos em 2026-10-02.

## O que deve ser copiado
- Linguagem visual e qualidade editorial, NÃO a duração.
- Intro oficial real do Radar dos Games no início; não recriar intro genérica com drawtext.
- Voz/identidade sonora igual aos Masters aprovados (Thalita PT-BR e tratamento equivalente).
- Conteúdo visual do jogo como protagonista, sempre relacionado ao trecho narrado.
- Cortes e mudanças de mídia guiados por mudança de assunto/frase, não por intervalos fixos.
- Encartes curtos/discretos sobre a própria mídia, com texto derivado do trecho falado naquele momento.
- Encartes não podem ser cenas independentes nem entrar por timestamps arbitrários.
- Marca Radar discreta; não competir com o jogo.
- CTA final no mesmo espírito dos Masters.
- Duração livre: roteiro define o tempo; não imitar 2:21/2:38.

## Thumbnail / capa — padrão oficial
Referência visual aprovada em 06/10/2026: família de capas enviada pelo usuário + capa Gears E-Day aprovada. Este é o default obrigatório para Master e capas de Shorts, salvo mudança explícita.

- A capa deve usar como base uma imagem oficial e aprovada do próprio jogo, preferencialmente screenshot/key art obtida da fonte exata usada no QA de mídia.
- Nunca escolher um frame do Master como primeira opção para a thumbnail.
- `src/thumbnail.py` deve procurar automaticamente uma imagem aprovada em `output/clips.json`; imagens com evidência `steam_exact_app*` têm prioridade.
- Frame do Master existe somente como fallback técnico para fluxos antigos sem imagem oficial e deve ficar registrado como `video_frame_fallback` em `output/thumbnail-policy.json`.
- Master: 1280x720 (16:9). Shorts cover: 1080x1920 (9:16).
- Identidade fixa das capas: **verde neon Radar** como cor de destaque principal. Vermelho não deve ser usado como cor dominante de branding.
- Manter badge/lockup `RADAR DOS GAMES` no topo, com `GAMES` em verde.
- Tipografia de headline deve ser enorme, pesada, agressiva e imediatamente legível no celular; combinar branco + verde Radar.
- Visual obrigatório: gamer premium, alto impacto, ação forte, iluminação dramática, molduras/painéis metálicos/tech e profundidade visual.
- A arte do jogo é protagonista; adaptar personagens, cenário, inimigos e atmosfera ao jogo atual, preservando a mesma linguagem visual da marca.
- Usar painel/faixa inferior estilizada para subtítulo ou complemento curto, sempre coerente com o modelo aprovado.
- Evitar capa simples, apagada, genérica, screenshot cru, excesso de texto ou composição com baixa taxa de clique.
- `src/premium_covers.py` é o gerador padrão obrigatório do Master e das três capas verticais.
- `src/thumbnail.py` e `src/short_cover.py` existem somente como fallback técnico automático quando o gerador premium não consegue concluir após as tentativas previstas.
- O gerador premium deve priorizar mídia oficial/aprovada do assunto, montar composição cinematográfica de alto impacto e manter a identidade Radar; não é permitido escolher screenshot cru como padrão principal.
- `src/cover_qa.py` é gate bloqueante das quatro capas e deve validar resolução, integridade visual, política aplicada e registrar se houve fallback.
- As quatro capas devem ser geradas automaticamente no mesmo fluxo da produção e incluídas nos artifacts e metadados do YouTube.
- O `final-qa.json` deve registrar `premium_cover_generation`, `premium_cover_qa`, `cover_fallback_used` e `cover_template_version`.

## Enquadramento obrigatório
- Nenhuma imagem/gameplay contextual pode sofrer crop destrutivo que corte personagem, HUD, texto, logo ou elemento importante.
- O conteúdo original deve ficar 100% visível dentro do quadro sempre que a proporção não coincidir com 16:9.
- Para preencher o restante da tela, usar fundo derivado da própria mídia (ampliado/desfocado/escurecido) ou padding discreto; nunca ampliar a mídia principal até cortar suas bordas.
- Antes da liberação, amostrar o vídeo e reprovar cenas claramente fora de quadro.

## Shorts
- Gerar exatamente 3 Shorts derivados do Master.
- A duração é variável e deve seguir a narração, não um número fixo de segundos.
- Nunca encerrar um Short no meio de uma fala.
- Quando houver `voice-timings.json`, cada Short deve começar e terminar em limites semânticos completos de fala (preferencialmente o parágrafo/cena selecionado inteiro).
- Sem timing estruturado, estender o corte até a primeira pausa/silêncio natural depois do conteúdo mínimo, com margem curta no final.
- O encerramento deve ter pequena folga após a última palavra para não parecer cortado.

## Quality gate bloqueante
Reprovar automaticamente se: intro oficial ausente; voz diferente do padrão; encarte sem relação semântica com a narração; mídia sem relação com o trecho falado; cards grandes/soltos; cenas genéricas repetitivas; sincronização ruim; crop destrutivo; elemento importante fora de quadro; Short cortando fala; ou tentativa de reconstruir o padrão apenas por timestamps fixos.

Para thumbnails de novos fluxos STRICT, também reprovar a liberação se não houver imagem oficial do jogo disponível para a capa. O fallback por frame existe somente por retrocompatibilidade técnica e deve ser tratado como exceção, não como padrão aprovado.

## Automação definitiva das capas
- Toda produção nova gera automaticamente 4 capas: 1 Master + 3 Shorts.
- A capa Master representa o tema principal; cada Short deve priorizar os assets da própria cena/assunto selecionado.
- A sequência obrigatória é: render Master -> gerar Shorts -> `premium_covers.py` -> `cover_qa.py` -> QA final -> upload/publicação.
- O gerador premium faz nova tentativa automática com composição alternativa antes de acionar o fallback legado.
- Publicação só pode avançar depois do `cover_qa.py` retornar uma aprovação.
- Fallback é permitido para continuidade operacional, porém deve ficar explicitamente registrado em QA; ele nunca redefine o padrão visual oficial.

## Ace Combat
Novo Master deve ser criado do zero. Nenhum render Ace Combat anterior é fonte visual/editorial. Os Masters Gears/Minecraft são as únicas referências de padrão.

## Sincronismo obrigatório entre narração e imagem
- Regra bloqueante: sempre que a narração citar um jogo, personagem, veículo, mapa, evento ou recurso específico, a mídia exibida naquele trecho deve mostrar exatamente esse assunto ou uma imagem/vídeo oficial diretamente relacionado.
- Em vídeos com vários jogos, cada jogo citado deve ter pelo menos um asset próprio e aprovado. Não é permitido ilustrar vários jogos diferentes repetindo apenas um deles.
- Antes do render, cada cena deve ter o assunto falado identificado e seus `media_indices` precisam apontar para assets daquele mesmo assunto.
- Se uma cena citar um jogo e não existir mídia oficial/aprovada desse jogo, o fluxo deve procurar outra fonte oficial antes de renderizar.
- Se ainda assim não houver mídia correspondente, o Quality Gate deve BLOQUEAR a liberação em vez de preencher com gameplay de outro jogo.
- Cards, logos da feira, imagens institucionais ou B-roll genérico podem complementar, mas nunca substituir a mídia do jogo enquanto ele estiver sendo citado.
- Em matérias de lista/roundup, a checagem deve cobrir TODOS os jogos mencionados no roteiro, não apenas o tema principal do vídeo.
- O QA final deve reprovar cenas em que a fala e a mídia não correspondam semanticamente, mesmo que resolução, áudio e duração estejam corretos.



## Narração — naturalidade obrigatória
- A narração fala com o **público do canal**, nunca com o operador, editor ou uma pessoa específica.
- O texto deve soar como apresentador humano de canal gamer: direto, informativo, energético e natural em português do Brasil.
- É proibido narrar o processo de edição ou explicar a própria sincronização. Exemplos bloqueados: "estou mostrando", "na tela eu coloquei", "este trecho mostra", "aqui a tela fica", "o vídeo tenta mostrar", "o que está na tela", "como vocês podem ver na minha tela" e equivalentes.
- É proibido justificar decisões internas do Radar durante a matéria, como "o Radar prioriza", "o Radar considera", "a gente confere", "separando o que é fato" ou comentários sobre como a pauta foi produzida.
- Não usar tom de sermão, correção, tutorial do próprio vídeo ou conversa privada com o usuário.
- Quando houver chamada direta, preferir linguagem coletiva ("vocês", "galera", "quem joga", "quem acompanha") e evitar tratamento individual recorrente.
- O sincronismo fala-imagem continua obrigatório, mas deve acontecer **silenciosamente na edição**; nunca deve ser explicado pela locução.
- Roteiros automáticos devem passar por `src/narration_qa.py` antes da geração da voz. Se houver linguagem meta/editorial proibida, a produção deve bloquear.


## Premium V3 — evolução do Fortnite V2 (07/10/2026)

O **Fortnite/Fortnitemares V2 é a base visual**. O Premium V3 acrescenta uma camada obrigatória de direção e QA ao pipeline inteiro.

- Antes do render, `src/director_v3.py` resolve o mapeamento cena -> mídia usando apenas assets aprovados. Fluxos STRICT com papéis explícitos preservam esse mapeamento; fluxos automáticos deixam de usar rotação cega de mídia.
- A fala determina o ritmo: alvo de ~4,2 s por corte, mantendo normalmente 3–6 s por mudança visual.
- Gameplay/vídeo contextual continua em primeiro lugar. Imagens oficiais são usadas com movimento sutil não destrutivo; nenhum crop pode sacrificar personagem, HUD, logo ou informação importante.
- Cenas consecutivas devem variar o primeiro asset quando houver alternativa relevante.
- `src/semantic_gate.py` permanece bloqueante antes do render.
- `src/premium_v3_qa.py` valida cadência, sincronismo semântico, movimento e os 3 Shorts antes de permitir publicação.
- Shorts usam cenas escolhidas pelo diretor por força de hook, preservam fim completo da fala e exibem headline desde o primeiro frame.
- O `final-qa.json` deve registrar `premium_version=PREMIUM_V3`, `semantic_visual_sync` e `visual_cadence`.

Sequência oficial: pesquisa -> roteiro -> narração -> mídia -> **diretor V3** -> gate semântico -> render V3 -> 3 Shorts -> QA V3 -> capas premium -> QA final -> publicação.


## Premium V4 — Director Cut (07/10/2026)

O V4 é a evolução do **Fortnite V2 -> Premium V3** e passa a ser o default do pipeline automático.

- Direção deixa de ser apenas por cena e passa a ser **por frase**, sem recortar a locução da Thalita em TTS separados.
- Cada sentença pode gerar vários beats visuais; frases de impacto usam ritmo mais rápido e explicações usam cortes mais longos.
- Cold open pode anteceder a identidade Radar quando houver limite semântico seguro; nenhuma fala é duplicada.
- Overlays de palavra-chave são seletivos e curtos, apenas em informação de impacto.
- Sound design usa compressão, normalização, limiter e impactos editoriais discretos. Música só entra quando existir cama sonora aprovada/licenciada; o pipeline não inventa nem baixa música de terceiros.
- Os 3 Shorts passam a ser renderizações próprias 9:16 a partir dos assets aprovados + áudio completo da cena selecionada.
- O QA visual amostra frames do Master para detectar telas quase pretas/vazias e baixa informação visual.
- **PRO_SCORE >= 85/100** é condição bloqueante para publicação automática.
- V3 permanece disponível como fallback técnico, mas não é mais o padrão do `daily-video.yml`.


## Padrão cinematográfico oficial — aprovado em 08/10/2026

Masters e os três Shorts passam a usar `RADAR_CINEMATIC_V1` por padrão.
- Trilha Five Armies, de Kevin MacLeod, incluída no repositório, CC BY 4.0, com créditos automáticos nos metadados e no envio ao YouTube.
- Música normalizada, baixa sob a voz, com ducking e fades; impactos discretos do diretor V4. Voz Thalita mantida, alvo -16 LUFS e limiter sem ganho automático.
- Tratamento sutil de cor (contraste 1.025, saturação 0.94, brilho +0.008), aplicado à mídia antes dos textos. Não acrescentar faixas de cinema ou recortes destrutivos.
- Intro oficial integral primeiro, com áudio original; a trilha começa no corpo do Master. Cards, sincronismo, identidade, formatos e agenda continuam os aprovados.
- Shorts V4 recebem mixagem própria a partir da voz e mídias originais. O fallback legado recorta o Master já tratado, sem aplicar uma segunda trilha ou uma segunda correção de cor.
- Trilha ausente bloqueia o render; gate V4 exige trilha com ducking e perfil cinematográfico nos dois formatos.
- Módulo compartilhado: `src/cinematic.py`.
