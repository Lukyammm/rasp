# RASP — Social Listening, Web Scraping & BI (EBM Quintto)

Plataforma local para coletar publicações de **X, TikTok, Instagram, YouTube e Facebook**, analisar engajamento
e exportar relatórios executivos em Excel e PDF.

## Como usar

| Ação | Como |
|---|---|
| Iniciar | Atalho **RASP** na área de trabalho (`iniciar_rasp_silencioso.vbs`) — abre `http://127.0.0.1:8080` |
| Parar | Atalho **Parar RASP** (`parar_rasp_silencioso.vbs`) |
| Conectar redes | Botão **Contas** → abre o Chrome com o perfil da rede → faça login e feche a janela |
| Logs do servidor | `backend/logs/rasp.log` (o servidor roda oculto) |

A interface também é servida pela própria API em `http://127.0.0.1:8000`.

## Arquitetura

```
backend/
  main.py              Rotas FastAPI (REST + WebSocket /ws/scrape/{client_id})
  jobs.py              Extrações em segundo plano: fila, logs por job, cancelamento, persistência e Excel
  analytics.py         Dashboard: KPIs, redes, nuvem de palavras, histórico
  comments_service.py  Comentários: seleção de posts pendentes, resumo por rede, listagem e linhas do Excel
  scheduler_service.py Agendamentos (APScheduler) persistidos e recarregados no início
  database.py          SQLAlchemy/SQLite (WAL): scraped_posts, scrape_runs, brands, schedules + migrações aditivas
  excel_builder.py     Planilha executiva: Dashboard, Share of Voice, Top Autores, Base de Posts
  pdf_generator.py     Relatório PDF executivo (ReportLab)
  top_words.py         Termos mais frequentes para a nuvem de palavras (o sistema não faz análise de sentimento)
  utils.py             Parser booleano seguro, métricas ("1,2 mil"), datas ("há 2 dias"), autores
  config.py            Caminhos, redes, cookies de autenticação, logging
  scrapers/
    base_scraper.py    Despachante: abre o navegador e chama o scraper da rede
    browser.py         Estratégia de sessões (json ↔ perfil), lock por rede, User-Agent do Chrome real
    common.py          ScrapeContext (limite, período, exclusões, progresso, cancelamento) e interceptação de rede
    x_scraper.py       GraphQL SearchTimeline/UserTweets
    tiktok_scraper.py  API api/search/item + complemento do DOM
    instagram_scraper.py GraphQL xdt_fbsearch (sem abrir modais) + fallback /media/{id}/info
    youtube_scraper.py ytInitialData + continuações youtubei/v1
    facebook_scraper.py DOM atômico (page.evaluate)
    comments.py        Coleta de comentários por rede, com novas tentativas, reinício do navegador e disjuntor
    login_manager.py   Status das contas (cookies válidos e não expirados)
    login_worker.py    Processo isolado da janela de login
  tests/               python -m unittest discover -s tests
frontend/
  index.html, app.js   Dashboard (Tailwind), editor booleano, logs ao vivo, filtros, agendamentos, marcas
```

### Princípios que não podem ser quebrados
1. **Playwright síncrono em `asyncio.to_thread`**, isolado do event loop do FastAPI.
2. **WebSocket thread-safe**: mensagens do scraper via `asyncio.run_coroutine_threadsafe`.
3. **Extração em lote**: nada de `page.locator().all()` com chamadas por elemento — usar interceptação de JSON
   da rede ou um único `page.evaluate` por rodada.
4. **Sessões sincronizadas** entre `sessao_{rede}_dir` (perfil real) e `sessao_{rede}.json` (storage_state).
   O `.json` só é renovado se ainda contiver os cookies de login.

