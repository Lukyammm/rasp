"""
TikTok: interceptação da API interna (api/search/item, api/post/item_list) + complemento atômico do DOM
via um único page.evaluate por rodada. Sem chamadas Playwright por elemento.
"""
import re
import urllib.parse

from scrapers.common import ResponseCollector, ScrapeContext, loads_lenient, scroll
from utils import epoch_to_local

API_MARKERS = ["api/search/item", "api/search/general", "api/post/item_list", "api/item/list"]

DOM_JS = """() => {
    const items = [];
    const nodes = document.querySelectorAll('div[data-e2e="search_video-item"], div[data-e2e="user-post-item"], a[href*="/video/"], a[href*="/photo/"]');
    for (const node of nodes) {
        const a = node.tagName.toLowerCase() === 'a' ? node : node.querySelector('a[href*="/video/"], a[href*="/photo/"]');
        if (!a) continue;
        const img = a.querySelector('img');
        items.push({ href: a.getAttribute('href') || '', alt: img ? (img.getAttribute('alt') || '') : '', text: node.innerText || '' });
    }
    return items;
}"""


def _item_to_post(ctx: ScrapeContext, item: dict, term: str) -> bool:
    item_id = str(item.get("id") or item.get("item_id") or "")
    if not item_id:
        return False
    author_obj = item.get("author") or {}
    author_name = author_obj.get("uniqueId") or author_obj.get("nickname") or term
    nickname = str(author_obj.get("nickname") or "")
    author = f"@{str(author_name).lstrip('@')}"
    stats = item.get("statsV2") or item.get("stats") or {}
    desc = str(item.get("desc") or "").strip()
    text = desc or "[Vídeo no TikTok sem legenda]"
    return ctx.add_post(
        key=item_id,
        author=author,
        text=text,
        link=f"https://www.tiktok.com/{author}/video/{item_id}",
        date=epoch_to_local(item.get("createTime")),
        likes=stats.get("diggCount", 0),
        comments=stats.get("commentCount", 0),
        views=stats.get("playCount", 0),
        shares=stats.get("shareCount", 0),
        term_fallback=term,
        match_text=f"{desc} {nickname} {author}",
        require_match=True,
    )


def _extract_items(body: str):
    for doc in loads_lenient(body):
        if not isinstance(doc, dict):
            continue
        items = doc.get("itemList") or doc.get("item_list") or []
        if not items and isinstance(doc.get("data"), list):  # api/search/general
            items = [d.get("item") for d in doc["data"] if isinstance(d, dict) and d.get("item")]
        for it in items if isinstance(items, list) else []:
            if isinstance(it, dict):
                yield it


def scrape_tiktok(page, ctx: ScrapeContext):
    if ctx.search_type == "profile":
        sub_queries = [ctx.profile_handle()]
    else:
        sub_queries = [ctx.render_variant(v, quote_phrases=True) for v in ctx.search_variants()]

    collector = ResponseCollector(page, API_MARKERS)
    api_items = {}

    try:
        for term in sub_queries:
            if ctx.should_stop():
                break
            if ctx.search_type == "profile":
                url = f"https://www.tiktok.com/@{term}"
            else:
                url = f"https://www.tiktok.com/search/video?q={urllib.parse.quote(term)}"
            ctx.log(f"TikTok: pesquisando '{term}' ({len(ctx.results)}/{ctx.limit} posts já coletados)...")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=25000)
                # A API de busca costuma responder entre 3 e 5s; o DOM só é usado se ela não vier
                collector.wait(timeout_ms=7000)
            except Exception as exc:
                ctx.log(f"TikTok: falha ao abrir {url}: {str(exc).splitlines()[0]}", "WARN")
                continue

            needed = ctx.limit - len(ctx.results)
            max_scrolls = min(max((needed // 4) + 2, 4), 30)
            scrolls = stagnant = 0
            received_for_term = 0

            while not ctx.should_stop() and scrolls <= max_scrolls:
                before = len(ctx.results)

                # 1. Itens da API oficial (métricas completas)
                for _, body in collector.drain():
                    for item in _extract_items(body):
                        item_id = str(item.get("id") or item.get("item_id") or "")
                        if item_id:
                            api_items.setdefault(item_id, item)
                            received_for_term += 1
                        _item_to_post(ctx, item, term)

                # 2. Complemento do DOM (apenas se a interceptação não entregou dados ou estagnou)
                if not ctx.full and ((received_for_term == 0 and scrolls >= 1) or stagnant >= 2):
                    try:
                        for d in page.evaluate(DOM_JS):
                            if ctx.full:
                                break
                            m_id = re.search(r"/(?:video|photo)/(\d+)", d.get("href", ""))
                            if not m_id:
                                continue
                            item_id = m_id.group(1)
                            if item_id in api_items:
                                _item_to_post(ctx, api_items[item_id], term)
                                continue
                            m_author = re.search(r"(@[\w\.\-]+)/", d.get("href", ""))
                            author = m_author.group(1) if m_author else f"@{term.replace(' ', '')}"
                            m_likes = re.search(r"([\d\.,]+[KMBkmb]?)\s*$", d.get("text", ""))
                            ts = int(item_id) >> 32
                            raw_alt = d.get("alt", "").strip()
                            ctx.add_post(
                                key=item_id,
                                author=author,
                                text=raw_alt or "[Vídeo no TikTok sem legenda]",
                                link=f"https://www.tiktok.com/{author}/video/{item_id}",
                                date=epoch_to_local(ts) if 1451606400 <= ts <= 2000000000 else None,
                                likes=m_likes.group(1) if m_likes else 0,
                                views="N/A",
                                term_fallback=term,
                                match_text=f"{raw_alt} {author}",
                                require_match=True,
                            )
                    except Exception:
                        pass

                if len(ctx.results) > before:
                    stagnant = 0
                    ctx.report()
                else:
                    stagnant += 1
                    if stagnant >= 3:
                        break

                if ctx.should_stop() or not scroll(page, 2500, 600):
                    break
                collector.wait(timeout_ms=2500)
                scrolls += 1
    finally:
        collector.detach()

    if "login" in page.url and not ctx.results:
        ctx.login_required = True
    return ctx.results
