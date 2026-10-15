# Anúncio de produto com IA

Verbete da central Dominação IA, seção "Vídeo, imagem e voz com IA" (versão de 28/09/2026). Cada item saiu de um post; o "nó" é o número do post, com link em Fontes.

Cinco posts, e o padrão é sempre o mesmo em dois tempos: um modelo prepara o insumo visual ou o roteiro, outro gera o vídeo. Ninguém pede o anúncio pronto de uma vez, e é isso que faz funcionar, porque preserva o produto real.

*5 fontes · confiança alta*

**O padrão de dois tempos**

- Etapa 1: a partir da foto do produto, gerar o storyboard (ChatGPT) ou a product sheet (o produto em vários ângulos numa imagem só)
- Etapa 2: entregar esse insumo ao gerador de vídeo (Gemini, Google Flow) com o pedido do comercial

**Detalhes que controlam o resultado**

- Pedir o storyboard com número de tomadas definido (nove, no exemplo) para controlar o ritmo
- As nove tomadas de um storyboard de sérum: hero shot, splash, textura do sérum, textura, ingrediente, aplicação, modelo, lifestyle e quadro final
- Especificar formato, estilo e duração: vertical, estilo UGC, 20 a 25 segundos
- Configurar 9:16 antes de gerar, quando o destino é vertical
- Enviar a foto real do produto e pedir o efeito por escrito, em vez de gerar o produto do zero

**Ferramentas**

| Ferramenta | Para que | Fontes |
|---|---|---|
| ChatGPT | Storyboard e product sheet a partir das fotos | nó 26, nó 33, nó 38, nó 47 |
| Gemini | Gerar o vídeo a partir do storyboard | nó 26, nó 38 |
| Google Flow | Gerar o comercial a partir da product sheet | nó 47 |
| Krea | Gerar vídeo de produto | nó 46 |

**Prompts e comandos**

Etapa 1, storyboard no chatgpt com a foto do produto (nó 38):

```text
Ai story board for brand shoot
Size 9:16
```

Etapa 2, vídeo no gemini com o storyboard anexado (nó 38):

```text
Generate uge style video according to this story board
Size 9:16
```

Etapa 1, variação com barra no começo (nó 26):

```text
/Ai story board for brand shoot
```

Etapa 2, variação; só o começo, o resto aparece recolhido na tela (nó 26):

```text
Create a 20-25 sec vertical 9:16 UGC beauty video for KIKO Milano 3D Hydra Lipgloss using the attached storyboard as the visual reference
```

Pronto (nó 47):

```text
Crie um product sheet desse produto sem texto, apenas o texto que estiver no produto, e o produto de vários ângulos diferentes.
```

Atalho (nó 33):

```text
/gravitydefying: produto flutuando
```

**Fontes**

- [nó 26](https://www.instagram.com/reel/DcnwxdntGsN/) @by.shaaima: Anúncio de gloss com storyboard no ChatGPT e vídeo no Gemini
- [nó 33](https://www.instagram.com/reel/DcZHd68SlUI/) @waf_brownie_guilt_free_goodies: Foto de produto de brownies gerada no ChatGPT
- [nó 38](https://www.instagram.com/reel/Dcs46_lOh2o/) @by.shaaima: Anúncio de sérum com storyboard no ChatGPT e vídeo no Gemini
- [nó 46](https://www.instagram.com/reel/Dc7K3LIAmjt/) @annaflo.dev: Vídeo de produto (boné) feito no Krea
- [nó 47](https://www.instagram.com/reel/DbLxjOlxq5X/) @davidabn_: Animação de produto com ChatGPT e Google Flow

**Observações.** Os pedidos dos nós 26 e 38 foram copiados da tela: são curtos, porque quem carrega o trabalho é o storyboard. O pedido de vídeo do nó 26 aparece recolhido pelo app e só o começo é legível. O prompt do vídeo do nó 47 é oferecido por comentário e não está no post. O nó 47 é publicidade paga de uma marca de camiseta. Os valores do nó 46 (vendido por US$ 3.250 gastando US$ 4) são alegação sem comprovação.

**O que não tem aqui.** O prompt longo de vídeo (nó 47) só vem por comentário; os que aparecem inteiros são curtos e se apoiam no storyboard, então não dá para comparar os dois caminhos. Também não há nada sobre direitos de uso comercial das imagens geradas.
