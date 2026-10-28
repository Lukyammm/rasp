"""
Instagram: interceptação do GraphQL (xdt_fbsearch__top_serp_graphql na busca e timeline no perfil).
Cada mídia já traz @autor, legenda, curtidas, comentários, visualizações e data — sem abrir modais.
Fallback: links do DOM via page.evaluate + enriquecimento em lote pela API /media/{id}/info/.
"""
import re
import urllib.parse

from scrapers.common import ResponseCollector, ScrapeContext, iter_dicts, loads_lenient, scroll
from utils import decode_instagram_shortcode, epoch_to_local, parse_numeric_metric

API_MARKERS = ["/api/graphql", "/graphql/query", "/api/v1/fbsearch", "/api/v1/feed/user", "/api/v1/clips"]

DOM_JS = """() => Array.from(document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]')).map(a => {
    const img = a.querySelector('img');
    return { href: a.getAttribute('href') || '', alt: img ? (img.getAttribute('alt') || '') : '' };
})"""

ENRICH_JS = """async (ids) => {
    const out = {};
    const headers = { 'X-IG-App-ID': '936619743392459', 'X-Requested-With': 'XMLHttpRequest' };
    const csrf = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1];
    if (csrf) headers['X-CSRFToken'] = csrf;
    let i = 0;
    const worker = async () => {
        while (i < ids.length) {
            const id = ids[i++];
            try {
                const r = await fetch('/api/v1/media/' + id + '/info/', { headers, credentials: 'include' });
                if (r.ok) out[id] = await r.text();
            } catch (e) {}
        }
    };
    await Promise.all([worker(), worker(), worker()]);
    return out;
}"""

EMBEDDED_JSON_JS = """() => Array.from(document.querySelectorAll('script[type="application/json"]'))
    .map(s => s.textContent || '').filter(t => t.includes('play_count'))"""

PROFILE_STATS_JS = """(handle) => {
    const h = handle.toLowerCase();
    const link = (suffix) => Array.from(document.querySelectorAll('a[href]')).find(a =>
        (a.getAttribute('href') || '').toLowerCase().replace(/\\/+$/, '').endsWith('/' + h + '/' + suffix));
    const read = (el) => {
        if (!el) return null;
        const t = el.querySelector('[title]');
        return { title: t ? t.getAttribute('title') : null, text: el.innerText || '' };
    };
    return { followers: read(link('followers')), following: read(link('following')) };
}"""

SEARCH_KEYS = ("xdt_fbsearch", "fbsearch", "top_serp", "keyword_search")
PROFILE_KEYS = ("user_timeline", "feed__user", "clips__user", "profile")


def _relevant_roots(doc, search_type: str):
    """Somente blocos da busca (ou do perfil) — ignora feed da home e sugestões carregadas em paralelo."""
    data = doc.get("data") if isinstance(doc, dict) else None
    keys = SEARCH_KEYS if search_type != "profile" else PROFILE_KEYS
    if isinstance(data, dict):
        return [v for k, v in data.items() if any(s in k for s in keys)]
    if isinstance(doc, dict) and ("media_grid" in doc or "sections" in doc or "items" in doc):
        return [doc]
    return []


def _post_format(media: dict) -> str:
    """Formato que o próprio Instagram informa: imagem | carrossel | reel | video ("" se não veio)."""
    if media.get("product_type") == "clips":
        return "reel"
    kind = media.get("media_type")
    typename = str(media.get("__typename") or "")
    if kind == 8 or media.get("product_type") == "carousel_container" or "Sidecar" in typename:
        return "carrossel"
    if kind == 2 or "Video" in typename:
        return "video"
    if kind == 1 or "Image" in typename:
        return "imagem"
    return ""


def _coauthors(media: dict) -> set:
    """Contas convidadas como coautoras (post em parceria): o post aparece na grade de todas elas."""
    return {str(u.get("username") or "").lower() for key in ("coauthor_producers", "invited_coauthor_producers")
            for u in (media.get(key) or []) if isinstance(u, dict)}


