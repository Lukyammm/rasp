# HISTÓRICO DE DESENVOLVIMENTO E EVOLUÇÃO — PROJETO RASP (SocialScraper)

Este documento registra em detalhes as implementações, decisões de arquitetura, fluxos de dados e justificativas técnicas realizadas no ecossistema do **RASP (SocialScraper)**, servindo como guia mestre para qualquer desenvolvedor ou modelo de IA (Claude, etc.) que for dar manutenção ou evoluir o projeto.

---

## 1. MÓDULO: EXTRAÇÃO POR POST ESPECÍFICO (LINKS DIRETOS)
**Data de entrega:** Outubro de 2026  
**Demanda do usuário:** Capacidade de extrair dados e métricas de posts específicos a partir de URLs diretas, e não apenas por busca booleana por palavras-chave, com uma aba dedicada no menu superior.

### 1.1. Arquitetura e Engenharia de Extração
- **Arquivo Criado:** `backend/scrapers/post_scraper.py`
- **Técnicas Empregadas por Rede Social:**
  1. **Instagram (`extract_instagram_single_post`):**
     - Parser do shortcode a partir de `/p/{code}/`, `/reel/{code}/`, `/reels/{code}/`.
     - Consulta à rota interna `/api/v1/media/{media_id}/info/` ou `xdt_fbsearch` para extração de caption, autor, contagem de likes e comentários.
     - Fallback robusto via DOM e tags OpenGraph (`meta[property='og:description']`, `meta[property='og:title']`).
  2. **TikTok (`extract_tiktok_single_post`):**
     - Extração rápida de JSON por reidratação do script `__UNIVERSAL_DATA_FOR_REHYDRATION__` presente no DOM da página do vídeo.
     - Fallback por seletores específicos do layout web do TikTok.
  3. **X / Twitter (`extract_x_single_post`):**
     - Interceptação de chamadas GraphQL de detalhe (`TweetDetail`).
     - Fallback via DOM atômico (`article[data-testid="tweet"]`), capturando autor, texto e métricas tabulares.
  4. **YouTube (`extract_youtube_single_post`):**
     - Extração do objeto `ytInitialData` e da resposta do player InnerTube (`videoDetails`).
     - Coleta precisa de autor (canal), título/descrição, views, likes e contagem de comentários.
  5. **Facebook (`extract_facebook_single_post`):**
     - Avaliação em contexto isolado de DOM (`page.evaluate`) e metadados OpenGraph.
  6. **Detecção Inteligente de Rede (`detect_network_from_url`):**
     - Identifica a rede social a partir do domínio (ex.: `instagram.com` -> `instagram`, `youtu.be` -> `youtube`).
  7. **Execução em Lote (`scrape_posts_by_urls`):**
     - Agrupa URLs por rede para abrir o navegador Playwright apenas uma vez por rede social.
     - Utiliza as sessões autenticadas existentes (`sessao_{rede}_dir` e `sessao_{rede}.json`).
     - Notifica progresso em tempo real via WebSocket.

### 1.2. Integração no Backend
- `backend/main.py`:
  - Modelo `ScrapeRequest` atualizado com `search_type: Literal["keyword", "profile", "url"]`.
  - Flags opcionais `scrape_comments: bool` e `max_comments: int`.
  - Suporte ao valor `"auto"` em `networks`.
- `backend/jobs.py`:
  - Roteamento de jobs com `search_type == "url"` diretamente para `scrape_posts_by_urls`.
  - Execução cooperativa da coleta de comentários após a extração dos posts quando `scrape_comments` estiver ativo.
- `backend/utils.py`:
  - Geração de nome de arquivo amigável para Excel (`RASP_Post-Especifico_Posts-Especificos_...xlsx`).

### 1.3. Interface do Usuário (Frontend)
- `frontend/index.html`:
  - Adicionado botão de aba no menu superior: **`Post Específico`** (`tab-direct-link`).
  - Container da aba `#tab-direct-link`:
    - Seletor com 6 cards interativos (Automático, Instagram, TikTok, X, YouTube, Facebook).
    - Campo textarea para colar links com contador dinâmico de URLs válidas (`#directUrlsCountBadge`).
    - Checkbox para ativar/desativar raspagem de comentários com limite numérico por post.
    - Terminal de log em tempo real dedicado (`#directTerminalLogs`).
    - Card de conclusão com botão direto de download do Excel e atalho para o Dashboard.
- `frontend/app.js`:
  - Métodos `updateDirectNetworkSelection`, `updateDirectUrlsCount`, `toggleDirectCommentsLimit`, `handleDirectPostSubmit`.
  - Redirecionamento de logs de WebSocket do job para o terminal da aba ativa.

---

## 2. MÓDULO: SELEÇÃO DE REDE E LIMITES ADAPTATIVOS NA COLETA DE COMENTÁRIOS DO DASHBOARD
**Data de entrega:** Outubro de 2026  
**Demanda do usuário:** 
1. Na coleta de comentários do Dashboard (após a busca padrão por palavras-chave com AND/OR), permitir que o usuário escolha qual rede social específica deseja coletar ou todas as redes.
2. Permitir escolher a quantidade de posts para coletar comentários (ex.: 50 mais, 100 maiores), adaptando-se dinamicamente à quantidade real de posts existentes (ex.: se houver apenas 30 posts, sugerir 10, 20 ou Todas as 30; se houver 3.000 posts, sugerir 50, 100, 250, 500, 1.000, 2.000 ou Todas as 3.000; além de entrada personalizada).

