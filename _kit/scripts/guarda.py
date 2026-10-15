# -*- coding: utf-8 -*-
"""Gancho de antes de cada comando ou edição do Claude Code (evento PreToolUse). Feito por script: não gasta token.

Regra escrita a IA pode esquecer; gancho roda sempre. Este transforma em pergunta ao usuário, com o motivo:
- apagar, mover ou sobrescrever o que o CLAUDE.md lista como insubstituível (linha "Insubstituível" da seção
  "Fontes", caminhos entre crases);
- alterar com a ferramenta de edição um arquivo dessa lista;
- apagar ou mover o CLAUDE.md, o AGENTS.md, o HISTORICO.md, a pasta _kit, a pasta .claude ou o cofre de fotos;
- apagar em massa (rm -r, Remove-Item -Recurse, rmdir /s, del /s, git clean, git reset --hard, find -delete,
  curinga), a não ser que o alvo seja só pasta de dependência ou de build (node_modules, dist, __pycache__...).

Ler, copiar de um insubstituível para outro lugar e gravar arquivo novo dentro de pasta protegida passam direto.
Não bloqueia: quem decide é o usuário. Vale também para os subagentes. É uma rede, não uma muralha: comando que
apaga por dentro de um script ou por variável passa sem ser visto. Em qualquer erro de leitura, sai calado, para
nunca travar o trabalho.

Projeto ainda sem configurar (o CLAUDE.md ainda tem a seção "Primeira conversa"): a primeira gravação com a
ferramenta de edição dentro da pasta, em cada conversa, volta para a IA com o lembrete de perguntar antes. A
segunda passa. Motivo: no teste real de 10/10/2026, a IA (Haiku) fez a análise e criou pasta antes de perguntar
onde a entrega ficava. Gravar pelo terminal (redirecionar, mkdir) não é visto.

O mesmo arquivo pode ser copiado para a pasta global (~/.claude/hooks/) e ligado no ~/.claude/settings.json, para
valer em todo projeto. Nesse caso ele sai calado onde o projeto já tem a sua cópia em _kit/scripts/, para não
perguntar duas vezes.
"""
import json
import os
import re
import shlex
import sys

SEMPRE = ["CLAUDE.md", "AGENTS.md", "HISTORICO.md", "_kit", ".claude"]
PREFIXO = "Proteção do kit: "
DESCARTAVEIS = {"node_modules", "dist", "build", "__pycache__", ".pytest_cache", ".venv", "venv", ".next",
                "coverage", "target", "out", ".cache", ".parcel-cache", ".turbo", "tmp", "temp"}

APAGA_OU_MOVE = re.compile(
    r"\b(rm|rmdir|rd|del|erase|unlink|mv|move|ren|rename)\b|remove-item|move-item|rename-item|\bri\b|"
    r"git\s+(rm|clean|mv)\b|shutil\.(rmtree|move)|os\.(remove|unlink|rename|replace|rmdir)|\.unlink\(|"
    r"\.rmtree\(", re.I)
ESCREVE_NO_CITADO = re.compile(r"set-content|out-file|clear-content|\btruncate\b|git\s+(checkout|restore)\b", re.I)
COPIA = re.compile(r"\b(cp|copy|xcopy|robocopy)\b|copy-item|shutil\.copy", re.I)
REDIRECIONA = re.compile(r"(?<![>2&-])>(?!>)\s*(\"[^\"]+\"|'[^']+'|[^\s|;&<>]+)")
EM_MASSA = re.compile(
    r"\brm\s+(-\w*[rR]|--recursive)|remove-item\b[^|;&]*-r(ecurse)?\b|\b(rmdir|rd)\s+/s|\bdel\b[^|;&]*/s|"
    r"shutil\.rmtree|git\s+clean\s+-\w*f|git\s+reset\s+--hard|\bfind\b[^|;&]*-delete|"
    r"\|\s*(remove-item|rm|del|ri)\b|\b(rm|del|erase|remove-item|ri)\b[^|;&]*\*", re.I)


def normal(caminho):
    return caminho.replace("\\", "/").strip().strip("\"'").rstrip("/").lower()


