"""
Coleta de comentários dos posts já extraídos (acionada pelo dashboard).

Estratégia por rede (APIs internas validadas em 2026-09):
- YouTube: token da seção de comentários (ytInitialData) + POST youtubei/v1/next paginado.
- Instagram: GET /api/v1/media/{id}/comments/ paginado por next_min_id (exige sessão logada).
- TikTok: GET /api/comment/list/ paginado por cursor; fallback: abre o painel de comentários e intercepta a API.
- X: interceptação do GraphQL TweetDetail na página do post (respostas do mesmo conversation_id) com rolagem.
- Facebook: melhor esforço pelo DOM (um page.evaluate por rodada, expandindo "Ver mais comentários").

Tolerância a falhas:
- cada post é isolado (a falha de um não afeta os outros) e gravado assim que termina;
- falhas transitórias (rede, HTTP 429/5xx, resposta inválida) ganham novas tentativas com espera crescente;
- navegador travado/fechado é reaberto automaticamente; falhas seguidas abrem o "disjuntor" da rede;
- sessão expirada encerra a rede e marca os posts restantes como "conectar conta" (sem gastar tempo à toa);
- tempo máximo por post e cancelamento cooperativo; comentários já coletados nunca são descartados.
"""
import hashlib
import html
import json
import logging
import random
import re
import threading
import time
import urllib.parse
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

try:
    from patchright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    from playwright.sync_api import sync_playwright

from scrapers.browser import network_lock, open_page
from scrapers.common import DISPLAY_NAMES, ResponseCollector, iter_dicts, loads_lenient, scroll, text_runs
from scrapers.x_scraper import _parse_created_at, _tweet_from_result
from scrapers.youtube_scraper import INITIAL_DATA_JS, _initial_data
from utils import decode_instagram_shortcode, epoch_to_local, format_date, parse_numeric_metric

logger = logging.getLogger("rasp.comments")

MAX_ATTEMPTS = 3
RETRY_WAIT = (0, 4, 10)
MAX_CONSECUTIVE_FAILURES = 4
MAX_BROWSER_RESTARTS = 2
MAX_CRASHES_PER_POST = 2

LOGIN_MESSAGES = {
    "x": "Sessão do X desconectada. Conecte a conta em 'Contas' e tente novamente.",
    "instagram": "Sessão do Instagram expirada ou em verificação. Reconecte a conta em 'Contas'.",
    "facebook": "É preciso conectar a conta do Facebook em 'Contas' para ler comentários.",
    "tiktok": "O TikTok pediu login/verificação. Reconecte a conta em 'Contas'.",
    "youtube": "O YouTube pediu login. Reconecte a conta em 'Contas'.",
}


class LoginRequired(Exception):
    """Sessão ausente/expirada: não adianta insistir nesta rede."""


class PostUnavailable(Exception):
    """Post removido, privado ou link inválido: não adianta repetir."""


class TransientError(Exception):
    """Falha temporária: vale uma nova tentativa."""


class BrowserDead(Exception):
    """O navegador/aba fechou ou travou: é preciso reabrir."""


# --------------------------------------------------------------------------- balde de comentários
@dataclass
class CommentBucket:
    limit: int
    deadline: float
    cancel_event: Optional[threading.Event] = None
    items: List[dict] = field(default_factory=list)
    exhausted: bool = False  # a rede confirmou que não há mais comentários
    disabled: bool = False  # comentários desativados pelo autor
    timed_out: bool = False

    def __post_init__(self):
        self._ids = set()

    @property
    def full(self) -> bool:
        return len(self.items) >= self.limit

    def cancelled(self) -> bool:
        return bool(self.cancel_event and self.cancel_event.is_set())

    def should_stop(self) -> bool:
        if self.full or self.cancelled():
            return True
        if time.monotonic() > self.deadline:
            self.timed_out = True
            return True
        return False

    def add(self, comment_id, author="", text="", likes=0, replies=0, date="", parent_id="") -> bool:
        text = " ".join(str(text or "").split())
        author = str(author or "").strip()
        if self.full or not (text or author):
            return False
        cid = str(comment_id or "").strip()
        if not cid:  # sem id na origem (DOM): identificador estável pelo conteúdo
            cid = "h" + hashlib.sha1(f"{author}|{text}".encode("utf-8")).hexdigest()[:24]
        if cid in self._ids:
            return False
        self._ids.add(cid)
        self.items.append({
            "id": cid, "parent_id": str(parent_id or ""), "author": author, "text": text,
            "likes": parse_numeric_metric(likes), "replies": parse_numeric_metric(replies), "date": str(date or ""),
        })
        return True


