# Padrão oficial dos Shorts — Radar dos Games

**Padrão oficial atualizado em 10/10/2026: RADAR_PREMIUM_CONVERSAO_V1 para TODOS os Shorts informativos, promocionais e institucionais.** A aprovação do usuário substitui a regra anterior que reservava o Premium Conversão apenas para convites/campanhas. Não voltar ao layout clássico como padrão sem nova aprovação explícita.

## Identidade e composição obrigatórias

- Formato vertical 9:16, 1080 × 1920, 30 fps, H.264/yuv420p e áudio AAC estéreo.
- Cabeçalho Radar dos Games em azul-escuro, acentos verde neon e alto contraste.
- Gameplay/mídia contextual centralizada dentro de moldura; preservar a ação e evitar recortes destrutivos que cortem personagens, texto ou informação importante.
- Fundo gamer/tech escurecido e cinematográfico, bloco de título grande e legível em tela de celular, rodapé limpo e assinatura RADAR DOS GAMES.
- CTA visível: **INSCREVA-SE AGORA** e **DEIXE O LIKE**. Assinatura: **RADAR DOS GAMES**.
- **Não incluir** “ATIVE O SININHO”, **@radardosgamesbr**, nomes/logos de plataformas (YouTube, TikTok, Instagram, Facebook, Kwai) nem endereço exclusivo de uma rede no visual exportável.
- Trilha cinematográfica sob a voz, ducking/fades, mixagem equilibrada e tratamento de cor consistente.
- Voz Thalita Multilingual PT-BR; revisar pronúncia de nomes e termos em inglês sem traduzir nomes próprios.
- O texto narrado deve corresponder à mídia realmente exibida. Selecionar e inspecionar as mídias antes de fechar a narração; priorizar gameplay em movimento e cenas semanticamente correspondentes ao hook.
- Gerar exatamente 3 Shorts por Master, cada um com hook e trecho próprios, sem repetição visual desnecessária.
- Gerar automaticamente uma capa vertical premium para cada Short, com arte oficial/aprovada do jogo, branding Radar, verde neon como destaque e headline grande. A capa é separada do layout interno do vídeo.
- Padrão gratuito: não depender de serviços pagos, templates pagos ou recursos que exijam créditos.

## QA obrigatório antes de publicar

- Confirmar 1080 × 1920, 30 fps, áudio presente, duração válida e exatamente três Shorts.
- Confirmar CTA aprovado e ausência de “ATIVE O SININHO”, @radardosgamesbr e branding exclusivo de plataforma.
- Conferir que gameplay, título, narração e cena estão alinhados; headlines devem ser específicas, nunca “Destaque 1”/“Cena 2”.
- Confirmar mixagem cinematográfica, voz inteligível, dicção dos termos em inglês, capas e metadados.
- Fallback técnico só pode ser usado se registrado no QA; não deve redefinir o padrão visual oficial.

## Histórico e compatibilidade

- Este padrão Premium substitui, a partir de 10/10/2026, o antigo RADAR_SHORTS_CLASSIC_V1 como padrão visual de saída.
- O gerador deve continuar produzindo exatamente três arquivos em `output/shorts/` e manter compatibilidade com a pipeline de produção.
- A capa vertical usa `src/short_cover.py`/geração premium existente e deve ser referenciada nos metadados correspondentes.
- Referência de composição e CTA: [RADAR PREMIUM CONVERSÃO](RADAR_PREMIUM_CONVERSAO.md).
