# -*- coding: utf-8 -*-
"""Registro automático do que mudou na pasta e lembrete do "Onde parou". Feito por script: não gasta token.

Guarda um retrato leve da pasta (nome, tamanho e data de cada arquivo, sem abrir nenhum) e escreve no HISTORICO.md,
seção "Registro automático", o que cada conversa criou, alterou, moveu ou apagou, e a seção "Onde parou" do
CLAUDE.md como ela ficou. Assim a IA pode enxugar o "Onde parou" sem medo: a versão anterior fica guardada.

No Claude Code roda sozinho (ganchos em .claude/settings.json):
- depois de cada ferramenta que pode mexer em arquivo (PostToolUse), o settings.json só marca a pasta como
  "mexida" (um arquivo vazio em .claude/estado/), sem rodar este script;
- ao fim de cada resposta (Stop): se a pasta foi mexida, tira o retrato. Se algum arquivo ficou mais novo que o
  CLAUDE.md, segura a conversa uma vez e pede para a IA atualizar o "Onde parou" (fica calado se o usuário já tem
  um gancho igual no arquivo global, para não cobrar duas vezes). Resposta sem ferramenta não custa nada;
- no início da conversa seguinte (SessionStart): escreve no HISTORICO.md o registro da conversa anterior e, à
  parte, o que mudou entre as duas (o usuário ou outra ferramenta); desse segundo, avisa a IA em poucas linhas.
  O HISTORICO.md é escrito uma vez por conversa, não a cada resposta.

À mão ou em outra ferramenta (da raiz do projeto):
    python _kit/scripts/mudancas.py          # registra no HISTORICO.md o que mudou desde o último retrato
    python _kit/scripts/mudancas.py --ver    # só mostra, não grava

Não olha a pasta _kit, pastas ocultas (.claude, .git), de dependência ou de build, nem o próprio HISTORICO.md.
O retrato fica em .claude/estado/, que o git ignora. Em qualquer erro, o gancho sai calado: nunca trava a conversa.
"""
import hashlib
import json
import os
import sys
from datetime import datetime

PASTAS_IGNORADAS = {"_kit", "node_modules", "__pycache__", "venv", "env", "dist", "build", "site-packages"}
# Arquivos que contam para o lembrete do "Onde parou" (imagem e vídeo entram no registro, não no lembrete)
EXTENSOES_ESTADO = {
    ".py", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".json", ".jsonl", ".csv", ".tsv", ".md", ".sql", ".xlsx",
    ".xls", ".ipynb", ".go", ".rs", ".java", ".rb", ".php", ".html", ".css", ".scss", ".sh", ".ps1", ".yml",
    ".yaml", ".toml", ".txt", ".xml", ".docx", ".doc", ".odt", ".rtf", ".pptx", ".pdf",
}
LIMITE_ARQUIVOS = 20000
LIMITE_LISTA = 30
LIMITE_AVISO = 10
LIMITE_ONDE_PAROU = 40
MARCA = "<!-- novos registros entram abaixo desta linha -->"
SECAO = "## Registro automático"
INTRO = (
    "Escrito por `_kit/scripts/mudancas.py`, sem gastar token, no início de cada conversa: o que a conversa "
    "anterior mudou e, à parte, o que mudou entre conversas. Arquivos criados, alterados, movidos e sumidos, e a "
    "seção \"Onde parou\" do `CLAUDE.md` como ela ficou. O mais novo fica em cima. Decisão, com o porquê, vai para "
    "as seções acima."
)


def agora_texto():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def retrato(raiz):
    """{caminho relativo com /: [tamanho, data em segundos]}. Não abre arquivo: só lê tamanho e data."""
    arquivos, n = {}, 0
    for pasta, subpastas, nomes in os.walk(raiz):
        subpastas[:] = sorted(d for d in subpastas if d not in PASTAS_IGNORADAS and not d.startswith("."))
        for nome in sorted(nomes):
            n += 1
            if n > LIMITE_ARQUIVOS:
                return arquivos, False
            caminho = os.path.join(pasta, nome)
            rel = os.path.relpath(caminho, raiz).replace(os.sep, "/")
            if rel == "HISTORICO.md":
                continue
            try:
                st = os.stat(caminho)
            except OSError:
                continue
            arquivos[rel] = [st.st_size, int(st.st_mtime)]
    return arquivos, True


