"""
X (Twitter): interceptação das respostas GraphQL SearchTimeline / UserTweets (texto completo, curtidas,
respostas, reposts, visualizações e data exata) com complemento atômico do DOM via page.evaluate.
"""
import html
import re
import urllib.parse
from datetime import datetime, timedelta

from scrapers.common import ResponseCollector, ScrapeContext, iter_dicts, loads_lenient, scroll
from utils import parse_numeric_metric, parse_social_date

GRAPHQL_MARKERS = ["/SearchTimeline", "/UserTweets", "/UserTweetsAndReplies"]

DOM_JS = """() => {
    const out = [];
    for (const art of document.querySelectorAll('article')) {
        const statusLink = Array.from(art.querySelectorAll('a[href*="/status/"]')).find(a => a.querySelector('time')) || art.querySelector('a[href*="/status/"]');
        if (!statusLink) continue;
        const time = art.querySelector('time');
        const textEl = art.querySelector('[data-testid="tweetText"]');
        const userEl = art.querySelector('[data-testid="User-Name"]');
        const metric = (sel) => { const el = art.querySelector(sel); return el ? (el.getAttribute('aria-label') || el.innerText || '') : ''; };
        out.push({
            href: statusLink.getAttribute('href') || '',
            datetime: time ? time.getAttribute('datetime') : '',
            text: textEl ? textEl.innerText : '',
            user: userEl ? userEl.innerText : '',
            replies: metric('[data-testid="reply"]'),
            likes: metric('[data-testid="like"], [data-testid="unlike"]'),
            reposts: metric('[data-testid="retweet"], [data-testid="unretweet"]'),
            views: metric('a[href*="/analytics"]'),
            promoted: !!art.querySelector('[data-testid="placementTracking"]')
        });
    }
    return out;
}"""


def _tweet_from_result(result):
    if not isinstance(result, dict):
        return None
    if result.get("__typename") == "TweetWithVisibilityResults":
        result = result.get("tweet") or {}
    return result if isinstance(result.get("legacy"), dict) else None


def _parse_created_at(value):
    try:
        return datetime.strptime(value, "%a %b %d %H:%M:%S %z %Y").astimezone().replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


def _process_graphql(ctx: ScrapeContext, body: str, profile_handle: str = "") -> int:
    added = 0
    for doc in loads_lenient(body):
        for d in iter_dicts(doc):
            item = d.get("itemContent")
            if not isinstance(item, dict) or "tweet_results" not in item or item.get("promotedMetadata"):
                continue
            tweet = _tweet_from_result((item.get("tweet_results") or {}).get("result"))
            if not tweet:
                continue
            legacy = tweet["legacy"]
            tweet_id = legacy.get("id_str") or tweet.get("rest_id")
            user = ((tweet.get("core") or {}).get("user_results") or {}).get("result") or {}
            handle = (user.get("core") or {}).get("screen_name") or (user.get("legacy") or {}).get("screen_name") or ""
            name = (user.get("core") or {}).get("name") or (user.get("legacy") or {}).get("name") or ""
            note = (((tweet.get("note_tweet") or {}).get("note_tweet_results") or {}).get("result") or {}).get("text")
            text = html.unescape(note or legacy.get("full_text") or "") or "[Postagem com Mídia / Sem texto]"
            quoted = _tweet_from_result(((tweet.get("quoted_status_result") or {}).get("result")))
            quoted_text = (quoted or {}).get("legacy", {}).get("full_text", "")
            if profile_handle and handle and handle.lower() != profile_handle.lower() and not text.startswith("RT @"):
                continue
            if ctx.add_post(
                key=str(tweet_id),
                author=f"@{handle}" if handle else "@desconhecido",
                text=text,
                link=f"https://x.com/{handle or 'i'}/status/{tweet_id}",
                date=_parse_created_at(legacy.get("created_at")),
                likes=legacy.get("favorite_count", 0),
                comments=legacy.get("reply_count", 0),
                views=(tweet.get("views") or {}).get("count", 0),
                shares=int(legacy.get("retweet_count", 0) or 0) + int(legacy.get("quote_count", 0) or 0),
                match_text=f"{text} {quoted_text} {name} {handle}",
                require_match=True,
            ):
                added += 1
    return added


def _metric(label: str) -> int:
    m = re.search(r"([\d\.,]+(?:\s*(?:mil|mi|k|m|b))?)", label or "", re.IGNORECASE)
    return parse_numeric_metric(m.group(1)) if m else 0


def _process_dom(ctx: ScrapeContext, page) -> int:
    added = 0
    try:
        items = page.evaluate(DOM_JS)
    except Exception:
        return 0
    for it in items:
        m = re.search(r"/([\w]+)/status/(\d+)", it.get("href", ""))
        if not m or it.get("promoted"):
            continue
        handle, tweet_id = m.group(1), m.group(2)
        text = " ".join((it.get("text") or "").split()) or "[Postagem com Mídia / Sem texto]"
        if ctx.add_post(
            key=tweet_id,
            author=f"@{handle}",
            text=text,
            link=f"https://x.com/{handle}/status/{tweet_id}",
            date=parse_social_date(it.get("datetime")),
            likes=_metric(it.get("likes")),
            comments=_metric(it.get("replies")),
            views=_metric(it.get("views")),
            shares=_metric(it.get("reposts")),
            match_text=f"{text} {it.get('user', '')}",
            require_match=True,
        ):
            added += 1
    return added


def scrape_x(page, ctx: ScrapeContext):
    profile_handle = ""
    if ctx.search_type == "profile":
        profile_handle = ctx.profile_handle()
        url = f"https://x.com/{profile_handle}"
    else:
        query = ctx.query.to_x_query() or ctx.keyword
        if ctx.start_dt:
            query += f" since:{ctx.start_dt:%Y-%m-%d}"
        if ctx.end_dt:
            query += f" until:{(ctx.end_dt + timedelta(days=1)):%Y-%m-%d}"  # 'until' do X é exclusivo
        url = f"https://x.com/search?q={urllib.parse.quote(query)}&src=typed_query&f=live"

    collector = ResponseCollector(page, GRAPHQL_MARKERS)
    try:
        ctx.log(f"X: acessando {'perfil @' + profile_handle if profile_handle else 'busca ' + repr(ctx.query.to_x_query())}...")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as exc:
            ctx.log(f"X: falha ao abrir a página: {str(exc).splitlines()[0]}", "WARN")
            return ctx.results

        collector.wait(timeout_ms=9000)
        if "/login" in page.url or "/i/flow/" in page.url:
            ctx.login_required = True
            ctx.log("X: a sessão não está logada. Conecte a conta em 'Contas' para buscar no X.", "WARN")
            return ctx.results

        max_scrolls = min((ctx.limit // 5) + 5, 80)
        scrolls = stagnant = 0
        while not ctx.should_stop() and scrolls <= max_scrolls:
            before = len(ctx.results)
            for _, body in collector.drain():
                _process_graphql(ctx, body, profile_handle)
            if collector.total == 0 or stagnant >= 2:
                _process_dom(ctx, page)

            if len(ctx.results) > before:
                stagnant = 0
                ctx.report()
            else:
                stagnant += 1
                if stagnant >= 4:
                    break

            if ctx.should_stop() or not scroll(page, 2800, 700):
                break
            collector.wait(timeout_ms=2500)
            scrolls += 1
    finally:
        collector.detach()
    return ctx.results
