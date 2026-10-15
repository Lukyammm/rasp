# Atalhos de prompt e o aviso que ninguém dá

Verbete da central Dominação IA, seção "Prompt e uso de modelo" (versão de 28/09/2026). Cada item saiu de um post; o "nó" é o número do post, com link em Fontes.

Sete posts distribuem listas de "códigos secretos" (/godmode, /blueprint, /eli5) como se fossem recursos do produto. Não são: funcionam só como convenção de texto que o modelo interpreta, e o autor do nó 156 diz isso com todas as letras. Isso não os torna inúteis, mas muda completamente o que esperar deles.

*7 fontes · confiança média*

**AVISO**

- Nenhum desses atalhos é comando oficial de Claude ou de ChatGPT
- Eles funcionam como instrução escrita no começo da mensagem; o efeito depende do modelo interpretar a convenção
- Não há garantia de comportamento consistente entre modelos, versões ou idiomas
- Para usar de verdade: explicar na conversa o que cada atalho significa antes de usá-lo. Quem diz isso é a própria autora de um dos posts, na legenda
- O autor do nó 156 diz o mesmo: não é comando escondido do ChatGPT, do Claude nem do Gemini, é convenção que você instala uma vez, e o vocabulário é seu. O bloco que ele diz fazer os códigos funcionarem vai por comentário
- O mesmo atalho muda de sentido entre posts: /brief é "resposta mais curta" num e "resumo executivo" noutro; /teacher é "mentor, debate" num e "explicar com paciência" noutro
- Dois posts com o mesmo formato de 99 códigos, um para o Claude e outro para o ChatGPT, só têm 22 códigos em comum: /plain e /human fazem a mesma coisa, assim como /pro e /expert, /founder e /ceo, /five e /eli5, /tight e /brief, /skeptic e /critic. O nome é convenção inventada por quem escreveu o post; o que o modelo lê é a descrição

**Para forçar contraposição**

- /skeptic, /devil, /pushback, /critique: forçar crítica em vez de concordância
- /scout: levantar riscos e pontos cegos
- Os doze códigos do nó 167, feitos só para isso (/PREMORTEM, /STEELMAN, /BASELINE e os outros), estão no verbete "Fazer a IA discordar", nesta mesma área, junto com a instrução permanente e a pré-morte de projeto

**Para raciocínio e decisão**

- /firstprinciples, /tradeoffs, /decide, /compare

**Para empacotar, verificar e perguntar antes**

- /HANDOFF: empacota a conversa para colar em outro modelo sem perder nada; o autor do nó 156 aponta como o melhor dos vinte
- /SOURCE: só afirma o que tem fonte com link e data; segundo o mesmo autor, é o que mata a invenção
- /ASK3: faz três perguntas antes de responder, e espera
- /CHANCE: dá a chance em porcentagem com o raciocínio aberto

**Para código**

- /debug, /ooda, /refactor, /testit, /secure, /verify, /finalcheck

**Para formato da saída**

- /brief: resposta curta
- /plain: sem enfeite
- /eli5, /explainlikeim5: explicação simples
- /ghost, /human: resposta com cara humana
- /json, /checklist, /roadmap, /quiz: estrutura da saída
- /hook, /pitch, /viral, /copywriter: texto de marketing

**Para transformar imagem (com a imagem anexada)**

- /360view: o objeto em vários ângulos
- /blueprint: planta técnica
- /Anatomy: objeto desmontado com rótulos
- /Xray: raio-x
- /handwritten: esboço de caderno
- /impossibleangle, /surreal
- /gravitydefying: produto flutuando

**Prompts e comandos**

Os 15 do post, em inglês como no original; repete /artifacts e /devil (nó 70):

```text
/godmode: aggressive, powerful mode
/ghost: human-like response
/10x: rewrite 10x sharper
/pitch: 30-sec investor/client pitch
/compare: side-by-side analysis
/scout: find risks and blind spots
/ooda: complex code problem solving
/artifacts: builds live apps in chat
/devil: "steelman" the opposition
/artifacts: improve & find faults
/critique: improve & find faults
/teacher: mentor, debate
/explainlikeim5: super clear explanation
/brief: shortest, no-fluff answer
/devil: deep contrarian perspective
```

