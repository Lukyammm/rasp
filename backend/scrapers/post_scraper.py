"""
RASP — Scraper de publicações específicas diretamente por URL.
Suporta:
- Instagram: posts (/p/), reels (/reel/), vídeos (/tv/)
- TikTok: vídeos (/video/), fotos (/photo/)
- X (Twitter): tweets (/status/)
- YouTube: vídeos (/watch?v=), shorts (/shorts/), youtu.be
- Facebook: posts, reels, vídeos

Extrai metadados completos:
- Autor / Handle (@perfil)
- Texto / Legenda / Descrição
- Curtidas (Likes)
- Comentários (Comments)
- Visualizações (Views)
- Compartilhamentos (Shares / Reposts)
- Data de publicação
- Link canônico
"""
import html
import logging
import os
import re
import threading
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd

try:
    from patchright.sync_api import sync_playwright
except ImportError:
    from playwright.sync_api import sync_playwright

import urllib.parse
import urllib.request

from scrapers.browser import network_lock, open_page
from scrapers.comments import _yt_video_id
from scrapers.common import DISPLAY_NAMES, POST_COLUMNS, ResponseCollector, iter_dicts, loads_lenient
from scrapers.facebook_scraper import NUM, _find_metric
from scrapers.x_scraper import DOM_JS as X_DOM_JS, _metric as x_metric, _parse_created_at, _tweet_from_result
from utils import (decode_instagram_shortcode, epoch_to_local, format_date, parse_metricas_og_description,
                   parse_numeric_metric, parse_social_date, sanitizar_metricas_ebm)

logger = logging.getLogger("rasp.post_scraper")


def detect_network_from_url(url: str) -> Optional[str]:
    """Identifica automaticamente a rede social pela URL."""
    u = (url or "").lower().strip()
    if any(d in u for d in ("instagram.com", "instagr.am")):
        return "instagram"
    if any(d in u for d in ("tiktok.com", "vm.tiktok.com")):
        return "tiktok"
    if any(d in u for d in ("twitter.com", "x.com")):
        return "x"
    if any(d in u for d in ("youtube.com", "youtu.be")):
        return "youtube"
    if any(d in u for d in ("facebook.com", "fb.watch", "fb.com")):
        return "facebook"
    return None


