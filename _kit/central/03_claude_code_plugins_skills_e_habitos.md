# Claude Code: plugins, skills e hábitos

Verbete da central Dominação IA, seção "Construir com IA sem parecer que foi IA" (versão de 28/09/2026). Cada item saiu de um post; o "nó" é o número do post, com link em Fontes.

Junta o ferramental (o que instalar), a prática (como trabalhar) e como escrever a própria skill. O fio comum é tirar trabalho repetido do seu lado: memória entre sessões, configuração automática do projeto, plano antes da execução e revisão antes da entrega.

*11 fontes · confiança alta*

**Hábitos de uso**

- Manter um arquivo CLAUDE.md com as regras do projeto
- Pedir o plano, ler o plano, e só então mandar executar
- Pedir que ele teste e confira o resultado antes de entregar
- Usar o próprio Claude para ele explicar o sistema a você
- Revisar a memória com /memory
- Rodar vários Claudes em paralelo, em terminais diferentes

**Os vinte comandos, por função**

- /init: cria o CLAUDE.md do projeto
- /memory: edita o que ele nunca esquece
- /add-dir: trabalha em dois repositórios
- /agents: subagente com contexto próprio
- /context: o mapa de quem ocupa a janela
- /compact: resume em vez de recomeçar
- /cost: o taxímetro da sessão
- /usage: o que empurra para o limite
- /resume: volta a conversa de ontem
- /rewind: desfaz com o código junto
- /todos: a lista que ele mesmo escreve
- /export: tira a conversa do terminal
- /review: revisa o seu diff atrás de bug
- /security-review: acha a senha esquecida no meio do código
- /doctor: culpa a instalação, não o modelo
- /permissions: onde o automático fica seguro
- /mcp: pluga ele nas suas ferramentas
- /artifacts: as páginas que você publicou
- agentes em paralelo: o que multiplica o trabalho
- /hooks: toda edição roda o seu comando, e é assim que ele testa sozinho sem ninguém pedir

**Um arquivo de quatro regras do que não fazer**

- No over-engineering: pensar antes de escrever, entendendo o problema antes da primeira linha
- No assumptions: não chutar quando estiver confuso
- No pointless changes: mudança cirúrgica, não mexer no que não está quebrado
- Double-check work: definir o que é sucesso e repetir até verificar, o que corta o terminei sem conferir
- Por que proibir rende mais que instruir, no argumento do autor: instrução do que fazer o modelo já tem, o que ele não tem é noção de quando parar
- O que o arquivo não faz: não deixa o modelo mais inteligente, deixa mais disciplinado, e problema que exige o contexto do seu negócio continua exigindo que você escreva esse contexto
- O teste que o próprio post propõe, em vez de confiar nas 210 mil estrelas: uma semana com o arquivo, uma semana sem, contando quantas vezes você pediu para simplificar
- A regra de simplicidade é literal no arquivo, segundo a legenda: se saiu em 200 linhas e cabia em 50, reescreve

**Instalar skills oficiais**

- Instalar as skills oficiais de cada tecnologia que você adicionar ao projeto (Supabase, Convex)
- Procurar biblioteca consagrada em vez de mandar a IA reescrever tudo do zero
- Montar e customizar um design system para a IA não reconstruir a UI toda vez

**Repositório aberto de skills e subagentes, e a ordem de instalar**

- A ordem que o nó 174 propõe, e que é o conselho central dele: só o cofre de memória na primeira semana, depois dois ou três agentes do seu gargalo, e o scanner de segurança por último
- O motivo da ordem: instalar as 286 skills de uma vez é o jeito mais rápido de não saber o que ajudou, e no projeto seguinte você repete tudo sem saber do que precisa
- A definição de skill que o post usa: um conjunto de instruções que o modelo lê antes de escrever qualquer código, não um plugin
- Por que subagente importa: em vez de um assistente tentando fazer tudo, cada tarefa vai para quem foi feito para ela, um escreve, outro revisa, outro procura brecha de segurança
- Os subagentes aparecem nomeados na tela, rodando dois ao mesmo tempo: code-reviewer, que faz o passe de revisão de código, e security-reviewer, que faz a revisão de segurança
- O cofre de memória, como a tela mostra por dentro: uma pasta memory com project dentro, e dentro dela seis pastas separadas por tipo de lembrança, contexts, decisions, facts, handoffs, lessons e notes
- O ganho declarado do cofre: como é arquivo de texto na própria máquina, o que o modelo aprendeu do projeto atravessa de uma ferramenta para outra
- A parte que o autor diz que quase ninguém percebe: o que se descobre numa sessão some quando o terminal fecha, e esse setup transforma o que deu certo em skill nova sozinho