Os 99 do post, em inglês como no original (nó 96):

```text
/plain: write in plain, natural language
/pro: answer like a seasoned specialist
/founder: think with founder-level instinct
/coach: respond like a supportive mentor
/skeptic: poke holes before i commit
/teacher: explain with patience and clarity
/five: explain it like i'm five
/tight: give the shortest possible answer
/longform: give the full, unabridged answer
/sell: write copy built to convert
/calm: keep the tone measured and steady
/dig: go deep, skip nothing
/gut: give your instinct, not just logic
/devil: argue the opposing side
/firstprinciples: rebuild the idea from the ground up
/longgame: think five years out
/worstcase: map out what could go wrong
/bestcase: map out what could go right
/tradeoffs: lay out what each option costs
/reframe: look at this from a new angle
/zoomout: step back to the bigger picture
/zoomin: drill into the smallest detail
/remix: reimagine this from scratch
/twist: add an unexpected angle
/mashup: combine two unrelated ideas
/wild: go for the boldest version
/safe: give the most cautious version
/name: brainstorm names or titles
/openers: write ten different opening lines
/story: turn this into a narrative
/metaphor: explain it through analogy
/series: turn this into a content series
/hook: craft a scroll-stopping first line
/pitch: write the elevator version
/goals: turn the idea into measurable objectives
/budget: think in terms of cost and return
/risk: flag what could go wrong
/market: size up the competitive landscape
/persona: describe the target audience
/roadmap: lay out the plan over time
/kpi: define how success gets measured
/negotiate: prep the talking points for a deal
/scale: plan how this grows
/exit: think through the endgame
/teachme: explain it patiently, step by step
/quiz: turn this into practice questions
/recap: summarize what was just covered
/gaps: find what i'm missing
/sources: point me toward where to learn more
/debate: argue both sides of the issue
/history: explain how this came to be
/forecast: project where this is heading
/jargon: translate the technical terms
/kidsafe: explain it for a curious kid
/oneline: explain it in a single sentence
/outline: lay this out as a clean outline
/checklist: turn this into a practical checklist
/template: build a reusable template
/table: convert this into a table
/matrix: organize the options into a decision grid
/timeline: lay this out on a timeline
/bullets: strip it down to bullet points
/json: structure the answer as json
/form: shape this into a fill-in form
/script: format this as a spoken script
/brief: write it as an executive brief
/code: write clean, working code
/debug: find what's breaking in this
/refactor: clean up this code without changing behavior
/comment: annotate the code so it's easy to follow
/testit: write tests to cover the edge cases
/explainit: walk through what this code actually does
/optimize: make this run faster or leaner
/convert: translate this into another language
/schema: design the data structure
/api: sketch out the endpoint design
/secure: check this for security holes
/compare: weigh multiple options side by side
/proscons: list the upside and the downside
/decide: recommend one option and defend it
/priority: rank these by what matters most
/root: find the actual root cause
/data: pull the signal out of this data
/pattern: spot the trend hiding in this
/assumption: surface what i'm assuming without saying it
/verify: fact-check this before i use it
/counter: give the counter-argument
/simplify: cut this down to its essentials
/improve: sharpen something that already exists
/automate: find a way to make this repeatable
/reusable: build something i can use again and again
/habit: turn this into a daily practice
/frame: build a structured framework
/gridit: organize options into a decision grid
/reverse: work backward from the result i want
/roleplay: simulate a realistic scenario
/pushback: challenge me before i commit to this
/finalcheck: do one last pass before i ship this
/allin: give me your strongest, most complete answer
```

Os 14 do post, para o chatgpt, em português como no original (nó 100):

