# -*- coding: utf-8 -*-
"""Mede quanto cada modelo gastou neste projeto, a partir das transcrições que o Claude Code grava no computador.

Serve para saber, com número, se a escada de modelos está funcionando: volume indo para modelo menor, julgamento
no principal. Não estima nada: soma o que o próprio Claude Code registrou em cada resposta. Não lê o texto das
conversas, só os campos de modelo, data e contagem de tokens.

Uso (da raiz do projeto):
    python _kit/scripts/medir_uso.py              # últimos 7 dias
    python _kit/scripts/medir_uso.py --dias 30
    python _kit/scripts/medir_uso.py --tudo
    python _kit/scripts/medir_uso.py --pasta "<outra pasta de projeto>"

As transcrições ficam em ~/.claude/projects/ (ou na pasta de CLAUDE_CONFIG_DIR). Só existem para o Claude Code;
outras ferramentas não entram na conta.
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone


def pasta_config():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")


def mesma_pasta(a, b):
    return os.path.normcase(os.path.abspath(a)).rstrip("\\/") == os.path.normcase(os.path.abspath(b)).rstrip("\\/")


def pasta_das_transcricoes(projeto):
    """A pasta do Claude Code para este projeto: o caminho com tudo que não é letra ou número trocado por hífen.
    Se o nome não bater (versões que encurtam nomes longos), procura pela pasta de trabalho gravada nas linhas."""
    base = os.path.join(pasta_config(), "projects")
    if not os.path.isdir(base):
        return None
    direto = os.path.join(base, re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(projeto)))
    if os.path.isdir(direto):
        return direto
    for nome in os.listdir(base):
        pasta = os.path.join(base, nome)
        if not os.path.isdir(pasta):
            continue
        for arq in os.listdir(pasta):
            if not arq.endswith(".jsonl"):
                continue
            try:
                with open(os.path.join(pasta, arq), encoding="utf-8", errors="replace") as f:
                    for _, linha in zip(range(40), f):
                        cwd = json.loads(linha).get("cwd")
                        if cwd:
                            if mesma_pasta(cwd, projeto):
                                return pasta
                            break
            except (OSError, ValueError):
                continue
    return None


def arquivos_jsonl(pasta):
    for raiz, _, arquivos in os.walk(pasta):
        for nome in arquivos:
            if nome.endswith(".jsonl"):
                caminho = os.path.join(raiz, nome)
                yield caminho, ("subagents" in os.path.relpath(caminho, pasta).split(os.sep))


def ler_data(texto):
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def somar(pasta, desde):
    tabela = defaultdict(lambda: [0, 0, 0, 0, 0])  # respostas, entrada nova, cache lido, saída, linhas
    conversas, arquivos = set(), 0
    for caminho, eh_sub in arquivos_jsonl(pasta):
        arquivos += 1
        vistos = {}  # resposta -> linha da tabela onde entrou e a saída já somada
        try:
            f = open(caminho, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with f:
            for linha in f:
                if '"usage"' not in linha:
                    continue
                try:
                    d = json.loads(linha)
                except ValueError:
                    continue
                if d.get("type") != "assistant":
                    continue
                msg = d.get("message") or {}
                modelo, uso = msg.get("model"), msg.get("usage")
                if not modelo or not uso or modelo.startswith("<"):
                    continue
                chave_msg = msg.get("id") or d.get("requestId") or d.get("uuid")
                saida = uso.get("output_tokens") or 0
                if chave_msg in vistos:
                    # a mesma resposta aparece em várias linhas, uma por bloco; a saída fica com a maior contagem
                    linha_t, ja = vistos[chave_msg]
                    if linha_t is not None and saida > ja:
                        linha_t[3] += saida - ja
                        vistos[chave_msg] = (linha_t, saida)
                    continue
                vistos[chave_msg] = (None, 0)
                quando = ler_data(d.get("timestamp"))
                if desde and (quando is None or quando < desde):
                    continue
                quem = "subagente" if (eh_sub or d.get("isSidechain")) else "principal"
                linha_t = tabela[(quem, modelo)]
                linha_t[0] += 1
                linha_t[1] += (uso.get("input_tokens") or 0) + (uso.get("cache_creation_input_tokens") or 0)
                linha_t[2] += uso.get("cache_read_input_tokens") or 0
                linha_t[3] += saida
                vistos[chave_msg] = (linha_t, saida)
                if d.get("sessionId"):
                    conversas.add(d["sessionId"])
    return tabela, len(conversas), arquivos


def mil(n):
    return f"{n:,}".replace(",", ".")


def porcentagem(parte, total):
    return f"{100 * parte / total:.0f}%" if total else "sem dado"


def main():
    ap = argparse.ArgumentParser(description="Tokens por modelo neste projeto, medidos nas transcrições do Claude Code.")
    ap.add_argument("--pasta", default=os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    ap.add_argument("--dias", type=int, default=7)
    ap.add_argument("--tudo", action="store_true", help="sem limite de data")
    args = ap.parse_args()

    pasta = pasta_das_transcricoes(args.pasta)
    if not pasta:
        print(f"Nenhuma transcrição do Claude Code encontrada para {os.path.abspath(args.pasta)}.")
        print("Ou o projeto ainda não foi aberto no Claude Code neste computador, ou as transcrições foram apagadas.")
        return
    desde = None if args.tudo else datetime.now(timezone.utc) - timedelta(days=args.dias)
    tabela, n_conversas, n_arquivos = somar(pasta, desde)
    periodo = "todo o histórico guardado" if args.tudo else f"últimos {args.dias} dias"
    if not tabela:
        print(f"Nenhuma resposta com contagem de tokens em {periodo} ({n_arquivos} arquivos lidos em {pasta}).")
        return

    print(f"Uso de tokens deste projeto, {periodo}: {n_conversas} conversas, {n_arquivos} arquivos de transcrição.")
    print("Entrada nova = texto que o modelo leu pela primeira vez (inclui o que foi para o cache).")
    print("Cache lido = texto repetido de turnos anteriores, mais barato que entrada nova, mas também conta.\n")
    cab = f"{'Quem':<10} {'Modelo':<28} {'Respostas':>9} {'Entrada nova':>14} {'Cache lido':>14} {'Saída':>11}"
    print(cab)
    print("-" * len(cab))
    tot = [0, 0, 0, 0]
    por_modelo = defaultdict(lambda: [0, 0])
    saida_principal = 0
    for (quem, modelo), v in sorted(tabela.items(), key=lambda kv: (kv[0][0] != "principal", -kv[1][1])):
        saida = mil(v[3]) + ("*" if quem == "subagente" else " ")
        print(f"{quem:<10} {modelo:<28} {mil(v[0]):>9} {mil(v[1]):>14} {mil(v[2]):>14} {saida:>12}")
        for i in range(4):
            tot[i] += v[i]
        por_modelo[modelo][0] += v[1]
        if quem == "principal":
            por_modelo[modelo][1] += v[3]
            saida_principal += v[3]
    print("-" * len(cab))
    print(f"{'total':<10} {'':<28} {mil(tot[0]):>9} {mil(tot[1]):>14} {mil(tot[2]):>14} {mil(tot[3]) + '*':>12}")
    if any(q == "subagente" for q, _ in tabela):
        # visto no teste real de 10/10/2026: resposta de 13.715 caracteres registrada com saída 3
        print("* Saída de subagente: a transcrição dele costuma guardar a contagem do começo da resposta, então o")
        print("  número fica menor que o real. Entrada nova e cache lido já vêm completos no começo da resposta.")
    print()

    print("Parte de cada modelo (a saída conta só a conversa principal):")
    for modelo, (entrada, saida) in sorted(por_modelo.items(), key=lambda kv: -kv[1][0]):
        print(f"  {modelo}: {porcentagem(entrada, tot[1])} da entrada nova, {porcentagem(saida, saida_principal)} da saída")

    caros = sorted({m for (q, m), v in tabela.items() if q == "subagente" and "opus" in m.lower()})
    if caros:
        n = sum(v[0] for (q, m), v in tabela.items() if q == "subagente" and m in caros)
        print(f"\nAtenção: {n} respostas de subagente rodaram no modelo mais caro ({', '.join(caros)}). Subagente de")
        print("leitura em volume deveria ser `varredor` (Haiku) ou `leitor` (Sonnet); ver _kit/guias/delegacao_e_custo.md.")
    sub = sum(v[1] for (q, _), v in tabela.items() if q == "subagente")
    print(f"\nEntrada nova lida por subagentes: {porcentagem(sub, tot[1])} do total.")
    print(f"Transcrições lidas em: {pasta}")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    main()
