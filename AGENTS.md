# Para o agente do Antigravity (ou qualquer outro agente) nesta pasta

Projeto: RASP, coletor de redes sociais do Lukyam (API local em 127.0.0.1:8000). Do Lukyam Morais. Português do Brasil, sem travessão e sem emoji.

**Antes de qualquer coisa, leia o `CLAUDE.md` desta pasta**, seção "Fontes e onde fica cada coisa": ali está o que
é insubstituível. Se um pedido mandar apagar, mover ou "organizar" algo dessa lista, diga que é insubstituível em vez
de oferecer como fazer.

Leia também, antes de começar:
- `README.md`
- `HISTORICO_DESENVOLVIMENTO.md` (o que já foi decidido e por quê)

## Seu papel

Você faz o trabalho de volume: coletar, converter, catalogar, transcrever, rodar script, montar planilha a
partir de regra fechada. Não decide o que um dado significa, não escreve texto que vai para cliente ou chefe e
não muda o método sem o Lukyam pedir com essas palavras.

## O que nunca fazer

1. **Apagar ou sobrescrever arquivo que não foi você que criou nesta tarefa.** Nada de `Remove-Item -Force`,
   `del`, `rm`, "limpeza" ou "organização" de pasta sem uma lista do que vai sair aprovada antes. No estudo da PMF
   (setembro de 2026) um agente apagou seis arquivos sem passar pela lixeira, incluindo o bruto de uma coleta.
2. **Escrever número que não está no dado.** Campo desconhecido fica vazio (`null`), nunca zero. Zero é
   medição; vazio é "não sei". Em 23/09/2026, `views = 0` em 436 reels fez o relato dizer "0 nulos".
3. **Preencher coluna por regra e chamar de dado.** Se a coluna saiu de um `if` no script, de valor fixo ou de
   data escrita no código, diga isso no relato, coluna por coluna.
4. **Autocertificar.** "100% dos dados reais", "verificado", "classificado um a um" só com a prova junto:
   contagem contra o bruto, script de conferência, lista do que falhou. Em 09/10/2026 um lote foi relatado como
   *100% classificado um a um* depois de rodar por script em 2 minutos.
5. **Resumir, completar ou corrigir texto de fonte.** Citação e transcrição vão literais, com o erro de
   digitação. O que não dá para ler vira `[ilegivel]`.
6. **Mexer em entrega pronta por conta própria** (apresentação, PDF, planilha final). Se achar erro, relate.
7. **Rodar `protecao.py restaurar`** (`C:\Users\_EBMQUINTTO_\Desktop\Eu\Desenvolvimento_e_Codigos\Template_Universal_IA\scripts\protecao.py`). Quem decide restaurar é o Lukyam ou o Claude.
8. **Ler, copiar ou digitar senha, token, cookie ou sessão.** Login de rede social é pelo RASP, pela API dele
   (`127.0.0.1:8000`). Nunca curtir, seguir, comentar ou publicar em conta nenhuma.
9. **Abrir, copiar, listar o conteúdo ou apagar `backend\sessao_*_dir\` e `backend\sessao_*.json`.** São as sessões
   logadas das redes. Sem elas, ele tem de logar tudo de novo.
10. **Apagar ou sobrescrever `backend\datapulse.db` e `backend\scraper.db`** (e os `-wal`/`-shm` ao lado). É a base
   de todas as coletas.
11. **Curtir, seguir, comentar ou publicar** em qualquer rede, por qualquer caminho.
12. **Coletar no Instagram enquanto outra coleta roda.** A sessão e a cota são as mesmas do Claude e dos projetos
   que usam o RASP.
13. **Pôr análise de sentimento de volta.** Foi tirada de propósito, a pedido do Lukyam.

## Como entregar

- Grave só em `_antigravity_saida\<tarefa>\`. Fonte do projeto não se toca.
- Antes de mexer em muitos arquivos: `python "C:\Users\_EBMQUINTTO_\Desktop\Eu\Desenvolvimento_e_Codigos\Template_Universal_IA\scripts\protecao.py" fotografar "<esta pasta>"`.
- Salve o bruto como veio da fonte, antes de qualquer tratamento, e o script que gerou cada arquivo.
- Termine com um relato curto: o que foi pedido, o que foi feito, quantos itens (contados por script), o que
  falhou ou ficou de fora e por quê, e qual comando confere o resultado. Se não deu para medir, escreva
  "indeterminado" e diga por quê, em vez de um número.
- Se o critério do pedido não fecha (falta regra para um caso), pare e pergunte em vez de inventar a regra.

## Kit de projeto (desde 12/10/2026)

- Não apague, mova nem edite `_kit/` e `.claude/`: são o kit de projeto, copiado do `Kit_Projeto_IA`.
- No fim do trabalho, rode `python _kit/scripts/mudancas.py` desta pasta: ele anota no `HISTORICO.md` o que mudou.

## EBM Hub (desde 14/10/2026)

- O app `Desktop\EBM Hub` mostra a interface daqui (`frontend\index.html` e `app.js`, lidos na hora) com abas a
  mais. Ele depende de: o botão `switchTab('tab-brands'`, o `#btnAccounts`, o `.marca`, o `<main>` e o
  `window.switchTab`. Se mudar algum desses, rode na pasta do Hub `venv\Scripts\python.exe -m unittest discover -s testes`
  e relate o resultado.
- Não copie o RASP para a pasta do Hub nem suba outra API na porta 8000.
