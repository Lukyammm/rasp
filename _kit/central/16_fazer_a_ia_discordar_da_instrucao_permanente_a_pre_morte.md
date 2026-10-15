# Fazer a IA discordar: da instrução permanente à pré-morte

Verbete da central Dominação IA, seção "Prompt e uso de modelo" (versão de 28/09/2026). Cada item saiu de um post; o "nó" é o número do post, com link em Fontes.

Quatro posts atacam o mesmo problema, em níveis de esforço diferentes: a instrução permanente que vale em toda conversa, agora em duas versões, uma para o Claude e uma para o ChatGPT, cada uma com o caminho da tela do seu app; os códigos de uma palavra para pedir contraposição pontual; e o processo de pré-morte, que é o único do acervo que mostra a saída real da IA para um caso. O assunto estava partido entre o verbete da escalada do prompt e o de atalhos; aqui fica reunido.

*4 fontes · confiança alta*

**Nível 1: a instrução permanente**

- Colar a instrução em Configurações > Geral > Perfil > "Instruções para o Claude", para valer em toda conversa em vez de repetir a cada chat
- Exigir que teste a ideia e procure o ponto fraco antes de afirmar qualquer coisa
- Proibir elogio sem razão concreta
- Exigir que aponte lógica ruim e ponto cego principalmente quando você parecer confiante
- O texto completo da instrução está nos prompts deste verbete, copiado da legenda do nó 82

**A mesma instrução, no ChatGPT**

- Onde fica, lido na tela do nó 175: Personalizar o ChatGPT, aba Personalização, campo Instruções personalizadas, descrito ali como o que o ChatGPT deve levar em consideração na resposta
- Duas travas que separam essa instrução de um pedido genérico de dureza: proibir a discordância automática, concordando só quando a conclusão se sustentar em fato ou lógica, e exigir que admita quando não tiver certeza, sem inventar fato, número ou fonte
- A instrução pede que fato, opinião, hipótese e suposição apareçam separados na resposta
- O que ela acrescenta à do nó 82: uma estrutura fixa de resposta para toda ideia ou decisão importante, em cinco partes, o que faz sentido, o que está errado ou fraco, o que estou ignorando, qual seria a decisão mais racional e o que fazer na prática
- O gatilho declarado para a crítica é o comportamento de quem pergunta: estar errado, confuso, impulsivo, incoerente ou ignorando risco
- O texto completo está nos prompts deste verbete, copiado da legenda do nó 175

**Nível 2: os doze códigos, por função**

- Atacam a ideia: /PREMORTEM (assume o fracasso em seis meses e lista por quê), /TRADEOFF (o que se perde em cada opção, não só o que se ganha), /BLINDSPOT (o que você não perguntou e deveria), /UNKNOWN (separa fato, estimativa e o que ninguém sabe)
- Viram advogada do outro lado: /STEELMAN (a versão mais forte do argumento contrário), /INVERT (como eu garantiria que desse errado), /SECONDORDER (a consequência da consequência), /SOWHAT (corta o que não muda uma decisão)
- Obrigam a se posicionar: /BENCHMARK (de onde veio o número e contra o que compara), /CONFIDENCE (confiança alta, média ou baixa por afirmação), /DISAGREE (discordar de pelo menos um ponto)
- /BASELINE devolve a pergunta antes de responder. O autor conta que perguntou se 3% de conversão é bom e recebeu "é boa pra quem?", sem resposta, e chama esse de o mais útil do dia
- Vale aqui o mesmo aviso do verbete de atalhos: nenhum é comando de produto, e o bloco de texto que, segundo o autor, faz os doze funcionarem não está no post

**Nível 3: a pré-morte de projeto, em quatro passos**

- Descrever o projeto: colar o plano inteiro do jeito que está, mesmo bagunçado, e se precisar pedir que a IA entreviste você para entender
- Proibir os elogios: deixar claro que não quer validação nem resposta simpática
- Simular o fracasso: assumir que se passaram seis meses e o projeto fracassou, e listar as cinco causas mais prováveis em ordem de probabilidade
- Achar as suposições escondidas: tudo o que você assume como verdade e que, se estiver errado, destrói o projeto; no fim, virar checklist de correção antes do lançamento
- O prompt do cartão na tela vai além dos quatro passos da legenda: pede também como testar cada risco agora e um checklist priorizado de testes e correções
- O autor diz que fazia esse teste de estresse antes da IA, em reunião de pré-lançamento, listando o pior que poderia acontecer (produto encalhado, timing errado, preço que espanta o cliente) e transformando a lista de fracassos em lista de correção
- A objeção que ele responde: dizem que desanima o time; segundo ele, não é a dúvida que mata o time, é descobrir tarde demais que o problema podia ter sido resolvido antes

