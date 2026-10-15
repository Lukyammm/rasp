"""
Abertura do navegador para extração, com a estratégia de sessões consolidada:
1. sessao_{rede}.json com cookies de login válidos -> storage_state (rápido e estável)
2. perfil sessao_{rede}_dir com login -> sincroniza para o .json e usa o passo 1
3. perfil persistente sem login confirmado
4. navegação anônima

Também garante: um navegador por rede por vez (network_lock), User-Agent coerente com a versão real do Chrome
instalado (evita a assinatura "Chrome/122" desatualizada) e renovação do .json ao final da coleta.
"""
import json
import logging
import os
import threading
import time
from contextlib import contextmanager
from typing import Optional

from config import AUTH_COOKIES, NETWORKS, session_dir_path, session_json_path
from scrapers.login_manager import json_auth_status, profile_dir_has_auth

logger = logging.getLogger("rasp.browser")

LAUNCH_ARGS = ["--disable-blink-features=AutomationControlled", "--disable-infobars", "--test-type", "--lang=pt-BR"]
IGNORE_DEFAULT_ARGS = ["--enable-automation"]
VIEWPORT = {"width": 1366, "height": 850}

_network_locks = {n: threading.Lock() for n in NETWORKS}
_chrome_version: Optional[str] = None


def installed_chrome_version() -> Optional[str]:
    global _chrome_version
    if _chrome_version:
        return _chrome_version
    if os.name == "nt":
        import winreg
        candidates = [
            (winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon", "version"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Google\Update\Clients\{8A69D345-D564-463c-AFF1-A69D9E530F96}", "pv"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Google\Update\Clients\{8A69D345-D564-463c-AFF1-A69D9E530F96}", "pv"),
        ]
        for hive, path, value in candidates:
            try:
                with winreg.OpenKey(hive, path) as key:
                    _chrome_version = str(winreg.QueryValueEx(key, value)[0])
                    return _chrome_version
            except OSError:
                continue
    return None


def chrome_user_agent(version: Optional[str] = None) -> Optional[str]:
    global _chrome_version
    if version:
        _chrome_version = version
    version = version or installed_chrome_version()
    if not version:
        return None
    major = str(version).split(".")[0]
    return (f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            f"(KHTML, like Gecko) Chrome/{major}.0.0.0 Safari/537.36")


def _launch(p):
    try:
        return p.chromium.launch(headless=True, channel="chrome", args=LAUNCH_ARGS, ignore_default_args=IGNORE_DEFAULT_ARGS)
    except Exception as exc:
        logger.info("Google Chrome indisponível (%s). Usando o Chromium do Playwright.", str(exc).splitlines()[0])
        return p.chromium.launch(headless=True, args=LAUNCH_ARGS, ignore_default_args=IGNORE_DEFAULT_ARGS)


def _launch_persistent(p, user_dir: str):
    options = dict(user_data_dir=user_dir, headless=True, args=LAUNCH_ARGS, ignore_default_args=IGNORE_DEFAULT_ARGS,
                   viewport=VIEWPORT, locale="pt-BR")
    ua = chrome_user_agent()
    if ua:
        options["user_agent"] = ua
    last_error = None
    for attempt in range(3):
        for channel in ("chrome", None):
            try:
                if channel:
                    return p.chromium.launch_persistent_context(channel=channel, **options)
                return p.chromium.launch_persistent_context(**options)
            except Exception as exc:  # perfil em uso (janela de login aberta) ou Chrome ausente
                last_error = exc
        time.sleep(1.2 * (attempt + 1))
    raise last_error


def _save_session_if_authenticated(context, network: str) -> None:
    try:
        state = context.storage_state()
    except Exception:
        return
    names = {c.get("name") for c in state.get("cookies", [])}
    if not any(n in names for n in AUTH_COOKIES.get(network, [])):
        return  # nunca sobrescreve uma sessão boa com um estado deslogado
    path = session_json_path(network)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(tmp, path)
    except OSError as exc:
        logger.debug("Não foi possível renovar %s: %s", path, exc)


@contextmanager
def network_lock(network: str, cancel_event: Optional[threading.Event] = None, on_wait=None):
    """
    Um navegador por rede por vez. Espera sem prazo fixo (a outra extração sempre libera ao terminar),
    mas desiste se a extração atual for cancelada. Entrega False nesse caso.
    """
    lock = _network_locks.get(network) or threading.Lock()
    waited = 0.0
    while not lock.acquire(timeout=2.0):
        if cancel_event is not None and cancel_event.is_set():
            yield False
            return
        if on_wait and waited % 60 == 0:
            on_wait()
        waited += 2.0
    try:
        yield True
    finally:
        lock.release()


@contextmanager
def open_page(p, network: str):
    """Context manager que entrega (page, modo) e fecha tudo ao final. Use dentro de network_lock()."""
    browser = context = None
    mode = "anonimo"
    json_path, dir_path = session_json_path(network), session_dir_path(network)
    try:
        has_json_auth = json_auth_status(network)[0]
        if not has_json_auth and os.path.isdir(dir_path) and profile_dir_has_auth(network):
            try:
                tmp_ctx = _launch_persistent(p, dir_path)
                tmp_ctx.storage_state(path=json_path)
                tmp_ctx.close()
                has_json_auth = json_auth_status(network)[0]
                logger.info("Sessão de %s sincronizada do perfil para %s", network, json_path)
            except Exception as exc:
                logger.warning("Falha ao sincronizar perfil de %s: %s", network, exc)

        if has_json_auth:
            browser = _launch(p)
            context = browser.new_context(storage_state=json_path, viewport=VIEWPORT, locale="pt-BR",
                                          user_agent=chrome_user_agent(browser.version))
            mode = "sessao"
        elif os.path.isdir(dir_path):
            context = _launch_persistent(p, dir_path)
            mode = "perfil"
        else:
            browser = _launch(p)
            context = browser.new_context(viewport=VIEWPORT, locale="pt-BR", user_agent=chrome_user_agent(browser.version))

        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(30000)
        logger.info("Navegador de %s aberto (modo: %s)", network, mode)
        yield page, mode

        if mode == "sessao":
            _save_session_if_authenticated(context, network)
    finally:
        for obj in (context, browser):
            if obj is not None:
                try:
                    obj.close()
                except Exception:
                    pass