### 2.1. Backend (`backend/comments_service.py` e `backend/main.py`)
- **Ordenação Prioritária pelos Maiores Posts:**
  - Em `comments_service.py` (`select_posts`), os candidatos a coleta de comentários passaram a ser ordenados por `(c[1]["comments"], c[1]["likes"])` de forma decrescente:
    - Posts com mais comentários vêm primeiro.
    - Em caso de empate (ou quando a rede não relata contagem prévia de comentários, como buscas simples), o volume de **curtidas** desempata, garantindo que os maiores posts por engajamento sejam priorizados.
- **Filtro de Redes:**
  - `select_posts` já recebe `networks: Optional[List[str]]`. Quando fornecido, processa estritamente as redes selecionadas.
- **Validação de Limites Ampliada:**
  - Em `backend/main.py` (`CommentsRequest`), `max_posts` teve o limite máximo ampliado de `le=5000` para `le=50000`, acomodando extrações em larga escala.

### 2.2. Frontend (`frontend/index.html` e `frontend/app.js`)
- **Novo Controle de Seleção de Rede Social (`#commentsSelectedNetwork`):**
  - Adicionado ao cabeçalho de `#commentsCard`.
  - Alimentado dinamicamente com as redes sociais presentes na extração atual e que possuem posts compatíveis.
  - Exibe para cada rede o número exato de posts pendentes (ex.: `Instagram (24 pendentes)`).
  - Clicar nos chips de estatísticas por rede (`#commentsNetworkStats`) agora seleciona automaticamente a rede correspondente no dropdown e recalcula o painel.
- **Seletor de Quantidade Adaptativo (`#commentsMaxPosts`):**
  - Substitui as opções estáticas anteriores (`20, 50, 100`) por um algoritmo inteligente (`updateAdaptiveCommentsMaxPosts`):
    - Se $N$ for a quantidade de publicações pendentes:
      - Primeira opção sempre: `Todas (N publicações)`.
      - Gera degraus proporcionais inferiores a $N$ a partir da escala `[10, 20, 50, 100, 250, 500, 1000, 2000, 5000, 10000]`.
      - Se $N = 30$: exibe `Todas (30)`, `20 maiores`, `10 maiores`, `Personalizado...`.
      - Se $N = 3.000$: exibe `Todas (3.000)`, `2.000 maiores`, `1.000 maiores`, `500 maiores`, `250 maiores`, `100 maiores`, `50 maiores`, `Personalizado...`.
      - Se o usuário escolher `Personalizado...`, um prompt solicita a quantidade desejada, valida contra o teto e adiciona a opção personalizada ao select.
- **Feedback Visual e Ação Clara:**
  - O subtítulo de `#commentsCard` e o texto do botão principal (`#btnCommentsStart`) adaptam-se imediatamente à rede e quantidade selecionadas (ex.: `Coletar Instagram (20)` ou `Coletar comentários (500)`).
  - O payload enviado ao endpoint `/api/comments/scrape` passa a incluir `networks: [selectedNetwork]` quando uma rede for selecionada, e `max_posts` respeita o valor escolhido.

---

---

## 3. INVESTIGAÇÃO PERICIAL & RESOLUÇÃO: COLETA DE COMENTÁRIOS DO X (TWITTER)
**Data de entrega:** Outubro de 2026  
**Demanda do usuário:** *"eu acho que nao ta puxando certo os comentarios do twitter, pode conferir? coloquei os 20 maiores e nao puxou os 20 mairoes, posso ta errado, verifica"*

### 3.1. Diagnóstico Pericial
1. **Os 20 maiores posts do X já haviam sido coletados:**
   - Mais cedo, o usuário já havia executado uma rodada completa de coleta onde os **20 maiores posts do X** foram processados com 100% de sucesso, somando **979 comentários coletados** no Top 20 e **1.612 comentários no total**. Todos estavam gravados com status `done`.
   - O botão principal operava em `mode="pending"` (apenas posts pendentes). Ao clicar em "20 maiores", o sistema descartou os 124 posts do X já concluídos e pegou os 20 maiores **dentre os pendentes restantes** (que eram posts menores, de apenas 2 comentários). Isso causou a impressão visual de que o sistema não estava puxando os maiores.
2. **Bug Crítico no Scraper do X para Posts em Threads (`backend/scrapers/comments.py`):**
   - Na função `_x_collect`, a linha original:
     `if not tweet_id or tweet_id == focal_id or str(legacy.get("conversation_id_str") or "") != focal_id:`
     exigia que o `conversation_id_str` fosse idêntico ao `focal_id`.
   - Porém, no Twitter/X, quando o post coletado na busca é **ele próprio uma resposta a outro tweet (51% dos posts da base)**, o `conversation_id_str` aponta para o tweet raiz da conversa, e não para o post em análise.
   - Isso descartava 100% dos comentários legítimos de posts que fossem respostas, marcando-os erroneamente com status `empty` (0 comentários).