def insubstituiveis(raiz):
    """Caminhos entre crases na linha "Insubstituível" da seção Fontes do CLAUDE.md (e nas linhas que a continuam)."""
    try:
        with open(os.path.join(raiz, "CLAUDE.md"), encoding="utf-8", errors="replace") as f:
            linhas = f.read().split("\n")
    except OSError:
        return []
    itens, em_fontes, dentro = [], False, False
    for linha in linhas:
        if linha.startswith("## "):
            em_fontes, dentro = "fontes" in linha.lower(), False
            continue
        if not em_fontes:
            continue
        if "insubstitu" in linha.lower() and linha.lstrip().startswith("- **"):
            resto = linha.split(":**", 1)[-1].strip()
            dentro = not resto.startswith("[")  # entre colchetes: molde ainda não preenchido, com exemplo
            if dentro:
                itens += re.findall(r"`([^`]+)`", resto)
        elif dentro and linha.strip() and not linha.lstrip().startswith("- ") and linha.startswith(" "):
            itens += re.findall(r"`([^`]+)`", linha)
        else:
            dentro = False
    return [i for i in itens if i.strip() and "[" not in i and "<" not in i]


def relativo(raiz, caminho):
    try:
        absoluto = os.path.abspath(os.path.join(raiz, caminho.strip().strip("\"'")))
        rel = os.path.relpath(absoluto, raiz)
    except ValueError:  # outro disco no Windows
        return normal(caminho)
    return normal(rel)


def protege(item_rel, alvo_rel):
    return alvo_rel == item_rel or alvo_rel.startswith(item_rel + "/")


def citado(comando, item):
    """O comando menciona o item? Compara pelo caminho e, se o item tem mais de uma parte, também pelo nome final."""
    c = normal(comando)
    n = normal(item)
    if not n:
        return False
    if re.search(r"(?<![\w.-])" + re.escape(n) + r"(?![\w-])", c):
        return True
    final = n.rsplit("/", 1)[-1]
    return final != n and len(final) > 3 and bool(re.search(r"(?<![\w.-])" + re.escape(final) + r"(?![\w-])", c))


def palavras(trecho):
    try:
        return [p.strip("\"'") for p in shlex.split(trecho, posix=False)]
    except ValueError:
        return trecho.split()


def so_descartavel(trecho):
    alvos = [p for p in palavras(trecho)[1:] if p and not p.startswith("-") and not p.startswith("/")]
    alvos = [normal(a).rsplit("/", 1)[-1] for a in alvos]
    return bool(alvos) and all(a in DESCARTAVEIS for a in alvos)


def destino_da_copia(trecho):
    alvos = [p for p in palavras(trecho)[1:] if p and not p.startswith("-") and not p.startswith("/")]
    return alvos[-1] if len(alvos) >= 2 else None


LIVRES_NA_PRIMEIRA = ("claude.md", "agents.md", "historico.md")


def primeira_conversa_pendente(raiz):
    try:
        with open(os.path.join(raiz, "CLAUDE.md"), encoding="utf-8", errors="replace") as f:
            return any(linha.startswith("## Primeira conversa") for linha in f)
    except OSError:
        return False


def lembrar_configuracao(raiz, sessao, alvo):
    """Projeto sem configurar: barra uma vez por conversa a primeira gravação dentro da pasta, com o lembrete."""
    alvo_rel = relativo(raiz, alvo)
    if alvo_rel.startswith("..") or ":" in alvo_rel or alvo_rel in LIVRES_NA_PRIMEIRA or \
            alvo_rel.split("/", 1)[0] in (".claude", "_kit") or not primeira_conversa_pendente(raiz):
        return
    marca = os.path.join(raiz, ".claude", "estado", "primeira_conversa_lembrada")
    try:
        with open(marca, encoding="utf-8") as f:
            if f.read().strip() == sessao:
                return
    except OSError:
        pass
    try:
        os.makedirs(os.path.dirname(marca), exist_ok=True)
        with open(marca, "w", encoding="utf-8") as f:
            f.write(sessao)
    except OSError:
        return  # sem onde marcar, não barra: sem a marca, barraria toda gravação
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            "Kit de projeto: este projeto ainda não foi configurado (o CLAUDE.md ainda tem a seção \"Primeira "
            "conversa neste projeto\"). Antes de criar ou alterar arquivo na pasta, faça ao usuário as perguntas "
            "dessa seção numa mensagem só e espere a resposta: onde a entrega fica e o que é insubstituível mudam "
            "onde e como gravar. Olhar a pasta, ler e calcular fora dela pode. Se o usuário já respondeu ou mandou "
            "seguir sem configurar, siga: este aviso aparece uma vez por conversa."),
    }}))
    sys.exit(0)


