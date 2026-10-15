# A escalada do prompt: do pedido cru ao processo

Verbete da central Dominação IA, seção "Prompt e uso de modelo" (versão de 28/09/2026). Cada item saiu de um post; o "nó" é o número do post, com link em Fontes.

O padrão mais valioso do acervo em prompt, mostrado em dois posts com o mesmo formato (ruim, melhor, ideal) aplicado a tarefas diferentes. A progressão é sempre a mesma: parar de pedir o resultado e passar a construir o contexto e o caminho junto com o modelo. Um quarto post sobe mais um nível, saindo do pedido para o system prompt: a instrução fixa que vale antes de qualquer pedido, em quatro blocos que cabem numa página.

*4 fontes · confiança alta*

**A progressão**

- Ruim: pedir a entrega direto ("Write me a LinkedIn post about AI tools", "Explain system design")
- Melhor: dar contexto e instruir a NÃO começar ainda, fazendo perguntas de esclarecimento antes
- Ideal: anexar arquivos de contexto, mandar ler tudo antes de responder, não executar ainda, e refinar a abordagem junto com você

**O que anexar em vez de descrever**

- Quem você é
- Seu estilo de escrita (inclusive "sem cara de IA")
- Princípios de copy que você segue
- Suas metas, seu nível atual e suas áreas de foco

**Palavras que só ocupam espaço**

- Cortar "por favor", "obrigado", "se possível", "faça o melhor que puder": o modelo não fica motivado e você gasta token à toa
- Cortar "aja como se fosse" e "você é um especialista mundial": não cria especialista, cria texto de LinkedIn
- Cortar "pense fora da caixa" e "seja criativo"
- Cortar "quero que você", "me ajude a", "de forma detalhada", "seja completo"
- Cortar emoji e adjetivo empilhado
- Cortar "resuma tudo", "seja incrível" e o pedido de exemplo genérico
- Nunca escrever "não erre": mandar não errar AUMENTA a chance de invenção
- Trocar "me diga tudo o que você sabe sobre X" por "o que eu preciso decidir é Y"

**O system prompt, em quatro blocos**

- A estrutura que o nó 177 manda copiar, e que cabe numa página: definição de papel, limites do que não fazer, formato de saída, e o que fazer quando não souber
- Por que não colar o texto inteiro de um system prompt vazado: 120 mil caracteres num modelo aberto consomem contexto e pioram o resultado antes de melhorar. O que se copia é a estrutura
- O caminho oficial existe e é de graça: a Anthropic publica na documentação o system prompt de cada modelo, com data de versão
- Por que o oficial é muito menor que o vazado: a versão publicada traz só o bloco de comportamento e vale para o aplicativo, não para a API, e definição de ferramenta não entra
- A ressalva sobre o vazado: a empresa não confirmou nada e ninguém de fora consegue verificar se o arquivo está completo ou modificado, então é material de estudo e não fonte
- O que a tela revela e a legenda não diz: não é um arquivo só, é uma pasta com um markdown por produto (claude-design.md, claude-cowork.md, claude-desktop-code.md, claude-for-excel.md, claude-for-word.md, claude-in-chrome.md, claude-in-powerpoint.md, claude-mobile-ios.md, claude-opus-4.6.md, claude-opus-4.6-no-tools.md, anthropic_reminders.md e claude-fable-5.md)
- A lista de seções de um desses arquivos, lida no filtro de títulos: Data Scope, Error Handling, Limitations, Connector directory first, After search, [third_party_mcp_app] tools need opt-in, When to call an [third_party_mcp_app] tool directly, What not to do e What this should feel like
- O teste proposto: escrever a sua versão de uma página e rodar contra a mesma tarefa sem ela

**Prompts e comandos**

Ruim, post no linkedin (nó 67):

```text
Write me a LinkedIn post about AI tools.
```

Melhor, post no linkedin (nó 67):

