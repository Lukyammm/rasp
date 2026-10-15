# Delegação e custo

Para qualquer tarefa em que dá vontade de passar parte do trabalho a outro agente (subagente, outra IA, outra
ferramenta), ou que vai ler muito material. A cota de uso costuma ser uma só para a conversa e para os agentes
que ela dispara: se estoura, o trabalho inteiro para, não só a parte delegada.

## O que já deu errado

- **Seis subagentes do modelo mais caro lendo um livro em paralelo** esgotaram a cota semanal antes de gravar
  qualquer coisa. A sessão parou até a cota voltar.
- **O usuário pediu para delegar a uma ferramenta específica para economizar.** A IA disparou 12 subagentes em
  paralelo sobre 45.763 comentários, a cota acabou no meio, e a outra ferramenta terminou o trabalho.
- **Um agente "terminou" 54 lotes de comentários em 2 minutos**, por script (um rótulo padrão mais exceções), e
  escreveu que 100% tinha sido classificado um a um. Contra um gabarito de 200 comentários lidos antes, acertou
  78%; leitores que leram de fato, 89%.
- **Um agente entregou 164 posts com "100% dos dados reais".** Seis colunas tinham sido preenchidas por regra no
  script, 90 datas eram uma data fixa escrita no código, e ele apagou seis arquivos sem passar pela lixeira,
  incluindo o bruto.
- **Um agente com a instrução de ler o arquivo de regras da pasta não leu**, e ofereceu apagar uma pasta marcada
  como insubstituível. Por isso as regras de segurança vão repetidas no `AGENTS.md`, que ele lê sozinho.

## Os quatro testes

Uma tarefa vai para fora quando passa nos quatro:

1. **É volume, não julgamento.** Varrer muitos arquivos, catalogar, comparar, converter formato, conferir link,
   transcrever. Se o trabalho é decidir o que uma coisa significa, não passa.
2. **A volta é conferível sem refazer.** Dá para checar por script, amostra ou leitura curta. Se para confiar
   seria preciso refazer tudo, não passa.
3. **Explicar custa menos que fazer.** Regra de bolso: vale a partir de umas 5 imagens, 20 mil caracteres de
   material bruto ou 150 linhas de código de rotina. Abaixo disso, fazer direto.
4. **Não toca no proibido:** fonte insubstituível, login, conta do usuário, texto que o usuário vai ler,
   decisão de conteúdo.

**Nunca delegar:** a decisão de conteúdo, o julgamento sobre o que uma coisa significa, qualquer texto que o
usuário, o chefe ou o cliente vão ler, e qualquer coisa irreversível ou que fale com serviço externo em nome do
usuário.

## Antes de disparar

1. **Se o usuário disse para qual ferramenta delegar, é para ela.** Não trocar sem avisar e explicar por quê.
2. **Medir o volume e dizer antes:** quantos arquivos, quantos caracteres, quantos agentes, em quantas levas.
   Número medido. Se for grande, perguntar se segue.
3. **Separar por regra o que a regra decide sem perda** (texto vazio, só emoji) e mandar para leitura só o resto.
4. **Fazer o gabarito antes:** uma amostra sorteada, lida e decidida por quem decide, guardada antes de a volta
   chegar. É ela que mede a volta.
5. **Decidir antes como a volta será conferida:** por script contra a fonte (contagem, ids, citação literal com
   `_kit/scripts/conferir_citacoes.py`), não pela palavra do agente.
6. **Foto da pasta antes de soltar um agente que roda comando nela:** `python _kit/scripts/protecao.py fotografar`.
7. **Passar a lista do que parece erro e é de propósito** (nomes, grafias, termos do cliente). *Caso:* leitores
   marcaram como erro dois nomes de personagem que eram de propósito.
8. **Guardar o texto inteiro do pedido num arquivo** na pasta de saída.

## Outra IA no computador (Antigravity, Gemini CLI, Codex)

Vale quando o `CLAUDE.md` do projeto tem nome em "Outra IA para trabalho pesado". Ela poupa a cota desta
conversa, por isso vem antes dos subagentes para volume.

- **A IA sugere sem esperar o pedido.** Tarefa que passa nos quatro testes: antes de começar, uma linha com o
  tamanho medido e a proposta. Quem decide é o usuário; quem leva o pedido até a outra IA também.
