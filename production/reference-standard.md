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
- A capa deve usar como base uma imagem oficial e aprovada do próprio jogo, preferencialmente screenshot/key art obtida da fonte exata usada no QA de mídia.
- Nunca escolher um frame do Master como primeira opção para a thumbnail.
- `src/thumbnail.py` deve procurar automaticamente uma imagem aprovada em `output/clips.json`; imagens com evidência `steam_exact_app*` têm prioridade.
- Frame do Master existe somente como fallback técnico para fluxos antigos sem imagem oficial e deve ficar registrado como `video_frame_fallback` em `output/thumbnail-policy.json`.
- Formato obrigatório: 1280x720 (16:9), alto contraste e leitura imediata em tela pequena.
- O jogo é o protagonista visual. Evitar tarjas pesadas, excesso de texto e composição com aparência de screenshot cru.
- O nome do jogo/título principal deve ser curto, grande e legível; remover caudas editoriais longas da capa quando possível.
- Aplicar sempre o lockup visual do Radar dos Games: radar + controle + nome da marca em branco/verde, de forma profissional e sem competir com a arte do jogo.
- Manter identidade visual coerente com a arte escolhida, preservando o verde Radar como assinatura.
- A thumbnail final deve ser gerada automaticamente no mesmo fluxo do Master e registrada no pacote de artifacts.

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

## Ace Combat
Novo Master deve ser criado do zero. Nenhum render Ace Combat anterior é fonte visual/editorial. Os Masters Gears/Minecraft são as únicas referências de padrão.