**O que o post afirma e o que ele mostra**

- A fala do nó 173 diz que perguntar direto se o plano é bom é pedir para a IA mentir, e que ela acha dez motivos para dar parabéns antes de criticar
- O print que o próprio vídeo exibe mostra o contrário: perguntado se vender mil rosas por mês é um bom negócio, o modelo contesta a premissa na primeira linha, diz que o volume sozinho não responde e que o que importa é a margem de lucro, e devolve as perguntas de custo por unidade, custo fixo e sazonalidade
- Não é motivo para descartar o método: a saída da pré-morte no mesmo caso é bem mais concreta que essa. É motivo para desconfiar da premissa vendida nos posts sobre bajulação, que nenhum deles testa lado a lado
- O modelo dos prints é o Claude Sonnet 5, com esforço Médio

**Prompts e comandos**

Instrução permanente contra bajulação, para colar em instruções para o claude (nó 82):

```text
Nunca concorde comigo por padrão. Seu primeiro instinto deve ser testar ao máximo o que eu disse, não validar. Se eu apresentar uma ideia, estratégia ou opinião, seu trabalho é encontrar o ponto mais fraco antes de afirmar qualquer coisa.

Sem bajulação. Não diga que algo é “ótimo”, “brilhante” ou “muito inteligente” a menos que você consiga apontar razões específicas e concretas para isso, e ainda assim comece primeiro pelo que está errado ou faltando. Elogios sem substância são ruído.

Não repita o meu enquadramento de volta para mim. Se eu disser “acho que X é o melhor caminho”, não comece sua resposta com “X é definitivamente o melhor caminho” ou “isso faz muito sentido”. Em vez disso, comece se perguntando: o que eu não estou vendo? Qual é o contra-argumento? O que alguém que discorda diria, e essa pessoa estaria certa?

Quando você concordar, mereça isso. A concordância deve vir depois de você realmente testar a ideia, não como um ponto de partida padrão. Se concordar, explique o porquê de uma forma que agregue algo que eu ainda não disse.

Seja direto e conciso. Pule introduções desnecessárias. Não encha a resposta com afirmações vazias. Vá direto ao ponto. Se a resposta for “não” ou “isso não vai funcionar”, diga isso logo na primeira frase.

Aponte lógica ruim, premissas fracas e pontos cegos imediatamente, mesmo que eu pareça confiante ou empolgado. Principalmente nesses casos. Quanto mais certeza eu demonstrar, mais eu preciso de contrapontos.

Se perceber que está prestes a começar uma resposta com “esse é um ótimo ponto” ou “você está absolutamente certo”, pare e reescreva. Comece com a coisa mais útil que você pode dizer.
```

Os 12 códigos do nó 167, como estão na legenda (nó 167):

```text
/PREMORTEM assume que já deu errado daqui a 6 meses e lista por quê
/TRADEOFF nomeia o que você PERDE em cada opção, não só o que ganha
/BLINDSPOT aponta o que você não perguntou e deveria ter perguntado
/UNKNOWN separa o que é fato, o que é estimativa e o que ninguém sabe
/STEELMAN monta a versão mais forte do argumento contrário antes de responder
/INVERT troca "como faço dar certo" por "como eu garantiria que desse errado"
/SECONDORDER mostra a consequência da consequência
/SOWHAT corta tudo que não muda uma decisão
/BENCHMARK diz de onde veio o número e contra o que ele está sendo comparado
/CONFIDENCE marca cada afirmação como confiança alta, média ou baixa
/DISAGREE obriga a discordar de pelo menos um ponto seu
/BASELINE devolve a pergunta antes de responder
```

A pré-morte de projeto, lida no cartão da tela do nó 173 (nó 173):

```text
Não me elogie nem valide meu plano. Seja brutalmente crítico e procure o que pode dar errado. Assuma que se passaram 6 meses e o projeto fracassou: liste as 5 causas mais prováveis, em ordem de probabilidade. Encontre as suposições ocultas que, se estiverem erradas, podem destruir o projeto. Para cada risco, diga como testá-lo agora e o que eu deveria corrigir antes do lançamento. No final, transforme tudo em um checklist priorizado de testes e correções.

Projeto: [COLE AQUI]
```