- **Nunca chamar a outra IA por conta própria**, nem por comando: é outro serviço e outra conta.
- **O `PEDIDO.md`** fica na pasta do projeto e se lê sem esta conversa: o objetivo em uma frase; os caminhos
  exatos de entrada e de saída; o formato da volta (colunas, um arquivo por lote); o que é insubstituível e não
  pode ser apagado, movido nem "organizado"; a lista do que parece erro e é de propósito; "não preencha campo
  que não existe na fonte: deixe vazio e diga quantos ficaram vazios"; e como a volta será conferida.
- **A volta passa pela mesma conferência** de "Quando a volta chega", abaixo. Foto da pasta antes
  (`python _kit/scripts/protecao.py fotografar`) e conferência depois (`conferir`): já houve
  agente que apagou o arquivo bruto ao "organizar".
- Se a outra IA falhar duas vezes no mesmo ponto, a tarefa volta para cá.

## Subagentes

- **Antes de subagente, script.** Contar, comparar, conferir citação e listar o que mudou não precisam de modelo:
  `_kit/scripts/` e os ganchos do kit fazem sem gastar token.
- **Os subagentes do kit já vêm com o modelo fixo** (`.claude/agents/`): `varredor` (Haiku) para volume mecânico,
  `leitor` (Sonnet) para ler material grande inteiro, `conferente` (Haiku) para conferir a volta contra a fonte,
  `leitor-frio` (Haiku) para ler a entrega como o leitor final. Usar pelo nome: subagente genérico herda o modelo
  da conversa, que costuma ser o mais caro.
- **Eles não leem o `CLAUDE.md`**, de propósito: cada chamada ficaria mais cara, e a "Primeira conversa" os
  confundiria. O pedido leva o que importa: a pasta de saída, o formato da volta, como ela será conferida, a
  lista do que parece erro e é de propósito, e a regra do projeto que vale para a tarefa.
- **Levas de 2 ou 3**, nunca dezenas em paralelo.
- Cada um grava o resultado aos poucos num arquivo, para nada se perder se cair.
- Instrução explícita: ler tudo, sem pular trecho, sem ler por busca de palavra.
- **Medir depois:** `/medir` mostra quanto foi para cada modelo e avisa se algum subagente rodou no mais caro.

## Quando a volta chega

- **Autocertificação não é sinal.** "100%", "verificado", "um a um" vieram junto com os defeitos todas as vezes.
- **O relato do agente não é o arquivo.** Já houve *45 de 45 com sucesso* com 24 falhas gravadas no próprio
  arquivo, e "visualizações exatas" com `null` nos 45 vídeos. Conferir arquivo por arquivo e campo a campo.
- Cada coluna existe no bruto ou foi preenchida pelo script? Qual trecho do código preenche? O bruto foi salvo?
  Algum arquivo sumiu (`python _kit/scripts/protecao.py conferir`)?
- Em coleta de perfil: o dono de cada post no bruto, a data mais antiga por perfil contra o que o perfil mostra,
  zero onde o perfil exibe conteúdo, métricas idênticas às de uma coleta anterior.
- Comparar com o gabarito e dizer o acerto em número (ex.: *174 de 200*), não em adjetivo.
- Sinais rápidos de defeito: o mesmo valor em 100% das linhas, categoria residual acima de metade, total que
  fecha com linhas erradas (erros que se cancelam), seção "casos que não couberam" vazia, nenhum caso
  *indeterminado* numa base grande.
- Aproveitar o fato conferido, não o pacote: achado útil vem misturado com erro.
- Tarefa que erra duas vezes no mesmo ponto volta para quem decide.
- O usuário às vezes pede coisas direto a outra ferramenta: processo rodando ou arquivo novo que ninguém pediu
  nesta conversa pode ser isso. Confirmar com ele antes de parar ou mexer.

## Enquanto roda

- Dar o andamento em número (ex.: *lote 14 de 26, 5.600 de 13.839 comentários*) sem esperar a pergunta.
- Com agente rodando na pasta, não editar a fonte do projeto: vira alarme falso na conferência.

## Na central

- `_kit/central/04_gastar_menos_token.md`: reduzir o que entra, o que sai e o que circula.
- `_kit/central/13_a_escalada_do_prompt_do_pedido_cru_ao_processo.md`: como escrever o `PEDIDO.md` (contexto em arquivo,
  "não execute ainda", perguntas antes) e o que cortar do pedido porque só gasta token.
- `_kit/central/17_qual_ferramenta_de_ia_usar_para_que.md`: qual ferramenta para qual tarefa (validade curta: conferir).
- `_kit/central/03_claude_code_plugins_skills_e_habitos.md`: subagentes com função própria (um escreve, outro revisa).
