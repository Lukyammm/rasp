"""
Despachante central de redes: abre o navegador (Playwright síncrono — executado via asyncio.to_thread pelo backend),
delega ao scraper da rede e devolve um DataFrame padronizado.
"""
import logging
import threading
import time
from typing import Callable, Optional

import pandas as pd

try:
    from patchright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    from playwright.sync_api import sync_playwright

from database import load_brand_handles
from scrapers.browser import network_lock, open_page
from scrapers.common import POST_COLUMNS, ScrapeContext
from scrapers.facebook_scraper import scrape_facebook
from scrapers.instagram_scraper import scrape_instagram
from scrapers.tiktok_scraper import scrape_tiktok
from scrapers.x_scraper import scrape_x
from scrapers.youtube_scraper import scrape_youtube
# Reexportados por compatibilidade com scripts antigos
from utils import check_boolean_query, decode_instagram_date, parse_numeric_metric, parse_social_date  # noqa: F401

logger = logging.getLogger("rasp.scraper")

SCRAPERS = {
    "x": scrape_x,
    "tiktok": scrape_tiktok,
    "instagram": scrape_instagram,
    "youtube": scrape_youtube,
    "facebook": scrape_facebook,
}

REQUIRES_LOGIN = {"x", "instagram", "facebook"}


def scrape_network(network: str, keyword: str, limit: int = 20, scrape_comments: bool = False,
                   start_date: Optional[str] = None, end_date: Optional[str] = None, search_type: str = "keyword",
                   progress_callback: Optional[Callable[[str], None]] = None,
                   cancel_event: Optional[threading.Event] = None, brand_handles: Optional[dict] = None):
    """Retorna (DataFrame, total_de_posts, soma_de_comentarios)."""
    network = (network or "").lower().strip()
    if network not in SCRAPERS:
        raise ValueError(f"Rede não suportada: {network}")

    if brand_handles is None and search_type == "profile":
        try:
            brand_handles = load_brand_handles()
        except Exception:
            brand_handles = {}

    ctx = ScrapeContext(
        network=network, keyword=keyword, limit=limit, search_type=search_type,
        start_date=start_date or None, end_date=end_date or None, brand_handles=brand_handles or {},
        progress_callback=progress_callback, cancel_event=cancel_event,
    )
    logger.info("[%s] %s por '%s' (termos: %s, limite %s)", network.upper(), search_type, ctx.keyword, ctx.atomic_terms, limit)

    wait_msg = f"{ctx.name}: aguardando outra extração nesta rede terminar..."
    with network_lock(network, cancel_event, on_wait=lambda: ctx.log(wait_msg)) as acquired:
        if acquired:
            ctx.started_at = time.monotonic()  # o tempo de espera não consome o tempo máximo da busca
            try:
                with sync_playwright() as p:
                    with open_page(p, network) as (page, mode):
                        ctx.authenticated = mode == "sessao"
                        if network in REQUIRES_LOGIN and mode != "sessao":
                            ctx.log(f"{ctx.name}: nenhuma sessão logada encontrada — os resultados podem ser limitados.", "WARN")
                        SCRAPERS[network](page, ctx)
            except Exception as exc:
                if not ctx.results:
                    raise
                ctx.log(f"{ctx.name}: extração interrompida por erro ({str(exc).splitlines()[0]}). "
                        f"Mantendo {len(ctx.results)} posts já coletados.", "WARN")
                logger.exception("Erro durante scrape de %s", network)

    if ctx.skipped_by_date:
        ctx.log(f"{ctx.name}: {ctx.skipped_by_date} posts ignorados por estarem fora do período selecionado.")

    df = pd.DataFrame(ctx.results[:limit], columns=POST_COLUMNS)
    comments_total = int(df["Comentarios"].map(parse_numeric_metric).sum()) if not df.empty else 0
    return df, len(df), comments_total
