# Gastar menos token

Verbete da central Dominação IA, seção "Construir com IA sem parecer que foi IA" (versão de 28/09/2026). Cada item saiu de um post; o "nó" é o número do post, com link em Fontes.

Três frentes distintas: reduzir o que entra (converter arquivo antes de mandar), reduzir o que sai (resposta mais curta) e reduzir o que circula (filtrar saída de terminal e ler o código seletivamente). A primeira é a mais fácil e a mais ignorada.

*3 fontes · confiança média*

**Reduzir o que entra**

- Não mandar PDF direto: uma página pode consumir milhares de tokens
- Converter para Markdown antes de enviar: é o formato que o modelo lê melhor e mais barato

**Reduzir o que sai e o que circula**

- Comprimir o contexto, deixando passar só o que importa
- Filtrar a saída do terminal antes de chegar ao modelo
- Fazer o modelo ler só a parte relevante do código, em vez do repositório inteiro
- Isolar saída bruta fora do contexto

**Ferramentas**

| Ferramenta | Para que | Fontes |
|---|---|---|
| MarkItDown (Microsoft) | Converte PDF, Word, PowerPoint e vídeo do YouTube em Markdown | nó 88 |
| Caveman | Faz o modelo responder de forma telegráfica | nó 79 |
| RTK | Proxy que filtra a saída do terminal | nó 79 |
| code-review-graph | Usa grafo para o modelo ler só o que importa | nó 79 |
| Context Mode | Isola saída bruta em SQLite | nó 79 |
| Headroom | Camada de compressão de contexto | nó 13 |

**Fontes**

- [nó 13](https://www.instagram.com/reel/DbqfZusDXwO/) @oguiadaia: Cinco plugins e ferramentas para o Claude Code
- [nó 79](https://www.instagram.com/reel/DboRCyBD0jo/) @oguiadaia: Cinco repositórios para gastar menos tokens no Claude Code
- [nó 88](https://www.instagram.com/reel/DbUQ-h1BwXJ/) @marcelaluzzio: Não envie PDF ao Claude: converta com o MarkItDown

**Observações.** ATENÇÃO aos números: as porcentagens de economia do nó 79 (98%, 75%, 60-90%, 49x) são alegações do vídeo, sem nenhuma verificação. A direção é correta; a magnitude não é confiável. O nome do quinto repositório não foi confirmado na tela.

**O que não tem aqui.** Ninguém mede antes e depois de forma reproduzível. Não há comparação de qualidade da resposta com e sem compressão.