def _media_to_post(ctx: ScrapeContext, media: dict, term: str, profile_handle: str = "", reels: dict = None) -> bool:
    code = media.get("code")
    user = media.get("user") or media.get("owner") or {}
    username = user.get("username") or ""
    # No perfil entram os posts dele e as parcerias em que ele é coautor (o Autor continua sendo o dono)
    if profile_handle and username and username.lower() != profile_handle.lower() \
            and profile_handle.lower() not in _coauthors(media):
        return False
    caption = media.get("caption")
    text = caption.get("text", "") if isinstance(caption, dict) else ""
    if not text:
        edges = ((media.get("edge_media_to_caption") or {}).get("edges") or [])
        text = edges[0].get("node", {}).get("text", "") if edges else ""
    is_reel = media.get("product_type") == "clips" or media.get("media_type") == 2
    views = media.get("view_count") or media.get("play_count") or media.get("ig_play_count") or media.get("video_view_count") or 0
    likes = media.get("like_count")
    if likes is None:
        likes = ((media.get("edge_liked_by") or media.get("edge_media_preview_like") or {}).get("count", 0))
    hidden = bool(media.get("like_and_view_counts_disabled"))
    if hidden:
        likes = 0  # autor ocultou as curtidas: a API devolve um valor fictício (ex.: 3)
    comments = media.get("comment_count")
    if comments is None:
        comments = (media.get("edge_media_to_comment") or {}).get("count", 0)
    author = f"@{username}" if username else "@perfil_instagram"
    clean_text = text or "[Publicação no Instagram sem legenda]"
    added = ctx.add_post(
        key=code,
        author=author,
        text=clean_text,
        link=f"https://www.instagram.com/{'reel' if is_reel else 'p'}/{code}/",
        date=epoch_to_local(media.get("taken_at") or media.get("taken_at_timestamp")),
        likes=likes or 0,
        comments=comments or 0,
        views=views,
        shares=media.get("reshare_count") or media.get("media_repost_count") or 0,
        term_fallback=term,
        match_text=f"{text or ''} {username or ''} {author}",
        require_match=True,
        post_format=_post_format(media),
        metrics_status="oculto" if hidden else "",
    )
    # A busca do Instagram não informa visualizações; os reels são enriquecidos depois via /media/{id}/info/
    if added and reels is not None and is_reel and not views:
        media_id = str(media.get("pk") or "").split("_")[0] or str(decode_instagram_shortcode(code[:11]) or "")
        if media_id:
            reels[code] = media_id
    return added


def _enrich_reel_views(ctx: ScrapeContext, page, reels: dict) -> None:
    """Busca visualizações (e métricas atualizadas) dos reels coletados, em lotes com concorrência baixa."""
    pending = {code: mid for code, mid in reels.items()}
    if not pending or ctx.cancelled():
        return
    ctx.log(f"Instagram: buscando visualizações de {len(pending)} reels...")
    posts_by_code = {}
    for post in ctx.results:
        m = re.search(r"/(?:p|reel)/([\w-]+)", post.get("Link", ""))
        if m:
            posts_by_code[m.group(1)] = post
    codes = list(pending)
    updated = empty = 0
    for start in range(0, len(codes), 30):
        if ctx.cancelled():
            break
        batch = codes[start:start + 30]
        try:
            responses = page.evaluate(ENRICH_JS, [pending[c] for c in batch]) or {}
        except Exception:
            break
        # Lote inteiro sem resposta é o Instagram limitando a consulta: parar e avisar, sem insistir
        empty = 0 if responses else empty + 1
        if empty >= 2:
            ctx.log(f"Instagram: o Instagram parou de responder à consulta de visualizações (limite de uso); "
                    f"{len(codes) - start - len(batch)} reels não foram consultados.", "WARN")
            break
        for code in batch:
            body, post = responses.get(pending[code]), posts_by_code.get(code)
            if not body or not post:
                continue
            for doc in loads_lenient(body):
                items = doc.get("items") if isinstance(doc, dict) else None
                item = items[0] if items else {}
                plays = item.get("play_count") or item.get("ig_play_count") or item.get("view_count")
                if plays:
                    post["Views"] = str(plays)
                    updated += 1
                if item.get("like_count") is not None and not item.get("like_and_view_counts_disabled"):
                    post["Curtidas"] = str(item["like_count"])
                if item.get("comment_count") is not None:
                    post["Comentarios"] = str(item["comment_count"])
        page.wait_for_timeout(400)
    ctx.log(f"Instagram: visualizações obtidas para {updated} de {len(pending)} reels.")