### 3.2. Soluções de Engenharia Aplicadas
1. **Resolução de Árvore no Scraper do X (`backend/scrapers/comments.py`):**
   - Implementado conjunto dinâmico `accepted_ids = {focal_id}` e suporte tanto a `in_reply_to_status_id_str` quanto a `in_reply_to_status_id` (inteiro).
   - Suporte a respostas que chegam fora de ordem hierárquica e herança de sub-réplicas aninhadas.
2. **Balanceamento de Redes e Preservação de Métricas em `select_posts` (`backend/comments_service.py`):**
   - Normalização de nomes de redes via `target_nets = {network_key(n) for n in networks}`.
   - Ordenação resiliente usando `metric = max(parse_numeric_metric(p.comments), int(p.comments_collected or 0))`, garantindo que posts já coletados não percam sua posição no ranking durante uma recoleta geral (`mode="all"`).
   - Distribuição equilibrada entre redes quando `networks=None` (Todas as redes), impedindo que o Instagram monopolize todos os slots globais.
3. **UX Adaptativa Clara no Frontend (`frontend/app.js`):**
   - O seletor agora diferencia claramente entre `${tier} maiores pendentes` (quando `tier <= eligible`) e `${tier} maiores (recoleta da base)` (quando o usuário deseja reprocessar o Top N da base inteira).
   - O botão de ação e confirmações adaptam o texto para `Coletar pendentes` ou `Recoletar as X maiores` dependendo do contexto.

---

## 4. CHECKLIST PARA DESENVOLVIMENTOS FUTUROS
1. **Nunca quebrar a concorrência:** Playwright deve sempre rodar síncrono dentro de `asyncio.to_thread`.
2. **Respeitar o isolamento de sessões:** Não sobrescrever `sessao_{rede}.json` a menos que contenha cookies válidos de autenticação.
3. **Persistência atômica:** Nunca descartar dados de comentários ou posts já salvos em caso de cancelamento cooperativo ou falhas de rede.
4. **Fórmulas do Excel:** Ao gerar arquivos `.xlsx` executivos, preservar a integridade das fórmulas dinâmicas (`openpyxl`) e a sanitização de strings para evitar formula injection.

---

## 5. MÓDULO: AUDITORIA, HARDENING E INTEGRAÇÃO MULTIMÍDIA ZERO TOKEN (DOMINAÇÃO IA & EBM QUINTTO)
**Data de entrega:** Outubro de 2026  
**Demanda do usuário:** Implementação integral dos 3 grandes tópicos da auditoria RASP sob as normas do Domination IA e Template Universal IA (Zero Token AI pago, sem emojis na interface/Excel, sem ícones de varinha/sparkles, tipografia editorial Plus Jakarta Sans + Newsreader + JetBrains Mono, paleta Alabaster/Obsidian):
1. **Áudio e Transcrição Fonética Local (Zero Token):**
   - Transcrição fonética via `faster-whisper` (`large-v3-turbo`, CPU int8, 4 threads, VAD filter) com fallback seguro para `base`.
   - Pre-flight determinístico com `ffprobe` (`tem_audio`) antes de carregar o modelo em memória.
   - Filtro anti-alucinação por regex (`ALUCINACOES`) e probabilidade de silêncio (`no_speech_prob` e logprob).
   - Botão de cópia seguro no modal do frontend imune a quebras de linha e caracteres especiais (`copyTranscription`).
2. **Vídeo, Imagem e Varredura Visual Rápida (Zero Token):**
   - Folha de Contato 4x4 (Contact Sheet) gerada em FFmpeg com carimbo de tempo embutido (`pts:hms`).
   - Detecção de cortes de cena via FFmpeg (`scene > 0.08`) para capturar pontos centrais e quadros originais.
   - Download híbrido de mídias (`yt-dlp` como primeira linha, com fallback para sessão logada Playwright interceptando manifesto DASH/BaseURL e requisições `.mp4`).
   - Download leve de imagens de carrosséis via HTTP direto, com extração de `accessibility_caption` (alt text).
   - Galeria interativa de imagens de carrossel no modal multimídia e indicador de mídia na tabela de publicações.
   - Desduplicação temporal de linhas de texto em vídeo (`ler_ocr.py`).
3. **Coleta Leve, Inteligência de Métricas, UI/UX Anti-Vibe e Excel Executivo:**
   - Consulta em lote rápida autenticada na API interna do Instagram com guardrail preventivo contra paredes de login e rate limits (400, 401, 403, 429, checkpoint_required).
   - Higienização e taxonomia estrita EBM Quintto (`sanitizar_metricas_ebm`): rejeição de preenchimentos fixos legados `(1000, 50)`, estimativas sintéticas `views = likes * 15` e overlays corrompidos `views == likes`, normalizando `views = 0` para ausente (`None`).
   - Resiliência matemática no `build_dashboard` impedindo `TypeError` em agregação com `views` nulos.
   - Sanitização XSS estrita de SVGs de marcas (`brand_logo_service.py`), bloqueando tags perigosas, scripts, manipuladores de evento (`onload`), `href`/`xlink:href` externos e declarações DTD/ENTITY.
   - Aba dedicada `Transcrições & Mídias` no Excel gerado (`build_executive_workbook`), com links automáticos e sem emojis.
   - Interface ajustada com tipografia Plus Jakarta Sans, Newsreader e JetBrains Mono, paleta Alabaster/Obsidian com acentos Cobalto e Terracota, 0 emojis e 0 ícones de estrelinha/varinha mágica.

