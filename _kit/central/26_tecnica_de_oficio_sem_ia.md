# Técnica de ofício, sem IA

Verbete da central Dominação IA, seção "Design e direção de arte" (versão de 28/09/2026). Cada item saiu de um post; o "nó" é o número do post, com link em Fontes.

Quatro posts que não usam IA nenhuma e por isso mesmo merecem lugar: são técnica de ferramenta, do tipo que continua valendo independente do modelo da vez.

*4 fontes · confiança média*

**Repetir formas no Illustrator, em três níveis**

- Iniciante: duplicar e redimensionar à mão (trabalhoso e não editável)
- Intermediário: Object > Transform > Scale com cópia repetida
- Avançado: Effect > Distort & Transform > Transform com escala, várias cópias e rotação, gerando uma espiral que continua editável

**Tirar o aspecto digital de uma animação 2D**

- Aplicar textura de papel e granulação sobre formas e texto
- Dessaturar as cores junto com a textura: cor saturada denuncia o digital mesmo com grão aplicado

**Textura grunge no After Effects, passo a passo**

- 1. Camadas: separar a animação em frente e fundo, para a camada de ajuste não vazar no fundo
- 2. Wiggle: Wiggle de posição com velocidade 24 e quantidade 4, imitando a tinta que vaza e o desalinhamento da impressão escaneada
- 3. Scatterize: CC Scatterize 4, Gaussian Blur 5 e Levels no canal alfa, com o ponto branco puxado para a esquerda até estrangular a máscara; é a base do grunge
- 4. Displace: pilha de mapas de deslocamento movidos por texturas animadas e rotação, cada um empurrando 10 pixels na horizontal e na vertical
- 5. Step-print: Posterize Time a 8 quadros por segundo, para o jeito de stop motion
- 6. Textura: texturas nos modos Screen, Difference e Overlay e cintilação de brilho e saturação com Brightness & Contrast e Lumetri Color, imitando erro de escaneamento

**Alternativa de ferramenta**

- O mesmo motion graphics feito no After Effects pode ser recriado no DaVinci Resolve

**Ferramentas**

| Ferramenta | Para que | Fontes |
|---|---|---|
| Adobe Illustrator | Effect > Distort & Transform > Transform para repetição não-destrutiva | nó 94 |
| DaVinci Resolve | Alternativa ao After Effects para motion graphics | nó 55 |
| After Effects | Textura grunge: Wiggle, CC Scatterize, mapas de deslocamento, Posterize Time e Lumetri Color | nó 110 |

**Fontes**

- [nó 55](https://www.instagram.com/reel/DcwcdRiiCRi/) @vantyxvisuals: Motion graphics recriado no DaVinci Resolve comparado ao original
- [nó 92](https://www.instagram.com/reel/DaosWlez72O/) @arizonaboba: Antes e depois de textura em animação 2D
- [nó 94](https://www.instagram.com/reel/DcG_nWECJ6v/) @pixelwizardfx: Três níveis de técnica no Adobe Illustrator
- [nó 110](https://www.instagram.com/reel/Da2k8pOza9e/) @arizonaboba: Textura grunge no After Effects: seis passos com os valores

**Observações.** O valor de 72% de escala no nó 94 é o do exemplo, não uma regra. O nó 92 só mostra o antes e depois; o processo, da mesma autora, está no nó 110, com os valores na tela e na legenda. Os valores são os do projeto dela, não regra, e o arquivo de projeto oferecido no link da bio não foi baixado. O nó 55 mostra o resultado equivalente, não como fazer.

**O que não tem aqui.** O nó 55 não ensina o caminho no DaVinci, só prova que dá.
