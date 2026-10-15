# Histórico: SocialScraper

Memória permanente do projeto. Duas partes: decisões (por que algo é como é) e mudanças (o que foi feito e
quando). Serve para nenhuma conversa nova refazer decisão tomada nem perguntar de novo o que já foi respondido.
O mais novo fica em cima.

## Decisões

Formato: data, decisão, por quê, o que foi descartado, quem decidiu (com a frase, quando houver).

### [AAAA-MM-DD] [título curto]
- **Decisão:** [o que ficou valendo]
- **Por quê:** [o motivo, com número se houver]
- **Descartado:** [as outras opções e por que não]
- **Quem:** [usuário / chefe / cliente], [frase literal entre aspas]

## Mudanças

Formato: data, o que mudou, arquivos, como foi conferido. A lista de arquivos de cada conversa e a versão do
"Onde parou" já ficam no "Registro automático", no fim deste arquivo, escritas por script; aqui entra só o que
precisa de explicação: o que foi feito, por quê e como foi conferido.

- **[AAAA-MM-DD]** [o que foi feito]. Arquivos: `[caminho]`. Conferido: [como; ex.: *contagem bate com o bruto,
  1.524 linhas*].
- **[AAAA-MM-DD]** Apagado: `[caminho]`, porque [motivo]. (Todo apagamento fica registrado.)
- **2026-10-14** Calendário (flatpickr) refeito no `frontend/index.html`, a pedido do Lukyam pelo EBM Hub ("os
  elementos não são bem centralizados e os tamanhos não são bons"). Só o bloco de estilo do calendário mudou:
  setas e título no mesmo eixo (antes as setas ficavam 9 px acima e encostadas na borda), mês e ano com o mesmo
  tamanho e peso (15 px, antes 18,9 px com pesos 700 e 800 contra 13 px dos dias), fundo sólido no lugar do vidro
  com desfoque, dia escolhido em cobalto #1D4ED8 no lugar do roxo #4f46e5 com brilho, raio de 8 px, seletor de
  mês do tamanho do nome. Conferido num Chromium invisível: centro do título igual ao centro do calendário, colunas
  da semana e dos dias com o mesmo centro, claro e escuro. Testes do Hub passando (14). Foto antes da mudança:
  `SocialScraper_cofre\20261014_100430`.

## Registro automático

Escrito por `_kit/scripts/mudancas.py`, sem gastar token, no início de cada conversa: o que a conversa anterior mudou e, à parte, o que mudou entre conversas. Arquivos criados, alterados, movidos e sumidos, e a seção "Onde parou" do `CLAUDE.md` como ela ficou. O mais novo fica em cima. Decisão, com o porquê, vai para as seções acima.

<!-- novos registros entram abaixo desta linha -->

### 2026-10-14 10:10, entre conversas (desde 2026-10-14 09:54)

- Alterados (1): `frontend/index.html`

### 2026-10-14 09:49, entre conversas (desde 2026-10-14 09:30)

- Alterados (4): `AGENTS.md`, `CLAUDE.md`, `backend/datapulse.db-shm`, `backend/logs/rasp.log`

### 2026-10-14 09:14, entre conversas (desde 2026-10-12 19:55)

- Alterados (6): `backend/datapulse.db-shm`, `backend/datapulse.db-wal`, `backend/logs/rasp.log`, `backend/sessao_instagram.json`, `backend/sessao_x.json`, `backend/sessao_youtube.json`

### 2026-10-12 19:55, entre conversas (desde 2026-10-12 19:43)

- Alterados (2): `backend/datapulse.db-shm`, `backend/logs/rasp.log`

### 2026-10-12 19:14 a 19:43, conversa 7e957bdd

- Criados (11): `PEDIDO.md`, `marca/_opcoes_v4/opcoes_rodada3.html`, `marca/_opcoes_v4/opcoes_rodada3.png`, `marca/_opcoes_v4/rodada4/A_lamina_frontal.png`, `marca/_opcoes_v4/rodada4/B_lamina_volume.png`, `marca/_opcoes_v4/rodada4/B_simbolo_chroma.png`, `marca/_opcoes_v4/rodada4/B_simbolo_chroma_2.png`, `marca/_opcoes_v4/rodada4/C_duas_laminas.png`, `marca/_opcoes_v4/rodada4/LEIAME.txt`, `marca/fonte/rasp_simbolo_chroma.png`, `rasp_icon_v5.ico`
- Alterados (19): `CLAUDE.md`, `HISTORICO_DESENVOLVIMENTO.md`, `backend/datapulse.db-shm`, `backend/logs/rasp.log`, `build_brand_assets.py`, `frontend/favicon.ico`, `frontend/favicon.png`, `frontend/index.html`, `frontend/logo.png`, `frontend/logo.svg`, `marca/rasp_icon.ico`, `marca/rasp_icone.svg`, `marca/rasp_icone_1024.png`, `marca/rasp_logo_apresentacao.png`, `marca/rasp_logo_claro.png`, `marca/rasp_logo_escuro.png`, `marca/rasp_simbolo.svg`, `marca/rasp_simbolo_1024.png`, `rasp_icon.ico`
- "Onde parou" como ficou:

  > Atualizado em 2026-10-12. Esta seção tem no máximo 40 linhas: o que fechou vai para `HISTORICO_DESENVOLVIMENTO.md`.
  >
  > - **Kit de projeto (12/10/2026):** `_kit/` e `.claude/` copiados do `Kit_Projeto_IA` (81 arquivos, iguais
  >   byte a byte ao original). Ganchos testados por simulação: a guarda pediu confirmação para apagar `backend/sessao_instagram_dir/`
  >   e `_kit/`; o início de conversa levou 7,2 s. Ainda não rodaram numa conversa real.
  > - **Logo nova aplicada (12/10/2026):** placa cobalto em isométrico com a ponta descascando e o verso terracota
  >   (direção B da rodada 4, escolhida por ele com "b"). O símbolo é imagem gerada pelo Antigravity (modelo Pro) sobre
  >   magenta, em `marca/fonte/rasp_simbolo_chroma.png`; `build_brand_assets.py` (reescrito) tira o magenta e gera
  >   `marca/` (símbolo e ícone 2048px, lockups, apresentação, .ico de 16 a 256px), `frontend/logo.svg|png`,
  >   `favicon.png|ico` e `rasp_icon.ico` da raiz (o do atalho). Os SVG só embalam o PNG: não há vetor de verdade.
  >   `?v=8` em `frontend/index.html`. Conferido: fundo sem resto de magenta (0 pixels rosados na borda), cabeçalho
  >   e aba do RASP com a logo nova em 127.0.0.1:8080. Cópia em `Desktop\RASP logo nova\`. A v3 (barras) está em
  >   `marca/_v3_ondas/`; as opções descartadas em `marca/_opcoes_v4/`.
  >   O `PEDIDO.md` da raiz já foi executado (conversa do Antigravity `45beadf6`): pode ser apagado quando ele quiser.
  >   Ícone (.ico, favicon) sem fundo desde 12/10, a pedido dele: só a placa, sem o quadrado escuro. O atalho
  >   `Desktop\RASP.lnk` aponta para `rasp_icon_v5.ico` (nome novo a cada troca, por causa do cache do Windows; o
  >   gerador também grava esse arquivo). Conferido: cantos com transparência total no .ico em 16, 32 e 256px e no ícone que o Windows tira do atalho. **Falta:** ele confirmar na área de trabalho. Se um dia precisar de vetor (impressão grande), pedir ao Antigravity uma versão chapada e vetorizar.
  > - **Ponto atual:** última entrada do histórico é de 10/10/2026 ("Revisão Global de Alinhamento e Centralização de
  >   Controles"); código do backend com data de 09 e 10/10/2026.
  > - **Em curso fora desta conversa:** desconhecido; o Antigravity também trabalha nesta pasta.
  > - **Desconhecido:** se os testes passam hoje (não rodados nesta atualização).
  > - **Esperando o Lukyam decidir:** se o RASP ganha repositório próprio (hoje não tem cópia fora deste PC, fora o
  >   backup do Drive, se houver).