def secao_onde_parou(raiz):
    """(texto do estado, número de linhas com conteúdo da seção inteira)."""
    try:
        with open(os.path.join(raiz, "CLAUDE.md"), encoding="utf-8", errors="replace") as f:
            linhas = f.read().split("\n")
    except OSError:
        return "", 0
    dentro, trecho = False, []
    for linha in linhas:
        if linha.startswith("## "):
            if dentro:
                break
            dentro = linha.strip().lower() == "## onde parou"
            continue
        if dentro:
            trecho.append(linha.rstrip())
    n = sum(1 for l in trecho if l.strip())
    # o parágrafo fixo de instrução da seção não é estado: o estado começa em "Atualizado em", quando existe
    inicio = next((i for i, l in enumerate(trecho) if l.startswith("Atualizado em")), 0)
    return "\n".join(trecho[inicio:]).strip(), n


def resumo(texto):
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()


def comparar(antes, agora):
    criados = sorted(set(agora) - set(antes))
    sumidos = sorted(set(antes) - set(agora))
    alterados = sorted(c for c in set(antes) & set(agora) if antes[c] != agora[c])
    movidos = []
    for velho in list(sumidos):
        nome, tamanho = velho.rsplit("/", 1)[-1], antes[velho][0]
        par = next((n for n in criados if n.rsplit("/", 1)[-1] == nome and agora[n][0] == tamanho), None)
        if par:
            movidos.append((velho, par))
            sumidos.remove(velho)
            criados.remove(par)
    return criados, alterados, movidos, sumidos


def lista(itens, limite=LIMITE_LISTA):
    mostra = [f"`{i}`" for i in itens[:limite]]
    resto = len(itens) - len(mostra)
    return ", ".join(mostra) + (f" e mais {resto}" if resto > 0 else "")


def lista_movidos(movidos, limite=LIMITE_LISTA):
    mostra = [f"`{a}` para `{b}`" for a, b in movidos[:limite]]
    resto = len(movidos) - len(mostra)
    return ", ".join(mostra) + (f" e mais {resto}" if resto > 0 else "")


# ---------------------------------------------------------------- estado em .claude/estado/

def pasta_estado(raiz):
    return os.path.join(raiz, ".claude", "estado")


