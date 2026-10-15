"""
Facebook: extração atômica do DOM (um único page.evaluate por rodada) com heurísticas de métricas.
A busca de posts exige sessão logada; sem ela o Facebook redireciona para o login.
"""
import re
import urllib.parse

from scrapers.common import ScrapeContext, scroll
from utils import parse_numeric_metric

DOM_JS = """() => {
    const out = [];
    const selector = 'a[href*="/posts/"], a[href*="/permalink.php"], a[href*="story_fbid"], a[href*="/videos/"], a[href*="/reel/"], a[href*="/photo"], a[href*="/watch/?v="]';
    for (const art of document.querySelectorAll('div[role="feed"] > div, div[role="article"]')) {
        const a = art.querySelector(selector);
        if (!a) continue;
        const authorEl = art.querySelector('h2 a, h3 a, h4 a, strong a, a[role="link"] strong');
        const texts = [];
        for (const t of art.querySelectorAll('div[dir="auto"], span[dir="auto"]')) {
            const s = (t.innerText || '').trim();
            if (s.length > 10 && !texts.some(x => x.includes(s))) texts.push(s);
        }
        const arias = Array.from(art.querySelectorAll('[aria-label]'))
            .map(e => e.getAttribute('aria-label') || '').filter(x => /\\d/.test(x)).slice(0, 40);
        out.push({
            href: a.href || '',
            author: authorEl ? (authorEl.innerText || '').trim() : '',
            text: texts.join(' '),
            raw: (art.innerText || '').slice(0, 5000),
            arias: arias
        });
    }
    return out;
}"""

NUM = r"([\d\.,]+(?:\s*(?:mil|mi|k|m))?)"


def _canonical_link(href: str) -> str:
    parsed = urllib.parse.urlparse(href)
    if "permalink.php" in parsed.path or "story.php" in parsed.path or parsed.path.startswith("/watch"):
        keep = {k: v for k, v in urllib.parse.parse_qs(parsed.query).items() if k in ("story_fbid", "id", "v")}
        return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(keep, doseq=True), fragment=""))
    return urllib.parse.urlunparse(parsed._replace(query="", fragment=""))


def _find_metric(patterns, *sources) -> int:
    for src in sources:
        for pattern in patterns:
            m = re.search(pattern, src or "", re.IGNORECASE)
            if m:
                return parse_numeric_metric(m.group(1))
    return 0


def scrape_facebook(page, ctx: ScrapeContext):
    if ctx.search_type == "profile":
        sub_queries = [ctx.profile_handle()]
    else:
        sub_queries = [ctx.render_variant(v, quote_phrases=True) for v in ctx.search_variants()]

    target_per_term = max((ctx.limit // len(sub_queries)) + 2, 8)
    for term in sub_queries:
        if ctx.should_stop():
            break
        if ctx.search_type == "profile":
            url = f"https://www.facebook.com/{urllib.parse.quote(term)}"
        else:
            url = f"https://www.facebook.com/search/posts/?q={urllib.parse.quote(term)}"
        ctx.log(f"Facebook: pesquisando '{term}' ({len(ctx.results)}/{ctx.limit} posts já coletados)...")
        start_count = len(ctx.results)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)
        except Exception as exc:
            ctx.log(f"Facebook: falha ao abrir {url}: {str(exc).splitlines()[0]}", "WARN")
            continue

        login_wall = "login" in page.url.lower() or "/recover/" in page.url.lower() or "checkpoint" in page.url.lower()
        if not login_wall:
            try:
                login_wall = page.evaluate(
                    "() => !!document.querySelector('input[name=\"email\"], input[name=\"pass\"]') && !document.querySelector('div[role=\"feed\"]')"
                )
            except Exception:
                login_wall = False
        if login_wall:
            ctx.login_required = True
            ctx.log("Facebook: é necessário conectar a conta em 'Contas' para buscar publicações.", "WARN")
            break

        max_scrolls = min((target_per_term // 3) + 4, 25)
        scrolls = stagnant = 0
        while not ctx.should_stop() and (len(ctx.results) - start_count) < target_per_term and scrolls <= max_scrolls:
            before = len(ctx.results)
            try:
                items = page.evaluate(DOM_JS)
            except Exception:
                items = []
            for it in items:
                href = it.get("href", "")
                if not href:
                    continue
                link = _canonical_link(href)
                raw, arias = it.get("raw", ""), " | ".join(it.get("arias") or [])
                author_name = it.get("author", "").strip().lstrip("@")
                author = f"@{author_name}" if author_name else "@facebook_user"
                clean_text = it.get("text") or "[Publicação no Facebook sem texto]"
                ctx.add_post(
                    key=link,
                    author=author,
                    text=clean_text,
                    link=link,
                    date=None,
                    likes=_find_metric([NUM + r"\s*(?:curtidas?|reações|likes?)", r"(?:e outras?)\s*" + NUM + r"\s*pessoas?",
                                        r"(?:reaç\w*|curtid\w*|like\w*)[^\d]{0,20}" + NUM], raw, arias),
                    comments=_find_metric([NUM + r"\s*coment[áa]rios?", r"coment\w*[^\d]{0,20}" + NUM], raw, arias),
                    views=_find_metric([NUM + r"\s*(?:visualizaç(?:ão|ões)|views?|reproduç(?:ão|ões))"], raw, arias),
                    shares=_find_metric([NUM + r"\s*compartilhamentos?", NUM + r"\s*shares?"], raw, arias),
                    term_fallback=term,
                    match_text=f"{it.get('text', '')} {raw} {author}",
                    require_match=True,
                )
            if len(ctx.results) > before:
                stagnant = 0
                ctx.report()
            else:
                stagnant += 1
                if stagnant >= 3:
                    break
            if ctx.should_stop() or not scroll(page, 2500, 1100):
                break
            scrolls += 1

        if not ctx.authenticated and len(ctx.results) == start_count:
            ctx.login_required = True
            ctx.log("Facebook: nenhum post visível sem login. Conecte a conta em 'Contas' para buscar no Facebook.", "WARN")
            break
    return ctx.results