def pedir(motivo):
    # json.dumps sem ensure_ascii=False: no Windows a saída do Python não é UTF-8 por padrão, e o acento quebraria
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": PREFIXO + motivo,
    }}))
    sys.exit(0)


def olhar_comando(raiz, comando, lista):
    trechos = [t.strip() for t in re.split(r"&&|\|\||;|\n", comando) if t.strip()]
    for trecho in trechos:
        if EM_MASSA.search(trecho) and not so_descartavel(trecho):
            pedir(f"este comando apaga em massa (`{trecho[:120]}`). Confirme só se foi você quem pediu.")
    for trecho in (s.strip() for t in trechos for s in t.split("|")):
        apaga = APAGA_OU_MOVE.search(trecho)
        escritos = [m.group(1) for m in REDIRECIONA.finditer(trecho)]
        if COPIA.search(trecho) and destino_da_copia(trecho):
            escritos.append(destino_da_copia(trecho))
        for item in lista:
            item_rel = relativo(raiz, item)
            if (citado(trecho, item) and (apaga or ESCREVE_NO_CITADO.search(trecho))) or \
                    any(protege(item_rel, relativo(raiz, e)) for e in escritos):
                pedir(f"`{item}` está marcado como insubstituível no CLAUDE.md, e este comando pode apagar, mover "
                      "ou sobrescrever. Confirme só se foi você quem pediu.")
        if apaga:
            for item in SEMPRE:
                if citado(trecho, item):
                    pedir(f"este comando pode apagar ou mover `{item}`, que o kit usa para funcionar. "
                          "Confirme só se foi você quem pediu.")
            if "_cofre" in normal(trecho):
                pedir("este comando pode apagar ou mover o cofre de fotos da proteção. "
                      "Confirme só se foi você quem pediu.")


def main():
    try:
        entrada = json.load(sys.stdin)
    except Exception:
        return
    global PREFIXO
    raiz = os.environ.get("CLAUDE_PROJECT_DIR") or entrada.get("cwd") or os.getcwd()
    do_projeto = os.path.join(raiz, "_kit", "scripts", "guarda.py")
    if os.path.normcase(os.path.abspath(__file__)) != os.path.normcase(os.path.abspath(do_projeto)):
        if os.path.isfile(do_projeto):
            return  # cópia global num projeto que tem a sua: a do projeto já roda
        PREFIXO = "Proteção (gancho global): "
    ferramenta = entrada.get("tool_name", "")
    dados = entrada.get("tool_input") or {}
    lista = insubstituiveis(raiz)

    if ferramenta in ("Bash", "PowerShell"):
        olhar_comando(raiz, str(dados.get("command", "")), lista)
        return
    if ferramenta not in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        return
    alvo = dados.get("file_path") or dados.get("notebook_path")
    if alvo:
        lembrar_configuracao(raiz, str(entrada.get("session_id") or ""), alvo)
    if not alvo or not lista:
        return
    alvo_rel = relativo(raiz, alvo)
    for item in lista:
        if protege(relativo(raiz, item), alvo_rel):
            if ferramenta == "Write" and not os.path.exists(alvo):
                return  # arquivo novo dentro de pasta protegida: não apaga nada
            acao = "sobrescrever" if ferramenta == "Write" else "alterar"
            pedir(f"`{item}` está marcado como insubstituível no CLAUDE.md, e esta ação vai {acao} "
                  f"`{alvo_rel}`. Confirme só se foi você quem pediu.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