def ler_estado(raiz):
    try:
        with open(os.path.join(pasta_estado(raiz), "retrato.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def gravar_estado(raiz, estado):
    pasta = pasta_estado(raiz)
    os.makedirs(pasta, exist_ok=True)
    ignora = os.path.join(pasta, ".gitignore")
    if not os.path.exists(ignora):
        with open(ignora, "w", encoding="utf-8") as f:
            f.write("*\n")
    with open(os.path.join(pasta, "retrato.json"), "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False)


def pasta_mexida(raiz, limpar=False):
    marca = os.path.join(pasta_estado(raiz), "mexida")
    existe = os.path.exists(marca)
    if existe and limpar:
        try:
            os.remove(marca)
        except OSError:
            pass
    return existe


# ---------------------------------------------------------------- HISTORICO.md

def escrever_historico(raiz, blocos):
    """Põe os blocos no topo do registro, na ordem dada (o primeiro fica em cima)."""
    if not blocos:
        return
    caminho = os.path.join(raiz, "HISTORICO.md")
    quebra = "\n"
    if os.path.exists(caminho):
        with open(caminho, "rb") as f:
            bruto = f.read()
        quebra = "\r\n" if b"\r\n" in bruto else "\n"
        texto = bruto.decode("utf-8", errors="replace").replace("\r\n", "\n")
    else:
        try:
            with open(os.path.join(raiz, "_kit", "modelos", "HISTORICO.md"), encoding="utf-8") as f:
                texto = f.read()
            texto = "\n".join(l for l in texto.split("\n") if not l.startswith("Copiar para a raiz do projeto"))
            texto = texto.replace("[nome do projeto]", os.path.basename(os.path.abspath(raiz)))
        except OSError:
            texto = f"# Histórico: {os.path.basename(os.path.abspath(raiz))}\n"
    if MARCA not in texto:
        texto = texto.rstrip("\n") + f"\n\n{SECAO}\n\n{INTRO}\n\n{MARCA}\n"
    novo = "\n\n".join(b.rstrip("\n") for b in blocos)
    texto = texto.replace(MARCA, MARCA + "\n\n" + novo + "\n", 1)
    while "\n\n\n" in texto:
        texto = texto.replace("\n\n\n", "\n\n")
    with open(caminho, "w", encoding="utf-8", newline=quebra) as f:
        f.write(texto if texto.endswith("\n") else texto + "\n")


def montar(titulo, mudancas, parou=None, completo=True):
    criados, alterados, movidos, sumidos = mudancas
    linhas = [f"### {titulo}", ""]
    if criados:
        linhas.append(f"- Criados ({len(criados)}): {lista(criados)}")
    if alterados:
        linhas.append(f"- Alterados ({len(alterados)}): {lista(alterados)}")
    if movidos:
        linhas.append(f"- Movidos ou renomeados ({len(movidos)}): {lista_movidos(movidos)}")
    if sumidos:
        linhas.append(f"- Sumiram ({len(sumidos)}; apagados ou levados para fora da pasta): {lista(sumidos)}")
    if not any(mudancas):
        linhas.append("- Nenhum arquivo mudou.")
    if not completo:
        linhas.append(f"- A pasta tem mais de {LIMITE_ARQUIVOS} arquivos; só os primeiros entraram na conta.")
    if parou:
        linhas.append("- \"Onde parou\" como ficou:")
        linhas.append("")
        linhas.extend("  > " + l if l else "  >" for l in parou.split("\n"))
    return "\n".join(linhas) + "\n"


def periodo(inicio, fim):
    if inicio and fim and inicio[:10] == fim[:10]:
        return f"{inicio} a {fim[11:]}"
    return f"{inicio or '?'} a {fim or '?'}"


# ---------------------------------------------------------------- momentos

def inicio_de_conversa(raiz, sessao, origem):
    """Fecha o registro da conversa anterior, registra o que mudou entre conversas e marca a base desta.
    Devolve o aviso para a IA (vazio se nada mudou fora de conversa)."""
    estado = ler_estado(raiz)
    if origem == "compact" and estado and estado.get("sessao") == sessao:
        return ""  # a conversa continua; o registro dela segue aberto
    agora, completo = retrato(raiz)
    parou, _ = secao_onde_parou(raiz)
    blocos, aviso = [], ""
    if estado is not None:
        ultimo = estado.get("arquivos", {})
        fora = comparar(ultimo, agora)
        if any(fora):
            blocos.append(montar(f"{agora_texto()}, entre conversas (desde {estado.get('data', '?')})", fora,
                                 completo=completo))
            if origem != "compact":
                aviso = aviso_para_a_ia(fora, estado.get("data", "?"))
        mesma = estado.get("sessao") == sessao
        if not mesma and estado.get("fim_data") and "base" in estado:
            da_conversa = comparar(estado["base"], ultimo)
            parou_fim = estado.get("fim_parou", "")
            parou_mudou = resumo(parou_fim) != estado.get("base_parou")
            if any(da_conversa) or parou_mudou:
                titulo = f"{periodo(estado.get('base_data'), estado['fim_data'])}, conversa {str(estado.get('sessao'))[:8]}"
                blocos.append(montar(titulo, da_conversa, parou_fim if parou_mudou else None, completo))
        if mesma:
            estado.update({"data": agora_texto(), "arquivos": agora})
            escrever_historico(raiz, blocos)
            gravar_estado(raiz, estado)
            return aviso
    escrever_historico(raiz, blocos)
    gravar_estado(raiz, {"data": agora_texto(), "arquivos": agora, "sessao": sessao, "base": agora,
                         "base_data": agora_texto(), "base_parou": resumo(parou), "fim_data": None})
    pasta_mexida(raiz, limpar=True)
    return aviso


def fim_de_resposta(raiz, sessao, entrada):
    """Ao fim de cada resposta: se a pasta foi mexida, novo retrato e, se for o caso, o lembrete do "Onde parou"."""
    estado = ler_estado(raiz)
    if estado is None or estado.get("sessao") != sessao:
        # o gancho de início não rodou para esta conversa: fecha a anterior e abre esta agora
        inicio_de_conversa(raiz, sessao, "startup")
        estado = ler_estado(raiz) or {}
    elif not pasta_mexida(raiz):
        return None  # resposta sem ferramenta que mexe em arquivo: nada a fazer
    pasta_mexida(raiz, limpar=True)
    agora, _ = retrato(raiz)
    parou, n_linhas = secao_onde_parou(raiz)
    estado.update({"data": agora_texto(), "arquivos": agora, "fim_data": agora_texto(), "fim_parou": parou})
    gravar_estado(raiz, estado)

    if entrada.get("stop_hook_active") or gancho_global_igual():
        return None
    try:
        marca = int(os.path.getmtime(os.path.join(raiz, "CLAUDE.md")))
    except OSError:
        return None
    novos = sorted(c for c, (_, data) in agora.items()
                   if data > marca and c != "CLAUDE.md" and os.path.splitext(c)[1].lower() in EXTENSOES_ESTADO)
    if not novos:
        return None
    razao = (
        f"O CLAUDE.md está mais antigo que arquivos que mudaram: {lista(novos, 6)}. Antes de encerrar, atualize a "
        "seção \"Onde parou\" com o estado real: o que foi feito, o número conferido de cada coisa, o que está em "
        "curso e o que falta, para a próxima conversa não precisar perguntar. Se as mudanças não alteram o estado "
        "do projeto, diga isso em uma linha e encerre."
    )
    if n_linhas > LIMITE_ONDE_PAROU:
        razao += (
            f" A seção \"Onde parou\" tem {n_linhas} linhas (limite {LIMITE_ONDE_PAROU}): enxugue para o que ainda "
            "está valendo. A versão atual fica guardada sozinha no HISTORICO.md no início da próxima conversa."
        )
    return razao


def gancho_global_igual():
    caminho = os.path.join(os.path.expanduser("~"), ".claude", "settings.json")
    try:
        with open(caminho, encoding="utf-8") as f:
            return "registro_estado" in f.read()
    except OSError:
        return False


def a_mao(raiz, gravar):
    estado = ler_estado(raiz)
    agora, completo = retrato(raiz)
    if estado is None:
        if gravar:
            gravar_estado(raiz, {"data": agora_texto(), "arquivos": agora})
        return None, None
    mudancas = comparar(estado.get("arquivos", {}), agora)
    if gravar and any(mudancas):
        titulo = f"{agora_texto()}, rodado à mão (desde {estado.get('data', '?')})"
        escrever_historico(raiz, [montar(titulo, mudancas, completo=completo)])
        estado.update({"data": agora_texto(), "arquivos": agora})
        gravar_estado(raiz, estado)
    return mudancas, estado.get("data")


def aviso_para_a_ia(mudancas, data):
    criados, alterados, movidos, sumidos = mudancas
    total = len(criados) + len(alterados) + len(movidos) + len(sumidos)
    partes = []
    if criados:
        partes.append(f"criados {lista(criados, LIMITE_AVISO)}")
    if alterados:
        partes.append(f"alterados {lista(alterados, LIMITE_AVISO)}")
    if movidos:
        partes.append(f"movidos {lista_movidos(movidos, LIMITE_AVISO)}")
    if sumidos:
        partes.append(f"sumiram {lista(sumidos, LIMITE_AVISO)}")
    quantos = "1 arquivo mudou" if total == 1 else f"{total} arquivos mudaram"
    return (
        f"Registro automático do kit: desde {data}, {quantos} nesta pasta fora de uma conversa "
        f"registrada ({'; '.join(partes)}). Pode ter sido o usuário, outra ferramenta ou uma conversa interrompida. "
        "Antes de mexer neles, ou de tratar um arquivo novo como erro, confirme com o usuário. Já está anotado no "
        "HISTORICO.md, seção \"Registro automático\", junto com o que a conversa anterior mudou: não precisa "
        "registrar de novo."
    )


def main():
    args = sys.argv[1:]
    gancho = "--gancho" in args
    entrada = {}
    if gancho:
        try:
            entrada = json.load(sys.stdin)
        except Exception:
            entrada = {}
    raiz = os.environ.get("CLAUDE_PROJECT_DIR") or entrada.get("cwd") or os.getcwd()
    if not (os.path.isfile(os.path.join(raiz, "CLAUDE.md")) and os.path.isdir(os.path.join(raiz, "_kit"))):
        if not gancho:
            print("Rode da raiz do projeto (a pasta que tem o CLAUDE.md e a pasta _kit).")
        return
    if gancho:
        evento = entrada.get("hook_event_name", "")
        sessao = entrada.get("session_id") or "sem-id"
        if evento == "SessionStart":
            aviso = inicio_de_conversa(raiz, sessao, entrada.get("source", "startup"))
            if aviso:
                print(aviso)
        elif evento == "Stop":
            razao = fim_de_resposta(raiz, sessao, entrada)
            if razao:
                # ASCII: no Windows a saída do Python não é UTF-8 por padrão, e o acento quebraria o JSON
                print(json.dumps({"decision": "block", "reason": razao}))
        return
    gravar = "--ver" not in args
    mudancas, data = a_mao(raiz, gravar)
    if mudancas is None:
        print("Primeira rodada: retrato tirado. A próxima mostra o que mudou." if gravar else
              "Ainda não há retrato. Rode sem --ver para tirar o primeiro.")
        return
    criados, alterados, movidos, sumidos = mudancas
    if not any(mudancas):
        print(f"Nada mudou desde o registro de {data}.")
        return
    print(f"Desde o registro de {data}: {len(criados)} criados, {len(alterados)} alterados, "
          f"{len(movidos)} movidos, {len(sumidos)} sumiram.")
    for rotulo, itens in (("Criados", criados), ("Alterados", alterados), ("Sumiram", sumidos)):
        if itens:
            print(f"{rotulo}: {lista(itens)}")
    if movidos:
        print(f"Movidos: {lista_movidos(movidos)}")
    print("Gravado no HISTORICO.md, seção Registro automático." if gravar else "Nada foi gravado (--ver).")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # o aviso de SessionStart é texto puro com acento
    except AttributeError:
        pass
    try:
        main()
    except Exception:
        if "--gancho" not in sys.argv:
            raise
        sys.exit(0)