---

## 6. MÓDULO: REFINAMENTO DE UI/UX, CORREÇÃO ESTRUTURAL DO DOM E COMPACTAÇÃO DO DASHBOARD
**Data de entrega:** Outubro de 2026  
**Demanda do usuário:** Eliminação de títulos em caixa alta, correção da seleção visual de redes sociais, correção da navegação das abas Agendamentos e Marcas, remoção de elementos visuais redundantes e reestruturação do Dashboard com largura balanceada e agrupamento de cartões:
1. **Correção Estrutural da Árvore do DOM (`frontend/index.html`):**
   - Identificado e corrigido desbalanceamento de fechamento de tags `<div>` em `#commentsModal`. A ausência da tag de fechamento fazia o `#mediaModal` ser aninhado indevidamente e consumia o fechamento da aba `#tab-dashboard`.
   - Com a árvore do DOM corrigida, `#tab-schedule` e `#tab-brands` deixaram de ser filhas de `#tab-dashboard`, tornando-se nós irmãos diretos no `<main>`. A alternância entre abas via `switchTab` voltou a funcionar sem que `display: none` do dashboard oculte as demais telas.
   - Removida tag de fechamento órfã residual `</div>` após `</main>`.
   - Validação de integridade do DOM automatizada via parser: 0 tags pendentes e 0 erros de emparelhamento.
2. **Eliminação de Caixa Alta (All-Caps):**
   - Removidas 100% das classes `uppercase`, `tracking-wider` e regras CSS de `text-transform: uppercase` tanto em `frontend/index.html` quanto em `frontend/app.js`.
3. **Refatoração dos Seletores de Rede Social:**
   - Eliminadas classes inline do Tailwind fixas no primeiro item do `#directNetworkSelector` que conflitavam com a função de troca de rede.
   - Estilização de seleção padronizada via pseudo-classe CSS nativa `:checked + .direct-net-card`, com ring sutil de 1px, tint de fundo suave e ícone de confirmação (`.check-icon`) no canto superior direito para ambos os temas (claro e escuro).
   - Função `updateDirectNetworkSelection` simplificada para manipular unicamente `radio.checked = true`, sem colisão de classes de cores legadas (como classes `indigo` residuais).
4. **Limpeza Visual do Cabeçalho de Post Específico:**
   - Removida a pílula/badge redundante `Link Direto` com ícone de alvo e fonte monoespaçada que quebrava linha em telas menores, uniformizando o cabeçalho com o padrão limpo de todas as outras abas do sistema.
5. **Reestruturação e Compactação do Dashboard (Opção A):**
   - Contêiner de `#tab-dashboard` reduzido de `max-w-7xl` (1280px) para `max-w-6xl` (1152px), garantindo respiro lateral equilibrado e evitando que os cartões encostem nas bordas da tela.
   - Emparelhamento em grade de duas colunas (`lg:grid-cols-12`):
     - Linha 1: Linha do tempo (7 colunas) + Top Autores (5 colunas com lista rolável compacta), eliminando o card de autores que ocupava 100% da tela sozinho.
     - Linha 2: Nuvem de termos (6 colunas) + Módulo de coleta de comentários (6 colunas).
   - Redução de alturas úteis e preenchimentos:
     - Altura dos gráficos de barras e linha do tempo reduzida para 185px (era 220px/230px).
     - Gráfico de rosca de volume reduzido para 145px.
     - Nuvem de palavras ajustada para 185px tanto no contêiner HTML quanto no cálculo do canvas em `frontend/app.js`.
     - Cartões de KPI com padding compacto (10px 14px) e números principais em 22px (eram 26px).
     - Padding geral dos cards reduzido de `p-5` para `p-4` / `p-3.5`.
6. **Validação de Testes:**
   - Suíte backend com 76 testes unitários executada com sucesso (`OK`).
   - Validação de sintaxe JS (`node -c frontend/app.js`) sem erros.
   - Incremento do parâmetro de controle de versão dos scripts (`app.js?v=12`).

---

