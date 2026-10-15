# Fluxo de design com IA

Verbete da central Dominação IA, seção "Design e direção de arte" (versão de 28/09/2026). Cada item saiu de um post; o "nó" é o número do post, com link em Fontes.

Três tutoriais com a mesma estrutura de três tempos, que é o achado: preparar os insumos, transformá-los em algo detalhado que a IA siga (um pedido escrito por ela ou um design system) e só então gerar. Ninguém pede a peça pronta de primeira.

*3 fontes · confiança média*

**Interface (nó 84)**

- Criar primeiro um design system, antes de pedir qualquer tela
- Buscar referência visual real (Behance, Figma ou Pinterest) em vez de descrever o estilo por escrito
- Escolher uma referência completa, com fontes, cores, grid e ícones: com referência crua você precisa especificar o resto, senão o Claude Design inventa
- Trazer as imagens de referência e entregá-las junto com exemplos do seu próprio design system
- Antes de gerar, ele faz perguntas: responder com o que você tiver ou clicar em "decida por mim"
- Usar o Opus 5 com esforço Extra ao criar o design system

**Interface a partir do clima das referências (nó 117)**

- Começar pelas referências visuais e pelo clima que você quer, num quadro do Pinterest
- Transformar o quadro num design system com o Claude Code: cor, tipografia, espaçamento e regras de imagem
- No exemplo, as regras de imagem ganham nome (flagrado e não posado, enevoado, brilho quente sobre névoa fria, espontâneo e não clínico), o tratamento de cor vai em CSS igual para todas as imagens em vez de uma a uma no Photoshop, e o recorte deixa o assunto num terço com espaço para o texto
- Entregar o design system ao Claude Design, que gera várias direções de uma vez dentro dessas regras
- Ajustar direto no canvas em vez de gerar tudo de novo e perder o que já estava bom

**Mockup de marca (nó 64)**

- Entregar logo, paleta e fotos de produto organizados numa pasta antes de pedir qualquer coisa
- Fazer a IA escrever o prompt com direção de arte explícita: intenção, iluminação, emoção e direção
- Salvar as imagens em pastas por tipo de peça: roupa, outdoor, dispositivos, loja, ecobag

**Ferramentas**

| Ferramenta | Para que | Fontes |
|---|---|---|
| Claude Design (claude.ai/design) | Criar o design system e gerar a interface | nó 84, nó 117 |
| Behance | Referência visual real | nó 84 |
| ChatGPT | Baixar em lote as imagens de referência | nó 84 |
| Claude Code | Transformar o quadro de referências em design system | nó 117 |
| Pinterest | Quadro de referências e clima, que vira o design system | nó 117 |

**Prompts e comandos**

Auxiliar (nó 84):

```text
Baixe as imagens desse projeto e salve na minha pasta downloads.
```

**Fontes**

- [nó 64](https://www.instagram.com/p/DcxGYORDN3C/) @thehelderpenaloza: Mockups de marca gerados com Claude e skill própria
- [nó 84](https://www.instagram.com/reel/DdMjjtITgul/) @matheusgomes: Interfaces bonitas com o Claude Design e referências do Behance
- [nó 117](https://www.instagram.com/reel/DafmOoWIdn5/) @uxgoodies: Do quadro de referências ao site: design system no Claude Code e páginas no Claude Design (patrocinado)

**Observações.** O nó 84 é Parte 1 de uma série e termina antes do resultado final. A skill do nó 64 é própria do autor e não é distribuída: o fluxo é reproduzível, a skill não. O nó 117 é patrocinado pela Anthropic: a autora se declara parceira do Claude, chama o projeto de prévia e diz que o Claude Design ainda está no começo. O fluxo é reproduzível; o elogio à ferramenta é publicidade.

**O que não tem aqui.** Nenhum dos três compara o resultado com uma tentativa sem o processo: o ganho do método é afirmado, não demonstrado. O nó 117 mostra o resultado, mas é patrocinado.
