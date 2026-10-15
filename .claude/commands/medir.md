---
description: Quanto cada modelo gastou neste projeto e se a escada de modelos está funcionando
argument-hint: "[número de dias; vazio usa 7]"
---

Rode `python _kit/scripts/medir_uso.py --dias $ARGUMENTS` (sem número, rode sem `--dias`). Não estime nada além do
que o script mostrar. Responda em até 6 linhas:

1. Quanto foi para cada modelo, em número, e quanto foi lido por subagentes.
2. Se o script avisou de subagente no modelo mais caro, diga qual tarefa provavelmente foi (pela conversa) e qual
   subagente do kit deveria ter feito (`varredor`, `leitor`, `conferente`, `leitor-frio`).
3. Se o "cache lido" do modelo principal é o maior número da tabela, isso é conversa longa relida a cada turno:
   sugira `/compact` ou conversa nova por tarefa.
4. Uma mudança concreta para a próxima semana, só se os números mostrarem motivo para ela.
