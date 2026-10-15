# Front-end: estrutura, bibliotecas e microinteração

Verbete da central Dominação IA, seção "Construir com IA sem parecer que foi IA" (versão de 28/09/2026). Cada item saiu de um post; o "nó" é o número do post, com link em Fontes.

Três camadas do front-end que aparecem no acervo: a marcação que diz o que cada bloco da página é, as bibliotecas de animação por especialidade, e a microinteração que transforma espera em resposta.

*4 fontes · confiança média*

**Estrutura semântica da página**

- O nó 178 mostra o mesmo leiaute duas vezes, primeiro com cinco div e depois com cinco tags semânticas na mesma posição: header no topo, section e aside lado a lado, article abaixo do section e footer no rodapé
- O motivo declarado na tela: excesso de div prejudica semântica, acessibilidade e SEO
- O ganho declarado na tela: tags semânticas deixam o HTML mais organizado, acessível e fácil de entender

**Bibliotecas de animação, por especialidade**

- GSAP: animação ligada ao scroll
- Anime.js: animações vetoriais
- Motion.dev: animações em bloco
- React Spring: física realista

**Microinteração**

- Uma microinteração no botão de confirmação transforma espera em feedback: o estado final confirma o pedido em vez de só sumir
- Navbar com indicador que desliza entre abas comunica onde você está sem texto adicional

**Ferramentas**

| Ferramenta | Para que | Fontes |
|---|---|---|
| GSAP | Animação de scroll | nó 17, nó 31 |
| Anime.js | Animações vetoriais | nó 17 |
| Motion.dev | Animações em bloco | nó 17 |
| React Spring | Animação com física realista | nó 17 |
| Framer Motion | Animação das abas de navegação, com React e CSS | nó 18 |

**Fontes**

- [nó 17](https://www.instagram.com/reel/Da292PShs6w/) @erickcastilio.ia: Quatro bibliotecas de animação para sites (GSAP, Anime.js, Motion, React Spring)
- [nó 18](https://www.instagram.com/reel/Dc3chX6zlR6/) @code.xr: Barras de navegação com abas animadas em React
- [nó 76](https://www.instagram.com/reel/Db_GsVnNvKl/) @iusmanshams: Microinteração de botão de pedido com caminhão
- [nó 178](https://www.instagram.com/reel/DZVo1w0AfN0/) @devmedia.com.br: Trocar excesso de div por tags semânticas do HTML5

**Observações.** Nos nós 18 e 76 o código aparece na tela mas não foi transcrito por inteiro: dá para entender a técnica, não para copiar o componente. O nó 178 não tem fala: os dois cartões são todo o conteúdo, e foram lidos em resolução cheia nos quadros aos 1 e aos 9 segundos. O post termina em oferta de mentoria com desconto por comentário.

**O que não tem aqui.** Nenhum post compara peso, desempenho ou curva de aprendizado entre as bibliotecas. Nada sobre animação e acessibilidade (prefers-reduced-motion). O nó 178 entrega só os nomes e a posição de cinco tags. Nenhum post do acervo diz quando usar section em vez de article, cita as outras tags semânticas do HTML5 (nav, main, figure, time) nem mostra código escrito.