## 7. MÓDULO: CORREÇÃO DO BOTÃO DE EXTRAÇÃO DIRETA, SLIDER DE COMENTÁRIOS E ESTÚDIO DE NUVEM DE PALAVRAS (WORDART LOCAL)
**Data de entrega:** Outubro de 2026  
**Demanda do usuário:** Correção do clique inoperante no botão "Extrair Publicações" na aba de link direto, alinhamento visual do controle de limite de comentários com o padrão da primeira página, e implementação do Estúdio de Nuvem de Palavras 100% local (Zero Token, funcionalidade inspirada no WordArt.com com tipografia, paletas e formatos customizados):
1. **Correção do Botão "Extrair Publicações" e Normalização de Links (`frontend/index.html` e `frontend/app.js`):**
   - Implementada a função determinística `extractValidUrls`: aceita links colados sem protocolo (ex.: `instagram.com/p/...` ou `tiktok.com/@...`), prefixando `https://` automaticamente e reformatando o campo de texto.
   - Adicionado tratamento visual imediato quando o campo está vazio ou inválido: foco automático, realce temporário com borda e ring em tom de alerta (`ring-rose-500`), e feedback claro.
   - Vinculação de `onclick="handleDirectPostSubmit(event)"` diretamente ao botão `#btnDirectScrape`, garantindo resposta imediata sem dependência exclusiva do evento de submit do formulário.
   - Contador `#directUrlsCountBadge` sincronizado dinamicamente via `updateDirectUrlsCount`, exibindo a contagem correta mesmo para URLs digitadas sem protocolo.
2. **Padronização do Slider de Comentários em Post Específico:**
   - Substituído o `<input type="number">` solto por slider estilizado idêntico ao da primeira página (`#tab-extract`): barra de range com acento `#1D4ED8` e badge numérico `#directLimitValue` em fonte monoespaçada.
   - Integração completa com o botão de limpar formulário (`clearDirectPostForm`), restaurando o valor padrão de 100 comentários.
3. **Estúdio de Nuvem de Palavras (100% Local, Zero Token):**
   - Modal `#wordCloudStudioModal` estruturado em duas colunas: painel esquerdo com abas de configuração e painel direito com pré-visualização ao vivo sobre fundo xadrez (transparência real) e barra de exportação.
   - **Aba Palavras:** Tabela editável de termos com ativação/desativação individual por checkbox, edição de texto e frequência, exclusão, inserção manual e botão de filtro rápido de stopwords em português (`cleanStudioStopwords`).
   - **Aba Formato (Silhuetas):** Máscaras geométricas nativas via Canvas com teste de contenção de caixa: 16:9 Slide Deck, 1:1 Card Quadrado, Círculo/Globo, Balão de Diálogo (Social Listening), Coração e Nuvem Orgânica, além de opção para inversão da máscara.
   - **Aba Ângulos e Tipografia:** Modos de rotação Horizontal (0°), Misto (0° e 90°), Cruzado (0°, 45° e 90°) e Livre (-45°, 0° e 45°); seleção de fontes executivas (Plus Jakarta Sans, Newsreader, Montserrat, Inter, JetBrains Mono) e controle de peso e padding.
   - **Aba Cores:** Paletas institucionais predefinidas (Cobalto Executivo, Corporativo Slate, Sunset/Calor, Floresta/Sustentabilidade e Monocromático) e modos de fundo (Transparente, Claro e Escuro).
   - **Exportação e Sincronização:** Botão "Aplicar ao Dashboard" (propaga os parâmetros e renderiza a nuvem da tela inicial na forma e cores selecionadas), cópia direta em PNG transparente para o clipboard, cópia formatada para WhatsApp e download em resolução Ultra HD 3x.
4. **Validação de Integridade:**
   - Parser de HTML: 0 tags pendentes e balanceamento perfeito da árvore do DOM.
   - Validação de sintaxe JS com Node.js: 0 erros.
   - Suíte de 76 testes backend executada com sucesso.
   - Atualização do cache-buster para `app.js?v=13`.

### 10/10/2026 - Revisão Global de Alinhamento e Centralização de Controles (Checkboxes, Radios, Ícones e Paleta EBM)
1. **Eliminação da Descentralização do Checkmark ("Vezinho")**:
   - Causa raiz: o CSS anterior utilizava pseudo-elemento `::before` desenhado com bordas `border-left` + `border-bottom` rotacionadas em `-45deg` com translação manual arbitrária. A rotação de retângulos assimétricos em telas de alta densidade/subpixels causava deslocamento geométrico perceptível para o topo e para a esquerda.
   - Solução definitiva: substituído o desenho por SVG embutido via `background-image` com viewBox `0 0 16 16`, traço `M3.5 8.5l3 3 6-6`, centralização absoluta `background-position: center; background-size: 80% 80%; background-repeat: no-repeat;` e `display: inline-flex; align-items: center; justify-content: center;`.
   - Radio buttons igualmente convertidos para SVG de círculo com centro analítico exato `cx="8" cy="8" r="4"` em viewBox `0 0 16 16`.