def _reels_tab(ctx: ScrapeContext, page, collector, handle: str, reels: dict, period_profile: bool) -> None:
    """Aba Reels do perfil: cada reel já vem com as reproduções, então as visualizações saem daqui sem consultar
    reel por reel. No perfil com período também entram os reels que não foram para a grade."""
    if ctx.cancelled():
        return
    posts_by_code = {}
    for post in ctx.results:
        m = re.search(r"/(?:p|reel)/([\w-]+)", post.get("Link", ""))
        if m:
            posts_by_code[m.group(1)] = post
    before_total = len(ctx.results)
    try:
        page.goto(f"https://www.instagram.com/{urllib.parse.quote(handle)}/reels/", wait_until="domcontentloaded",
                  timeout=30000)
    except Exception as exc:
        ctx.log(f"Instagram: falha ao abrir a aba Reels de @{handle}: {str(exc).splitlines()[0]}", "WARN")
        return
    collector.wait(timeout_ms=7000)
    seen, only_tab = set(), []
    filled = older = stagnant = scrolls = 0
    # Os primeiros reels vêm escritos na própria página (sem XHR); os seguintes chegam ao rolar
    try:
        bodies = [("pagina", b) for b in (page.evaluate(EMBEDDED_JSON_JS) or [])]
    except Exception:
        bodies = []
    while not ctx.cancelled() and (period_profile or scrolls <= 25):
        new_codes = 0
        for _, body in bodies + list(collector.drain()):
            for doc in loads_lenient(body):
                for d in _reels_tab_items(doc, handle):
                    code = d["code"]
                    if code in seen:
                        continue
                    seen.add(code)
                    new_codes += 1
                    plays = d.get("play_count") or d.get("ig_play_count") or d.get("view_count")
                    when = _media_when(d)
                    post = posts_by_code.get(code)
                    if post is not None:
                        if plays and not parse_numeric_metric(post.get("Views")):
                            post["Views"] = str(plays)
                            filled += 1
                        if plays:
                            reels.pop(code, None)
                    elif period_profile and when is not None:
                        # A aba Reels não traz taken_at: a data sai do id do post (momento em que foi criado)
                        if _media_to_post(ctx, {**d, "taken_at": d.get("taken_at") or when.timestamp()},
                                          handle, handle, reels):
                            only_tab.append(code)
                    if period_profile and when is not None and when < ctx.start_dt \
                            and not (d.get("clips_tab_pinned_user_ids") or d.get("timeline_pinned_user_ids")):
                        older += 1
        bodies = []
        if period_profile and older >= 4:
            break
        if not period_profile and not reels:
            break  # todos os reels coletados já têm visualização
        stagnant = 0 if new_codes else stagnant + 1
        if stagnant >= 3 or not scroll(page, 3000, 900):
            break
        collector.wait(timeout_ms=3000)
        scrolls += 1
    ctx.log(f"Instagram: aba Reels de @{handle}: {len(seen)} reels lidos, visualizações preenchidas em {filled}"
            + (f"; {len(ctx.results) - before_total} reels do período só na aba Reels: {', '.join(only_tab)}"
               if only_tab else "") + ".")


def _media_when(media: dict):
    """Data do post: taken_at quando vem; senão, o momento gravado no próprio id do post."""
    if media.get("taken_at") or media.get("taken_at_timestamp"):
        return epoch_to_local(media.get("taken_at") or media.get("taken_at_timestamp"))
    media_id = str(media.get("pk") or media.get("id") or "").split("_")[0]
    if not media_id.isdigit():
        media_id = str(decode_instagram_shortcode(str(media.get("code") or "")[:11]) or "")
    return epoch_to_local(((int(media_id) >> 23) + 1314220800000) / 1000.0) if media_id.isdigit() else None


def _reels_tab_items(doc, handle: str):
    """Reels do perfil numa resposta da aba Reels (o nome do bloco muda; vale o dono ou a coautoria)."""
    h = handle.lower()
    for d in iter_dicts(doc):
        if not isinstance(d.get("code"), str) or d.get("product_type") != "clips":
            continue
        user = d.get("user") or d.get("owner") or {}
        if str(user.get("username") or "").lower() == h or h in _coauthors(d):
            yield d


def _iter_medias(body: str, search_type: str):
    for doc in loads_lenient(body):
        for root in _relevant_roots(doc, search_type):
            for d in iter_dicts(root):
                if isinstance(d.get("code"), str) and ("taken_at" in d or "taken_at_timestamp" in d) \
                        and isinstance(d.get("user") or d.get("owner"), dict):
                    yield d


