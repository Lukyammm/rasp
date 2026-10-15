"""
Gestão de sessões das redes sociais.
- interactive_login: abre uma janela real do Chrome (processo separado, fora do event loop do Uvicorn)
  usando o perfil persistente sessao_{rede}_dir e sincronizando sessao_{rede}.json.
- check_accounts: verifica cookies de autenticação válidos (presentes e não expirados).
"""
import json
import logging
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

from config import AUTH_COOKIES, BACKEND_DIR, NETWORKS, session_dir_path, session_json_path

logger = logging.getLogger("rasp.sessions")

_login_processes = {}

# Chrome grava expires_utc em microssegundos desde 1601-01-01
_CHROME_EPOCH_OFFSET = 11644473600


def json_auth_status(network: str):
    """(autenticado, expira_em_epoch|None) a partir do sessao_{rede}.json."""
    path = session_json_path(network)
    if not os.path.exists(path):
        return False, None
    try:
        with open(path, "r", encoding="utf-8") as f:
            cookies = json.load(f).get("cookies", [])
    except (OSError, ValueError, AttributeError):
        return False, None
    needed = set(AUTH_COOKIES.get(network, []))
    now = time.time()
    expiries = []
    for c in cookies:
        if c.get("name") not in needed:
            continue
        exp = c.get("expires", -1)
        if exp in (-1, None) or float(exp) > now:
            expiries.append(None if exp in (-1, None) else float(exp))
    if not expiries:
        return False, None
    finite = [e for e in expiries if e]
    return True, (max(finite) if finite else None)


def _copy_locked_file(src: str, dst: str) -> bool:
    try:
        shutil.copyfile(src, dst)
        return True
    except OSError:
        if os.name == "nt":
            subprocess.run(["cmd", "/c", "copy", "/Y", src, dst], capture_output=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return os.path.exists(dst)
    return False


def profile_dir_has_auth(network: str) -> bool:
    """Verifica, numa cópia do banco de cookies do perfil persistente, se há cookie de login válido."""
    session_dir = session_dir_path(network)
    if not os.path.isdir(session_dir):
        return False
    cookie_db = os.path.join(session_dir, "Default", "Network", "Cookies")
    if not os.path.exists(cookie_db):
        cookie_db = os.path.join(session_dir, "Default", "Cookies")
    if not os.path.exists(cookie_db):
        return False
    tmp_path = os.path.join(tempfile.gettempdir(), f"rasp_check_{network}_{os.getpid()}.db")
    try:
        if not _copy_locked_file(cookie_db, tmp_path):
            return False
        conn = sqlite3.connect(tmp_path)
        try:
            rows = conn.execute("SELECT name, expires_utc, has_expires FROM cookies").fetchall()
        finally:
            conn.close()
        now_chrome = (time.time() + _CHROME_EPOCH_OFFSET) * 1_000_000
        needed = set(AUTH_COOKIES.get(network, []))
        return any(name in needed and (not has_exp or exp > now_chrome) for name, exp, has_exp in rows)
    except Exception as exc:
        logger.debug("Falha ao ler cookies do perfil %s: %s", network, exc)
        return False
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def login_window_open(network: str) -> bool:
    proc = _login_processes.get(network)
    return bool(proc and proc.poll() is None)


def check_accounts() -> dict:
    status = {}
    for net in NETWORKS:
        ok, expires = json_auth_status(net)
        source = "sessao" if ok else None
        if not ok and profile_dir_has_auth(net):
            ok, source = True, "perfil"
        status[net] = {
            "logged_in": ok,
            "source": source,
            "expires_at": time.strftime("%d/%m/%Y", time.localtime(expires)) if expires else None,
            "login_window_open": login_window_open(net),
        }
    return status


def interactive_login(network: str) -> dict:
    if network not in NETWORKS:
        raise ValueError("Rede não suportada para login")
    if login_window_open(network):
        return {"status": "success", "message": f"A janela de login do {network} já está aberta."}
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    proc = subprocess.Popen(
        [sys.executable, "-X", "utf8", "-m", "scrapers.login_worker", network],
        cwd=BACKEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    _login_processes[network] = proc
    logger.info("Janela de login aberta para %s (pid %s)", network, proc.pid)
    return {"status": "success", "message": f"Janela do {network} aberta. Faça login e feche a janela ao terminar."}
