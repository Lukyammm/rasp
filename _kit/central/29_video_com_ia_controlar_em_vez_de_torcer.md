# Vídeo com IA: controlar em vez de torcer

Verbete da central Dominação IA, seção "Vídeo, imagem e voz com IA" (versão de 28/09/2026). Cada item saiu de um post; o "nó" é o número do post, com link em Fontes.

O mesmo problema (a IA muda tudo entre um quadro e outro) com formas diferentes de controle: fixar os extremos, fixar os personagens, partir de uma imagem pronta, editar um vídeo que já existe preservando o movimento e trocando só a textura, e escrever no prompt tudo o que não pode mudar. Um post mostra que estilo e imperfeição também se planejam, e o nó 181 é o único do verbete que entrega o prompt de vídeo inteiro e literal.

*6 fontes · confiança média*

**Fixar os extremos**

- Gerar o primeiro e o último quadro antes de gerar o vídeo: fixa início e fim e tira a aleatoriedade do meio
- Tratar a IA como interpolador entre dois pontos definidos por você, não como geradora da cena inteira
- Deixar a pós-produção fora da IA: o acabamento é feito no editor

**Fixar os personagens**

- Montar folhas de personagem antes de gerar: é o que impede o personagem de mudar de aparência entre as tomadas
- Organizar o roteiro por tomadas dentro da ferramenta, em vez de gerar clipes soltos e montar depois

**Partir de uma imagem pronta**

- Gerar primeiro a imagem, com um prompt, e depois o vídeo a partir dela, com outro, em vez de usar primeiro e último quadro
- O motivo dado é controlar pessoalmente o visual: a imagem fixa o que o vídeo vai mostrar
- Fluxo mostrado na tela: Nano Banana Pro para a imagem, Veo 3.1 para a imagem virar vídeo

**Editar um vídeo que já existe**

- No Higgsfield: Create Video, Video Edit e o modelo Kling 3.0 Omni Edit
- Enviar o vídeo que vai receber o efeito; a tela pede um trecho de até 10 segundos
- Colar o prompt e trocar o @image1 pelo identificador do vídeo enviado (na tela, @Video 1)
- Gerar, e repetir com os outros dois prompts do efeito
- No editor: juntar as versões, pôr por cima o menu de resolução (144p, 240p, 720p, 1080p), tirar o fundo verde e acrescentar a música
- O que faz funcionar: o prompt manda preservar movimento, tempo, ângulo, enquadramento e movimento de câmera exatamente como estão; só a textura muda

**O que denuncia animação de IA**

- Cinco estilos que o post apresenta como impossíveis de imitar: desenho animado dos anos 1980, quadrinho moderno, anime retrô dos anos 1990, desenho clássico e anime brilhante
- O que cada um tem e a geração automática costuma perder: traço áspero, contorno grosso, grão vintage, linha imperfeita e textura
- A virada do post é que todas as imagens foram geradas por IA, e o argumento é que estilo, grão e imperfeição se planejam em vez de se aceitar o resultado padrão

**Revelação de logo animada, com o prompt inteiro**

- O caminho na ferramenta, no nó 181: Google Flow, novo projeto, conferir o tamanho, modelo Omni Flash, uma geração, escolher a duração
- Enviar a logo pelo sinal de mais, esperar carregar, clicar nela e usar a opção de incluir no comando: é isso que amarra a imagem ao prompt
- Se o resultado não agradar, repetir o mesmo comando gera outra versão, sem reescrever o prompt
- Baixar na resolução aumentada, não na prévia
- O prompt controla três coisas separadas: o que preservar da logo (design, cor, proporção e posição exatamente como enviada), o que inventar no fundo (os elementos da própria logo, ampliados, borrados ou parciais, de baixo contraste) e o que proibir (trilha sonora, e qualquer elemento de fundo que compita com a logo ou se sobreponha a ela)
- O som também vai no prompt: sem música, só efeitos limpos sincronizados com cada elemento que aparece
- O tempo é declarado dentro do prompt, não só no seletor da ferramenta: exatamente 5 segundos, com a logo se montando elemento por elemento e o quadro final só com a respiração do brilho

**Ferramentas**

| Ferramenta | Para que | Fontes |
|---|---|---|
| Nano Banana Pro | Criar o personagem, os quadros-chave e a imagem de partida | nó 21, nó 155 |
| Veo 3.1 | Interpolar entre primeiro e último quadro, ou gerar o vídeo a partir de uma imagem | nó 21, nó 155 |
| After Effects | Pós-produção: sincronizar com a batida e aplicar grão de VHS | nó 21 |
| OpenArt | Workspace "Frame to Video" com roteiro por tomadas | nó 40 |
| Higgsfield | Plataforma onde se faz o Video Edit | nó 159 |
| Kling 3.0 Omni Edit | Editar um vídeo existente a partir de um prompt de texto | nó 159 |
| Google Flow | Animar uma logo enviada a partir de um prompt de vídeo, no modelo Omni Flash | nó 181 |

**Prompts e comandos**