def extrair_post_publico_leve(url: str) -> Optional[dict]:
    """
    Extração leve de post público sem abrir o navegador (HTTP simples).
    Utiliza metadados OpenGraph, oEmbed oficiais e JSON embutido na página pública.
    Retorna dicionário de post se bem-sucedido, ou None caso precise do navegador/sessão.
    """
    net = detect_network_from_url(url)
    if not net:
        return None

    # 1. Instagram: og:description e og:title via HTTP simples
    if net == "instagram":
        m = re.search(r"/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)", url)
        if not m:
            return None
        code = m.group(1)
        canonical = f"https://www.instagram.com/p/{code}/"
        media_id = decode_instagram_shortcode(code[:11])
        calc_date = format_date(epoch_to_local(((media_id >> 23) + 1314220800000) / 1000.0)) if media_id else ""
        try:
            req = urllib.request.Request(
                canonical,
                headers={"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}
            )
            with urllib.request.urlopen(req, timeout=12) as r:
                html_txt = r.read().decode("utf-8", "replace")

            og_desc_m = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\'](.*?)["\']', html_txt, re.I)
            og_title_m = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\'](.*?)["\']', html_txt, re.I)
            og_desc = html.unescape(og_desc_m.group(1)) if og_desc_m else ""
            og_title = html.unescape(og_title_m.group(1)) if og_title_m else ""

            likes, comments = 0, 0
            stats = parse_metricas_og_description(og_desc)
            if stats:
                likes, comments = stats

            author = ""
            m_user = re.search(r"@([A-Za-z0-9_.]+)", og_title) or re.search(r"@([A-Za-z0-9_.]+)", og_desc)
            if m_user:
                author = f"@{m_user.group(1)}"
            elif "on Instagram" in og_title:
                author = f"@{og_title.split('on Instagram')[0].strip().replace(' ', '_')}"

            texto = ""
            if " - " in og_desc:
                texto = og_desc.split(" - ", 1)[-1].strip()
            elif og_desc:
                texto = og_desc

            alt_m = re.search(r'"accessibility_caption":"(.*?)"', html_txt)
            alt = alt_m.group(1) if alt_m else ""

            if author and (likes > 0 or comments > 0 or len(texto) > 10):
                clean_m = sanitizar_metricas_ebm(views=0, likes=likes, comments=comments, shares=0, status_base="coletado")
                return {
                    "Rede": "Instagram",
                    "Palavra-Chave": "Post Específico",
                    "Termo Específico": author,
                    "Autor": author or "@perfil_instagram",
                    "Texto": texto or "[Publicação no Instagram]",
                    "Curtidas": clean_m["likes"] or 0,
                    "Comentarios": clean_m["comments"] or 0,
                    "Views": 0,
                    "Compartilhamentos": 0,
                    "Link": canonical,
                    "Data": calc_date or format_date(datetime.now()),
                    "metrics_status": clean_m["status"],
                    "accessibility_caption": alt,
                }
        except Exception:
            pass

    # 2. YouTube: oEmbed oficial
    elif net == "youtube":
        try:
            oembed_url = f"https://www.youtube.com/oembed?url={urllib.parse.quote(url)}&format=json"
            req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8"))
            author = f"@{str(data.get('author_name', '')).replace(' ', '_')}" if data.get('author_name') else "@canal_youtube"
            title = data.get("title", "")
            if title:
                return {
                    "Rede": "YouTube",
                    "Palavra-Chave": "Post Específico",
                    "Termo Específico": author,
                    "Autor": author,
                    "Texto": title,
                    "Curtidas": 0,
                    "Comentarios": 0,
                    "Views": 0,
                    "Compartilhamentos": 0,
                    "Link": url,
                    "Data": format_date(datetime.now()),
                    "metrics_status": "coletado",
                }
        except Exception:
            pass

    # 3. TikTok: oEmbed oficial
    elif net == "tiktok":
        try:
            oembed_url = f"https://www.tiktok.com/oembed?url={urllib.parse.quote(url)}"
            req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8"))
            author = f"@{str(data.get('author_unique_id') or data.get('author_name') or '').strip().lstrip('@')}"
            title = data.get("title", "")
            if title or author:
                return {
                    "Rede": "TikTok",
                    "Palavra-Chave": "Post Específico",
                    "Termo Específico": author or "@tiktok_user",
                    "Autor": author or "@tiktok_user",
                    "Texto": title or "[Vídeo no TikTok]",
                    "Curtidas": 0,
                    "Comentarios": 0,
                    "Views": 0,
                    "Compartilhamentos": 0,
                    "Link": url,
                    "Data": format_date(datetime.now()),
                    "metrics_status": "coletado",
                }
        except Exception:
            pass

    # 4. X (Twitter): oEmbed oficial
    elif net == "x":
        try:
            oembed_url = f"https://publish.twitter.com/oembed?url={urllib.parse.quote(url)}"
            req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8"))
            author = f"@{str(data.get('author_name', '')).replace(' ', '_')}" if data.get('author_name') else "@twitter_user"
            raw_html = data.get("html", "")
            text = re.sub(r"<[^>]+>", " ", raw_html).strip()
            if text:
                return {
                    "Rede": "X (Twitter)",
                    "Palavra-Chave": "Post Específico",
                    "Termo Específico": author,
                    "Autor": author,
                    "Texto": text[:280],
                    "Curtidas": 0,
                    "Comentarios": 0,
                    "Views": 0,
                    "Compartilhamentos": 0,
                    "Link": url,
                    "Data": format_date(datetime.now()),
                    "metrics_status": "coletado",
                }
        except Exception:
            pass

    return None


