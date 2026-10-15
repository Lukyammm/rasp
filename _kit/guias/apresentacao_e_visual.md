# Apresentação, PDF e visual

Para deck (PowerPoint, Google Slides), relatório em PDF, peça gráfica, capa e qualquer tela. Quem vê é cliente e
chefe; cara de template de IA tira credibilidade.

## Partir do modelo da casa

- **A base é a última entrega aprovada daquele cliente, no visual dela**, não um layout novo. Copiar o visual
  inteiro (molduras, cartões, fileiras, cores), não só trocar os números. Se houver mais de uma versão antiga,
  confirmar qual é a aprovada antes de começar.
- **Cliente sem modelo:** o estilo vem dos trabalhos anteriores do usuário, não de um layout inventado.
- **Onde o pptx e o PDF entregue divergem, vale o PDF.**
- **Antes de entregar, renderizar e olhar todos os slides**, um por um, e mostrar as imagens ao usuário: ele quer
  ver, não ler descrição. Com PowerPoint instalado no Windows, exportar pelo próprio PowerPoint
  (`win32com.client.dynamic` no Python). Renderizador próprio de pptx engana (ignora retângulo e preenchimento
  de imagem).
- **O arquivo tem que abrir.** Um pptx editado por script já saiu corrompido: abrir no programa antes de
  entregar.
- **PDF medido:** nada passa da página; rodapé não cresce além do modelo (encurtar o texto antes de aumentar a
  caixa).
- **Print de um slide aponta um padrão, não só aquele slide.** A correção vale para o deck inteiro. Elemento
  repetido em vários slides se corrige no mestre e se confere em todos.

## Deck que vai para o Google Slides

Medido em 2026, convertendo pptx gerado por script:
- a fonte sai mais larga no Google: título com espaço para duas linhas;
- caixa com autoajuste encolhe e o texto sobe: tirar o autoajuste;
- rótulo curto dentro de forma quebra letra a letra: usar caixa de texto;
- gráfico nativo do PowerPoint perde o formato de número: desenhar o gráfico com formas e valores escritos;
- tabela: declarar as quatro bordas (só a de baixo visível) para o Google não desenhar a grade;
- teste de estresse: renderizar com a letra 8% maior e procurar sobreposição. Dizer na entrega se não foi visto
  no Google de verdade.

## Deck que será lido sem ninguém apresentando

- O slide tem que se explicar sozinho: link do que é citado, os valores escritos, miniatura clicável, exemplo
  com imagem e link.
- **Razão sozinha não se entende: mostrar a contagem crua ao lado.** *Caso:* "5.788x" não ficou claro; o cartão
  passou a mostrar as duas contagens que geram a razão.

## Marcas de IA que já saíram de entregas reais

- cartão branco com sombra e canto arredondado sobre fundo cinza-azulado;
- traço colorido curto mais rótulo em caixa alta espaçada em cima de cada bloco;
- fileira de números gigantes (cartões de painel) e grade 2x2 de números;
- lista numerada 01, 02, 03 com título curto, e frase de abertura do tipo "O que os dados mostram";
- marcador redondo mais título em negrito antes do texto;
- setas em link, separador "·", aspas retas misturadas com curvas;
- gradiente, emoji como ícone, três cards em fileira;
- a fórmula "X, não Y" e o mesmo aviso repetido no fim de várias páginas;
- a entrega se justificando, com a regra de bastidor virando texto: *Processamento 100% Local • Zero Token IA*
  carimbado numa imagem exportada, *Paletas Institucionais & Anti-Vibe-Code*, *Cores nobres sem gradientes neon
  clichês*;
- adjetivo de enfeite e termo técnico inflado: *Monocromático Nobre*, *Editorial & Elegante*, *4K Ultra HD* para
  escala de imagem 2D, *Transcrição Fonética* para transcrição comum de fala. Detalhe em `codigo_e_apps.md`.

Rótulo só quando nomeia o que vem abaixo. Número grande sempre com a frase que o explica, na mesma linha.

- **Contraste de texto de 4,5:1 ou mais, medido por script**, não a olho. Paleta de gráfico conferida também para
  daltonismo; se nenhuma paleta passa em todos os pares, dizer o limite.
- **Colisão de texto se mede:** altura real de cada caixa e varredura de sobreposição por script.

## Como propor mudança visual

- **"Como melhorar?", "o que acha?" e "tá confuso" pedem diagnóstico e opções, e param aí.** Mudar estilo, tipo
  de gráfico ou estrutura só depois do sim. Correção de erro de dado não precisa de aval.
- **Pedido visual se responde com visual.** Olhar a página renderizada antes de propor; mostrar escolha de gosto
  como A e B lado a lado.
- **Não iterar sozinho sobre o próprio gosto.** Mostrar cada versão, dizer o que parece defeito, e esperar: o
  que a IA trata como defeito o usuário pode achar o melhor da peça.
- **Aprovada a mudança, propagar para tudo que usa a peça** (PDF final, prévias, versões). Deixar uma versão
  desatualizada é erro.

## Telas, sites e apps

- Fundo levemente quente em vez de branco puro, canto de 4 a 8 px, fonte que não seja a padrão de todo template
  (Inter), sem gradiente, sem três cards em fileira, ícone em SVG em vez de emoji.
- Isso vale para tela e site. **Não vale para deck de cliente que já tem modelo:** o modelo da casa manda.
- Mudança de visual em app do usuário só com aval antes.

## Na central

Consultar antes de desenhar, não depois:
- `_kit/central/01_os_30_sinais_de_site_feito_por_ia.md`: a lista vai para o modelo como restrição ao gerar tela ou site.
- `_kit/central/02_como_tirar_a_cara_de_ia_na_pratica.md`: componente pronto, referência real, varredura de antipadrão, texto.
- `_kit/central/20_fundamentos_de_design_como_o_olho_le.md`: hierarquia e ordem de leitura; diagnóstico de "parece errado".
- `_kit/central/21_vocabulario_visual_de_interface_nomear_o_visual_do_site.md` e
  `_kit/central/22_vocabulario_visual_de_peca_grafica_nomear_a_direcao_de_arte.md`: pedir o estilo pelo nome.
- `_kit/central/25_fluxo_de_design_com_ia.md`: preparar o insumo, detalhar, só então gerar.
- `_kit/central/27_cor_e_paleta.md` e `_kit/central/23_ferramentas_e_sites_para_designer.md`.