Reestilizar o vídeo como pixel art em blocos; um dos três prompts do efeito, lido em três quadros que se sobrepõem (nó 159):

```text
Use @image1 as the mandatory visual-style reference for @vid1. Transform the COMPLETE video into an extremely low-resolution voxel world, as if the entire clip was natively rendered at 144p and then scaled up. Use the largest, coarsest possible cubic blocks — chunky voxel construction, thick stair-stepped edges, minimal texture detail, saturated daylight, hard-edged block shadows, and zero smooth surfaces anywhere. Rebuild every visible element, including the person, out of these oversized cubic blocks so the whole frame reads as heavily pixelated, low-fidelity 3D pixel art — the blockiest version of the three. The person should stay recognizable in his real proportions and pose, just rendered in the same coarse voxel texture as everything else, not simplified into a rigid game-character rig. Preserve his original movement, timing, camera angle, framing, and camera motion exactly as they are. Avoid rounded or tapered smoothing, curved surfaces, soft gradients, glossy plastic, anti-aliasing, blur, or cinematic depth of field.
```

Prompt completo de revelação de logo, copiado da legenda do nó 181 (nó 181):

```text
A modern and energetic brand reveal using the attached logo as the exact reference. Carefully analyze the logo and identify its visual elements, symbols, shapes, or concepts. Create a premium animated background inspired by those elements, incorporating subtle, oversized, low-opacity design details that reinforce the brand identity without distracting from the main logo.

Maintain the original design, colors, proportions, and placement of the logo exactly as provided. The entire animation should last exactly 5 seconds, with the logo progressively assembling during the first few seconds using a dynamic "pop-out" effect. Each letter or logo element should appear one by one with a slight elastic bounce and a soft localized glow that pulses as it lands.

The background should creatively reinterpret elements found within the logo itself. For example, if the logo contains geometric shapes, icons, lines, symbols, or abstract forms, use enlarged, blurred, or partially visible versions of those elements integrated into the background. These background elements should move very subtly, remain low contrast, and never compete with or overlap the primary logo. Their purpose is to enrich the composition while keeping the logo as the unmistakable focal point.

As the logo is fully assembled, a gentle ambient glow should radiate from behind it, creating a refined halo effect. The completed logo should remain on screen for the final moment with only subtle glow breathing and minimal background motion.

Do not include any background music or soundtrack. Use only clean, premium sound effects synchronized with the animation, such as subtle pop sounds, soft whooshes, light impacts, glow pulses, and elegant UI-style audio accents that enhance each logo element as it appears.

High-end motion graphics, premium brand identity animation, elegant composition, realistic light bloom, smooth easing, ultra-sharp 4K, vertical video (9:16).
```

**Fontes**

- [nó 21](https://www.instagram.com/reel/DZFaK-QMoDe/) @azatapa: Cena de vídeo com Nano Banana Pro e Veo 3.1 (primeiro e último quadro)
- [nó 40](https://www.instagram.com/reel/Dassx-MpCHF/) @heyaastha.ai: Animação 3D estilo Pixar com Claude e OpenArt
- [nó 140](https://www.instagram.com/p/Dc_NJSXDB5L/) @tudormorari.ai: Cinco estilos de animação ditos impossíveis para IA, todos feitos com IA
- [nó 155](https://www.instagram.com/reel/DZVTMk0Mu8K/) @azatapa: Vídeo a partir de imagem pré-gerada, em vez de primeiro e último quadro
- [nó 159](https://www.instagram.com/reel/DdOTVZ5B_2w/) @reputeforge: Efeito de vídeo pixelado no Higgsfield com Kling 3.0 Omni Edit
- [nó 181](https://www.instagram.com/reel/DcC8Z4xsUkF/) @owesley.sanja: Revelação de logo animada no Google Flow, com o prompt inteiro

**Observações.** A transcrição do nó 40 é só a fala dos personagens da animação, não explicação de método: as dicas vêm da leitura do workspace mostrado na tela. O nó 140 não mostra prompt nem ferramenta: os prompts e o desafio de 30 dias vão por comentário, e não há como verificar que as imagens são geradas além da afirmação do autor. O nó 155 não traz prompt nenhum: os de imagem e de vídeo ficam num canal privado do Telegram. No nó 159, os outros dois prompts vão por comentário, e o vídeo de exemplo é de outra conta, creditada na legenda. No nó 181, o seletor de geração na tela está em 6 segundos enquanto o prompt colado manda durar exatamente 5, e o post não comenta a diferença; conferido em resolução cheia no quadro aos 33 segundos. O tutorial inteiro é feito no celular, e o post não mostra a logo de entrada ao lado do resultado nem diz quantas tentativas foram necessárias.

**O que não tem aqui.** Nenhum post diz quanto custa uma geração. O nó 159 mostra o botão de gerar com 25, sem dizer a unidade, e o nó 181 mostra que o Google Flow trabalha por crédito e oferece 50 créditos extras por dia, mas também não diz o preço de um vídeo. Nada sobre consistência de cenário, só de personagem, e nenhum post compara os métodos de controle entre si.