def consulta_em_lote_instagram_com_guardrail(
    media_ids: List[str],
    page,
    tamanho_lote: int = 25,
) -> Tuple[Dict[str, dict], bool]:
    """
    Executa consulta em lote autenticada no endpoint /api/v1/media/{id}/info/
    com guardrail anti-bloqueio. Se a API retornar HTML (sinal de rate limit / parede),
    interrompe a chamada automaticamente para preservar a sessão.
    """
    if not media_ids:
        return {}, False

    js_info = """async (ids) => {
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
                    out[id] = r.ok ? await r.text() : JSON.stringify({ __http: r.status });
                } catch (e) {
                    out[id] = JSON.stringify({ __erro: String(e) });
                }
            }
        };
        await Promise.all([worker(), worker(), worker()]);
        return out;
    }"""

    resultados: Dict[str, dict] = {}
    lotes_ruins = 0
    bloqueado = False

    for inicio in range(0, len(media_ids), tamanho_lote):
        bloco = media_ids[inicio:inicio + tamanho_lote]
        try:
            respostas = page.evaluate(js_info, bloco) or {}
        except Exception as exc:
            logger.warning("Erro na consulta em lote JS: %s", exc)
            break

        bloqueados_neste_lote = 0
        for mid in bloco:
            corpo = respostas.get(mid) or ""
            if (
                corpo.lstrip().startswith("<")
                or any(f'"__http": {c}' in corpo or f'"__http":{c}' in corpo for c in (400, 401, 403, 429))
                or "checkpoint_required" in corpo
                or "feedback_required" in corpo
            ):
                bloqueados_neste_lote += 1
                continue
            try:
                doc = json.loads(corpo) if corpo else {}
                itens = doc.get("items") if isinstance(doc, dict) else None
                if itens and len(itens) > 0:
                    resultados[mid] = itens[0]
            except Exception:
                pass

        if bloqueados_neste_lote > 0:
            logger.warning("Guardrail: %d item(ns) retornaram HTML/429/Bloqueio pela API do Instagram. Interrompendo lote preventivamente.", bloqueados_neste_lote)
            bloqueado = True
            break

    return resultados, bloqueado


def extract_instagram_single_post(page, url: str) -> dict:
    m = re.search(r"/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)", url)
    if not m:
        raise ValueError(f"URL do Instagram não contém código de publicação válido: {url}")
    code = m.group(1)
    canonical = f"https://www.instagram.com/p/{code}/"
    media_id = decode_instagram_shortcode(code[:11])
    calc_date = format_date(epoch_to_local(((media_id >> 23) + 1314220800000) / 1000.0)) if media_id else ""

    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1500)

    # 1. Tenta API /media/{id}/info/ via fetch na página
    api_res = None
    if media_id:
        try:
            api_res = page.evaluate("""async (mediaId) => {
                try {
                    const headers = { 'X-IG-App-ID': '936619743392459', 'X-Requested-With': 'XMLHttpRequest' };
                    const csrf = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1];
                    if (csrf) headers['X-CSRFToken'] = csrf;
                    const r = await fetch('/api/v1/media/' + mediaId + '/info/', { headers, credentials: 'include' });
                    if (r.ok) return await r.json();
                } catch (e) {}
                return null;
            }""", str(media_id))
        except Exception:
            pass

    if api_res and isinstance(api_res.get("items"), list) and len(api_res["items"]) > 0:
        item = api_res["items"][0]
        user = item.get("user") or item.get("owner") or {}
        username = user.get("username") or ""
        caption = item.get("caption") or {}
        text = caption.get("text", "") if isinstance(caption, dict) else ""
        likes = item.get("like_count") or 0
        comments = item.get("comment_count") or 0
        views = item.get("play_count") or item.get("view_count") or 0
        taken_at = item.get("taken_at")
        date_str = format_date(epoch_to_local(taken_at)) if taken_at else calc_date
        return {
            "Rede": "Instagram",
            "Palavra-Chave": "Post Específico",
            "Termo Específico": f"@{username}" if username else "Instagram",
            "Autor": f"@{username}" if username else "@perfil_instagram",
            "Texto": text or "[Publicação no Instagram sem legenda]",
            "Curtidas": int(likes),
            "Comentarios": int(comments),
            "Views": int(views),
            "Compartilhamentos": 0,
            "Link": canonical,
            "Data": date_str
        }

    # 2. Fallback DOM / OpenGraph
    dom = page.evaluate("""() => {
        const ogTitle = document.querySelector('meta[property="og:title"]')?.content || '';
        const ogDesc = document.querySelector('meta[property="og:description"]')?.content || '';
        let author = '';
        const userEl = document.querySelector('header a, a[role="link"][href*="/"]');
        if (userEl) {
            const href = userEl.getAttribute('href') || '';
            const parts = href.split('/').filter(Boolean);
            if (parts.length === 1 && !['p', 'reel', 'explore'].includes(parts[0])) {
                author = parts[0];
            }
        }
        let text = '';
        const h1 = document.querySelector('h1');
        if (h1 && h1.innerText.trim()) {
            text = h1.innerText.trim();
        } else {
            const spans = Array.from(document.querySelectorAll('article span, div[role="main"] span'));
            const longest = spans.map(s => s.innerText.trim()).sort((a,b) => b.length - a.length)[0];
            if (longest && longest.length > 15) text = longest;
        }
        return { ogTitle, ogDesc, author, text };
    }""")

    author = dom.get("author") or ""
    og_title = dom.get("ogTitle") or ""
    og_desc = dom.get("ogDesc") or ""
    if not author:
        m_user = re.search(r"@([A-Za-z0-9_.]+)", og_title) or re.search(r"@([A-Za-z0-9_.]+)", og_desc)
        if m_user:
            author = m_user.group(1)

    likes = 0
    comments = 0
    m_stats = re.search(r"([\d\.,]+(?:\s*[km])?)\s*(?:curtidas|likes?)[^,]*,\s*([\d\.,]+(?:\s*[km])?)\s*(?:comentários|comments?)",
                        og_desc, re.IGNORECASE)
    if m_stats:
        likes = parse_numeric_metric(m_stats.group(1))
        comments = parse_numeric_metric(m_stats.group(2))

    text = dom.get("text") or og_desc
    return {
        "Rede": "Instagram",
        "Palavra-Chave": "Post Específico",
        "Termo Específico": f"@{author}" if author else "Instagram",
        "Autor": f"@{author}" if author else "@perfil_instagram",
        "Texto": text or "[Publicação no Instagram]",
        "Curtidas": int(likes),
        "Comentarios": int(comments),
        "Views": 0,
        "Compartilhamentos": 0,
        "Link": canonical,
        "Data": calc_date or format_date(datetime.now())
    }


