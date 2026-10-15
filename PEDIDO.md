# PEDIDO: logo do RASP, rodada 4 (imagens)

Data: 12/10/2026. Quem pede: Claude, a pedido do Lukyam.

## O que fazer

Gerar 3 imagens, uma por direção de símbolo (A, B e C abaixo), com o seu gerador de imagem. Cada imagem é
uma prancha de identidade no mesmo formato da que o Lukyam aprovou como referência visual (fundo escuro,
painéis lado a lado). Use o prompt de cada direção como está; se precisar ajustar, anote o que mudou.

## Onde salvar

`marca\_opcoes_v4\rodada4\` (criar a pasta). Nomes: `A_lamina_frontal.png`, `B_lamina_volume.png`,
`C_duas_laminas.png`. Se gerar mais de uma tentativa por direção, salvar todas com sufixo `_2`, `_3`.

## O que não fazer

- Não mexer em nenhum outro arquivo: nada em `marca\` fora da pasta `rodada4\`, nada em `frontend\`,
  `backend\`, `build_brand_assets.py`. A logo atual continua em uso até o Lukyam decidir.
- Não apagar nem "organizar" nada.
- Não escrever que algo foi "resolvido" ou "otimizado para 16px". A imagem gerada não prova isso; o teste
  de tamanho pequeno o Claude faz depois, a partir do vetor.

## Formato da volta

Um arquivo `marca\_opcoes_v4\rodada4\LEIAME.txt` com, para cada imagem: nome do arquivo, o prompt exato
usado e quantas tentativas foram feitas. Só isso.

## Como o Claude vai conferir

Abrir cada prancha reduzida; medir as cores do painel chapado por script (têm que bater com os hex abaixo);
redesenhar o painel chapado em vetor e testar em 16, 32 e 64px de verdade.

---

## Regras que valem para os 3 prompts

Colar no fim de cada prompt:

> Paleta exata, sem outras cores: cobalto #1D4ED8, cobalto escuro #1739A8, terracota #C2410C, fundo
> obsidian #090A0F, alabastro #FAF8F5. O único texto permitido na imagem inteira é a palavra RASP no
> lockup, em fonte geométrica sem serifa extra negrito (estilo Plus Jakarta Sans ExtraBold), espaçamento
> levemente apertado. Nenhum outro texto, legenda, título, número, código de cor ou rótulo em lugar
> nenhum. Proporção 16:9, fundo #090A0F liso, sem grade, sem linhas de construção, sem brilho, sem neon,
> sem reflexo. Estilo de marca de software premium, limpo, como um guia de marca da Linear ou da Stripe.

Layout da prancha (igual para as 3):

> Prancha de identidade visual em quatro painéis lado a lado, separados por espaço vazio:
> 1) o símbolo grande, renderizado com volume suave;
> 2) o mesmo símbolo em versão chapada: só cores sólidas, sem gradiente, sem sombra, sem volume, como um
>    ícone vetorial de duas ou três cores;
> 3) dois ícones de aplicativo em quadrado de cantos arredondados, um com fundo #090A0F e outro com fundo
>    #FAF8F5, usando a versão chapada;
> 4) o lockup: versão chapada do símbolo à esquerda e a palavra RASP à direita em #FAF8F5, com a altura das
>    letras igual à altura do símbolo.

## Prompt A: lâmina única, de frente

> Símbolo de logo: uma única lâmina quadrada cobalto #1D4ED8 vista de frente, com cantos levemente
> arredondados. O canto superior direito está dobrado para dentro em diagonal, como a ponta de uma folha
> raspada e levantada, e a dobra é grande, ocupando cerca de um terço da lâmina. O verso da dobra é
> terracota #C2410C e é o ponto de atenção do símbolo. Geometria simples, reconhecível em tamanho de
> favicon. Nada de pilha, nada de camadas extras.
> [layout da prancha] [regras]

## Prompt B: lâmina única com volume

> Símbolo de logo: uma única placa espessa cobalto #1D4ED8 em perspectiva isométrica de 30 graus, com a
> face de cima lisa e as laterais em #1739A8. O canto da frente à direita da face de cima está sendo
> descascado e curvado para cima, como uma camada fina sendo raspada, mostrando o verso terracota #C2410C.
> A curva da dobra é grande e generosa. Só uma placa: nenhuma placa empilhada embaixo.
> [layout da prancha] [regras]

## Prompt C: duas lâminas

> Símbolo de logo: duas placas finas cobalto #1D4ED8 em perspectiva isométrica de 30 graus, separadas por
> um espaço visível. A placa de baixo é inteira e está em #1739A8. A placa de cima está sendo descascada a
> partir do canto direito, curvando para cima e para trás, e o verso que aparece é terracota #C2410C; a
> dobra ocupa quase metade da placa de cima. Exatamente duas placas, nunca três.
> [layout da prancha] [regras]