def _stats_from_body(body: str, handle: str):
    """Seguidores, seguindo e posts do perfil nas respostas que a própria página carrega (número exato)."""
    for doc in loads_lenient(body):
        for d in iter_dicts(doc):
            if str(d.get("username") or "").lower() != handle.lower():
                continue
            followers = d.get("follower_count")
            if followers is None:
                followers = (d.get("edge_followed_by") or {}).get("count")
            if isinstance(followers, int):
                following = d.get("following_count")
                if following is None:
                    following = (d.get("edge_follow") or {}).get("count")
                posts = d.get("media_count")
                if posts is None:
                    posts = (d.get("edge_owner_to_timeline_media") or {}).get("count")
                # identidade do perfil: nome, selo e links da bio (servem para conferir se o @ é o oficial)
                links = [str(b.get("url") or "") for b in (d.get("bio_links") or []) if isinstance(b, dict)]
                if d.get("external_url") and d["external_url"] not in links:
                    links.insert(0, str(d["external_url"]))
                return {"followers": followers, "following": following, "posts": posts, "source": "resposta da página",
                        "full_name": d.get("full_name") or "", "verified": d.get("is_verified"),
                        "links": [l for l in links if l]}
    return None


def _stats_from_header(page, handle: str):
    """Seguidores pelo cabeçalho do perfil: o title do número é exato; o texto pode vir arredondado ("12,3 mil")."""
    try:
        found = page.evaluate(PROFILE_STATS_JS, handle) or {}
    except Exception:
        return None
    fol = found.get("followers") or {}
    if fol.get("title"):
        return {"followers": parse_numeric_metric(fol["title"]), "source": "cabeçalho do perfil, exato"}
    if fol.get("text"):
        return {"followers": parse_numeric_metric(fol["text"]), "source": "cabeçalho do perfil, arredondado"}
    return None


def _dom_fallback(ctx: ScrapeContext, page, term: str) -> None:
    try:
        links = page.evaluate(DOM_JS)
    except Exception:
        return
    pending = {}
    for it in links:
        m = re.search(r"/(p|reel)/([\w-]+)", it.get("href", ""))
        if not m:
            continue
        code = m.group(2)
        media_id = decode_instagram_shortcode(code[:11])
        if media_id and code not in pending and not ctx.has_seen(code):
            pending[code] = (media_id, it.get("alt", ""), m.group(1))
    if not pending:
        return

    enriched = {}
    try:
        ids = [str(v[0]) for v in list(pending.values())[:40]]
        enriched = page.evaluate(ENRICH_JS, ids) or {}
    except Exception:
        enriched = {}

    for code, (media_id, alt, kind) in pending.items():
        if ctx.full:
            break
        body = enriched.get(str(media_id))
        if body:
            used = False
            for doc in loads_lenient(body):
                for media in (doc.get("items") or []) if isinstance(doc, dict) else []:
                    used = _media_to_post(ctx, media, term) or used  # /info/ já traz play_count
            if used or ctx.has_seen(code):
                continue
        likes = re.search(r"([\d\.,]+(?:\s*(?:mil|k|m))?)\s*(?:curtidas?|likes?)", alt, re.IGNORECASE)
        mention = re.search(r"@[\w\.]+", alt)
        raw_alt = " ".join(alt.split())
        author = mention.group(0) if mention else "@perfil_instagram"
        ctx.add_post(
            key=code,
            author=author,
            text=raw_alt or "[Publicação no Instagram sem legenda]",
            link=f"https://www.instagram.com/{kind}/{code}/",
            date=epoch_to_local(((media_id >> 23) + 1314220800000) / 1000.0),
            likes=parse_numeric_metric(likes.group(1)) if likes else 0,
            term_fallback=term,
            match_text=f"{raw_alt} {author}",
            require_match=True,
        )