```text
/human: escrita natural e semelhante a humana
/expert: respostas de nível especialista
/ceo: análise de mentalidade de fundador
/viral: ideias de conteúdo de alto engajamento
/seo: conteúdo otimizado para buscas
/critic: encontre fraquezas e falhas
/teacher: explique de forma clara e simples
/eli5: explique como se eu tivesse 5 anos
/brief: resposta mais curta possível
/strategy: modo de planejamento a longo prazo
/copywriter: texto persuasivo para marketing
/research: modo de pesquisa profunda
/brainstorm: gerar ideias criativas
/promptengineer: melhorar qualquer prompt
```

- /human: escrita natural, com jeito humano
/expert: resposta em nível de especialista
/ceo: análise com cabeça de fundador
/viral: ideias de conteúdo de alto engajamento
/seo: conteúdo otimizado para busca
/critic: achar fraquezas e falhas
/teacher: explicar com clareza e simplicidade
/eli5: explicar como para uma criança de cinco anos
/brief: a resposta mais curta possível
/strategy: modo de planejamento de longo prazo
/copywriter: texto de marketing persuasivo
/research: modo de pesquisa profunda
/brainstorm: gerar ideias criativas
/promptengineer: melhorar qualquer prompt
/summarize: resumir os pontos principais
/simplify: simplificar conteúdo complexo
/detailed: explicação completa
/stepbystep: explicar passo a passo
/examples: dar exemplos práticos
/analyst: analisar dados ou informação
/compare: comparar várias opções
/proscons: mostrar vantagens e desvantagens
/decision: ajudar a tomar a melhor decisão
/planner: montar um plano acionável
/roadmap: criar um caminho até uma meta
/action: transformar ideias em passos
/prioritize: ordenar tarefas por importância
/productivity: melhorar a produtividade
/focus: identificar a tarefa mais importante
/time: montar um plano de gestão de tempo
/learn: montar um plano de aprendizado
/study: criar uma estratégia de estudo
/quiz: testar conhecimento com perguntas
/flashcards: criar fichas de estudo
/interview: preparar para entrevista
/resume: melhorar o currículo
/career: orientação de carreira
/mentor: responder como mentor pessoal
/coach: dar orientação prática
/consultant: recomendações profissionais
/editor: melhorar clareza e qualidade
/proofread: achar erro de gramática e ortografia
/rewrite: reescrever com melhor redação
/professional: deixar a escrita profissional
/casual: deixar a escrita conversacional
/friendly: deixar a escrita calorosa
/persuasive: deixar a mensagem mais convincente
/concise: tirar palavras desnecessárias
/polish: refinar a versão final
/tone: ajustar o tom da escrita
/storyteller: transformar informação em história
/hook: criar ganchos de atenção
/headline: gerar títulos fortes
/caption: escrever legenda para rede social
/linkedin: criar conteúdo para o LinkedIn
/instagram: criar conteúdo para o Instagram
/youtube: criar conteúdo para o YouTube
/reels: gerar ideias de vídeo curto
/script: escrever roteiro de vídeo ou apresentação
/email: escrever um e-mail eficaz
/sales: criar mensagem voltada a venda
/offer: criar uma oferta irresistível
/brand: desenvolver a mensagem da marca
/customer: pensar da perspectiva do cliente
/audience: analisar o público-alvo
/competitor: analisar concorrentes
/market: analisar oportunidades de mercado
/startup: pensar como estrategista de startup
/business: desenvolver ideias de negócio
/pricing: desenvolver estratégia de preço
/funnel: montar um funil de marketing
/growth: achar oportunidades de crescimento
/content: montar uma estratégia de conteúdo
/calendar: criar um calendário de conteúdo
/ideas: gerar ideias novas
/creative: pensar de forma criativa e diferente
/unpopular: desafiar o pensamento convencional
/devilsadvocate: defender o ponto de vista contrário
/contrarian: achar perspectivas alternativas
/assumptions: identificar pressupostos escondidos
/risks: identificar riscos
/factcheck: separar fato de afirmação
/verify: identificar o que precisa de verificação
/logic: conferir raciocínio e lógica
/rootcause: achar a causa raiz do problema
/debug: achar e corrigir problemas
/solution: gerar soluções práticas
/alternative: sugerir alternativas melhores
/optimize: melhorar uma abordagem existente
/automate: achar formas de automatizar a tarefa
/template: criar um modelo reutilizável
/checklist: criar uma lista de verificação prática
/framework: montar um quadro estruturado
/matrix: organizar opções numa matriz de decisão
/table: converter a informação em tabela
/json: estruturar a resposta em JSON
/roleplay: simular um cenário realista
/reverse: trabalhar de trás para frente a partir do resultado
/ultimate: dar a resposta mais completa *(descrito, não copiado do post; nó 150)*