2. **Revisão e Correção dos Controles e Rótulos na Interface**:
   - `input[type="range"]`: ajustado alinhamento do cursor (thumb) com `margin-top: -6px` no WebKit e regra para Firefox, garantindo centralização exata sobre a trilha de 6px.
   - Opções multimídia em Extração Geral (`#tab-extract`) e Post Específico (`#tab-direct-link`): ícones padronizados com `w-4 text-center` (16px fixos) e contêineres com `flex items-center gap-2.5`, alinhando os textos perfeitamente em linha reta entre colunas.
   - Filtro de comentários do Dashboard (`.dash .rp-check input`): removido o forçamento de `14px x 14px` que espremia o checkbox e deformava o desenho interno.
   - Radios de modo de busca (`search_type` e `sch_search_type`): removidas as classes `h-4 w-4` conflitantes e substituído `span.ml-2` por `inline-flex items-center gap-2 select-none`.
   - Checkboxes de redes sociais no Agendador (`#schNetworks`): ícones de marcas padronizados com `w-4 text-center` e rótulos com `select-none`.
   - Checkbox de inverter máscara no Estúdio de Palavras (`#studioInvertShape`): removido `w-4 h-4`, padronizado com `text-[#1D4ED8] rounded-sm`.
   - Tabela de termos do Estúdio de Palavras (`toggleStudioWord`): removido `w-3.5 h-3.5` e adicionado `align-middle` na célula.
3. **Erradicação de Resquícios da Família Indigo e Unificação Cobalto EBM**:
   - Todas as 22 ocorrências residuais de `indigo-*` em `index.html` e `app.js` (botões de enriquecimento, badges de redes e termos, modais de mídia, agendamentos, marcas e histórico de busca) foram unificadas para a paleta institucional Azul Cobalto EBM (`#1D4ED8` no tema claro e `#6A98F2` no tema escuro).
4. **Isolamento de Inputs Utilitários e Blindagem contra Conflitos de sr-only**:
   - Causa raiz do vazamento visual nos cards de rede social: o seletor CSS genérico `input[type="checkbox"]` aplicava `display: inline-flex; position: relative; width: 1.125rem; height: 1.125rem;` a todos os inputs da página, sobrepondo as propriedades da classe utilitária `.sr-only` do Tailwind nos inputs das redes sociais (`name="network"`) e do seletor direto (`name="direct_network"`). Isso fazia com que os checkboxes e rádios invisíveis passassem a ser renderizados como caixas físicas no fluxo do HTML, flutuando acima dos cartões.
   - Solução: escopo restrito com pseudo-classe de negação `input[type="checkbox"]:not(.sr-only)` e `input[type="radio"]:not(.sr-only)`, além de bloco CSS explícito com `!important` para `input.sr-only` mantendo dimensões de 1px, `clip: rect(0,0,0,0)`, `opacity: 0` e `pointer-events: none`.
5. **Verificação Estrutural, Visual e Testes**:
   - Captura visual automatizada via Playwright em modo claro e escuro: verificação de `networks_after_fix.png` (cards limpos sem caixas flutuantes), `multimedia_checked_dark.png` (vezinho centrado), `direct_tab_verified.png`, `schedule_tab_verified.png` e `studio_modal_full.png`.
   - `validate_tags.py`: 0 tags HTML pendentes, DOM perfeitamente balanceado.
   - `node -c frontend/app.js`: sintaxe validada sem erros.
   - Suíte de 76 testes unitários do backend aprovada com 100% de sucesso.
   - Cache-buster atualizado para `app.js?v=16`.


---

## 8. MÓDULO: MIGRAÇÃO PARA O TEMA ESCURO NEUTRO ANTIGRAVITY DARK & PURIFICAÇÃO ANTI-VIBE
**Data de entrega:** 10 de outubro de 2026  
**Demanda do usuário:** Eliminação completa do tema escuro azul marinho/navy/slate em prol do cinza escuro neutro sólido padrão Antigravity Dark (`#161618`), sem nenhum tom azulado residual em fundos, cartões, modais ou bordas, e alinhamento às diretrizes de design do Template Universal IA:
1. **Paleta Neutra Sólida Aplicada:**
   - Fundo base profundo (`body`, `#tab-*`): `#161618` (medido no Playwright como `rgb(22, 22, 24)`).
   - Superfície de cartões, modais e containers (`.bg-white`, `.dash .rp-card`): `#1E1E22` (`rgb(30, 30, 34)`).
   - Planos secundários, tabelas e cabeçalhos de grid: `#26262B`.
   - Bordas e divisores: `#323238`.
   - Textos no escuro: `#F4F4F6` (principal) e `#A1A1AA` (secundário).
   - Acento institucional Cobalto EBM: `#1D4ED8` (claro) e `#60A5FA` (escuro).
   - Backdrops de modais: purificados de `bg-slate-900` para `bg-black/75` neutro com desfoque suave, eliminando qualquer névoa azulada em segundo plano.
2. **Tipografia e Diretrizes Anti-Vibe:**
   - Tipografia principal: `Plus Jakarta Sans` configurada no Tailwind e importada com pesos 400 a 800.
   - Tipografia para métricas tabulares e mono: `JetBrains Mono` com `font-variant-numeric: tabular-nums`.
   - Tipografia para conteúdo editorial: `Newsreader`.
   - Raios de curvatura delimitados rigorosamente entre 4px e 8px (`rounded-md` e `rounded-lg`), erradicando `rounded-2xl` e `rounded-3xl`.
   - Sombras pesadas substituídas por `shadow-sm` e delimitação nítida por bordas neutras.
   - Remoção de ícones mágicos e gradientes arco-íris (badge do Instagram unificado em `#E1306C` sólido).

---

