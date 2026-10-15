r"""
Arquivamento das planilhas e relatórios na pasta do RASP, em pastas por mês:
  SocialScraper\RASP Planilhas\2026-09 Setembro\RASP_Debate-Ciro-Elmano_2026-09-12_20h07.xlsx
"""
import logging
import os
import shutil
from datetime import datetime
from typing import Optional

from config import EXPORTS_DIR

logger = logging.getLogger("rasp.exports")

MONTHS_PT = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro",
             "Outubro", "Novembro", "Dezembro"]


def month_folder(when: Optional[datetime] = None) -> str:
    when = when or datetime.now()
    return os.path.join(EXPORTS_DIR, f"{when:%Y-%m} {MONTHS_PT[when.month - 1]}")


def archive_copy(source_path: str, when: Optional[datetime] = None) -> Optional[str]:
    """Copia o arquivo para a pasta do mês. Nunca interrompe a extração se a cópia falhar."""
    try:
        folder = month_folder(when)
        os.makedirs(folder, exist_ok=True)
        target = os.path.join(folder, os.path.basename(source_path))
        shutil.copyfile(source_path, target)
        return target
    except OSError as exc:  # ex.: arquivo aberto no Excel com o mesmo nome
        logger.warning("Não foi possível salvar cópia em %s: %s", EXPORTS_DIR, exc)
        return None


def friendly_path(path: Optional[str]) -> str:
    """'Pasta do RASP › RASP Planilhas › 2026-09 Setembro' para exibir na interface."""
    if not path:
        return ""
    folder = os.path.dirname(path)
    parts = os.path.relpath(folder, os.path.dirname(EXPORTS_DIR)).split(os.sep)
    return " › ".join(["Pasta do RASP", *parts])