def scrape_instagram(page, ctx: ScrapeContext):
    profile_handle = ""
    if ctx.search_type == "profile":
        profile_handle = ctx.profile_handle()
        sub_queries = [profile_handle]
    else:
        # No Instagram, o endpoint /explore/search/keyword/ NÃO aceita aspas literais:
        # qualquer aspa (mesmo em frases compostas) zera a busca e retorna 0 resultados.
        # Por isso, passamos quote_phrases=False. A validação de frase exata é garantida
        # no pós-processamento pelo BooleanQuery em ctx.add_post.
        sub_queries = [ctx.render_variant(v, quote_phrases=False) for v in ctx.search_variants()]

    target_per_term = max((ctx.limit // len(sub_queries)) + 2, 8)
    # Perfil com data de início: rola até passar do início do período, sem teto de rolagens nem de tempo.
    # Posts mais novos que o fim do período não contam como rolagem parada.
    period_profile = bool(profile_handle and ctx.start_dt)
    if period_profile:
        ctx.time_budget = float("inf")
    collector = ResponseCollector(page, API_MARKERS)
    reels = {}
    try:
        for raw_term in sub_queries:
            if ctx.should_stop():
                break
            # Remove qualquer tipo de aspas para blindar o Explore do Instagram
            term = re.sub(r'["“”\'`]', '', raw_term).strip()
            if not term:
                continue
            if profile_handle:
                url = f"https://www.instagram.com/{urllib.parse.quote(term)}/"
            else:
                # Se for busca por palavra-chave no Explore e o termo começar com '@', busca o identificador limpo
                # (ex.: '@evandroleitao' -> 'evandroleitao'), pois o endpoint com '%40' não indexa posts
                search_q = term.lstrip("@") if term.startswith("@") and len(term) > 1 else term
                url = f"https://www.instagram.com/explore/search/keyword/?q={urllib.parse.quote(search_q)}"
            ctx.log(f"Instagram: pesquisando '{term}' ({len(ctx.results)}/{ctx.limit} posts já coletados)...")
            start_count = len(ctx.results)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as exc:
                ctx.log(f"Instagram: falha ao abrir {url}: {str(exc).splitlines()[0]}", "WARN")
                continue
            collector.wait(timeout_ms=7000)
            if "/accounts/login" in page.url or "/challenge" in page.url:
                ctx.login_required = True
                ctx.log("Instagram: sessão expirada ou verificação de segurança. Reconecte a conta em 'Contas'.", "WARN")
                break
            stats = None
            if profile_handle:
                # Seguidores do perfil: primeiro nas respostas já recebidas (sem tirá-las da fila), depois no cabeçalho
                for _, body in list(collector.queue):
                    stats = stats or _stats_from_body(body, term)
                stats = stats or _stats_from_header(page, term)

            max_scrolls = float("inf") if period_profile else min((target_per_term // 12) + 4, 25)
            scrolls = stagnant = 0
            api_hits = 0
            older = 0  # posts anteriores ao início; até 3 podem ser fixados no topo
            while not ctx.should_stop() and (len(ctx.results) - start_count) < target_per_term and scrolls <= max_scrolls:
                before = len(ctx.results)
                newer = False
                for _, body in collector.drain():
                    if profile_handle and (stats is None or stats["source"] != "resposta da página"):
                        stats = _stats_from_body(body, term) or stats
                    for media in _iter_medias(body, ctx.search_type):
                        api_hits += 1
                        _media_to_post(ctx, media, term, profile_handle, reels)
                        if period_profile:
                            when = epoch_to_local(media.get("taken_at") or media.get("taken_at_timestamp"))
                            if when is None or media.get("timeline_pinned_user_ids"):
                                continue
                            if ctx.end_dt and when > ctx.end_dt:
                                newer = True
                            elif when < ctx.start_dt:
                                older += 1
                if period_profile and older >= 4:
                    ctx.log(f"Instagram: período coberto em '{term}' (chegou a posts anteriores ao início).")
                    break
                # Perfis podem vir renderizados no HTML (sem XHR): lê o DOM na 1ª rodada; na busca, só se a API falhar
                if (profile_handle and scrolls == 0) or (api_hits == 0 and scrolls >= 1) or stagnant >= 2:
                    _dom_fallback(ctx, page, term)

                if len(ctx.results) > before or newer:
                    stagnant = 0
                    ctx.report()
                else:
                    stagnant += 1
                    if stagnant >= 3:
                        break
                if ctx.should_stop() or not scroll(page, 3000, 900):
                    break
                collector.wait(timeout_ms=3000)
                scrolls += 1
            if profile_handle:
                # Vai no log do job: a API não muda e quem precisa lê a linha "seguidores de @..."
                ctx.profile_stats = stats
                if stats:
                    ctx.log(f"Instagram: seguidores de @{term}: {stats['followers']} (fonte: {stats['source']}).")
                    if stats.get("full_name") or stats.get("links") or stats.get("verified") is not None:
                        ctx.log(f"Instagram: perfil @{term}: nome '{stats.get('full_name', '')}', "
                                f"verificado {'sim' if stats.get('verified') else 'não'}, "
                                f"posts {stats.get('posts')}, links da bio: {' | '.join(stats.get('links') or []) or '-'}.")
                else:
                    ctx.log(f"Instagram: seguidores de @{term} não encontrados na página.", "WARN")
                # Respostas da grade que chegaram depois da última rodada, antes de trocar de aba
                for _, body in collector.drain():
                    for media in _iter_medias(body, ctx.search_type):
                        _media_to_post(ctx, media, term, profile_handle, reels)
                if reels or period_profile:
                    _reels_tab(ctx, page, collector, term, reels, period_profile)
    finally:
        collector.detach()
    try:
        _enrich_reel_views(ctx, page, reels)
    except Exception as exc:
        ctx.log(f"Instagram: não foi possível obter as visualizações dos reels ({str(exc).splitlines()[0]}).", "WARN")
    return ctx.results
