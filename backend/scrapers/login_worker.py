"""
Processo isolado de login interativo: `python -m scrapers.login_worker <rede>` (executado a partir de /backend).
Abre o Chrome real com o perfil persistente e sincroniza o storage_state em sessao_{rede}.json
enquanto a janela estiver aberta.

As extrações renovam só o sessao_{rede}.json, então o perfil pode ter cookies mais antigos. Por isso:
1. os cookies válidos do .json são copiados para o perfil antes de abrir a página;
2. o .json só é regravado quando o estado ainda contém os cookies de login (nunca com um estado deslogado).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from patchright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    from playwright.sync_api import sync_playwright

from config import AUTH_COOKIES, LOGIN_URLS, session_dir_path, session_json_path  # noqa: E402
from scrapers.browser import IGNORE_DEFAULT_ARGS, LAUNCH_ARGS  # noqa: E402
from scrapers.login_manager import json_auth_status  # noqa: E402


def _has_auth(state: dict, network: str) -> bool:
    names = {c.get("name") for c in (state or {}).get("cookies", [])}
    return any(n in names for n in AUTH_COOKIES.get(network, []))


def _save_state(context, path: str, network: str) -> None:
    try:
        state = context.storage_state()
    except Exception:
        return
    if not _has_auth(state, network):
        return
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass


def _seed_from_json(context, path: str, network: str) -> None:
    """Leva para o perfil os cookies mais recentes renovados pelas extrações."""
    if not json_auth_status(network)[0]:
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            cookies = json.load(f).get("cookies", [])
        if cookies:
            context.add_cookies(cookies)
    except Exception:
        pass


def main(network: str) -> None:
    url = LOGIN_URLS[network]
    session_dir = session_dir_path(network)
    session_json = session_json_path(network)
    with sync_playwright() as p:
        options = dict(user_data_dir=session_dir, headless=False, args=LAUNCH_ARGS,
                       ignore_default_args=IGNORE_DEFAULT_ARGS, no_viewport=True, locale="pt-BR")
        try:
            context = p.chromium.launch_persistent_context(channel="chrome", **options)
        except Exception:
            context = p.chromium.launch_persistent_context(**options)

        _seed_from_json(context, session_json, network)
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            pass

        ticks = 0
        while True:
            pages = context.pages
            if not pages:
                break
            try:
                pages[0].wait_for_timeout(1500)
            except Exception:
                if not context.pages:
                    break
                continue
            ticks += 1
            if ticks % 2 == 0:
                _save_state(context, session_json, network)

        _save_state(context, session_json, network)
        try:
            context.close()
        except Exception:
            pass


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in LOGIN_URLS:
        sys.exit("uso: python -m scrapers.login_worker <x|tiktok|instagram|youtube|facebook>")
    main(sys.argv[1])
