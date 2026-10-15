# Código e apps

Para app, script, automação, painel e sistema.

## Antes de mexer

- **Ler o `CLAUDE.md` e o "Onde parou".** Se o código parece diferente do que o estado diz, apontar antes de
  mudar.
- **Mudança cirúrgica.** Mexer só no que o pedido exige; sem dependência pesada onde um script curto resolve.
- **Não acrescentar recurso que ninguém pediu.** *Caso:* uma IA pôs análise de sentimento num coletor sem pedido;
  o usuário mandou tirar e tudo foi removido.
- **Mudança de visual só com o aval antes.** Proposta com esboço; aplicar depois do sim.
- Instalar pacote novo só com liberação do usuário.

## O app tem que ser esperto, não o assistente

- Checagem que hoje é feita na conversa (fontes que discordam, arquivo fora do período, coluna faltando) vai para
  dentro do app, com a pergunta na tela. O objetivo é o usuário depender menos da conversa.
- **Quando a tarefa para numa ação do usuário** (login, "Salvar como", clique que só ele pode dar), fazer o que
  for permitido, pedir a parte dele e vigiar a página ou a pasta até acontecer, e então seguir sozinho, sem pedir
  que ele avise.

## Como fazer o app

- **Um atalho na área de trabalho que sobe tudo** (servidor, página), com ícone próprio e nome profissional.
  Se o usuário abre pelo atalho, o teste é pelo atalho, e depois de atualizar o app o atalho se confere.
- **Sem emoji na interface:** ícone em SVG. Minimalista, sem cara de app de IA. Usabilidade primeiro.
- **Preferir recurso que funcione sem token de IA pago**, com ferramenta gratuita e sem limite, quando der.
- **A regra de construção nunca vira texto de tela.** O app cumpre as regras em silêncio, sem se justificar nem
  cantar vantagem: nada de "anti-vibe", "zero token", "sem IA", "100% local", "sem gradiente neon" ou nome de
  diretriz interna em botão, título, legenda, tooltip, modal, planilha ou imagem exportada. *Caso:* uma IA pôs na
  tela de um app *Paletas Institucionais & Anti-Vibe-Code*, *Cores nobres sem gradientes neon clichês* e
  *Ultra HD • Zero Token IA*, e o dono do app teve de mandar tirar. O rótulo diz a função e só ela (*Paletas de cores*,
  *Transcrição de áudio*).
- **Sem adjetivo de enfeite nem termo técnico inflado** na tela e na entrega. *Casos do mesmo app:* *Monocromático
  Nobre*, *Editorial & Elegante*, *Minimalista clássico atemporal*, *Destaques executivos* em título de planilha,
  *4K Ultra HD* para escala de imagem 2D, *Transcrição Fonética* para transcrição comum de fala. Teste: sem o
  adjetivo, o rótulo ainda diz a função? Então o adjetivo sai.
- **A tela mostra o real.** Conta conectada só se estiver; nunca dado de exemplo misturado ao real.
- **Planilha exportada em xlsx formatado**, não csv cru.
- **Pedido de restaurar a versão de um horário é restaurar exatamente essa versão**, e conferir o atalho que
  aponta para ela. *Caso:* uma IA disse que tinha restaurado e não tinha.
- **Ler o terminal e o log sozinho** para achar o erro, em vez de pedir que o usuário cole.
- **Achou um bug, procurar a mesma classe no app todo** e nos outros apps do usuário que tenham a mesma peça.
- **Não reiniciar o Explorer do Windows** para atualizar ícone: deixa o computador travado.
- Antivírus já travou coleta no meio; se um processo parar sem erro, considerar isso.

## Testar antes de entregar

- **Testar a interface numa cópia, com janela invisível e conferência por código.** Não abrir e fechar o app do
  usuário enquanto ele trabalha. Captura de tela da máquina dele pode pegar outra janela que estava na frente.
- Testar com dado real (ou cópia dele) e dizer o que foi testado e o que não foi (ex.: *não testado: a caixa que
  pede o endereço*).
- Arquivo gerado se abre no programa de destino (PowerPoint, Excel) antes de dizer que está pronto.

## Armadilhas comuns no Windows

- PowerPoint e Word se automatizam por `win32com.client.dynamic` (Python) ou VBScript; pelo PowerShell a
  interface tipada falha e deixa processo invisível aberto. Word exporta PDF por `SaveAs2`, formato 17.
- Arquivo lido direto de disco sincronizado na nuvem (Google Drive, OneDrive) pode falhar no meio: copiar para
  uma pasta local antes. Atalho `.gdoc` não se lê nem se copia pelo Python.
- No Git Bash, barra invertida dentro de heredoc pode chegar alterada ao arquivo: escrever arquivo com barra
  invertida pela ferramenta de edição, não por heredoc.

## Mudar sem quebrar

- **Antes de mexer num gerador, rodar a cadeia sem mudança** e provar que ela reproduz a entrega atual. Só então
  aplicar a mudança e comparar.
- **O git é a prova do que mudou** entre rodadas de um agente; um original sobrescrito volta com
  `git checkout <commit> -- <arquivo>`. Commits automáticos guardam estados intermediários: comparar contra a
  versão conhecida e boa.
- Trava no script: dado inesperado (fora do período, campo faltando) para a montagem em vez de passar em silêncio.

## Segredos e repositórios

- **Nunca pôr senha, token, chave ou sessão no código ou no repositório.** Chave vem de variável de ambiente ou
  `.env` fora do git.
- **Sincronização automática (`git add .` agendado, autosync) sobe tudo que não está no `.gitignore`.** *Caso:*
  um arquivo de sessão logada voltou ao GitHub assim. Antes de criar arquivo com dado sensível numa pasta com
  git, conferir o `.gitignore`.
- Nunca force push nem reescrever histórico sem o usuário pedir.

## Fechar o trabalho

- Atualizar o "Onde parou" do `CLAUDE.md` (ponto atual com número conferido, o que falta).
- Dizer o que foi apagado e por quê.

## Na central

- `_kit/central/03_claude_code_plugins_skills_e_habitos.md`: plano antes de executar, skills, subagentes, loops que repetem
  até um fato ser verdade, ferramentas por sintoma.
- `_kit/central/07_a_especificacao_vale_mais_que_o_codigo.md`: especificar e decompor antes de gerar.
- `_kit/central/06_front_end_estrutura_bibliotecas_e_microinteracao.md`, `_kit/central/01_os_30_sinais_de_site_feito_por_ia.md` e
  `_kit/central/02_como_tirar_a_cara_de_ia_na_pratica.md` para qualquer tela.
- **Antes de pôr no ar:** `_kit/central/09_checklist_de_seguranca_antes_de_lancar.md`,
  `_kit/central/10_checklist_de_publicacao_de_site.md`, `_kit/central/11_o_lado_juridico_como_nao_ser_processado.md` e
  `_kit/central/12_ser_achado_seo_aeo_e_geo.md`. Rodar os três checklists é parte da entrega, não extra.
- Integração entre ferramentas: `_kit/central/19_mcp_contra_api_o_que_cada_camada_faz.md`. Custo de pôr no ar:
  `_kit/central/42_a_conta_de_lancar_servico_por_funcao_e_preco.md`.