def post_time_budget(limit: int) -> float:
    return min(240.0, 45.0 + limit * 0.6)


# --------------------------------------------------------------------------- utilitários
FETCH_JS = """async ([url, opts]) => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), opts.timeout || 20000);
    try {
        const init = { credentials: 'include', headers: Object.assign({}, opts.headers || {}), signal: ctrl.signal };
        if (opts.csrf) {
            const m = document.cookie.match(/csrftoken=([^;]+)/);
            if (m) init.headers['X-CSRFToken'] = m[1];
        }
        if (opts.body !== undefined && opts.body !== null) { init.method = 'POST'; init.body = opts.body; }
        const r = await fetch(url, init);
        return { status: r.status, body: await r.text() };
    } catch (e) {
        return { status: 0, body: '', error: String(e) };
    } finally {
        clearTimeout(timer);
    }
}"""


def _fetch(page, url: str, **opts):
    res = page.evaluate(FETCH_JS, [url, opts]) or {}
    status = int(res.get("status") or 0)
    if status == 0:
        raise TransientError(f"sem resposta da rede ({str(res.get('error') or 'timeout')[:80]})")
    return status, res.get("body") or ""


def _json(body: str):
    docs = loads_lenient(body)
    return docs[0] if docs and isinstance(docs[0], dict) else None


def _short(exc: BaseException) -> str:
    text = (str(exc).strip().splitlines() or [exc.__class__.__name__])[0]
    return text[:180] or exc.__class__.__name__


_DEAD_MARKERS = ("has been closed", "target closed", "browser closed", "connection closed", "crash",
                 "browser has disconnected", "context or browser")


def _browser_dead(page, exc: BaseException) -> bool:
    try:
        if page.is_closed():
            return True
    except Exception:
        return True
    return any(m in str(exc).lower() for m in _DEAD_MARKERS)


def _pause(seconds: float, cancel_event: Optional[threading.Event]) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if cancel_event is not None and cancel_event.is_set():
            return
        time.sleep(min(0.25, max(0.0, end - time.monotonic())))