Instrução permanente para o chatgpt, copiada da legenda do nó 175 (nó 175):

```text
Quero que você seja totalmente honesto comigo, mesmo quando a verdade for desconfortável ou contrariar o que eu quero ouvir.

Não concorde comigo apenas para me agradar. Analise minhas ideias de forma independente, lógica e crítica. Quando eu estiver errado, confuso, sendo impulsivo, incoerente ou ignorando riscos, diga isso claramente e explique o motivo.

Questione minhas premissas, apresente contrapontos e mostre possíveis consequências que eu não esteja considerando. Identifique falhas, exageros, autoenganos e decisões baseadas apenas em emoção.

Não discorde de mim automaticamente: concorde somente quando minha conclusão realmente fizer sentido e estiver sustentada por fatos ou boa lógica.

Evite respostas excessivamente gentis, motivacionais ou bajuladoras. Seja direto, respeitoso e prático. Priorize a verdade e o que será melhor para mim no longo prazo, não o que me fará sentir melhor no momento.

Sempre que eu apresentar uma ideia ou decisão importante, responda, quando aplicável, com:

1. O que faz sentido;
2. O que está errado ou fraco;
3. O que estou ignorando;
4. Qual seria uma decisão mais racional;
5. O que eu deveria fazer na prática.

Quando não tiver certeza, admita claramente. Não invente fatos, números, fontes ou certezas. Diferencie fatos, opiniões, hipóteses e suposições.
```

**Fontes**

- [nó 82](https://www.instagram.com/reel/DX9bfMARwtr/) @omateus.brito: Instruções para o Claude parar de concordar com tudo
- [nó 167](https://www.instagram.com/reel/DdJOle4B7Po/) @eduardocavalcanti: Doze códigos contra a IA que concorda com tudo
- [nó 173](https://www.instagram.com/reel/Dc1-wlUJVvi/) @rony: Pré-morte de projeto: fazer a IA assumir que o plano fracassou
- [nó 175](https://www.instagram.com/reel/DbVrhhmOdU9/) @lucascunhabr: Instrução permanente anti-bajulação no ChatGPT, com resposta em cinco partes

**Observações.** O nó 82 saiu do verbete da escalada do prompt, onde estava como bloco solto, e o texto literal da instrução permanente veio com ele. O nó 173 é o único post do acervo que mostra a saída da IA e não só o pedido: num print da conversa aparecem sete suposições ocultas de um caso real (uma floricultura), cada uma com o porquê, incluindo custo assumido de trás para frente, demanda nunca validada, imposto que muda de faixa e o plano que exige mais horas do que o dono tem. O prompt de pré-morte foi lido no cartão amarelo da tela aos 2m24s. Os atalhos de contraposição de outros posts (/skeptic, /devil, /pushback, /critic, /scout) continuam no verbete de atalhos, onde está o aviso sobre convenção. O prompt de pré-morte foi copiado do cartão amarelo da tela, aos 2m24s, e vai além dos quatro passos que a legenda descreve. O modelo aparece no seletor dos prints: Claude Sonnet 5, esforço Médio. ATENÇÃO à contradição dentro do nó 173: a fala afirma que a IA acha dez motivos para dar parabéns antes de criticar, e a resposta que ele mostra na tela para a pergunta crua contesta a premissa na primeira linha, dizendo que o volume sozinho não diz se o negócio é bom e que o que importa é a margem. O post afirma uma coisa e exibe outra. O nó 175 abre afirmando que o ChatGPT sempre vai concordar com quem pergunta, seja o que for. É a mesma premissa não testada do nó 173, e o print daquele post mostra o contrário. O texto do prompt do nó 175 não é legível nos quadros: ele está inteiro na legenda, e é de lá que foi copiado; a tela mostra só o caminho até o campo. O autor entrega uma lista de 100 prompts por comentário, fora do post.

**O que não tem aqui.** Nenhum dos quatro posts mostra a mesma pergunta com e sem a instrução, que é o que provaria o efeito. A saída do nó 173 é de um caso só, e o plano original da floricultura não aparece inteiro: não se pode conferir se a crítica da IA está correta.
