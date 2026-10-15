# -*- coding: utf-8 -*-
"""Barra de status do Claude Code: o que está gastando, à vista, sem gastar token (roda no computador).

Mostra o modelo em uso, quanto da janela de contexto a conversa já ocupa e quanto da cota de 5 horas e da semanal
já foi usado (quando o Claude Code informa). Acima dos limites abaixo, acrescenta o que fazer.

Por que importa: cada resposta relê a conversa inteira. Conversa longa custa mais a cada turno, mesmo quando o
pedido é pequeno; e a cota é uma só para a conversa e para os subagentes.

Ligada em .claude/settings.json (statusLine). Para tirar, apague o bloco "statusLine" de lá.
"""
import json
import sys

CONTEXTO_ALTO = 60   # % da janela: hora de /compact ou conversa nova
COTA_ALTA = 80       # % da cota: deixar o modelo mais caro para o que é decisão


def numero(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        d = {}
    partes, dicas = [], []

    modelo = (d.get("model") or {}).get("display_name") or (d.get("model") or {}).get("id")
    if modelo:
        partes.append(modelo)

    contexto = numero((d.get("context_window") or {}).get("used_percentage"))
    if contexto is not None:
        partes.append(f"contexto {contexto:.0f}%")
        if contexto >= CONTEXTO_ALTO:
            dicas.append("conversa longa: /compact, ou conversa nova se a tarefa mudou")

    cotas = d.get("rate_limits") or {}
    alta = False
    for chave, rotulo in (("five_hour", "cota 5h"), ("seven_day", "semana")):
        uso = numero((cotas.get(chave) or {}).get("used_percentage"))
        if uso is not None:
            partes.append(f"{rotulo} {uso:.0f}%")
            alta = alta or uso >= COTA_ALTA
    if alta:
        dicas.append("cota alta: volume para subagente menor, rotina em /model menor")

    linha = " | ".join(partes)
    if dicas:
        linha += "  >  " + "; ".join(dicas)
    print(linha or "kit de projeto")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    try:
        main()
    except Exception:
        print("kit de projeto")