def extract_tiktok_single_post(page, url: str) -> dict:
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)

    data = page.evaluate("""() => {
        let item = null;
        try {
            const el = document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__');
            if (el) {
                const d = JSON.parse(el.textContent);
                item = d?.['__DEFAULT_SCOPE__']?.['webapp.video-detail']?.['itemInfo']?.['itemStruct'];
            }
        } catch (e) {}
        if (!item && window['SIGI_STATE']?.['ItemModule']) {
            const vals = Object.values(window['SIGI_STATE']['ItemModule']);
            if (vals.length) item = vals[0];
        }
        if (item) {
            return {
                found: true,
                id: item.id || '',
                author: item.author?.uniqueId || item.author?.nickname || '',
                text: item.desc || '',
                likes: item.statsV2?.diggCount || item.stats?.diggCount || 0,
                comments: item.statsV2?.commentCount || item.stats?.commentCount || 0,
                views: item.statsV2?.playCount || item.stats?.playCount || 0,
                shares: item.statsV2?.shareCount || item.stats?.shareCount || 0,
                createTime: item.createTime || 0
            };
        }
        const authorEl = document.querySelector('[data-e2e="browse-username"], h1[data-e2e="user-title"], [data-e2e="user-subtitle"], [data-e2e="video-author-uniqueid"]');
        const descEl = document.querySelector('[data-e2e="browse-video-desc"], [data-e2e="video-desc"]');
        const likeEl = document.querySelector('[data-e2e="browse-like-count"], [data-e2e="like-count"]');
        const commEl = document.querySelector('[data-e2e="browse-comment-count"], [data-e2e="comment-count"]');
        const shareEl = document.querySelector('[data-e2e="browse-share-count"], [data-e2e="share-count"]');
        const ogDesc = document.querySelector('meta[property="og:description"]')?.content || '';
        return {
            found: false,
            id: '',
            author: authorEl ? authorEl.innerText.replace('@', '').trim() : '',
            text: descEl ? descEl.innerText.trim() : ogDesc,
            likes: likeEl ? likeEl.innerText.trim() : 0,
            comments: commEl ? commEl.innerText.trim() : 0,
            views: 0,
            shares: shareEl ? shareEl.innerText.trim() : 0,
            createTime: 0
        };
    }""")

    author = data.get("author") or ""
    if not author:
        m_author = re.search(r"@([A-Za-z0-9_.-]+)", url)
        if m_author:
            author = m_author.group(1)
    author = f"@{author.lstrip('@')}" if author else "@perfil_tiktok"

    create_time = data.get("createTime")
    date_str = format_date(epoch_to_local(create_time)) if create_time else format_date(datetime.now())

    likes = parse_numeric_metric(str(data.get("likes") or 0))
    comments = parse_numeric_metric(str(data.get("comments") or 0))
    views = parse_numeric_metric(str(data.get("views") or 0))
    shares = parse_numeric_metric(str(data.get("shares") or 0))

    return {
        "Rede": "TikTok",
        "Palavra-Chave": "Post Específico",
        "Termo Específico": author,
        "Autor": author,
        "Texto": data.get("text") or "[Vídeo no TikTok]",
        "Curtidas": int(likes),
        "Comentarios": int(comments),
        "Views": int(views),
        "Compartilhamentos": int(shares),
        "Link": url,
        "Data": date_str
    }