```text
I want to write a LinkedIn post about the AI tools I use daily. Don't start yet. Ask me clarifying questions first (use AskUserQuestion), so we align on angle, tone, and audience.
```

Ideal, post no linkedin (anexos: about me - ruben hassid.md, anti ai writing style.md e copywriting.md) (nó 67):

```text
I want to write a LinkedIn post about AI tools I use daily. First, read the uploaded files completely before responding. DO NOT start executing yet. Instead, ask me clarifying questions (use AskUserQuestion) so we can refine the approach together step by step.
```

Ruim, aprender system design (nó 72):

```text
Explain system design.
```

Melhor, aprender system design (nó 72):

```text
I want to learn about system design. Don't start yet. Ask me clarifying questions first (use AskUserQuestion), so we align on level, goals, and focus areas.
```

Ideal, aprender system design (anexos: my_goals.md, current_level.md e focus_areas.md) (nó 72):

```text
I want to learn system design. First, read the uploaded files completely before responding. DO NOT start teaching yet. Instead, ask me clarifying questions (use AskUserQuestion) so we can create a personalized learning path together step by step.
```

Contraexemplo: o que o nó 177 marca com x como o que não é system prompt (nó 177):

```text
Write clean, efficient [trecho coberto pelo emblema] ell-structured code based on the requirements below. Follow best practices and use modern syntax. Include meaningful variable names, proper indentation, and helpful comments where needed. Handle edge cases and ensure the code is optimized for performance and readability. Provide the code in a single code block.
```

**Fontes**

- [nó 67](https://www.instagram.com/reel/DZxAE6NSe0e/) @engineerchirag: Prompt ruim, melhor e ideal para um post no LinkedIn
- [nó 72](https://www.instagram.com/reel/DbLVpV8svfr/) @engineerchirag: Prompt ruim, melhor e ideal para aprender system design
- [nó 81](https://www.instagram.com/reel/DczQNdWun5b/) @eduardocavalcanti: 20 palavras para evitar em prompts
- [nó 177](https://www.instagram.com/reel/DdHjly9AOuq/) @fabianocarvalhojr: System prompt: o oficial contra o vazado, e a estrutura de uma página

**Observações.** Os prompts dos nós 67 e 72 foram copiados das imagens nos três níveis. Os arquivos anexados no nível ideal aparecem só pelo nome: o conteúdo deles não está no post. "AskUserQuestion" é a ferramenta do Claude Code que faz perguntas com opções; fora dele, basta pedir as perguntas (nota do projeto, não do post). O nó 81 promete a lista detalhada dos 20 termos por direct; aqui estão só os agrupamentos ditos em voz alta. O prompt anti-bajulação do nó 82 saiu daqui para o verbete "Fazer a IA discordar", nesta mesma área, onde ficou junto dos outros três posts sobre o assunto. O caso de aprender system design do nó 72 tem o desdobramento prático no verbete "Estudar com IA", com seis prompts prontos. O nó 177 se contradiz dentro do próprio post: a fala manda pegar as instruções vazadas e rodar num modelo mais barato para melhorar drasticamente os resultados, e mostra um diagrama ligando o arquivo a Kimi K3 e GLM-5.2; a legenda diz o contrário, que colar 120 mil caracteres num modelo aberto piora o resultado e que só a estrutura se aproveita. Nenhum dos dois é testado no post. As 49 mil estrelas e os 122.750 caracteres são afirmação do autor, e o nome do repositório vai por comentário. A árvore de arquivos, o prompt marcado com X e a lista de seções foram conferidos em resolução cheia; as três primeiras seções (Storage API, Usage Examples e Key Design Pattern) só foram lidas na folha reduzida. No prompt marcado com X, o emblema vermelho cobre parte de uma palavra, que não foi completada de propósito.

**O que não tem aqui.** Nenhum post mostra o resultado lado a lado dos três níveis: a superioridade do "ideal" é afirmada, não demonstrada.