## 9. MÓDULO: REFORMULAÇÃO PROFUNDA DO ESTÚDIO DE NUVEM DE PALAVRAS (WORDART EXECUTIVO LOCAL)
**Data de entrega:** 10 de outubro de 2026  
**Demanda do usuário:** Transformação do Estúdio de Nuvem de Palavras em um componente profundo, robusto e amigável ao usuário (Zero Token de IA, inspirado no WordArt.com com presets, tabela reativa, importação em massa, pan e zoom, e exportação executiva):
1. **Correção de Falhas Críticas Anteriores:**
   - Contorno de silhueta fantasma: implementada a rotina vetorial `drawStudioShapeOutline` com traçado tracejado no canvas.
   - Dessincronização de presets: criada a sincronização bidirecional `syncStudioControlsFromState`, impedindo que valores do DOM sobrescrevam os presets escolhidos.
   - Status dinâmico de termos: tabela reativa vinculada ao `placedSet` do algoritmo de posicionamento, indicando com precisão o status `Visível`, `Omitido` ou `Inativo`.
2. **Navegação Vetorial com Pan & Zoom:**
   - Suporte a arrasto livre do canvas com o mouse (pan) diferenciado do clique de termo por limiar de deslocamento (`distance > 6px`).
   - Zoom de 50% a 300% por botões ou roda do mouse com atalhos de teclado (`+`, `-`, `0`, `Fit` e reset).
   - Alternador de contraste rápido de fundo no canvas de edição.
3. **Presets Executivos Prontos com 1 Clique:**
   - Apresentação Executiva 16:9, Card Social & WhatsApp 1:1, Social Listening & Depoimentos (Balão), Top Destaques & Premiações (Estrela) e Editorial Nobre (Serif).
