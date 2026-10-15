# Códigos de conversa

Palavras curtas que o usuário escreve para pedir um tipo de resposta. Os doze primeiros vêm do verbete 16 da
central (nó 167 e, para a pré-morte, nó 173), detalhados aqui para virarem instrução que se cumpre; `ENTREGAR` é
do kit. Num chat comum esses códigos são só convenção
de texto, e o verbete 15 avisa disso. Aqui eles estão definidos: no Claude Code viram comandos
(`/premortem`, `/steelman`...); em outra ferramenta, o usuário escreve a palavra, com ou sem barra, e a IA aplica a
definição abaixo.

**Ao que se aplica:** ao texto que vem depois do código. Se não vier nada, ao último plano, ideia, decisão ou
entrega da conversa. Se não houver nada a que aplicar, perguntar a que se aplica.

## Atacar a ideia

**PREMORTEM**: assumir que se passaram seis meses e deu errado. Sem elogio nem validação.
1. As cinco causas mais prováveis do fracasso, em ordem de probabilidade.
2. As suposições escondidas: o que está sendo tomado como verdade e, se estiver errado, destrói o plano.
3. Para cada risco, como testá-lo agora e o que corrigir antes de lançar.
4. No fim, um checklist priorizado de testes e correções.

**TRADEOFF**: para cada opção, o que se perde, não só o que se ganha. Terminar dizendo qual perda é a mais cara
e para quem.

**BLINDSPOT**: o que o usuário não perguntou e deveria ter perguntado. As três perguntas mais importantes que
ficaram de fora, cada uma com o porquê.

**UNKNOWN**: separar o que é fato (com a fonte), o que é estimativa (de quem, com que base) e o que ninguém sabe.
Nada fica sem uma das três marcas.

## Advogar o outro lado

**STEELMAN**: a versão mais forte do argumento contrário, como a pessoa mais inteligente que discorda o
escreveria. Só depois, a resposta.

**INVERT**: trocar "como faço dar certo" por "como eu garantiria que desse errado". Listar os caminhos para o
fracasso e, ao lado de cada um, o que o plano atual faz (ou não faz) para evitá-lo.

**SECONDORDER**: a consequência da consequência. Para cada efeito imediato, o que ele provoca depois, e quem
sente.

**SOWHAT**: cortar tudo o que não muda uma decisão. Devolver só o que muda, e dizer qual decisão cada item muda.

## Obrigar a se posicionar

**BENCHMARK**: para cada número, de onde veio e contra o que está sendo comparado. Número sem origem ou sem
comparação fica marcado assim.

**CONFIDENCE**: marcar cada afirmação com confiança alta, média ou baixa, e o motivo da marca.

**DISAGREE**: discordar de pelo menos um ponto do usuário, o mais importante em que ele pode estar errado, com o
argumento. Não vale discordar de detalhe.

**BASELINE**: antes de responder, devolver a pergunta que falta para a resposta fazer sentido (no exemplo do
post, "3% de conversão é bom?" recebe "é bom para quem, comparado a quê?"). Responder só depois.

## Do kit

**ENTREGAR**: conferência antes de dizer que está pronto, item por item, com o resultado de cada um:
1. Cada número da entrega conferido contra a base, por script quando dá. Muitos números ou citações: passar ao
   subagente `conferente` (modelo pequeno) com a entrega e a fonte, e checar por amostra o que ele marcou.
2. O arquivo aberto do jeito que o usuário usa (no programa dele, pelo atalho, renderizado).
3. A mesma classe de erro procurada no resto do trabalho.
4. Nada inventado: dado de exemplo, sigla, título, nota de processo.
5. Texto sem marca de IA (lista em `_kit/guias/apresentacao_e_visual.md`).
6. Texto que outra pessoa vai ler sem ninguém explicar (relatório, mensagem, README): passar ao subagente
   `leitor-frio`, que lê sem o contexto da conversa, e resolver o que ele não entendeu.
7. O que ficou de fora, e por quê.
8. O caminho completo de cada arquivo criado ou mudado, com uma linha do que mudou.
9. O "Onde parou" do `CLAUDE.md` atualizado.