def short_link(link: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", str(link or ""))[:70]


# --------------------------------------------------------------------------- YouTube
YT_CONFIG_JS = """() => Array.from(document.querySelectorAll('script'))
    .map(s => s.textContent || '').filter(t => t.includes('INNERTUBE_CONTEXT')).join('\\n')"""


def _yt_video_id(link: str) -> str:
    m = re.search(r"(?:[?&]v=|/shorts/|youtu\.be/|/live/|/embed/)([\w-]{11})", link or "")
    return m.group(1) if m else ""


def _yt_config(page) -> dict:
    text = page.evaluate(YT_CONFIG_JS) or ""
    cfg, decoder = {}, json.JSONDecoder()
    for m in re.finditer(r"ytcfg\.set\(\s*", text):
        try:
            obj, _ = decoder.raw_decode(text, m.end())
            if isinstance(obj, dict):
                cfg.update(obj)
        except ValueError:
            continue
    return cfg


def _yt_first_token(obj) -> str:
    for d in iter_dicts(obj):
        cmd = d.get("continuationCommand")
        if isinstance(cmd, dict) and cmd.get("token"):
            return str(cmd["token"])
    return ""


def _yt_next_token(doc: dict) -> str:
    """Token da próxima página de comentários (ignora os tokens de respostas, que ficam dentro de cada thread)."""
    for ep in doc.get("onResponseReceivedEndpoints") or []:
        for key in ("reloadContinuationItemsCommand", "appendContinuationItemsAction"):
            items = (ep.get(key) or {}).get("continuationItems") or []
            for item in reversed(items):
                if isinstance(item, dict) and "continuationItemRenderer" in item:
                    token = _yt_first_token(item["continuationItemRenderer"])
                    if token:
                        return token
    return ""


def _yt_collect(doc: dict, bucket: CommentBucket) -> int:
    added = 0
    for m in ((doc.get("frameworkUpdates") or {}).get("entityBatchUpdate") or {}).get("mutations") or []:
        c = (m.get("payload") or {}).get("commentEntityPayload") if isinstance(m, dict) else None
        if not isinstance(c, dict):
            continue
        props, toolbar = c.get("properties") or {}, c.get("toolbar") or {}
        if int(props.get("replyLevel") or 0) > 0:
            continue
        added += bucket.add(props.get("commentId"), author=(c.get("author") or {}).get("displayName"),
                            text=(props.get("content") or {}).get("content"), likes=toolbar.get("likeCountNotliked"),
                            replies=toolbar.get("replyCount"), date=props.get("publishedTime"))
    for d in iter_dicts(doc):  # formato antigo (commentRenderer)
        r = d.get("commentRenderer")
        if isinstance(r, dict) and r.get("commentId"):
            added += bucket.add(r["commentId"], author=text_runs(r.get("authorText")), text=text_runs(r.get("contentText")),
                                likes=text_runs(r.get("voteCount")), replies=r.get("replyCount"),
                                date=text_runs(r.get("publishedTimeText")))
    return added


def fetch_youtube(page, post: dict, bucket: CommentBucket, state: dict) -> None:
    video_id = _yt_video_id(post.get("link", ""))
    if not video_id:
        raise PostUnavailable("Link do YouTube inválido.")
    page.goto(f"https://www.youtube.com/watch?v={video_id}", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1200)
    data = _initial_data(page.evaluate(INITIAL_DATA_JS))
    if not isinstance(data, dict):
        raise TransientError("a página do vídeo não carregou")
    section = next((d["itemSectionRenderer"] for d in iter_dicts(data) if isinstance(d.get("itemSectionRenderer"), dict)
                    and d["itemSectionRenderer"].get("sectionIdentifier") == "comment-item-section"), None)
    if section is None:
        if not any("videoPrimaryInfoRenderer" in d for d in iter_dicts(data.get("contents") or {})):
            raise PostUnavailable("Vídeo indisponível, privado ou removido.")
        raise TransientError("a seção de comentários não carregou")
    token = _yt_first_token(section)
    if not token:
        if any("messageRenderer" in d for d in iter_dicts(section)):
            bucket.disabled = True
            return
        raise TransientError("token de comentários não encontrado")

    cfg = _yt_config(page)
    context = cfg.get("INNERTUBE_CONTEXT")
    if not isinstance(context, dict):
        raise TransientError("configuração do YouTube não encontrada")
    url = "/youtubei/v1/next?prettyPrint=false"
    if cfg.get("INNERTUBE_API_KEY"):
        url += "&key=" + urllib.parse.quote(str(cfg["INNERTUBE_API_KEY"]))

    used = set()
    while token and token not in used and not bucket.should_stop():
        used.add(token)
        status, body = _fetch(page, url, body=json.dumps({"context": context, "continuation": token}),
                              headers={"Content-Type": "application/json"})
        if status in (401, 403) and not bucket.items:
            raise LoginRequired(LOGIN_MESSAGES["youtube"])
        if status >= 400:
            raise TransientError(f"YouTube respondeu HTTP {status}")
        doc = _json(body)
        if doc is None:
            raise TransientError("resposta inválida do YouTube")
        _yt_collect(doc, bucket)
        token = _yt_next_token(doc)
        if not token:
            bucket.exhausted = True
        page.wait_for_timeout(random.randint(250, 550))


# --------------------------------------------------------------------------- Instagram
IG_HEADERS = {"X-IG-App-ID": "936619743392459", "X-Requested-With": "XMLHttpRequest"}


def fetch_instagram(page, post: dict, bucket: CommentBucket, state: dict) -> None:
    m = re.search(r"/(?:p|reel|reels|tv)/([\w-]+)", post.get("link", ""))
    media_id = decode_instagram_shortcode(m.group(1)[:11]) if m else None
    if not media_id:
        raise PostUnavailable("Link do Instagram inválido.")
    if not state.get("instagram_ready"):
        page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        if "/accounts/login" in page.url or "/challenge" in page.url:
            raise LoginRequired(LOGIN_MESSAGES["instagram"])
        state["instagram_ready"] = True

    min_id, rate_limited, stale_pages = None, 0, 0
    while not bucket.should_stop():
        url = f"/api/v1/media/{media_id}/comments/?can_support_threading=true&permalink_enabled=false"
        if min_id:
            url += "&min_id=" + urllib.parse.quote(str(min_id))
        status, body = _fetch(page, url, headers=IG_HEADERS, csrf=True)
        doc = _json(body) or {}
        message = str(doc.get("message") or "").lower()
        if status in (401, 403) or doc.get("require_login") or message in ("login_required", "checkpoint_required", "challenge_required"):
            state["instagram_ready"] = False
            raise LoginRequired(LOGIN_MESSAGES["instagram"])
        if status == 429 or "wait a few minutes" in message or "tente novamente" in message:
            if rate_limited >= 2:
                raise TransientError("o Instagram limitou as requisições (aguarde alguns minutos)")
            rate_limited += 1
            _pause(20 * rate_limited, bucket.cancel_event)
            continue
        if status == 404 or "media not found" in message:
            raise PostUnavailable("Publicação removida ou indisponível.")
        if status >= 400 or not doc:
            raise TransientError(f"Instagram respondeu HTTP {status}")
        if doc.get("comments_disabled"):
            bucket.disabled = True
            return
        comments = doc.get("comments") or []
        added = 0
        for c in comments:
            if not isinstance(c, dict):
                continue
            username = (c.get("user") or {}).get("username") or ""
            added += bucket.add(c.get("pk") or c.get("id"), author=f"@{username}" if username else "", text=c.get("text"),
                                likes=c.get("comment_like_count"), replies=c.get("child_comment_count"),
                                date=format_date(epoch_to_local(c.get("created_at"))))
        min_id = doc.get("next_min_id")
        stale_pages = 0 if added else stale_pages + 1
        if not min_id or not comments or stale_pages >= 2:
            bucket.exhausted = True
            return
        page.wait_for_timeout(random.randint(500, 900))


# --------------------------------------------------------------------------- TikTok
TT_OPEN_JS = """() => {
    const icon = document.querySelector('[data-e2e="comment-icon"], [data-e2e="browse-comment"]');
    if (!icon) return false;
    (icon.closest('button') || icon).click();
    return true;
}"""

TT_SCROLL_JS = """() => {
    const first = document.querySelector('[data-e2e="comment-level-1"]');
    let el = first;
    while (el && el !== document.body) {
        const style = getComputedStyle(el);
        if (el.scrollHeight > el.clientHeight + 20 && /(auto|scroll)/.test(style.overflowY)) break;
        el = el.parentElement;
    }
    (el && el !== document.body ? el : document.scrollingElement).scrollTop += 2500;
    return !!first;
}"""

TT_DOM_JS = """() => Array.from(document.querySelectorAll('[data-e2e="comment-level-1"]')).map(el => {
    const box = el.closest('[class*="CommentItem"], [class*="comment-item"]') || el.parentElement;
    const user = box ? box.querySelector('[data-e2e="comment-username-1"]') : null;
    return { text: el.innerText || '', author: user ? (user.innerText || '') : '' };
})"""


def _tt_collect(doc: dict, bucket: CommentBucket) -> int:
    added = 0
    for c in doc.get("comments") or []:
        if not isinstance(c, dict):
            continue
        user = c.get("user") or {}
        handle = user.get("unique_id") or user.get("uniqueId") or user.get("nickname") or ""
        added += bucket.add(c.get("cid"), author=f"@{handle}" if handle else "", text=c.get("text"),
                            likes=c.get("digg_count"), replies=c.get("reply_comment_total"),
                            date=format_date(epoch_to_local(c.get("create_time"))),
                            parent_id="" if str(c.get("reply_id") or "0") == "0" else c.get("reply_id"))
    return added


def _tt_direct(page, video_id: str, bucket: CommentBucket, expected: int) -> bool:
    """API direta. Retorna False quando ela não serve (ex.: exige assinatura) para acionar o fallback."""
    cursor, first = 0, True
    while not bucket.should_stop():
        status, body = _fetch(page, f"/api/comment/list/?aid=1988&aweme_id={video_id}&count=50&cursor={cursor}")
        doc = _json(body)
        if doc is None or status >= 400 or doc.get("status_code") not in (0, None):
            if first:
                return False
            raise TransientError(f"TikTok interrompeu a paginação (HTTP {status})")
        comments = doc.get("comments") or []
        if first and not comments and expected >= 5:
            return False  # a métrica diz que há comentários: resposta vazia é suspeita, tenta pela página
        first = False
        _tt_collect(doc, bucket)
        new_cursor = int(doc.get("cursor") or 0)
        if not doc.get("has_more") or not comments or new_cursor <= cursor:
            bucket.exhausted = True
            return True
        cursor = new_cursor
        page.wait_for_timeout(random.randint(400, 800))
    return True


def _tt_panel(page, post: dict, bucket: CommentBucket) -> None:
    collector = ResponseCollector(page, ["api/comment/list"])
    try:
        page.goto(post["link"], wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        if "login" in page.url.lower():
            raise LoginRequired(LOGIN_MESSAGES["tiktok"])
        if not page.evaluate(TT_OPEN_JS):
            raise TransientError("o painel de comentários do TikTok não abriu")
        collector.wait(timeout_ms=6000)
        responses = stagnant = 0
        for _ in range(40):
            if bucket.should_stop():
                return
            added = 0
            for _, body in collector.drain():
                doc = _json(body)
                if not doc:
                    continue
                responses += 1
                added += _tt_collect(doc, bucket)
                if doc.get("comments") is not None and not doc.get("has_more"):
                    bucket.exhausted = True
            if bucket.exhausted:
                return
            stagnant = 0 if added else stagnant + 1
            if stagnant >= 3:
                break
            page.evaluate(TT_SCROLL_JS)
            collector.wait(timeout_ms=2500)
        if not responses:  # último recurso: texto visível na tela
            for it in page.evaluate(TT_DOM_JS) or []:
                bucket.add("", author=it.get("author"), text=it.get("text"))
        if not bucket.items and not responses:
            raise TransientError("os comentários do TikTok não carregaram")
        bucket.exhausted = True
    finally:
        collector.detach()


def fetch_tiktok(page, post: dict, bucket: CommentBucket, state: dict) -> None:
    m = re.search(r"/(?:video|photo)/(\d+)", post.get("link", ""))
    if not m:
        raise PostUnavailable("Link do TikTok inválido.")
    if not state.get("tiktok_ready"):
        page.goto(post["link"], wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)
        state["tiktok_ready"] = True
    try:
        if _tt_direct(page, m.group(1), bucket, parse_numeric_metric(post.get("comments"))):
            return
    except TransientError:
        if bucket.should_stop():
            return
    _tt_panel(page, post, bucket)


# --------------------------------------------------------------------------- X
X_MORE_REPLIES_JS = """() => {
    let clicked = 0;
    for (const el of document.querySelectorAll('[role="button"], button')) {
        const t = (el.innerText || '').trim().toLowerCase();
        if (t && t.length < 70 && /(mostrar|exibir|ver|show)\\s+(mais\\s+)?(respostas|replies|more replies|additional replies|provável spam|probable spam)/.test(t)) {
            el.click();
            if (++clicked >= 3) break;
        }
    }
    return clicked;
}"""

X_UNAVAILABLE_RE = re.compile(
    r"(esta página não existe|this page doesn.t exist|post (foi excluído|is unavailable|não está disponível)|"
    r"publicação (foi excluída|não está disponível)|conta suspensa|account suspended|posts são protegidos|posts are protected)",
    re.IGNORECASE)


def _x_collect(body: str, focal_id: str, bucket: CommentBucket, accepted_ids: Optional[set] = None) -> int:
    focal_id = str(focal_id or "").strip()
    if accepted_ids is None:
        accepted_ids = {focal_id}
    else:
        accepted_ids.add(focal_id)
    for item in bucket.items:
        if item.get("id"):
            accepted_ids.add(str(item["id"]))

    candidates = []
    for doc in loads_lenient(body):
        for d in iter_dicts(doc):
            item = d.get("itemContent")
            if not isinstance(item, dict) or "tweet_results" not in item or item.get("promotedMetadata"):
                continue
            tweet = _tweet_from_result((item.get("tweet_results") or {}).get("result"))
            if not tweet:
                continue
            legacy = tweet.get("legacy") or {}
            tweet_id = str(legacy.get("id_str") or tweet.get("rest_id") or "")
            if not tweet_id or tweet_id == focal_id:
                continue
            candidates.append((tweet_id, tweet, legacy))

    added = 0
    progress = True
    while progress:
        progress = False
        remaining = []
        for tweet_id, tweet, legacy in candidates:
            conv_id = str(legacy.get("conversation_id_str") or "")
            in_reply_to = str(legacy.get("in_reply_to_status_id_str") or legacy.get("in_reply_to_status_id") or "")
            if (in_reply_to and in_reply_to in accepted_ids) or conv_id == focal_id:
                accepted_ids.add(tweet_id)
                user = ((tweet.get("core") or {}).get("user_results") or {}).get("result") or {}
                handle = (user.get("core") or {}).get("screen_name") or (user.get("legacy") or {}).get("screen_name") or ""
                note = (((tweet.get("note_tweet") or {}).get("note_tweet_results") or {}).get("result") or {}).get("text")
                text = html.unescape(note or legacy.get("full_text") or "")
                if in_reply_to:
                    text = re.sub(r"^(?:@\w+\s+)+", "", text)  # remove as menções automáticas da resposta
                parent = in_reply_to
                if bucket.add(tweet_id, author=f"@{handle}" if handle else "", text=text or "[mídia]",
                              likes=legacy.get("favorite_count"), replies=legacy.get("reply_count"),
                              date=format_date(_parse_created_at(legacy.get("created_at"))),
                              parent_id="" if (not parent or parent == focal_id) else parent):
                    added += 1
                progress = True
            else:
                remaining.append((tweet_id, tweet, legacy))
        candidates = remaining

    return added


def fetch_x(page, post: dict, bucket: CommentBucket, state: dict) -> None:
    m = re.search(r"/status(?:es)?/(\d+)", post.get("link", ""))
    if not m:
        raise PostUnavailable("Link do X inválido.")
    focal_id = m.group(1)
    collector = ResponseCollector(page, ["/TweetDetail"])
    accepted_ids = {focal_id}
    try:
        page.goto(post["link"], wait_until="domcontentloaded", timeout=30000)
        got = collector.wait(timeout_ms=12000)
        if "/login" in page.url or "/i/flow/" in page.url:
            raise LoginRequired(LOGIN_MESSAGES["x"])
        if not got:
            text = page.evaluate("() => document.body ? document.body.innerText.slice(0, 3000) : ''") or ""
            if X_UNAVAILABLE_RE.search(text):
                raise PostUnavailable("Post indisponível, protegido ou excluído.")
            raise TransientError("o X não retornou as respostas")
        stagnant = clicks = rounds = 0
        while not bucket.should_stop() and rounds < 60:
            added = sum(_x_collect(body, focal_id, bucket, accepted_ids) for _, body in collector.drain())
            stagnant = 0 if added else stagnant + 1
            if stagnant >= 2 and clicks < 6:
                pressed = page.evaluate(X_MORE_REPLIES_JS) or 0
                if pressed:
                    clicks += 1
                    stagnant = 1
            if stagnant >= 4:
                bucket.exhausted = True
                return
            if bucket.should_stop() or not scroll(page, 2500, 600):
                return
            collector.wait(timeout_ms=2500)
            rounds += 1
    finally:
        collector.detach()


# --------------------------------------------------------------------------- Facebook
FB_COMMENTS_JS = """() => {
    let clicked = 0;
    for (const el of document.querySelectorAll('div[role="button"], span[role="button"]')) {
        const t = (el.innerText || '').trim().toLowerCase();
        if (t && t.length < 60 && /^(ver mais comentários|ver comentários anteriores|mostrar mais comentários|ver mais \\d+ comentários|view more comments|view previous comments|see more comments)/.test(t)) {
            el.click();
            if (++clicked >= 4) break;
        }
    }
    const out = [];
    for (const art of document.querySelectorAll('div[role="article"]')) {
        const label = art.getAttribute('aria-label') || '';
        if (!/^(comentário|comment|resposta|reply)/i.test(label)) continue;
        const link = art.querySelector('a[href*="comment_id"]');
        const authorEl = art.querySelector('a[role="link"] span, span > a > span');
        const parts = [];
        for (const t of art.querySelectorAll('div[dir="auto"]')) {
            const s = (t.innerText || '').trim();
            if (s && !parts.some(p => p.includes(s))) parts.push(s);
        }
        out.push({ label, href: link ? link.href : '', author: authorEl ? (authorEl.innerText || '') : '', text: parts.join(' ') });
    }
    const loginWall = !!document.querySelector('input[name="email"], input[name="pass"]') && !document.querySelector('div[role="main"]');
    return { clicked, comments: out, loginWall };
}"""


def fetch_facebook(page, post: dict, bucket: CommentBucket, state: dict) -> None:
    link = post.get("link", "")
    if "facebook.com" not in link:
        raise PostUnavailable("Link do Facebook inválido.")
    page.goto(link, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    url = page.url.lower()
    if "login" in url or "checkpoint" in url or "/recover/" in url:
        raise LoginRequired(LOGIN_MESSAGES["facebook"])
    stagnant = 0
    for _ in range(30):
        if bucket.should_stop():
            return
        res = page.evaluate(FB_COMMENTS_JS) or {}
        if res.get("loginWall"):
            raise LoginRequired(LOGIN_MESSAGES["facebook"])
        added = 0
        for c in res.get("comments") or []:
            href = c.get("href") or ""
            query = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
            reply_id = (query.get("reply_comment_id") or [""])[0]
            comment_id = (query.get("comment_id") or [""])[0]
            label = c.get("label") or ""
            author = c.get("author") or ""
            if not author:
                lm = re.match(r"^(?:coment[áa]rio|resposta|comment|reply)\s+(?:de|by|from)\s+(.+?)(?:\s+h[áa]\s+|\s+\d|$)", label, re.I)
                author = lm.group(1) if lm else ""
            added += bucket.add(reply_id or comment_id, author=author, text=c.get("text"),
                                parent_id=comment_id if reply_id else "")
        stagnant = 0 if (added or res.get("clicked")) else stagnant + 1
        if stagnant >= 3:
            if not bucket.items and state.get("mode") != "sessao":
                raise LoginRequired(LOGIN_MESSAGES["facebook"])  # sem login o Facebook esconde os comentários
            bucket.exhausted = True
            return
        scroll(page, 1800, 1200)


FETCHERS: Dict[str, Callable] = {
    "youtube": fetch_youtube,
    "instagram": fetch_instagram,
    "tiktok": fetch_tiktok,
    "x": fetch_x,
    "facebook": fetch_facebook,
}
SUPPORTED_NETWORKS = tuple(FETCHERS)


# --------------------------------------------------------------------------- orquestração
def _final_status(bucket: CommentBucket):
    count = len(bucket.items)
    if bucket.disabled and not count:
        return "disabled", "Comentários desativados nesta publicação."
    if not count:
        if bucket.timed_out:
            return "error", "Tempo máximo atingido sem receber comentários."
        return "empty", ""
    if bucket.full or bucket.exhausted:
        return "done", ""
    if bucket.cancelled():
        return "partial", "Coleta cancelada antes do fim."
    if bucket.timed_out:
        return "partial", "Tempo máximo por publicação atingido."
    return "done", ""


def collect_post_comments(network: str, page, post: dict, limit: int, state: dict,
                          cancel_event: Optional[threading.Event] = None, log: Optional[Callable] = None):
    """
    Coleta os comentários de um post com novas tentativas.
    Retorna (status, comentários, mensagem) — status None significa "cancelado sem nada coletado" (fica pendente).
    Lança BrowserDead quando o navegador precisa ser reaberto e nada foi coletado.
    """
    fetcher = FETCHERS[network]
    name = DISPLAY_NAMES.get(network, network)
    bucket = CommentBucket(limit=limit, deadline=time.monotonic() + post_time_budget(limit), cancel_event=cancel_event)
    last_error = ""
    for attempt in range(MAX_ATTEMPTS):
        if bucket.should_stop():
            break
        if attempt:
            if log:
                log(f"{name}: nova tentativa ({attempt + 1}/{MAX_ATTEMPTS}) em {short_link(post.get('link'))} — {last_error}", "WARN")
            _pause(RETRY_WAIT[attempt], cancel_event)
            if bucket.should_stop():
                break
        try:
            fetcher(page, post, bucket, state)
            last_error = ""
            break
        except LoginRequired as exc:
            return ("partial" if bucket.items else "login"), bucket.items, str(exc) or LOGIN_MESSAGES.get(network, "")
        except PostUnavailable as exc:
            return ("partial" if bucket.items else "error"), bucket.items, str(exc)
        except Exception as exc:
            if _browser_dead(page, exc):
                if bucket.items:
                    return "partial", bucket.items, "O navegador fechou durante a coleta."
                raise BrowserDead(_short(exc)) from exc
            last_error = _short(exc)
            logger.warning("[%s] tentativa %s falhou em %s: %s", network, attempt + 1, post.get("link"), last_error)
    if bucket.cancelled() and not bucket.items:
        return None, [], ""
    if last_error:
        return ("partial" if bucket.items else "error"), bucket.items, last_error
    status, message = _final_status(bucket)
    return status, bucket.items, message


def collect_network_comments(network: str, posts: List[dict], limit: int,
                             on_result: Callable[[dict, str, List[dict], str], None],
                             log: Callable[[str, str], None], cancel_event: Optional[threading.Event] = None) -> None:
    """
    Percorre os posts de uma rede reaproveitando um único navegador.
    posts: [{"id", "link", "comments"}]. on_result(post, status, comentários, mensagem) deve persistir o resultado.
    """
    if network not in FETCHERS:
        for post in posts:
            on_result(post, "error", [], "Rede não suportada para comentários.")
        return
    name = DISPLAY_NAMES.get(network, network)
    cancelled = lambda: bool(cancel_event and cancel_event.is_set())  # noqa: E731
    pending = deque(posts)
    crashes: Dict[int, int] = {}
    restarts = 0

    def abandon(status: str, message: str):
        while pending:
            on_result(pending.popleft(), status, [], message)

    with network_lock(network, cancel_event, on_wait=lambda: log(f"{name}: aguardando outra coleta nesta rede terminar...", "INFO")) as acquired:
        if not acquired:
            return
        while pending and not cancelled():
            reason = ""
            try:
                with sync_playwright() as p:
                    with open_page(p, network) as (page, mode):
                        state = {"mode": mode}
                        if network in ("x", "instagram", "facebook") and mode != "sessao":
                            log(f"{name}: nenhuma sessão logada encontrada — a coleta pode falhar.", "WARN")
                        failures = 0
                        while pending and not cancelled():
                            post = pending[0]
                            status, items, message = collect_post_comments(network, page, post, limit, state, cancel_event, log)
                            if status is None:
                                break
                            pending.popleft()
                            on_result(post, status, items, message)
                            if status == "login":
                                log(f"{name}: {message} {len(pending)} publicações ficaram pendentes.", "WARN")
                                abandon("login", message)
                                break
                            failures = failures + 1 if status == "error" else 0
                            if failures >= MAX_CONSECUTIVE_FAILURES:
                                reason = f"{failures} falhas seguidas"
                                break
                            if pending:
                                _pause(random.uniform(0.8, 1.8), cancel_event)
                if not reason:
                    break
            except BrowserDead as exc:
                reason = f"navegador fechou ({exc})"
                if pending:
                    key = pending[0]["id"]
                    crashes[key] = crashes.get(key, 0) + 1
                    if crashes[key] >= MAX_CRASHES_PER_POST:
                        on_result(pending.popleft(), "error", [], "O navegador falhou repetidamente ao abrir esta publicação.")
            except Exception as exc:
                logger.exception("Falha no navegador de %s durante a coleta de comentários", network)
                reason = _short(exc)
            if cancelled() or not pending:
                break
            restarts += 1
            if restarts > MAX_BROWSER_RESTARTS:
                log(f"{name}: coleta interrompida após {restarts} reinícios ({reason}). "
                    f"As {len(pending)} publicações restantes ficaram como falha — use 'Tentar novamente' mais tarde.", "ERROR")
                abandon("error", f"Coleta interrompida: {reason}.")
                break
            log(f"{name}: reiniciando o navegador ({reason})...", "WARN")
            _pause(4.0 * restarts, cancel_event)