4. **Tabela Gerencial de Termos e Importador em Massa:**
   - Tabela com 6 colunas, medalhas de ranking (#1 a #3), edição inline com debounce, steppers de incremento rápido (-5 / +5) e barra proporcional.
   - Filtros por digitação e seleção rápida (Top 10 a 50, Todas, Inverter e Excluir inativas).
   - Importador em massa (Bulk Import) com parser multi-formato para TSV (Excel), CSV, emojis, marcadores de lista e pares `Termo: Peso`.
5. **Motor Geométrico de 11 Silhuetas e Algoritmo de 3 Etapas:**
   - 11 geometrias vetoriais: Slide Deck, Card Quadrado, Story, Círculo, Balão de Diálogo, Coração, Nuvem Orgânica, Estrela, Troféu, Escudo de Governança e Hexágono.
   - Algoritmo de espiral com redução progressiva de escala hierárquica (1.0x, 0.8x, 0.64x), alcançando 100% de termos posicionados mesmo em formas recortadas.
6. **Exportações Executivas em Alta Resolução:**
   - Suporte a Ultra HD (3x) e 4K nativo.
   - PNG transparente para lâminas e cópia de dados tabulares (TSV para planilhas).
   - Renderizador dedicado de Card WhatsApp em 1200x1200 com Alabastro Editorial ou Neutro Escuro, metadados estatísticos e fallback seguro via blob.
7. **Resolução de Erro de Renderização no Dashboard:**
   - Corrigido `TypeError` no `renderCommentsCard` envolvendo `btnCommentsStart` desprovido de tag `<span>`, blindando a manipulação do texto de ação contra nós nulos.
8. **Validação Completa:**
   - Suíte com 76 testes do backend executada com 100% de aprovação.
   - 0 erros no console do navegador inspecionados via Playwright.
   - Cache-buster atualizado para `app.js?v=21`.

### 11 de outubro de 2026: Remoção de Marcas de IA e Blindagem Anti-Vazamento de Bastidor
- **Demanda do usuário:** Eliminação completa de textos onde o sistema se explica, canta vantagem ou expõe regras de prompt/desenvolvimento na interface, relatórios e entregas.
- **Modificações aplicadas:**
  1. `frontend/index.html`:
     - "Inteligência multimídia (zero token IA)" substituído por "Processamento de mídia".
     - "Transcrição Local (Whisper Zero Token)" e "Transcrição Whisper (Zero Token)" substituídos por "Transcrição de áudio".
     - Removido selo de autocertificação "Extração Segura Ativada".
     - "Zero Tokens IA Pagos • 100% Processamento Local (Whisper & FFmpeg)" simplificado para "Processamento local".
     - "WordArt Executivo" removido e subtítulo ajustado de "Termos, silhuetas, tipografia nobre, paletas corporativas e exportações em Ultra HD • Zero Token IA" para "Termos, silhuetas, tipografia, paletas e exportação em alta resolução".
     - "Editorial Nobre (Livro/Impresso)" ajustado para "Serifado (Editorial)".
     - "Paletas Institucionais EBM & Anti-Vibe-Code" e "Cores nobres sem gradientes neon clichês" ajustado para "Paletas de Cores" sem frases de prompt como legenda.
     - "Bicolor nobre institucional" -> "Bicolor azul e dourado"; "Monocromático Nobre" -> "Monocromático".
     - "Ultra HD (3x)" e "4K (4x)" substituídos por "Alta Resolução (3x)" e "Escala 4x".
  2. `frontend/app.js`:
     - Preset `editorial_serif` renomeado de "Editorial Nobre Serifado" para "Serifado Editorial".
     - Removido carimbo gravado em imagem exportada (`Processamento 100% Local • Zero Token IA • EBM Quintto`), substituído por `EBM Quintto Comunicação`.
     - Removida justificativa de tokens do diálogo de confirmação de enriquecimento.
  3. `backend/excel_builder.py` e `backend/tests/test_multimedia.py`:
     - Cabeçalho de coluna no Excel alterado de "Transcrição Fonética Local (Zero Token)" para "Transcrição de Áudio".
  4. `backend/jobs.py`:
     - Log de progresso limpo de "(zero token)".
- **Validação:** 76 testes de backend aprovados; script de integridade DOM passou com 0 erros; `protecao.py conferir` confirmou alteração restrita aos arquivos modificados.

## 12/10/2026: logo v4 (placa descascando)

- Rodadas 1 a 3 recusadas (R cortado com ciano; opções A/B/C; 1/2/3; pilha isométrica de 3 lâminas, que repete o logo
  da Buffer e some em 16px). Rodada 4 gerada pelo Antigravity (Pro) a partir do `PEDIDO.md`: A lâmina de frente
  (ícone de documento), B placa única descascando, C duas lâminas. Ele escolheu B.
- `build_brand_assets.py` reescrito: entrada é `marca/fonte/rasp_simbolo_chroma.png` (magenta), saída igual à da v3
  nos mesmos nomes de arquivo. `?v=6` subiu para `?v=7` em `frontend/index.html`. Backup da v3 em `marca/_v3_ondas/`.


- 12/10/2026, mais tarde: ícone sem fundo (pedido do Lukyam). `icone()` em `build_brand_assets.py` devolve só a placa a 98% da largura; .ico, favicon e `rasp_icone_1024.png` ficaram transparentes. Atalho passou para `rasp_icon_v5.ico`; `rasp_icon_v4.ico` apagado. `?v=8` no index.html.

## 27/10/2026: perfil do Instagram com período rola até o início

- **Problema medido:** extração de perfil com data de início e fim voltava 0 posts quando o fim não era hoje
  (perfil de teste, 01 a 30/09/2026: 0 posts). Os posts mais novos que o fim eram descartados pelo filtro de datas e contavam
  como rolagem parada; 3 rolagens assim encerravam a busca. Havia também o teto de 25 rolagens (cerca de 300 posts) e
  o tempo máximo de 900 s, curtos para um ano de perfil ativo.
- **Mudança** (`backend/scrapers/instagram_scraper.py`, só quando `search_type == "profile"` e há `start_date`): post
  mais novo que o fim não conta como rolagem parada; a busca termina ao ver 4 posts não fixados anteriores ao início
  (até 3 podem estar fixados no topo); teto de 400 rolagens; tempo máximo de pelo menos 2.400 s. Busca por palavra e
  perfil sem data seguem como antes. A API não mudou.
- **Conferido:** 76 testes do backend e `test_integrity.py` passando; o mesmo pedido trouxe 31 posts, de 01/09 14:03
  a 30/09 15:15, todos do perfil pedido, com o log "período coberto". Foto antes da mudança:
  `C:\Users\_EBMQUINTTO_\SocialScraper_cofre\20261027_125229`.
- Commit e push em 27/10/2026, junto com as duas mudanças abaixo; o EBM Hub recebe pelo `atualizar.bat`.

- 27/10/2026, mais tarde: **sem teto** (pedido do Lukyam: "tire esse teto, eu nao quero limitacao, sério").
  `config.py`: `MAX_LIMIT_PER_NETWORK` de 1.000 para 1.000.000 (a API aceita esse limite em `/api/scrape`).
  `instagram_scraper.py`: perfil com data de início sem teto de rolagens e sem tempo máximo (para ao passar do início
  do período ou quando o perfil acaba); visualizações buscadas para todos os reels coletados, não só os 400 primeiros
  (vale também para a busca por palavra). Busca por palavra e as outras redes seguem com o tempo máximo de 900 s de
  `common.py`. A interface continua com o controle até 1.000 ("1.000+ (Sem Limite)"), que agora é de fato 1.000:
  para pedir mais, só pela API. 76 testes e `test_integrity.py` passando; API religada e conferida (limite máximo
  1.000.000 no `openapi.json`, Instagram logado).

- 27/10/2026, fim da tarde: **seguidores no perfil do Instagram** (pedido do Lukyam: "ajusta o RASP para ler os
  seguidores quando abre o perfil logado"). `instagram_scraper.py`: ao abrir um perfil, procura seguidores, seguindo e
  posts nas respostas que a página já recebe (número exato) e, se não achar, no link "seguidores" do cabeçalho (title
  exato ou texto arredondado). Escreve no log do job "Instagram: seguidores de @x: N (fonte: ...)" e guarda em
  `ctx.profile_stats`. A API e as colunas do Excel não mudaram. Conferido: 76 testes e `test_integrity.py` passando;
  54 perfis lidos, todos pela resposta da página; num perfil com série externa, o número bateu com a tendência dela.