def extract_x_single_post(page, url: str) -> dict:
    m = re.search(r"/status(?:es)?/(\d+)", url)
    tweet_id = m.group(1) if m else ""
    collector = ResponseCollector(page, ["/TweetDetail"])

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        collector.wait(timeout_ms=7000)

        found_tweet = None
        for _, body in collector.drain():
            for doc in loads_lenient(body):
                for d in iter_dicts(doc):
                    item = d.get("itemContent") or {}
                    res = (item.get("tweet_results") or {}).get("result")
                    tweet = _tweet_from_result(res)
                    if tweet:
                        tid = str(tweet.get("rest_id") or (tweet.get("legacy") or {}).get("id_str") or "")
                        if not tweet_id or tid == tweet_id:
                            found_tweet = tweet
                            break
                if found_tweet:
                    break
            if found_tweet:
                break

        if found_tweet:
            legacy = found_tweet.get("legacy") or {}
            user_res = ((found_tweet.get("core") or {}).get("user_results") or {}).get("result") or {}
            handle = (user_res.get("core") or {}).get("screen_name") or (user_res.get("legacy") or {}).get("screen_name") or ""
            note = (((found_tweet.get("note_tweet") or {}).get("note_tweet_results") or {}).get("result") or {}).get("text")
            text = html.unescape(note or legacy.get("full_text") or "")
            likes = legacy.get("favorite_count", 0)
            comments = legacy.get("reply_count", 0)
            views = (found_tweet.get("views") or {}).get("count", 0)
            shares = int(legacy.get("retweet_count", 0) or 0) + int(legacy.get("quote_count", 0) or 0)
            date_val = _parse_created_at(legacy.get("created_at"))
            date_str = format_date(date_val) if date_val else format_date(datetime.now())
            return {
                "Rede": "X",
                "Palavra-Chave": "Post Específico",
                "Termo Específico": f"@{handle}" if handle else "X",
                "Autor": f"@{handle}" if handle else "@desconhecido",
                "Texto": text or "[Publicação no X]",
                "Curtidas": int(likes),
                "Comentarios": int(comments),
                "Views": int(views),
                "Compartilhamentos": int(shares),
                "Link": url,
                "Data": date_str
            }
    finally:
        collector.detach()

    dom_articles = page.evaluate(X_DOM_JS) or []
    if dom_articles:
        art = dom_articles[0]
        user_raw = art.get("user") or ""
        m_h = re.search(r"@(\w+)", user_raw)
        handle = m_h.group(1) if m_h else ""
        return {
            "Rede": "X",
            "Palavra-Chave": "Post Específico",
            "Termo Específico": f"@{handle}" if handle else "X",
            "Autor": f"@{handle}" if handle else "@desconhecido",
            "Texto": art.get("text") or "[Publicação no X]",
            "Curtidas": int(x_metric(art.get("likes"))),
            "Comentarios": int(x_metric(art.get("replies"))),
            "Views": int(x_metric(art.get("views"))),
            "Compartilhamentos": int(x_metric(art.get("reposts"))),
            "Link": url,
            "Data": format_date(parse_social_date(art.get("datetime")) or datetime.now())
        }

    return {
        "Rede": "X",
        "Palavra-Chave": "Post Específico",
        "Termo Específico": "X",
        "Autor": "@desconhecido",
        "Texto": "[Publicação no X]",
        "Curtidas": 0, "Comentarios": 0, "Views": 0, "Compartilhamentos": 0,
        "Link": url,
        "Data": format_date(datetime.now())
    }


