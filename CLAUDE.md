# RASP (SocialScraper)

Coletor local de redes sociais do Lukyam (X, TikTok, Instagram, YouTube, Facebook), feito para o trabalho na EBM
Quintto: coleta posts e comentários com as sessões logadas guardadas aqui e exporta Excel e PDF. Interface em
`http://127.0.0.1:8080`; API em `http://127.0.0.1:8000`. Python (FastAPI, Playwright, SQLite), front em HTML e JS.

**Quase todo projeto dele depende daqui**: PMF, RioMar, monitoramentos da EBM, EBM Report Guide (`modules\rasp.py`),
central Dominação IA (`scripts\metricas_via_rasp.py`), Mayrlla e o EBM Hub (`Desktop\EBM Hub`, desde 14/10/2026, que
serve esta interface na porta 8090 com as ferramentas do Dashboard EBM a mais). Mudança na API quebra os outros.

## Antes de qualquer coisa

- As regras gerais do Lukyam estão em `~/.claude/CLAUDE.md` e valem aqui. Não copiar para este arquivo.
- Guias que se aplicam, em `C:\Users\_EBMQUINTTO_\Desktop\Eu\Desenvolvimento_e_Codigos\Template_Universal_IA\guias\`:
  `codigo_e_apps.md`, `coleta_de_dados.md`.
- `README.md` tem a arquitetura, as rotas e os 4 princípios que não podem ser quebrados (Playwright síncrono em
  `asyncio.to_thread`, WebSocket thread-safe, extração em lote, sessões sincronizadas entre `_dir` e `.json`).
- Histórico de decisões e mudanças: `HISTORICO_DESENVOLVIMENTO.md` (faz o papel do `HISTORICO.md` do modelo; o novo
  vai no fim, com data). Agente executor (Antigravity): `AGENTS.md`.

## Kit de projeto (`_kit/`, desde 12/10/2026)

Cópia do `Kit_Projeto_IA` (pedido do Lukyam, 12/10: "garanta também que o rasp, o dashboard ebm e o ebm guide
report tenham esse kit dentro dos projeto"). As regras de trabalho continuam no global; daqui vale o que ele não
cobre:

- **Ganchos** (`.claude/settings.json`, rodam sozinhos, sem gastar token): `_kit/scripts/guarda.py` pede a
  confirmação do Lukyam antes de apagar, mover ou sobrescrever o que a linha "Insubstituível" desta pasta lista,
  antes de apagar ou mover este arquivo, o `AGENTS.md`, o `HISTORICO.md`, `_kit/` e `.claude/`, e antes de apagar
  em massa. `_kit/scripts/mudancas.py` anota no fim do `HISTORICO.md` (seção "Registro automático") o que cada
  conversa mudou e avisa o que mudou entre uma conversa e outra.
- **Antes de criar** (tela, peça, texto, plano): abrir `_kit/central/INDICE.md` e ler só o verbete da tarefa. É
  método de criador e entra como hipótese; em conflito com regra daqui ou do global, vale a regra.
- **Antes de trabalho grande:** plano curto, critério de sucesso que se confere (a conta fecha, o teste passa, o
  arquivo abre) e foto da pasta (`python _kit/scripts/protecao.py fotografar`, rodado desta pasta).
- **Códigos de conversa:** `/premortem`, `/tradeoff`, `/blindspot`, `/unknown`, `/steelman`, `/invert`,
  `/secondorder`, `/sowhat`, `/benchmark`, `/confidence`, `/disagree`, `/baseline`, `/entregar`; `/medir` mostra o
  gasto por modelo. Definições em `_kit/codigos.md`.
- **Guias:** valem os do Template (caminho acima). `_kit/guias/` é a cópia sem nome pessoal, para quando o Template
  não abrir (outra máquina, sessão na nuvem). As auxiliares de `.claude/agents/` são as mesmas do global.
- **`_kit/` não se edita aqui.** Regra nova vai para o Template ou para o `Kit_Projeto_IA`; para atualizar o kit
  desta pasta, copiar de novo de lá.
- **Histórico:** o registro automático cria um `HISTORICO.md` nesta pasta; o histórico escrito à mão continua
  em `HISTORICO_DESENVOLVIMENTO.md`. O início de conversa levou 7,2 s na simulação de 12/10 (o retrato passa
  por 12.704 arquivos).

## Fontes e onde fica cada coisa

| O quê | Onde | Se perder |
|---|---|---|
| Sessões logadas | `backend\sessao_*_dir\` e `backend\sessao_*.json` (X, TikTok, Instagram, YouTube, Facebook) | ele loga de novo em cada rede; **nunca abrir, copiar ou listar o conteúdo** |
| Base de coletas | `backend\datapulse.db` (com `-wal` e `-shm`) e `backend\scraper.db` | insubstituível; há `datapulse.db.bak` e `.bak_lukyam` de 12/09/2026 |
| Arquivos baixados | `backend\downloads\`, `backend\media_store\` | refaz coletando de novo, se o post existir |
| Código | `backend\`, `frontend\` | GitHub público github.com/Lukyammm/rasp desde 15/10/2026 (esta pasta é o repositório); há também `_backup_antes_melhorias_2026-09-12\` e `_arquivo_legado\` |

- **Insubstituível (nunca apagar, nunca sobrescrever):** sessões, as duas bases, os backups e o legado:
  `backend/sessao_facebook_dir/`, `backend/sessao_instagram_dir/`, `backend/sessao_tiktok_dir/`, `backend/sessao_x_dir/`,
  `backend/sessao_youtube_dir/`, `backend/sessao_instagram.json`, `backend/sessao_tiktok.json`, `backend/sessao_x.json`,
  `backend/sessao_youtube.json`, `backend/datapulse.db`, `backend/scraper.db`, `backend/datapulse.db.bak`,
  `backend/datapulse.db.bak_lukyam`, `_backup_antes_melhorias_2026-09-12/`, `_arquivo_legado/`.
- **Derivado:** `backend\logs\`, Excel e PDF exportados.
- A pasta mora no `scratch` do Antigravity. Só o código sobe para o GitHub: o `.gitignore` deixa de fora sessões,
  bases (`*.db`, backups), `RASP Planilhas\`, `media_store\`, `downloads\`, `logs\`, `venv\` e `screenshots_studio\`.
  Antes de pôr arquivo novo no git, conferir que ele não traz sessão, base ou planilha. Antes de mexer em código:
  `python "C:\Users\_EBMQUINTTO_\Desktop\Eu\Desenvolvimento_e_Codigos\Template_Universal_IA\scripts\protecao.py" fotografar "<esta pasta>"`.

## Regras deste projeto

- Sem análise de sentimento: foi tirada de propósito, a pedido dele. A nuvem de palavras é só frequência.
- Só leitura nas redes: nunca curtir, seguir, comentar ou publicar, nem em teste.
- A sessão e a cota do Instagram são uma só para todos os projetos: não rodar coleta de Instagram enquanto outra
  estiver rodando.
- Testes: `python -m unittest discover -s tests` dentro de `backend\`, e `test_integrity.py` na raiz.
- O EBM Hub lê o `frontend\index.html` e o `app.js` daqui na hora e procura neles: o botão `switchTab('tab-brands'`,
  o `#btnAccounts`, o `.marca`, o `<main>` e o `window.switchTab`. Mexeu em algum desses: rodar os testes do Hub
  (`venv\Scripts\python.exe -m unittest discover -s testes`, na pasta `Desktop\EBM Hub`).

## Onde parou

Atualizado em 2026-10-15. Esta seção tem no máximo 40 linhas: o que fechou vai para `HISTORICO_DESENVOLVIMENTO.md`.

- **Calendário (14/10/2026):** o estilo do flatpickr no `frontend/index.html` foi refeito (alinhamento, tamanhos,
  cobalto, sem vidro). Vale aqui e no EBM Hub, que lê esta página. Detalhes no `HISTORICO.md`.
- **EBM Hub (14/10/2026):** app novo em `Desktop\EBM Hub` (atalho `EBM Hub.lnk`) que serve a interface daqui na
  porta 8090 com as ferramentas do Dashboard EBM em duas abas a mais (Ferramentas, Arquivos). Nada do RASP foi
  copiado nem alterado no código; aqui só mudaram este arquivo e o `AGENTS.md` (aviso dos 5 pontos da interface de
  que o Hub depende). Conferido: as abas do RASP carregam de dentro do Hub com todas as chamadas à 8000 em 200
  (contas, agendamentos, marcas, histórico, dashboard); 14 testes do Hub passando. A API daqui foi ligada pelo
  `ligar_rasp.vbs` do Hub em 14/10 e ficou ligada. Detalhes e pendências no `CLAUDE.md` do Hub.

- **Kit de projeto (12/10/2026):** `_kit/` e `.claude/` copiados do `Kit_Projeto_IA` (81 arquivos, iguais
  byte a byte ao original). Ganchos testados por simulação: a guarda pediu confirmação para apagar `backend/sessao_instagram_dir/`
  e `_kit/`; o início de conversa levou 7,2 s. Ainda não rodaram numa conversa real.
- **Logo nova aplicada (12/10/2026):** placa cobalto em isométrico com a ponta descascando e o verso terracota
  (direção B da rodada 4, escolhida por ele com "b"). O símbolo é imagem gerada pelo Antigravity (modelo Pro) sobre
  magenta, em `marca/fonte/rasp_simbolo_chroma.png`; `build_brand_assets.py` (reescrito) tira o magenta e gera
  `marca/` (símbolo e ícone 2048px, lockups, apresentação, .ico de 16 a 256px), `frontend/logo.svg|png`,
  `favicon.png|ico` e `rasp_icon.ico` da raiz (o do atalho). Os SVG só embalam o PNG: não há vetor de verdade.
  `?v=8` em `frontend/index.html`. Conferido: fundo sem resto de magenta (0 pixels rosados na borda), cabeçalho
  e aba do RASP com a logo nova em 127.0.0.1:8080. Cópia em `Desktop\RASP logo nova\`. A v3 (barras) está em
  `marca/_v3_ondas/`; as opções descartadas em `marca/_opcoes_v4/`.
  O `PEDIDO.md` da raiz já foi executado (conversa do Antigravity `45beadf6`): pode ser apagado quando ele quiser.
  Ícone (.ico, favicon) sem fundo desde 12/10, a pedido dele: só a placa, sem o quadrado escuro. O atalho
  `Desktop\RASP.lnk` aponta para `rasp_icon_v5.ico` (nome novo a cada troca, por causa do cache do Windows; o
  gerador também grava esse arquivo). Conferido: cantos com transparência total no .ico em 16, 32 e 256px e no ícone que o Windows tira do atalho. **Falta:** ele confirmar na área de trabalho. Se um dia precisar de vetor (impressão grande), pedir ao Antigravity uma versão chapada e vetorizar.
- **Ponto atual:** última entrada do histórico é de 10/10/2026 ("Revisão Global de Alinhamento e Centralização de
  Controles"); código do backend com data de 09 e 10/10/2026.
- **Em curso fora desta conversa:** desconhecido; o Antigravity também trabalha nesta pasta.
- **Desconhecido:** se os testes passam hoje (não rodados nesta atualização).
- **GitHub (15/10/2026, pedido dele: "sobe a porra do rasp completo pro github"):** repositório público
  github.com/Lukyammm/rasp, commit `7964bee`, 194 arquivos (14,3 MB), conferidos no GitHub: nenhuma sessão, base,
  planilha ou chave. O `instalar.bat` do EBM Hub baixa este repositório para uma pasta `RASP` ao lado do Hub quando
  não acha o RASP, cria `backend\venv` e instala `backend\requirements.txt`; o `atualizar.bat` do Hub faz `git pull
  --ff-only` aqui (ou baixa o ZIP por cima, sem apagar nada) e só reinstala os pacotes se o `requirements.txt` mudou.
  Para outros computadores receberem uma mudança daqui, ela precisa de commit e push.

## Como refazer do zero

`pip install -r backend\requirements.txt`, Playwright com Chrome, e logar cada rede pelo botão Contas. As sessões
e as bases não se refazem.
