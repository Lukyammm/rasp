# MCP contra API: o que cada camada faz

Verbete da central Dominação IA, seção "Prompt e uso de modelo" (versão de 28/09/2026). Cada item saiu de um post; o "nó" é o número do post, com link em Fontes.

Um post explica por que o MCP não substitui a API, seguindo o problema desde o começo: uma integração é simples, cinco já custam, e pôr um modelo de IA no meio não tira nenhuma delas da sua mão. O que o protocolo resolve é outra coisa, a descoberta: o servidor avisa sozinho o que sabe fazer, e o modelo escolhe sem ninguém ter programado a escolha. É o único material do acervo sobre arquitetura de integração, e explica mecanismo em vez de listar ferramenta.

*1 fonte · confiança alta*

**O problema, antes do protocolo**

- Uma API é dois softwares conversando: o aplicativo manda a requisição, o serviço devolve os dados, e acabou
- O custo aparece na escala: para cada serviço alguém escreve a integração, configura a autenticação, faz as chamadas, trata erro, repete quando falha e entende uma resposta em formato diferente
- Pôr um modelo de IA no meio não tira nenhuma integração da mão de ninguém: o modelo entende o pedido e decide qual ação precisa acontecer, mas quem executa é o software em volta dele
- Sem interface padrão, o segundo aplicativo de IA da mesma empresa refaz as mesmas integrações, e cinco viram dez, escritas duas vezes por pessoas que nem sabem uma da outra

**O que o MCP acrescenta**

- É um protocolo comum: cada serviço pode ter um servidor MCP, e todos expõem o que sabem fazer no mesmo formato
- A descoberta de ferramentas é a parte que muda o jogo: o servidor avisa sozinho o que oferece, o aplicativo entrega essa lista ao modelo, e ele escolhe a ferramenta certa sem ninguém ter programado a escolha antes
- No exemplo do servidor MCP do GitHub, a chamada tools/list devolve as capacidades disponíveis, e cada uma vem com a assinatura: list_issues(repo, state), get_pull_request(number), search_code(query) e create_issue(title, body)
- Por baixo, o servidor MCP executa chamando a mesma API de sempre: ela nunca saiu de cena

**As quatro camadas**

- Camada 1, aplicações de IA: o aplicativo e o modelo
- Camada 2, MCP: as ferramentas e o protocolo
- Camada 3, APIs: HTTP e SDK
- Camada 4, serviços: o GitHub, o Notion, o banco de dados
- A tese, escrita na última tela: MCP e API não são a mesma coisa, porque descoberta padronizada e funcionalidade real também não são

**Fontes**

- [nó 180](https://www.instagram.com/reel/DdIcvsgDS1u/) @fabianocarvalhojr: MCP contra API: o que cada camada faz

**Observações.** O post é explicação conceitual, em nove telas numeradas de uma série de notas visuais de arquitetura. Não mostra código de servidor MCP escrito, não cita implementação e não mede ganho nenhum. Os cinco serviços do exemplo (GitHub, Gmail, Jira, Notion e o banco de usuários) ilustram o problema e não são recomendação. As assinaturas de tools/list são o desenho do autor para o servidor MCP do GitHub, não a documentação oficial dele: foram lidas em resolução cheia nos quadros aos 1m21s e 1m50s.

**O que não tem aqui.** Nenhum post do acervo mostra um servidor MCP sendo escrito, configurado ou ligado a um aplicativo, nem o que acontece quando o servidor expõe ferramenta demais para o modelo escolher. Os nós 136 e 164 citam MCP como ferramenta pronta, sem explicar a camada.