def extract_youtube_single_post(page, url: str) -> dict:
    vid = _yt_video_id(url)
    if not vid:
        raise ValueError(f"Link do YouTube inválido: {url}")
    canonical = f"https://www.youtube.com/watch?v={vid}"
    page.goto(canonical, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1500)

    data = page.evaluate("""() => {
        const pr = window.ytInitialPlayerResponse || {};
        const vd = pr.videoDetails || {};
        const title = vd.title || document.title || '';
        const author = vd.author || '';
        const views = vd.viewCount || 0;
        const desc = vd.shortDescription || '';

        let likes = 0;
        const likeBtn = document.querySelector('like-button-view-model button, button[aria-label*="gostei"], button[aria-label*="like"]');
        if (likeBtn) {
            likes = likeBtn.getAttribute('aria-label') || likeBtn.innerText || '';
        }
        const dateEl = document.querySelector('#info-strings yt-formatted-string, meta[itemprop="datePublished"]');
        const dateVal = dateEl ? (dateEl.getAttribute('content') || dateEl.innerText || '') : '';
        return { title, author, views, desc, likes, dateVal };
    }""")

    author_str = data.get("author") or ""
    author = f"@{author_str.replace(' ', '_')}" if author_str else "@canal_youtube"
    views = parse_numeric_metric(str(data.get("views") or 0))
    likes = parse_numeric_metric(str(data.get("likes") or 0))
    date_val = data.get("dateVal") or ""
    parsed_dt = parse_social_date(date_val) if date_val else datetime.now()

    return {
        "Rede": "YouTube",
        "Palavra-Chave": "Post Específico",
        "Termo Específico": author,
        "Autor": author,
        "Texto": data.get("title") or "[Vídeo no YouTube]",
        "Curtidas": int(likes),
        "Comentarios": 0,
        "Views": int(views),
        "Compartilhamentos": 0,
        "Link": canonical,
        "Data": format_date(parsed_dt)
    }


def extract_facebook_single_post(page, url: str) -> dict:
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2500)

    dom = page.evaluate("""() => {
        const ogTitle = document.querySelector('meta[property="og:title"]')?.content || '';
        const ogDesc = document.querySelector('meta[property="og:description"]')?.content || '';
        let author = '';
        const authorEl = document.querySelector('h2 a, h3 a, h4 a, strong a, a[role="link"] strong');
        if (authorEl) author = authorEl.innerText.trim();
        let text = '';
        for (const t of document.querySelectorAll('div[dir="auto"], span[dir="auto"]')) {
            const s = (t.innerText || '').trim();
            if (s.length > 20 && !text.includes(s)) text += ' ' + s;
        }
        const arias = Array.from(document.querySelectorAll('[aria-label]'))
            .map(e => e.getAttribute('aria-label') || '').filter(x => /\\d/.test(x)).slice(0, 30);
        return { ogTitle, ogDesc, author, text: text.trim(), arias };
    }""")

    author = dom.get("author") or ""
    if not author:
        m_a = re.search(r"^([^|•-]+)", dom.get("ogTitle") or "")
        if m_a:
            author = m_a.group(1).strip()
    author = f"@{author.replace(' ', '_')}" if author else "@facebook_user"

    arias = dom.get("arias") or []
    likes = _find_metric([r"([\d\.,]+(?:\s*[km])?)\s*(?:reaç|curtid|like)", NUM], *arias)
    comments = _find_metric([r"([\d\.,]+(?:\s*[km])?)\s*coment", NUM], *arias)
    shares = _find_metric([r"([\d\.,]+(?:\s*[km])?)\s*compartilh", NUM], *arias)

    text = dom.get("text") or dom.get("ogDesc") or "[Publicação no Facebook]"

    return {
        "Rede": "Facebook",
        "Palavra-Chave": "Post Específico",
        "Termo Específico": author,
        "Autor": author,
        "Texto": text,
        "Curtidas": int(likes),
        "Comentarios": int(comments),
        "Views": 0,
        "Compartilhamentos": int(shares),
        "Link": url,
        "Data": format_date(datetime.now())
    }


