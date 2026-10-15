"""
YouTube: leitura do ytInitialData (script da página, via page.evaluate) + interceptação das continuações
youtubei/v1/search e youtubei/v1/browse. Suporta layouts videoRenderer, gridVideoRenderer, reels/shorts e lockupViewModel.
"""
import json
import re
import urllib.parse

from scrapers.common import ResponseCollector, ScrapeContext, iter_dicts, loads_lenient, scroll, text_runs
from utils import parse_numeric_metric, parse_social_date

API_MARKERS = ["/youtubei/v1/search", "/youtubei/v1/browse"]

INITIAL_DATA_JS = """() => {
    for (const s of document.querySelectorAll('script')) {
        const t = s.textContent || '';
        if (t.includes('ytInitialData')) return t;
    }
    return '';
}"""


def _initial_data(script_text: str):
    m = re.search(r"ytInitialData\"?\]?\s*=\s*", script_text or "")
    if not m:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(script_text, m.end())
        return obj
    except ValueError:
        return None


def _views_from_text(value: str) -> int:
    txt = (value or "").lower()
    if not txt or "nenhuma" in txt or "no views" in txt:
        return 0
    return parse_numeric_metric(txt)


def _parse_renderer(key: str, r: dict):
    """Normaliza os diferentes renderers do YouTube em um dicionário comum."""
    if key in ("videoRenderer", "gridVideoRenderer", "compactVideoRenderer"):
        owner = r.get("ownerText") or r.get("longBylineText") or r.get("shortBylineText") or {}
        runs = owner.get("runs") or [{}]
        base_url = ((runs[0].get("navigationEndpoint") or {}).get("browseEndpoint") or {}).get("canonicalBaseUrl", "")
        snippet = " ".join(text_runs(s.get("snippetText")) for s in r.get("detailedMetadataSnippets") or [])
        return {
            "id": r.get("videoId"),
            "title": text_runs(r.get("title")),
            "channel": text_runs(owner),
            "handle": base_url.split("/@")[-1] if "/@" in base_url else "",
            "views": _views_from_text(text_runs(r.get("viewCountText")) or text_runs(r.get("shortViewCountText"))),
            "published": text_runs(r.get("publishedTimeText")),
            "snippet": snippet or text_runs(r.get("descriptionSnippet")),
            "short": False,
        }
    if key == "reelItemRenderer":
        return {"id": r.get("videoId"), "title": text_runs(r.get("headline")), "channel": "", "handle": "",
                "views": _views_from_text(text_runs(r.get("viewCountText"))), "published": "", "snippet": "", "short": True}
    if key == "shortsLockupViewModel":
        video_id = (((r.get("onTap") or {}).get("innertubeCommand") or {}).get("reelWatchEndpoint") or {}).get("videoId")
        overlay = r.get("overlayMetadata") or {}
        return {"id": video_id, "title": text_runs(overlay.get("primaryText")), "channel": "", "handle": "",
                "views": _views_from_text(text_runs(overlay.get("secondaryText"))), "published": "", "snippet": "", "short": True}
    if key == "lockupViewModel" and "VIDEO" in str(r.get("contentType", "")):
        meta = ((r.get("metadata") or {}).get("lockupMetadataViewModel") or {})
        parts = []
        for row in ((meta.get("metadata") or {}).get("contentMetadataViewModel") or {}).get("metadataRows") or []:
            parts.extend(text_runs(p.get("text")) for p in row.get("metadataParts") or [])
        views = next((p for p in parts if re.search(r"visualiza|views?", p, re.IGNORECASE)), "")
        published = next((p for p in parts if re.search(r"há|ago|atrás|transmitido|streamed", p, re.IGNORECASE)), "")
        channel = next((p for p in parts if p and p not in (views, published)), "")
        return {"id": r.get("contentId"), "title": text_runs(meta.get("title")), "channel": channel, "handle": "",
                "views": _views_from_text(views), "published": published, "snippet": "", "short": False}
    return None


RENDERER_KEYS = ("videoRenderer", "gridVideoRenderer", "reelItemRenderer", "shortsLockupViewModel", "lockupViewModel")


def _collect(ctx: ScrapeContext, doc, term: str, profile_handle: str) -> int:
    added = 0
    for d in iter_dicts(doc):
        for key in RENDERER_KEYS:
            r = d.get(key)
            if not isinstance(r, dict):
                continue
            video = _parse_renderer(key, r)
            if not video or not video.get("id") or not video.get("title"):
                continue
            handle = video["handle"] or profile_handle
            author = f"@{handle}" if handle else ("@" + video["channel"].replace(" ", "_") if video["channel"] else "@canal_youtube")
            link = (f"https://www.youtube.com/shorts/{video['id']}" if video["short"]
                    else f"https://www.youtube.com/watch?v={video['id']}")
            if ctx.add_post(
                key=video["id"],
                author=author,
                text=video["title"],
                link=link,
                date=parse_social_date(video["published"]) if video["published"] else None,
                views=video["views"],
                term_fallback=term,
                match_text=f"{video['title']} {video['snippet']} {video['channel']} {author}",
                require_match=True,
            ):
                added += 1
    return added


def scrape_youtube(page, ctx: ScrapeContext):
    profile_handle = ""
    if ctx.search_type == "profile":
        profile_handle = ctx.profile_handle()
        sub_queries = [profile_handle]
    else:
        sub_queries = [ctx.render_variant(v, quote_phrases=True) for v in ctx.search_variants()]

    # Vídeos apenas; com período definido, ordena por data de envio para priorizar conteúdo recente
    search_filter = "CAISAhAB" if (ctx.start_dt or ctx.end_dt) else "EgIQAQ%3D%3D"
    target_per_term = max((ctx.limit // len(sub_queries)) + 2, 8)
    collector = ResponseCollector(page, API_MARKERS)
    try:
        for term in sub_queries:
            if ctx.should_stop():
                break
            if profile_handle:
                url = f"https://www.youtube.com/@{urllib.parse.quote(term)}/videos"
            else:
                url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(term)}&sp={search_filter}"
            ctx.log(f"YouTube: pesquisando '{term}' ({len(ctx.results)}/{ctx.limit} posts já coletados)...")
            start_count = len(ctx.results)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1200)
                _collect(ctx, _initial_data(page.evaluate(INITIAL_DATA_JS)), term, profile_handle)
                ctx.report()
            except Exception as exc:
                ctx.log(f"YouTube: falha ao abrir {url}: {str(exc).splitlines()[0]}", "WARN")
                continue

            max_scrolls = min((target_per_term // 15) + 4, 25)
            scrolls = stagnant = 0
            while not ctx.should_stop() and (len(ctx.results) - start_count) < target_per_term and scrolls <= max_scrolls:
                if not scroll(page, 4000, 900):
                    break
                collector.wait(timeout_ms=3000)
                scrolls += 1
                before = len(ctx.results)
                for _, body in collector.drain():
                    for doc in loads_lenient(body):
                        _collect(ctx, doc, term, profile_handle)
                if len(ctx.results) > before:
                    stagnant = 0
                    ctx.report()
                else:
                    stagnant += 1
                    if stagnant >= 3:
                        break
    finally:
        collector.detach()
    return ctx.results