## API (principais rotas)

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/scrape` | Inicia extração (retorna `job_id`/`run_id`; `wait: true` aguarda o fim) |
| GET | `/api/jobs/{job_id}` | Status, progresso e logs · `POST .../cancel` cancela |
| GET | `/api/dashboard?run_id=` | Dados analíticos da extração |
| POST | `/api/comments/scrape` | Coleta comentários dos posts de uma extração (`mode: pending \| all`, `post_ids`, `max_per_post`) |
| GET | `/api/comments/summary?run_id=` · `/api/comments?run_id=&post_id=&q=` | Resumo por rede e leitura dos comentários |
| GET/DELETE | `/api/history/runs[/{run_id}]` | Histórico de extrações |
| GET | `/api/export/excel?run_id=` · `/api/report/pdf?run_id=` | Relatórios |
| GET/POST/DELETE | `/api/brands` | Marcas e seus @ por rede |
| GET/POST/PATCH/DELETE | `/api/schedules` · `POST /api/schedules/{id}/run` | Agendamentos |
| GET | `/api/accounts` · `POST /api/accounts/{rede}/login` | Sessões das redes |
| GET | `/api/health` | Saúde do servidor |

## Busca booleana

`(tecnologia OR inovação) AND mercado NOT política`, `"frase exata"`, `-exclusão`, AND implícito entre termos.
- **X**: a consulta é convertida para a sintaxe nativa do X e os resultados são validados localmente.
- **TikTok, Instagram, YouTube, Facebook**: a consulta é expandida em variantes (`(a OR b) AND c` → `a c`, `b c`)
  e posts com termos excluídos (NOT) são descartados.

## Extração por Post Específico (Links Diretos)

Na aba superior **Post Específico**, é possível colar URLs diretas de publicações (Instagram, TikTok, X, YouTube ou Facebook) para raspar dados completos:
- **Detecção automática da rede** ou seleção direta pelo usuário.
- Suporte a lote de até 50 URLs simultâneas com contador dinâmico.
- Opção para raspar os comentários das publicações na mesma execução.
- Extração de métricas profundas (Autor, Legenda, Curtidas, Comentários, Views, Shares, Data ISO e Link direto).

## Comentários das Publicações

No Dashboard, o painel **Comentários das publicações** coleta os comentários dos posts da extração aberta
(ou de um post só, pelo selo na tabela). Tudo fica em `post_comments` e sai na aba **Comentários** do Excel.

### Filtros e Seleção Adaptativa
- **Seleção por Rede:** Coleta de comentários de todas as redes ou filtrada por uma rede específica (Instagram, TikTok, YouTube, X, Facebook) com indicação em tempo real de posts pendentes por rede.
- **Degraus Adaptativos de Quantidade:** O limite de posts se ajusta de forma inteligente ao volume real de publicações encontradas na extração:
  - Para volumes menores (ex.: 30 posts): oferece patamares como 10, 20 ou Todas (30).
  - Para volumes maiores (ex.: 3.000 posts): oferece patamares como 50, 100, 250, 500, 1.000, 2.000 ou Todas (3.000).
  - Opção **Personalizado...** para definir manualmente qualquer número exato de posts.
- **Ordenação Inteligente:** Os posts são priorizados pelos mais comentados e com maior engajamento (curtidas).

| Rede | Como coleta | Observação |
|---|---|---|
| YouTube | API `youtubei/v1/next` (continuações) | Não exige login; data relativa ("há 2 dias") |
| Instagram | API `/api/v1/media/{id}/comments/` | Exige sessão; comentários principais (sem respostas) |
| TikTok | API `/api/comment/list/`; fallback abre o painel | Comentários principais |
| X | GraphQL `TweetDetail` da página do post | Exige sessão; inclui respostas da conversa |
| Facebook | DOM, expandindo "Ver mais comentários" | Exige sessão; melhor esforço |

Tolerância a falhas: cada post é gravado ao terminar (cancelar ou reiniciar o servidor não perde nada e a próxima
coleta continua dos pendentes); falhas temporárias têm 3 tentativas; o navegador é reaberto se cair; 4 falhas
seguidas reiniciam o navegador e, após 2 reinícios, a rede é encerrada; sessão expirada marca os posts como
"login" sem visitar os demais; comentários nunca duplicam (`post_id + comment_id` único) e uma recoleta que falha
não apaga o que já foi salvo.

## Desenvolvimento

```bash
cd backend
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m unittest discover -s tests
venv\Scripts\python.exe -X utf8 -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
