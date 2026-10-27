"""
Configuração central do RASP: caminhos, redes suportadas, cookies de autenticação e logging.
Todos os caminhos são absolutos para que o sistema funcione independentemente do diretório de trabalho.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BACKEND_DIR)
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")
# As variáveis RASP_* permitem apontar para outro banco/pasta (útil em testes)
DOWNLOADS_DIR = os.environ.get("RASP_DOWNLOADS_DIR") or os.path.join(BACKEND_DIR, "downloads")
LOGS_DIR = os.environ.get("RASP_LOGS_DIR") or os.path.join(BACKEND_DIR, "logs")
DB_PATH = os.environ.get("RASP_DB_PATH") or os.path.join(BACKEND_DIR, "datapulse.db")
# Sessões ficam no diretório do backend (sessao_{rede}.json e sessao_{rede}_dir) — mantido por compatibilidade.
SESSIONS_DIR = BACKEND_DIR
LEGACY_BRANDS_FILE = os.path.join(BACKEND_DIR, "brands.json")

MEDIA_DIR = os.environ.get("RASP_MEDIA_DIR") or os.path.join(BACKEND_DIR, "media_store")
VIDEOS_DIR = os.path.join(MEDIA_DIR, "videos")
CONTACT_SHEETS_DIR = os.path.join(MEDIA_DIR, "contact_sheets")
FRAMES_DIR = os.path.join(MEDIA_DIR, "frames")
LOGOS_DIR = os.path.join(MEDIA_DIR, "logos")

for _d in (DOWNLOADS_DIR, LOGS_DIR, MEDIA_DIR, VIDEOS_DIR, CONTACT_SHEETS_DIR, FRAMES_DIR, LOGOS_DIR):
    os.makedirs(_d, exist_ok=True)


def _desktop_dir() -> str:
    """Área de Trabalho real do usuário (respeita redirecionamento para OneDrive)."""
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
                path = os.path.expandvars(winreg.QueryValueEx(key, "Desktop")[0])
                if os.path.isdir(path):
                    return path
        except OSError:
            pass
    return os.path.join(os.path.expanduser("~"), "Desktop")


# Cópia organizada das planilhas e relatórios: <pasta do RASP>\RASP Planilhas\2026-09 Setembro\
EXPORTS_DIR = os.environ.get("RASP_EXPORTS_DIR") or os.path.join(PROJECT_DIR, "RASP Planilhas")

NETWORKS = ["x", "tiktok", "instagram", "youtube", "facebook"]

NETWORK_LABELS = {
    "x": "X (Twitter)",
    "tiktok": "TIKTOK",
    "instagram": "INSTAGRAM",
    "youtube": "YOUTUBE",
    "facebook": "FACEBOOK",
}

NETWORK_SHORT = {"tiktok": "T", "x": "X", "instagram": "Ig", "facebook": "Fb", "youtube": "Yt"}

LOGIN_URLS = {
    "x": "https://x.com/",
    "tiktok": "https://www.tiktok.com/",
    "instagram": "https://www.instagram.com/",
    "youtube": "https://www.youtube.com/",
    "facebook": "https://www.facebook.com/",
}

# Cookies que comprovam uma sessão autenticada em cada rede
AUTH_COOKIES = {
    "x": ["auth_token"],
    "tiktok": ["sessionid", "sessionid_ss", "sid_tt"],
    "instagram": ["sessionid"],
    "youtube": ["LOGIN_INFO", "SAPISID", "__Secure-3PSID", "SID"],
    "facebook": ["c_user", "xs"],
}

API_HOST = os.environ.get("RASP_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("RASP_PORT", "8000"))

ALLOWED_ORIGINS = [
    "http://127.0.0.1:8080",
    "http://localhost:8080",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

# Limites operacionais
MAX_LIMIT_PER_NETWORK = 1_000_000  # sem teto prático (pedido do Lukyam, 27/10/2026: "eu nao quero limitacao")
MAX_CONCURRENT_JOBS = 2
JOB_LOG_HISTORY = 400


def session_json_path(network: str) -> str:
    return os.path.join(SESSIONS_DIR, f"sessao_{network}.json")


def session_dir_path(network: str) -> str:
    return os.path.join(SESSIONS_DIR, f"sessao_{network}_dir")


_logging_configured = False


def setup_logging() -> None:
    """Log em arquivo rotativo (o servidor roda oculto via VBS, então o console não é visível)."""
    global _logging_configured
    if _logging_configured:
        return
    _logging_configured = True
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    file_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, "rasp.log"), maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)
    for noisy in ("apscheduler.executors.default", "apscheduler.scheduler"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