**Escrever uma skill do zero**

- Criar uma skill quando você pede a mesma formatação várias vezes, ou quando o mesmo prompt dá resultados diferentes para pessoas diferentes
- No topo do SKILL.md, entre os dois traços, vão o nome e a descrição
- Caprichar na descrição: é a única parte que o Claude lê antes de decidir se ativa a skill; dizer o que ela faz e quando usar
- Abaixo do segundo traço vão as instruções que o Claude segue para fazer o trabalho: os passos e o formato da saída
- Para não escrever o markdown à mão, pedir ao skill-creator, da Anthropic, que monte a skill a partir de um prompt

**Loops no lugar de prompt a cada passo**

- Polling loop: roda no relógio, nunca termina e vigia se há trabalho; a cada intervalo pergunta se existe issue aberta, e se não houver espera o próximo tique
- Quando há issue, o ciclo é ler, corrigir, abrir o PR, fazer o merge, fechar a issue e voltar ao relógio
- Dynamic run: não tem relógio, roda uma vez e para quando termina; uma rodada é uma unidade de trabalho
- A rodada começa pela especificação, que continua sendo escrita à mão, e segue por implementação, revisão de código e build
- Cada laço interno repete até um fato ser verdadeiro (revisão com zero achados, build verde), e não até parecer bom
- O fim da rodada avisa quem pediu, no exemplo por mensagem no Slack
- A unidade de trabalho deixa de ser o prompt e passa a ser o loop, o que muda o papel de quem usa

**Cinco ferramentas pelo problema que resolvem**

- O nó 164 organiza a escolha pelo sintoma, não pela categoria: visual com cara de vibe code, site lento, erro de back-end, ter que reexplicar o projeto a cada sessão e risco de invasão
- Duas delas servem a outros verbetes: o Lighthouse ao checklist de publicação de site e a skill never-get-hacked ao checklist de segurança antes de lançar

**Ferramentas**

| Ferramenta | Para que | Fontes |
|---|---|---|
| OmniRoute | Troca de provedor quando o limite de uso acaba | nó 13 |
| Headroom | Comprime o contexto: mesmo resultado com menos token | nó 13 |
| Claude Code Setup | Plugin oficial da Anthropic: escaneia o código e recomenda hooks, skills, subagentes e MCP | nó 13 |
| Task Observer | Observa como você trabalha e melhora suas outras skills | nó 13 |
| shadcn/ui | Design system pronto para a IA não reconstruir a UI do zero | nó 51 |
| claude-code-security-review | Plugin oficial de revisão de segurança | nó 51 |
| Skills de Matt Pocock | Skills avançadas | nó 51 |
| skill-creator | Skill da Anthropic que monta outra skill a partir de um prompt | nó 111 |
| Ruflo | Orquestrar agentes especializados em paralelo no Claude (planejar, executar, testar, cuidar da segurança), com aprendizado compartilhado entre eles | nó 126 |
| 21st.dev | Biblioteca de componentes React e Tailwind prontos, contra o visual genérico de front-end gerado por IA | nó 164 |
| Lighthouse | Auditoria aberta dentro do DevTools do Chrome: performance, acessibilidade e SEO da página, com o que trava o carregamento | nó 164 |
| Context7 MCP | Mantém o contexto de arquitetura, endpoint e configuração para o assistente não inventar dependência no back-end | nó 164 |
| Graphify | Memória persistente em grafo de conhecimento: decisões e padrões do projeto, para não reexplicar a arquitetura a cada sessão | nó 164 |
| never-get-hacked | Skill de segurança para agente de código: marca SQL injection, XSS, dependência insegura e credencial exposta antes de ir para produção | nó 164 |

**Prompts e comandos**

Instalação (nó 51):

```text
npx skills add https://github.com/anthropics/skills --skill frontend-design
```

Instalação (nó 51):

```text
npx skills add https://github.com/shadcn-ui/ui --skill shadcn
```

Cabeçalho de skill (exemplo) (nó 111):

```text
---
name: pr-description
description: Writes pull request descriptions. Use when create a PR, writing a PR, or when the user asks to summarize changes for a pull request.
---
```

Comando de loop, como aparece na tela do nó 136 (nó 136):

```text
/loop 2m run npm run build and tell me if it passed or failed
```

**Fontes**

