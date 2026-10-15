# Coleta de dados

Para puxar posts, comentários, métricas, notícias ou qualquer base de rede social, site ou ferramenta.

## Login e contas

- **Rede social logada se acessa pela ferramenta que o usuário já tem logada** (um coletor próprio, uma API, uma
  ferramenta paga), anotada nas "Fontes" do `CLAUDE.md`. Nunca ler, copiar ou digitar senha, cookie ou sessão:
  só usar a ferramenta.
- Antes de dizer que algo não dá para conferir por falta de login, perguntar se existe ferramenta logada.
- Ferramenta que exige login no navegador: o usuário entra; depois a IA vigia a página ou a pasta Downloads e
  segue sozinha, sem pedir que ele avise.
- **Coleta só lê.** Nunca curtir, seguir, comentar ou publicar.
- **Rede tem cota.** Se a sessão é compartilhada (o usuário, outro agente, outra conversa), dois não coletam ao
  mesmo tempo. Acima de certo volume por dia a rede passa a devolver página de login ou erro.

## Fonte oficial

- Quando o relatório diz "Fonte: X", o número vem de X, mesmo que outra ferramenta mostre outro.
- **Fontes que discordam a ponto de mudar o resultado:** mostrar os dois números e os links e perguntar qual
  usar. *Caso:* uma ferramenta paga perdeu 10 posts e mostrou 641 interações num vídeo que tinha 19.149.
- Ferramenta pode tratar a data final como exclusiva: para incluir o último dia, pedir até o dia seguinte e
  conferir. Comparar dois períodos só com os dois coletados no mesmo dia e com o mesmo critério.

## Armadilhas já medidas

- **Coletado não é o que existe.** Comparar o total coletado com a contagem que a rede mostra (comentários do
  post, número de vídeos do perfil) antes de afirmar qualquer total. *Caso:* 1.000 coletados, 20.000 no post.
- **Busca por termo não garante o post central.** Conferir se os posts que puxaram o assunto estão na base.
- **Horário em UTC** no bruto de algumas fontes. Converter e dizer qual fuso a peça usa. Em UTC, post feito à
  noite no Brasil pode cair no dia seguinte: conferir as fronteiras do período.
- **Ausência não é zero.** Campo que a fonte não trouxe fica vazio. *Caso:* `views = 0` em 436 vídeos era dado
  ausente. Curtida oculta pelo dono também é vazio, não zero.
- **Dono do post:** em coleta de vários perfis em fila, conferir no bruto que cada post é do perfil certo (já
  houve posts de uma conta atribuídos à seguinte).
- **Cobertura de perfil:** a rolagem pode parar num post fixado antigo; conferir pelo post não fixado mais antigo
  e pela contagem do perfil. Uma listagem independente comparada id a id pega o que a coleta perdeu.
- **"Sem texto" não é "vazio":** comentário só com emoji ou marcação conta na base e se diz quantos são.

## Coletor que não perde dado

- **Gravar cada página no momento em que chega**, num arquivo por página, em modo que nunca sobrescreve. *Caso:*
  um coletor que guardava tudo na memória para gravar no fim rodou 45 minutos sem gravar nada e sobrescreveu o
  bruto bom.
- **Testar contra um caso de resposta conhecida antes do lote** e abortar se não bater.
- **Definir a "parede":** qualquer resposta que não seja a esperada (HTTP 429, página de login) para o lote e vai
  para o log. 429 tratado como página vazia tirou posts da fila em silêncio.
- **Rodadas circulares** entre os posts (uma página de cada por vez), para que uma parada no meio deixe todos com
  profundidade parecida.
- **Coleta incremental** amplia a base sem repetir o que já foi puxado. Dois coletores gravando o mesmo arquivo
  final: o último a terminar apaga o trabalho do outro.
- Dedupe por autor e texto junta comentários diferentes (o mesmo emoji da mesma pessoa em dois posts); usar o id.

## Fatos de plataforma (medidos em 2026; podem mudar)

- Comentário de Instagram e TikTok exige sessão logada; YouTube sai sem login se a URL for `/watch?v=`, não
  `/shorts/`.
- Instagram: o campo que indica mais páginas de comentário é `has_more_headload_comments`.
- Instagram: o `play_count` soma reprodução no Facebook. Dizer isso no rótulo ou usar a medida só do Instagram.
- Instagram: o endereço das imagens no bruto vence em poucos dias. Baixar as capas logo.
- TikTok: o id do vídeo carrega a data de publicação (`int(id) >> 32` dá o timestamp).
- Página com player: esperar o elemento de dados aparecer, não `networkidle`, com três tentativas.

## Como guardar

- **Bruto primeiro, como veio,** antes de qualquer tratamento, e nunca apagado. O tratamento gera outro arquivo.
- **Nome com o período e a fonte.**
- **Registrar no `CLAUDE.md`:** quando foi coletado (data e hora), por qual ferramenta, com qual termo ou perfil,
  quantos itens, e o que a coleta não traz.

## Coleta delegada

Coleta feita por outro agente passa pela conferência de `delegacao_e_custo.md` antes de qualquer número ser
usado: cada coluna existe no bruto? o bruto foi salvo? dono, datas e cobertura conferem?

## Na central

- Integração por API ou MCP: `_kit/central/19_mcp_contra_api_o_que_cada_camada_faz.md`.
- Material grande para ler depois da coleta: `_kit/central/04_gastar_menos_token.md`.
