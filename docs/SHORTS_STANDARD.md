# Padrão oficial dos Shorts — Radar dos Games

**Padrão obrigatório desde 10/10/2026: `RADAR_PREMIUM_CONVERSAO_V1` em todos os Shorts.** Esta decisão do usuário substitui o uso do layout clássico como padrão de notícias, lançamentos e conteúdo recorrente.

## Pipeline obrigatória

- `src/shorts_v4.py` renderiza cada beat usando o layout Premium Conversão.
- `src/premium_v4_qa.py` bloqueia a produção se o manifesto não identificar `RADAR_PREMIUM_CONVERSAO_V1`, se o CTA não estiver correto ou se faltarem os três Shorts.
- `src/premium_covers.py` gera as quatro capas premium (Master + 3 Shorts); `src/cover_qa.py` valida as capas.
- `.github/workflows/daily-video.yml` executa renderização, QA e geração de capas no fluxo diário.
- `tests/test_shorts_v4_layout.py` verifica o layout, CTAs, preservação da mídia e renderização vertical.

## Elementos visuais obrigatórios

- Vertical 9:16, 1080 × 1920, 30 fps, H.264/yuv420p, com áudio preservado na mixagem final.
- Cabeçalho Radar dos Games em azul-escuro, acentos verde neon, título específico e legível.
- Gameplay ou mídia contextual centralizada dentro de moldura; ajustar escala e padding para preservar a imagem-fonte sem recorte destrutivo.
- Fundo tech escurecido com tratamento cinematográfico.
- CTA visível: **INSCREVA-SE AGORA** e **DEIXE O LIKE**; assinatura **RADAR DOS GAMES**.
- Capa vertical independente para cada Short, coerente com a identidade premium e a arte aprovada do jogo.
- **A capa de cada Short também deve ocupar os primeiros 1,4 segundos do MP4**, com a mesma headline do Short; manter o arquivo `short_N_cover.jpg` para seleção de capa nas plataformas que permitem essa escolha.
- A montagem da abertura deve preservar a narração, a trilha, o áudio original e a duração total; `src/cover_qa.py` valida que o primeiro frame do MP4 corresponde à capa exportada.

## Regras editoriais e de áudio

- Voz **Thalita Multilingual PT-BR**.
- Revisar pronúncia de nomes próprios e termos em inglês; não traduzir nomes de jogos.
- Selecionar e inspecionar as mídias antes de finalizar a narração; fala, headline e cena devem corresponder.
- Priorizar gameplay real em movimento, headlines específicas e três Shorts independentes por Master.
- Manter trilha cinematográfica, ducking, mixagem inteligível e efeitos discretos.

## Proibições no vídeo e no CTA

- Não incluir “ATIVE O SININHO”.
- Não incluir `@radardosgamesbr`.
- Não incluir marca exclusiva de uma plataforma nem endereço de perfil de rede social.
- Não publicar nem declarar concluído antes de passar pelos gates de qualidade.

## Compatibilidade e segurança

- O Master mantém seu próprio padrão cinematográfico; a mudança de layout aplica-se aos três Shorts.
- O padrão Premium não autoriza remover a revisão editorial, o QA semântico, a inspeção visual por frames ou a validação técnica.
- Nenhum serviço pago é requisito para o layout.
- O layout legado `RADAR_SHORTS_CLASSIC_V1` permanece apenas para compatibilidade histórica e não deve ser usado na pipeline diária.

## Regra permanente de contingência de mídia — aprendizados Fight Night (21/10/2026)

- Preservar o assunto e a fonte autorizada como restrições rígidas; não substituir o jogo por mídia genérica.
- Se não houver gameplay inédito suficiente para um Short, permitir imagens estáticas oficiais e contextuais do mesmo jogo, desde que aprovadas e rastreáveis (host/fonte oficial, role/contexto e subject match). Nomes opacos de CDN não são, isoladamente, motivo para reprovar uma imagem oficial pertinente.
- A sequência de contingência é: ampliar corretamente janelas adjacentes revisadas; usar fragmentos inéditos restantes; usar imagens oficiais distintas e contextualizadas; bloquear somente se ainda não houver mídia segura.
- Limites de duração por beat, inspeção, coerência fala-imagem e proibição de repetir o mesmo intervalo/imagem permanecem ativos. Não afrouxar o QA de identidade nem a regra antirrepetição.
- Corrigir e testar a etapa que falhou sem reiniciar ou refazer etapas já aprovadas quando isso puder ser evitado. As tentativas de correção e a fila de postagem devem ser idempotentes para impedir Shorts duplicados.