POST_EXTRACTORS = {
    "instagram": extract_instagram_single_post,
    "tiktok": extract_tiktok_single_post,
    "x": extract_x_single_post,
    "youtube": extract_youtube_single_post,
    "facebook": extract_facebook_single_post,
}


def scrape_single_post(network: str, url: str, page) -> dict:
    """Extrai uma publicação individual a partir da sua URL e da página aberta com Playwright."""
    net = (network or "").lower().strip()
    if net not in POST_EXTRACTORS:
        detected = detect_network_from_url(url)
        if detected and detected in POST_EXTRACTORS:
            net = detected
        else:
            raise ValueError(f"Rede não suportada para post individual: {network}")

    extractor = POST_EXTRACTORS[net]
    return extractor(page, url)


def scrape_posts_by_urls(
    urls: List[str],
    network: Optional[str] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> Tuple[pd.DataFrame, int, int]:
    """
    Navega em cada URL fornecida, extrai as métricas e retorna (DataFrame, total_posts, soma_comentários).
    Agrupa por rede para reaproveitar a instância do navegador de cada rede.
    """
    clean_urls = [u.strip() for u in urls if u and u.strip().startswith("http")]
    if not clean_urls:
        return pd.DataFrame(columns=POST_COLUMNS), 0, 0

    def log(msg, level="INFO"):
        if progress_callback:
            try:
                progress_callback(f"[{level}] {msg}")
            except Exception:
                pass
        logger.info(msg)

    # Tenta extração leve pré-flight (sem navegador) para URLs públicas suportadas
    pendentes_urls = []
    for u in clean_urls:
        if cancel_event and cancel_event.is_set():
            break
        try:
            leve = extrair_post_publico_leve(u)
            if leve and leve.get("Autor") and leve.get("Autor") != "@desconhecido" and (leve.get("Curtidas", 0) > 0 or len(leve.get("Texto", "")) > 15):
                log(f"[Leve/HTTP] Coletado com sucesso sem abrir navegador: {leve.get('Autor')} ({leve.get('Rede')})", "SUCCESS")
                collected_posts.append(leve)
                total_comments += leve.get("Comentarios", 0)
                continue
        except Exception:
            pass
        pendentes_urls.append(u)

    if not pendentes_urls:
        df = pd.DataFrame(collected_posts, columns=POST_COLUMNS)
        return df, len(df), total_comments

    # Agrupa URLs restantes por rede para o navegador
    grouped_urls: Dict[str, List[str]] = {}
    for u in pendentes_urls:
        net = (network or "").lower().strip()
        if not net or net == "auto":
            net = detect_network_from_url(u) or "instagram"
        grouped_urls.setdefault(net, []).append(u)

    for net, net_urls in grouped_urls.items():
        if cancel_event and cancel_event.is_set():
            break

        net_name = DISPLAY_NAMES.get(net, net.upper())
        log(f"{net_name}: iniciando extração via navegador de {len(net_urls)} publicações específicas...")

        with network_lock(net, cancel_event, on_wait=lambda: log(f"{net_name}: aguardando liberação do navegador...")):
            try:
                with sync_playwright() as p:
                    with open_page(p, net) as (page, mode):
                        urls_pendentes_net = list(net_urls)

                        # Instagram autenticado: consulta rápida em lote com guardrail anti-bloqueio
                        if net == "instagram" and mode != "anonimo" and len(urls_pendentes_net) > 1:
                            id_map = {}
                            for u in urls_pendentes_net:
                                m = re.search(r"/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)", u)
                                if m:
                                    mid = decode_instagram_shortcode(m.group(1)[:11])
                                    if mid:
                                        id_map[str(mid)] = u

                            if id_map:
                                log(f"{net_name}: consultando {len(id_map)} itens em lote na API interna com guardrail...")
                                lote_res, bloqueado = consulta_em_lote_instagram_com_guardrail(list(id_map.keys()), page)
                                for mid_str, item in lote_res.items():
                                    orig_url = id_map.get(mid_str)
                                    if not orig_url or not isinstance(item, dict):
                                        continue
                                    user = item.get("user") or item.get("owner") or {}
                                    username = user.get("username") or ""
                                    caption = item.get("caption") or {}
                                    text = caption.get("text", "") if isinstance(caption, dict) else ""
                                    likes = item.get("like_count") or 0
                                    comments = item.get("comment_count") or 0
                                    views = item.get("play_count") or item.get("view_count") or None
                                    taken_at = item.get("taken_at")
                                    calc_d = format_date(epoch_to_local(taken_at)) if taken_at else format_date(datetime.now())
                                    clean_m = sanitizar_metricas_ebm(views=views, likes=likes, comments=comments, shares=0, status_base="exato")
                                    post_dict = {
                                        "Rede": "Instagram",
                                        "Palavra-Chave": "Post Específico",
                                        "Termo Específico": f"@{username}" if username else "Instagram",
                                        "Autor": f"@{username}" if username else "@perfil_instagram",
                                        "Texto": text or "[Publicação no Instagram sem legenda]",
                                        "Curtidas": clean_m["likes"] or 0,
                                        "Comentarios": clean_m["comments"] or 0,
                                        "Views": clean_m["views"] or 0,
                                        "Compartilhamentos": 0,
                                        "Link": orig_url,
                                        "Data": calc_d,
                                        "metrics_status": clean_m["status"],
                                    }
                                    collected_posts.append(post_dict)
                                    total_comments += post_dict["Comentarios"]
                                    if orig_url in urls_pendentes_net:
                                        urls_pendentes_net.remove(orig_url)
                                    log(f"{net_name} [Lote]: coletado {post_dict['Autor']} | Curtidas: {post_dict['Curtidas']} | Comentários: {post_dict['Comentarios']}", "SUCCESS")

                                if bloqueado:
                                    log(f"{net_name}: Guardrail acionado (resposta HTML na API). Interrompendo lote para segurança da conta.", "WARN")
                                    urls_pendentes_net = []

                        for idx, url in enumerate(urls_pendentes_net, 1):
                            if cancel_event and cancel_event.is_set():
                                break

                            log(f"{net_name} ({idx}/{len(urls_pendentes_net)}): acessando {url}...")
                            try:
                                post_data = scrape_single_post(net, url, page)
                                collected_posts.append(post_data)
                                total_comments += post_data.get("Comentarios", 0)
                                author = post_data.get("Autor", "@perfil")
                                likes = post_data.get("Curtidas", 0)
                                comms = post_data.get("Comentarios", 0)
                                log(f"{net_name}: coletado {author} | Curtidas: {likes} | Comentários: {comms}", "SUCCESS")
                            except Exception as exc:
                                logger.exception("Falha ao extrair post %s em %s", url, net)
                                log(f"{net_name}: erro ao extrair {url}: {str(exc).splitlines()[0]}", "WARN")
                                # Mantém registro básico para não perder a referência
                                collected_posts.append({
                                    "Rede": net_name,
                                    "Palavra-Chave": "Post Específico",
                                    "Termo Específico": "Erro de Coleta",
                                    "Autor": "@desconhecido",
                                    "Texto": f"[Falha ao acessar: {str(exc).splitlines()[0]}]",
                                    "Curtidas": 0,
                                    "Comentarios": 0,
                                    "Views": 0,
                                    "Compartilhamentos": 0,
                                    "Link": url,
                                    "Data": format_date(datetime.now()),
                                    "metrics_status": "ausente",
                                })
            except Exception as exc:
                logger.exception("Erro crítico no navegador para %s", net)
                log(f"{net_name}: erro no navegador: {str(exc).splitlines()[0]}", "ERROR")

    df = pd.DataFrame(collected_posts, columns=POST_COLUMNS)
    return df, len(df), total_comments