- [nó 13](https://www.instagram.com/reel/DbqfZusDXwO/) @oguiadaia: Cinco plugins e ferramentas para o Claude Code
- [nó 51](https://www.instagram.com/reel/DcbONnzMkD_/) @buildwithnico: Três níveis de vibe coders
- [nó 85](https://www.instagram.com/reel/DdHoaoWMPOK/) @eugustavofelicori: Skill Humanizer para textos sem cara de IA
- [nó 102](https://www.instagram.com/p/Dcrd5KaCcf3/) @rony: Seis dicas de uso do Claude Code (CLAUDE.md, plano, /memory, paralelo)
- [nó 111](https://www.instagram.com/reel/DbDnSN3Ba4w/) @soojintech: Anatomia de uma skill do Claude Code e o skill-creator
- [nó 126](https://www.instagram.com/reel/DaG4LJqpgDd/) @rony: Ruflo, orquestrador de agentes no Claude, com promessas grandes
- [nó 136](https://www.instagram.com/reel/DZs5QKzSLkk/) @theodacoda: Loops no lugar de prompts: polling loop e dynamic run no Claude Code
- [nó 164](https://www.instagram.com/reel/DczvUteRsGJ/) @aj.on.ai: Cinco ferramentas para o que costuma quebrar no projeto com IA
- [nó 174](https://www.instagram.com/reel/DdB9aVqjUE8/) @fabianocarvalhojr: Repositório aberto de 286 skills e 68 subagentes, e a ordem de instalar
- [nó 176](https://www.instagram.com/reel/Dc_4u4bkogN/) @fabianocarvalhojr: Um arquivo de quatro regras que diz à IA o que não fazer
- [nó 179](https://www.instagram.com/reel/DcjoP_Dh4vL/) @eduardocavalcanti: Vinte comandos do Claude Code, agrupados por função

**Observações.** Os nomes dos plugins vieram da revisão manual das capturas de tela: a transcrição automática destrói todos eles ("Cloud Code", "Shatzian", "servidores em CEP"). A alegação de "1,6 bilhão de tokens gratuitos por mês" do OmniRoute é do vídeo, não verificada. As dicas do nó 102 são atribuídas pelo post ao criador do Claude Code, atribuição não verificada. Do corpo da skill de exemplo do nó 111 se leem os dois primeiros passos (rodar git diff main...HEAD para ver as mudanças do branch e escrever a descrição no formato) e as seções What, Why, Changes e Testing. O nó 136 fala em checar a cada cinco minutos, mas a tela e o comando mostram dois minutos, e as citações do criador do Claude Code e do autor do OpenClaw aparecem como captura, sem link. O nó 126 é apresentação comercial do Ruflo: a tela lista mais de 100 agentes, camada de comunicação zero-trust, coordenação em enxame e banco vetorial, enquanto a fala diz 60 agentes, e as promessas (empresa bilionária sozinho, trabalho de uma folha de R$ 100 mil de graça, 75% menos custo no Claude) não vêm com nenhuma medição. As cinco ferramentas do nó 164 vêm com a descrição da legenda do autor, sem teste mostrado; os links dele vão por comentário e Discord, fora do post. Os nós 174, 176 e 179 entraram em 22/09. Nenhum dos três dá o nome do repositório de que fala: os três entregam o link por comentário ou direct, e os números que citam (286 skills, 68 subagentes, 102 checagens, 210 mil estrelas) são afirmação dos autores, sem nada no post que os confira. As quatro regras do nó 176 foram lidas em resolução cheia no quadro aos 36 segundos, em inglês, e a tela mostra só as quatro linhas de título, não o arquivo inteiro. Do nó 174, três telas trazem o que a legenda não tem: a tabela do scanner com sete falhas corrigidas (Session tokens hashed at rest, Timing oracle, Raw token logging, Traversal, Rate limiting, Cross-origin text/plain POST e Reset replay com senha ou sessão antiga), os dois subagentes rodando e a árvore do cofre de memória. Do nó 179, o item 19 aparece na tela como /AGENTS PARALELO, com barra, como se fosse comando, e na legenda vem sem barra, que é o que ele de fato é; o mesmo post afirma, dizendo ter conferido no binário instalado e não em print, que /cost virou apelido de /usage, que /review virou apelido de /code-review e que /agents aparece como removido na versão 2.1.247.

**O que não tem aqui.** Nenhum post mostra um arquivo de regras real por inteiro. O nó 176 mostra as quatro regras em quatro linhas de título e o nó 174 mostra a árvore do cofre de memória, mas nenhum abre o conteúdo de um arquivo. A skill do nó 111 aparece com o cabeçalho inteiro, mas o corpo das instruções fica coberto em parte na tela, e o passo a passo completo é entregue por comentário. A ficha de cada um dos vinte comandos do nó 179 (quando usar, a linha para colar, o erro que faz não servir) também vai por direct.