Os 20 do nó 156, em português como na legenda (nó 156):

```text
/EXPERT responde como especialista sênior, sem simplificar
/CRITIC critica sem amenizar e aponta o que quebra primeiro
/DEEP vai três camadas abaixo da resposta óbvia
/RISK lista os riscos por probabilidade e impacto
/CHANCE dá a chance em % com o raciocínio aberto
/DEVIL assume que você está errado e argumenta contra
/DECISION vira decisão: opções, critérios e uma recomendação
/COMPARE tabela com critérios declarados e veredito
/ALT3 três caminhos diferentes de verdade, não variações
/PLAN etapas com dono, prazo e critério de pronto
/REVIEW revisa com nota de 0 a 10 e devolve corrigido
/ASK3 faz 3 perguntas antes de responder, e espera
/TEACHER ensina do zero com analogia, exemplo e teste
/SOURCE só afirma o que tem fonte com link e data
/RESEARCH cruza 5 fontes e mostra onde elas divergem
/CHECKLIST vira checklist com item verificável
/CANVAS entrega em documento editável, não no chat
/VISUAL entrega diagrama ou fluxo com legenda
/HANDOFF empacota a conversa pra colar em outro modelo
/NATURAL reescreve sem cara de texto de IA
```

**Fontes**

- [nó 33](https://www.instagram.com/reel/DcZHd68SlUI/) @waf_brownie_guilt_free_goodies: Foto de produto de brownies gerada no ChatGPT
- [nó 59](https://www.instagram.com/reel/DdH02q8RjM5/) @ia.dacarol: Comandos de barra para transformar imagens no ChatGPT
- [nó 70](https://www.instagram.com/reel/DctRupJOtMV/) @engineerchirag: "Códigos secretos" para o Claude (atalhos de texto)
- [nó 96](https://www.instagram.com/p/DcjHlzHEgFz/) @reputeforge: 99 atalhos de prompt para o Claude
- [nó 100](https://www.instagram.com/p/Dcs4hcyxJRv/) @pioneirosdigitaisoficial: "Códigos secretos" do ChatGPT (atalhos de texto)
- [nó 150](https://www.instagram.com/p/DdWcr59jbUj/) @web_development_wizard: Noventa e nove atalhos de texto para o ChatGPT
- [nó 156](https://www.instagram.com/reel/DcTsJ4VxJwi/) @eduardocavalcanti: Vinte atalhos de prompt explicados, e o aviso do próprio autor

**Observações.** As listas completas dos nós 70, 96 e 100 estão abaixo, copiadas das imagens; os agrupamentos por função são organização do projeto. O nó 70 repete /artifacts e /devil com descrições diferentes. O conselho de definir o atalho antes de usar vem da legenda do nó 59. Vários posts entregam "a lista completa" por comentário, não no post. A lista do nó 150 foi lida nas nove telas do carrossel, sem código repetido; as descrições estão traduzidas do inglês da tela, e os códigos ficaram como no post. Os 20 do nó 156 estão na legenda, com a função de cada um; a tela só numera os códigos.

**O que não tem aqui.** Nenhum post testa se o atalho realmente muda a saída. O /360view do nó 59 faz o mesmo que a product sheet do nó 47 pedida em português, o que sugere que a convenção importa menos que a clareza do pedido.
