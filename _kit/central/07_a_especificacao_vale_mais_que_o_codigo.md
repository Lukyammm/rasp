# A especificação vale mais que o código

Verbete da central Dominação IA, seção "Construir com IA sem parecer que foi IA" (versão de 28/09/2026). Cada item saiu de um post; o "nó" é o número do post, com link em Fontes.

A ideia mais interessante do acervo, e vem de dois posts que à primeira vista são só demonstração. Ambos mostram que o trabalho migrou para antes da geração: o que define o resultado é a especificação e a decomposição do problema, não o prompt.

*2 fontes · confiança média*

**A tese**

- Uma demo gráfica em WebGPU foi construída inteira pelo modelo a partir de uma especificação técnica de cerca de 10 páginas
- Investir na especificação em vez de no código: a spec passa a contar mais que a qualidade do código escrito

**Decompor em vez de pedir o todo**

- Pedir à IA que escreva a geometria 3D em código em vez de modelar no Blender: fica mais leve (~200 KB a cena inteira) e dá para manipular depois
- Gerar primeiro uma imagem-base do cenário e usá-la como referência para a IA montar a cena
- Converter elemento por elemento a partir de uma imagem de referência de cada um, em vez de pedir a cena pronta

**Ferramentas**

| Ferramenta | Para que | Fontes |
|---|---|---|
| Claude Opus 5 | Gerou a demo WebGPU do início ao fim | nó 29 |
| ChatGPT | Gerar a imagem-base do cenário | nó 31 |

**Fontes**

- [nó 29](https://www.instagram.com/reel/Dbbr8FgPwt-/) @daviduarte.ia: Demonstração em WebGPU feita só com o Claude Opus 5
- [nó 31](https://www.instagram.com/reel/DcgjDwEppLa/) @_gustavocampelo: Site 3D de Minecraft com modelos escritos em código por IA

**Observações.** Os números do nó 29 (9 horas de processamento, 4 milhões de tokens, ~10 páginas de spec) são relato do autor sobre trabalho de terceiro, sem verificação. O nome da skill de conversão de imagem para 3D do nó 31 sai corrompido na transcrição e não foi confirmado.

**O que não tem aqui.** Nenhum dos dois mostra a especificação em si, que é justamente o artefato que interessaria. A tese é sedutora e está sustentada em dois casos únicos, sem contraprova.
