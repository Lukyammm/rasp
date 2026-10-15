# -*- coding: utf-8 -*-
"""Foto da pasta do projeto antes de soltar um agente nela; confere depois e restaura se preciso.

Use antes de entregar a pasta a um agente que rode comando, e antes de "organizar" pastas. Precisa só de
Python 3, sem pacote extra.

- Arquivo de até 20 MB: cópia real, com sha256. Mudou, sumiu ou foi movido: aparece e volta.
- Arquivo maior (vídeo, base grande): espelho por hard link no cofre. Não ocupa espaço e segura o
  arquivo se ele for apagado ou movido. Não segura edição feita no próprio arquivo (o link é o mesmo
  arquivo). Em disco que não aceita hard link (Google Drive, rede), o grande só é anotado pelo tamanho.
- O cofre fica na pasta do usuário, em ~/<nome da pasta>_cofre, fora do projeto. Guarda as 5 últimas fotos.

Uso (da raiz do projeto, ou passando a pasta):
  python _kit/scripts/protecao.py fotografar [pasta]
  python _kit/scripts/protecao.py conferir   [pasta]
  python _kit/scripts/protecao.py restaurar  [pasta] --confirmo

Restaurar é decisão do usuário, nunca do agente que mexeu na pasta: já houve agente que restaurou
sozinho e desfez trabalho novo. Por isso o comando só age com --confirmo.
"""
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

LIMITE = 20 * 1024 * 1024
MANTER_FOTOS = 5
IGNORAR = {".git", "node_modules", "__pycache__", "venv", ".venv", ".pytest_cache", "dist", "build",
           ".next", ".cache"}


def raiz_do_projeto(args):
    pasta = next((a for a in args if not a.startswith("--")), None)
    if pasta:
        return Path(pasta).resolve()
    # Sem pasta, vale a pasta atual, mas só se ela for um projeto com o kit: rodar por engano na pasta do
    # usuário copiaria o disco inteiro para o cofre.
    atual = Path.cwd().resolve()
    if not (atual / "_kit").is_dir():
        raise SystemExit(f"{atual} não tem a pasta _kit: rode da raiz do projeto ou passe a pasta.")
    return atual


def cofre_de(raiz):
    return Path.home() / f"{raiz.name.replace(' ', '_')}_cofre"


def sha(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def listar(raiz):
    for atual, pastas, arquivos in os.walk(raiz):
        pastas[:] = [p for p in pastas if p not in IGNORAR and not p.endswith("_cofre")]
        for nome in arquivos:
            yield Path(atual) / nome


def fotografar(raiz):
    cofre = cofre_de(raiz)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = cofre / marca
    espelho = cofre / "_grandes"
    manifesto = {"raiz": str(raiz), "feita_em": marca, "pequenos": {}, "grandes": {}}
    sem_link = 0
    for p in listar(raiz):
        rel = p.relative_to(raiz).as_posix()
        tamanho = p.stat().st_size
        if tamanho <= LIMITE:
            alvo = destino / rel
            alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, alvo)
            manifesto["pequenos"][rel] = sha(p)
            continue
        manifesto["grandes"][rel] = tamanho
        link = espelho / rel
        if link.exists():
            continue
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(p, link)
        except OSError:
            sem_link += 1
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "_manifesto.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    fotos = sorted(d for d in cofre.iterdir() if d.is_dir() and d.name[0].isdigit())
    for velha in fotos[:-MANTER_FOTOS]:
        shutil.rmtree(velha)
    print(f"foto {marca} em {destino}: {len(manifesto['pequenos'])} arquivos copiados, "
          f"{len(manifesto['grandes'])} grandes no espelho")
    if sem_link:
        print(f"atenção: {sem_link} arquivos grandes sem hard link (disco não aceita); só o tamanho foi anotado")


def ultima_foto(raiz):
    cofre = cofre_de(raiz)
    fotos = sorted(d for d in cofre.iterdir() if d.is_dir() and d.name[0].isdigit()) if cofre.exists() else []
    return fotos[-1] if fotos else None


def diferencas(raiz):
    foto = ultima_foto(raiz)
    if foto is None:
        return None, [], [], [], []
    m = json.loads((foto / "_manifesto.json").read_text(encoding="utf-8"))
    mudados, sumidos, grandes = [], [], []
    for rel, h in m["pequenos"].items():
        atual = raiz / rel
        if not atual.exists():
            sumidos.append(rel)
        elif sha(atual) != h:
            mudados.append(rel)
    for rel, tamanho in m["grandes"].items():
        atual = raiz / rel
        if not atual.exists() or atual.stat().st_size != tamanho:
            grandes.append(rel)
    conhecidos = set(m["pequenos"]) | set(m["grandes"])
    novos = [p.relative_to(raiz).as_posix() for p in listar(raiz)
             if p.relative_to(raiz).as_posix() not in conhecidos]
    return foto, mudados, sumidos, grandes, novos


def conferir(raiz):
    foto, mudados, sumidos, grandes, novos = diferencas(raiz)
    if foto is None:
        print("nenhuma foto ainda")
        return 0
    for rel in mudados:
        print(f"MUDOU   {rel}")
    for rel in sumidos:
        print(f"SUMIU   {rel}")
    for rel in grandes:
        print(f"GRANDE  {rel} (sumiu ou mudou de tamanho)")
    for rel in novos:
        print(f"NOVO    {rel}")
    if not (mudados or sumidos or grandes):
        print(f"nada da foto {foto.name} mudou ou sumiu ({len(novos)} arquivos novos)")
        return 0
    print(f"\nse não era para mudar: python _kit/scripts/protecao.py restaurar \"{raiz}\" --confirmo  "
          f"(foto {foto.name})")
    return 1


def restaurar(raiz, confirmado):
    foto, mudados, sumidos, grandes, _ = diferencas(raiz)
    if foto is None:
        raise SystemExit("nenhuma foto para restaurar")
    if not confirmado:
        conferir(raiz)
        raise SystemExit("\nnada foi restaurado: rode de novo com --confirmo")
    for rel in mudados + sumidos:
        alvo = raiz / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(foto / rel, alvo)
        print(f"restaurado {rel}")
    espelho = cofre_de(raiz) / "_grandes"
    for rel in grandes:
        origem = espelho / rel
        if not origem.exists():
            print(f"sem cópia no espelho, não restaurado: {rel}")
            continue
        alvo = raiz / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        if alvo.exists():
            alvo.unlink()
        os.link(origem, alvo)
        print(f"restaurado {rel}")
    print("feito" if (mudados or sumidos or grandes) else "nada a restaurar")


if __name__ == "__main__":
    acao = sys.argv[1] if len(sys.argv) > 1 else ""
    resto = sys.argv[2:]
    raiz = raiz_do_projeto(resto)
    if acao == "fotografar":
        fotografar(raiz)
    elif acao == "conferir":
        raise SystemExit(conferir(raiz))
    elif acao == "restaurar":
        restaurar(raiz, "--confirmo" in resto)
    else:
        print(__doc__)
