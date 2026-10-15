# Relatório e análise

Para relatório de monitoramento, relatório de BI, estudo, análise de posts ou de comentários, e qualquer texto
com número que vá para chefe ou cliente. Quem lê costuma ler rápido e perguntar quando a frase admite duas
leituras.

## O princípio

Quem analisa entrega os ingredientes, não a receita. A peça mostra o que os dados dizem, com inferência marcada
como inferência, e não decide pelo cliente.

## Cobertura: a base inteira

- **Analisar tudo o que foi coletado, não uma parte.** *Caso:* um rascunho usou 345 de 1.085 posts e só os 120
  comentários mais curtidos; o chefe pediu para considerar o máximo possível, porque a parte não representava o todo.
- **Coletado não é o total.** Antes de dizer quantos existem, comparar com a contagem que a rede informa.
  *Caso:* "1.000 comentários" num post que tinha 20.000.
- **Busca por palavra perde post.** Uma busca com dois termos trouxe mais de 1.000 publicações e não trouxe o
  post que puxou o assunto. Conferir se os posts centrais estão na base antes de analisar.
- **As somas fecham.** Gráfico e tabela que dizem "todos" somam o total da base, ou a diferença é explicada na
  própria página.
- **"Todos" é todos do tema, e só do tema.** Puxar o que nem é do assunto para engordar a base é erro.
- **Link conferido antes de mandar.** Já foram entregues perfis e páginas que não existiam. Vínculo afirmado vem
  com o link que o prova.
- **Relatório novo a partir do anterior:** varrer a peça atrás de período, número, título, tema e imagem da
  edição anterior antes de entregar. Herdar dado velho é erro que se repete.

## Cada número diz o que conta

- **Separar sempre o que foi medido:** legenda dos posts, comentários de usuários, curtidas nos comentários,
  interações no post. *Caso:* a cliente perguntou se "posts" eram as legendas e "interações" os comentários.
- **Nomear o lado, não a ação.** Rótulo como *contesta* ou *acusa* exige interpretação; *defende X ou contesta a
  denúncia* não exige.
- **Não usar palavra que sugere outra conclusão.** "Este post é a exceção" foi lido como uma inversão geral,
  quando a exceção era só numa medida. Dizer exatamente o que é diferente e em qual medida.
- **Toda lista ou ranking diz o critério de seleção** (ex.: *os 10 com mais interações*; *todos os de imprensa*).
- **Eixo de gráfico tem título com a unidade.**
- **Cada página diz o que analisa e o que fica para outra página.**
- **Horários e períodos explícitos:** quando a coleta foi feita e de quando são os posts.
- **Proporção estranha se confere antes de publicar.** Se o número se sustenta, a página explica o que entrou
  naquela categoria. *Caso:* a cliente desconfiou de 23,6% de neutros num tema polarizado.
- **Medição não é impressão.** Afirmação sobre gancho, estética ou tom que não sai de um número vai declarada
  como leitura qualitativa. O que não dá para classificar vira *indeterminado* e entra na conta como tal.
- **Abreviação da plataforma fica como está.** "317.8K" não vira 317.800: é precisão falsa. Usar o campo
  numérico quando a fonte tem um.
- **Arredondar uma vez só**, a partir da contagem. Arredondar o que já foi arredondado tira um ponto de alguns
  percentuais.

## Linguagem

- **Clara, não formal.**
- **Análise, não recomendação**, quando o pedido é análise: sem "é preciso", sem juízo de valor, sem
  especulação, sem intenção atribuída a quem publica. Qualificador vago vira número ("poucas legendas" vira
  "8 de 562"). Se a entrega tem uma seção de recomendação, ela fica separada e marcada.
- Sem termo subjetivo ("raríssimos") e sem acusar além da evidência.
- Sem repetir a mesma palavra com sentidos diferentes na mesma página.

## Nota de método e rodapé

- **Curtos.**
- **Dizem o que entrou, não o bastidor:** fonte, horário da coleta, quantos itens, o que a coleta não traz, o
  que cada métrica mede (curtida mede adesão a um comentário, não pessoas únicas). "Todos os N lidos" é diferente
  de "N lidos à mão e o resto por regra": dizer qual foi.
- **Sem palavra que dê a entender amostra quando a análise foi da base inteira.** "Conferência de 150
  comentários sorteados" fez parecer que só 150 entraram. A conferência interna fica no registro do projeto, não
  no rodapé.
- **Nunca atribuir a uma pessoa o que a IA fez** ("lidos pelo analista" quando quem leu foi a IA).

## Classificação de comentários e posts

- Leitura, não contagem de palavra: regex de palavra já gerou número falso. Regra só para o que ela decide sem
  perda (texto vazio, só emoji).
- Mostrar o resultado por quantidade e por curtidas lado a lado.
- O critério de sentimento se escreve antes de classificar, com a lente (*fortalece, desgasta ou é indiferente
  para quem?*), o que fazer com ironia, com queixa sobre outro responsável e com debate entre internautas. O
  critério do cliente vai para as regras do projeto.
- Sentimento é julgamento: não se delega a script nem a agente sem gabarito (ver `delegacao_e_custo.md`).

## Planilha

- **xlsx formatado**, nunca csv cru.
- **Número calculado é fórmula viva** (`=CONT.SE`, `=SOMA`, percentual), nunca valor digitado ou colado.
- **Fórmula com o valor calculado gravado.** Planilha gerada por script só com fórmulas abre "vazia" em leitores
  que não recalculam. Abrir e salvar no Excel antes de entregar.
- **Percentuais de uma classificação fecham 100%.**
- Nada que quebre na conversão para o Google Sheets.
- Link de post e de perfil clicável. Campo sem dado fica vazio.
- Nunca misturar números de universos diferentes na mesma conta; cada indicador declara a sua base.

## Monitoramento e investigação de perfil

- **Link de cada post citado**, clicável.
- **Não acusar nem afirmar além da evidência.**
- **Achado novo vai primeiro para o chat**, com os links, para o usuário validar; só depois entra no documento.
- Separar por rede quando a busca cobre mais de uma, com um resumo do que se viu em cada.

## Antes de entregar

- Cada número da peça conferido contra a base por script.
- PDF medido: nada passa da página.
- Correção do chefe ou do cliente: separar o que responder do que mudar, aplicar, e registrar a regra no projeto
  com data e frase.
- Fontes que discordam a ponto de mudar o resultado: mostrar os dois números e os links, e perguntar qual usar.

## Na central

- Ler o resultado de post (qual número baixo aponta qual causa): `_kit/central/35_diagnostico_por_metrica_qual_numero_aponta_qual_problema.md`.
- Métrica de anúncio (o que cada sigla mede e o erro comum de cada uma): `_kit/central/43_metricas_de_anuncio_o_que_cada_sigla_mede.md`.
- Conclusão que vai pesar numa decisão do cliente: passar pelos códigos `UNKNOWN` e `BENCHMARK` (`_kit/codigos.md`).
