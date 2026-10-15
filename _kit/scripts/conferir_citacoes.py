# -*- coding: utf-8 -*-
"""Confere se cada citação de um arquivo devolvido por agente existe de fato na fonte.

Serve para qualquer volta de leitura delegada (outra IA ou subagente): o agente devolve achados com
citação literal entre aspas duplas, e este script procura cada citação no material de origem. Citação que
não está lá é inventada, juntada de dois lugares ou parafraseada, e não pode virar regra, número ou texto
de entrega sem conferência.

A comparação ignora diferença de espaço, quebra de linha, aspas curvas e maiúsculas. Não ignora palavra
trocada: "ta" e "tá" contam como diferentes, de propósito. Exemplo que não é citação deve ir sem aspas
duplas (em itálico, por exemplo), senão o script o confere também.

Uso:
  python conferir_citacoes.py volta.md fonte1.txt [fonte2.txt ...]
  python conferir_citacoes.py volta.md fonte.txt --minimo 12   (ignora citação com menos de 12 letras)

Saída: quantas batem, quantas não batem, e a lista das que não batem com o número da linha na volta.
Código de saída 1 se alguma não bater.
"""
import re
import sys
import unicodedata

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

ASPAS_CURVAS = {"“": '"', "”": '"', "‘": "'", "’": "'"}
CITACAO = re.compile(r'"([^"\n]{1,300}(?:\n[^"\n]{1,300}){0,3})"')


def trocar_aspas(texto):
    for curva, reta in ASPAS_CURVAS.items():
        texto = texto.replace(curva, reta)
    return texto


def normalizar(texto):
    texto = trocar_aspas(unicodedata.normalize("NFC", texto))
    return re.sub(r"\s+", " ", texto).strip().lower()


def citacoes(texto):
    """(linha, citação) de cada trecho entre aspas duplas, mesmo quando a citação quebra de linha."""
    texto = trocar_aspas(texto)
    for m in CITACAO.finditer(texto):
        yield texto.count("\n", 0, m.start()) + 1, m.group(1)


def main(args):
    minimo = 8
    if "--minimo" in args:
        i = args.index("--minimo")
        minimo = int(args[i + 1])
        args = args[:i] + args[i + 2:]
    if len(args) < 2:
        print(__doc__)
        return 2
    volta, fontes = args[0], args[1:]
    fonte = normalizar("\n".join(open(f, encoding="utf-8", errors="replace").read() for f in fontes))
    ok, falhas = 0, []
    for n, c in citacoes(open(volta, encoding="utf-8", errors="replace").read()):
        if len(re.sub(r"\W", "", c)) < minimo:
            continue
        # Reticências marcam corte: cada pedaço precisa estar na fonte.
        pedacos = [normalizar(p) for p in re.split(r"\[\.\.\.\]|\.\.\.|…", c)]
        pedacos = [p for p in pedacos if len(re.sub(r"\W", "", p)) >= 3]
        if pedacos and all(p in fonte for p in pedacos):
            ok += 1
        else:
            falhas.append((n, c))
    print(f"citações que batem: {ok}")
    print(f"citações que não batem: {len(falhas)}")
    for n, c in falhas:
        print(f"  linha {n}: \"{c[:140]}\"")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
