"""
Compilação analítica de uma extração (run): KPIs, gráficos por rede, nuvem de palavras e feed limpo.
Inclui as correções automáticas para registros antigos salvos com colunas desalinhadas.
"""
import json
import logging
import os
import re
from datetime import datetime
from typing import List, Optional

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import ScrapedPost, ScrapeRun
from top_words import get_top_words
from utils import (clean_author, clean_ui_noise, format_int_br, infer_author_from_text,
                   is_generic_author, parse_numeric_metric, sanitizar_metricas_ebm)

logger = logging.getLogger("rasp.analytics")

EMPTY_DASHBOARD = {
    "run": None,
    "summary": {"total_posts": 0, "total_engagement": 0, "total_likes": 0, "total_comments": 0, "total_views": 0,
                "total_shares": 0, "networks_count": 0, "avg_engagement": 0},
    "charts": {"engagement": {"labels": [], "data": []}, "volume": {"labels": [], "data": []}},
    "networks": [],
    "wordcloud": [],
    "feed": [],
}


def canonical_network(raw: str) -> str:
    n = (raw or "").strip().upper()
    if not n or n == "INSTAGRAM USER" or len(n) > 15 and "TWITTER" not in n:
        return "INSTAGRAM"
    if "TWITTER" in n or n == "X":
        return "X (TWITTER)"
    return n


def run_started_at(run_id: str, fallback=None):
    """Horário local de início: o run_id ('run_1789246001') carrega o epoch exato; runs antigas gravaram scraped_at em UTC."""
    m = re.search(r"_(\d{10})(?!\d)", str(run_id or ""))
    if m:
        try:
            return datetime.fromtimestamp(int(m.group(1)))
        except (OSError, ValueError):
            pass
    return fallback


def latest_run_id(db: Session) -> Optional[str]:
    latest = db.query(ScrapedPost.run_id).order_by(ScrapedPost.id.desc()).first()
    return latest[0] if latest else None


def _display_date(raw: str, scraped_at) -> tuple:
    raw = (raw or "").strip()
    if raw and raw.lower() not in ("none", "null", "n/a", "nan"):
        for fmt, length, out in (("%Y-%m-%d %H:%M:%S", 19, "%d/%m/%Y %H:%M"), ("%Y-%m-%d", 10, "%d/%m/%Y")):
            try:
                dt = datetime.strptime(raw[:length], fmt)
                return dt.strftime(out), dt.isoformat()
            except ValueError:
                continue
        return raw, ""
    if scraped_at:
        return scraped_at.strftime("%d/%m/%Y %H:%M"), ""
    return "Data desconhecida", ""


def safe_load_media_urls(media_paths_raw: str) -> List[str]:
    if not media_paths_raw:
        return []
    try:
        paths = json.loads(media_paths_raw) if isinstance(media_paths_raw, str) else list(media_paths_raw)
    except Exception:
        paths = [media_paths_raw] if isinstance(media_paths_raw, str) and media_paths_raw.strip() else []
    
    return [
        f"/api/media/{os.path.basename(f)}"
        for f in paths
        if f and str(f).lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".mp4", ".webm"))
    ]


def normalize_post(p: ScrapedPost) -> dict:
    """Converte um ScrapedPost em dicionário limpo (corrige autores, métricas e ruídos de registros antigos)."""
    author = (p.author or "").strip()
    text = (p.text or "").strip()
    network = canonical_network(p.network)

    likes = parse_numeric_metric(p.likes)
    comments = parse_numeric_metric(p.comments)
    views = parse_numeric_metric(p.views)
    shares = parse_numeric_metric(getattr(p, "shares", 0))
    # Extrações antigas do Instagram (via modal) gravavam "N/A" e a contagem vinha só no texto: "348 curtidas".
    # Só usamos esse resgate quando a métrica não foi coletada — nunca sobre um valor numérico real.
    likes_missing = not re.search(r"\d", str(p.likes or ""))
    if likes_missing and network == "INSTAGRAM" and text:
        m = re.search(r"(?<![\w$])(\d[\d\.,]*(?:\s*(?:mil|k|m))?)\s*curtidas", text, re.IGNORECASE)
        if m:
            likes = parse_numeric_metric(m.group(1))

    # Sanitização e taxonomia estrita EBM Quintto (Dominação IA):
    # Rejeita fillers fixos legados (1000, 50), estimativas sintéticas (views = likes * 15),
    # overlay de hover (views == likes) e normaliza views=0 para ausente (None).
    status_base = getattr(p, "metrics_status", "") or "coletado"
    clean_m = sanitizar_metricas_ebm(views=views, likes=likes, comments=comments, shares=shares, status_base=status_base)
    views = clean_m["views"]
    likes = clean_m["likes"] or 0
    comments = clean_m["comments"] or 0
    shares = clean_m["shares"] or 0
    metrics_status = clean_m["status"]

    if network == "INSTAGRAM":
        text = clean_ui_noise(text)
    text = " ".join(text.split()) or f"Publicação no {network}"

    if is_generic_author(author):
        author = infer_author_from_text(text) or "@perfil_instagram"
    else:
        author = clean_author(author) or "@desconhecido"

    date_display, date_iso = _display_date(getattr(p, "post_date", ""), p.scraped_at)
    engagement = likes + comments
    cs_path = getattr(p, "contact_sheet_path", "") or ""
    media_paths_val = getattr(p, "media_paths", "") or ""
    return {
        "id": p.id,
        "network": network.lower(),
        "author": author,
        "text": text,
        "link": p.link or "",
        "date": date_display,
        "date_iso": date_iso,
        "likes": likes, "likes_str": format_int_br(likes),
        "comments": comments, "comments_str": format_int_br(comments),
        "views": views, "views_str": format_int_br(views) if views is not None else "-",
        "shares": shares, "shares_str": format_int_br(shares),
        "engagement": engagement, "engagement_str": format_int_br(engagement),
        "specific_term": getattr(p, "specific_term", "") or p.keyword or "",
        "keyword": p.keyword or "",
        "comments_status": getattr(p, "comments_status", "") or "",
        "comments_collected": int(getattr(p, "comments_collected", 0) or 0),
        "comments_error": getattr(p, "comments_error", "") or "",
        "metrics_status": metrics_status,
        "media_type": getattr(p, "media_type", "") or "",
        "post_format": getattr(p, "post_format", "") or "",
        "media_paths": media_paths_val,
        "media_urls": safe_load_media_urls(media_paths_val),
        "contact_sheet_path": cs_path,
        "contact_sheet_url": f"/api/media/{os.path.basename(cs_path)}" if cs_path else "",
        "scenes_detected": int(getattr(p, "scenes_detected", 0) or 0),
        "transcription_text": getattr(p, "transcription_text", "") or "",
        "transcription_status": getattr(p, "transcription_status", "") or "",
        "accessibility_caption": getattr(p, "accessibility_caption", "") or "",
    }


def build_dashboard(db: Session, run_id: Optional[str] = None) -> dict:
    run_id = run_id or latest_run_id(db)
    if not run_id:
        return EMPTY_DASHBOARD
    posts = db.query(ScrapedPost).filter(ScrapedPost.run_id == run_id).order_by(ScrapedPost.id.asc()).all()
    if not posts:
        return EMPTY_DASHBOARD

    feed = [normalize_post(p) for p in posts]

    by_network = {}
    for item in feed:
        net = item["network"].upper()
        agg = by_network.setdefault(net, {"network": net, "posts": 0, "likes": 0, "comments": 0, "views": 0, "shares": 0, "engagement": 0})
        agg["posts"] += 1
        for key in ("likes", "comments", "views", "shares", "engagement"):
            agg[key] += (item[key] or 0)

    networks = sorted(by_network.values(), key=lambda n: n["engagement"], reverse=True)
    total_posts = len(feed)
    total_engagement = sum(n["engagement"] for n in networks)

    run = db.get(ScrapeRun, run_id)
    started = run.started_at if run else run_started_at(run_id, posts[0].scraped_at)
    run_info = {
        "run_id": run_id,
        "query": run.query if run else (posts[0].keyword or ""),
        "networks": run.networks if run else ",".join(sorted(by_network)),
        "origin": run.origin if run else "manual",
        "date": started.strftime("%d/%m/%Y %H:%M") if started else "",
        "file_name": run.file_name if run else "",
    }

    posts_transcribed = sum(1 for item in feed if item.get("transcription_text"))
    contact_sheets_count = sum(1 for item in feed if item.get("contact_sheet_path"))
    exact_metrics_count = sum(1 for item in feed if item.get("metrics_status") == "exato")

    return {
        "run": run_info,
        "summary": {
            "total_posts": total_posts,
            "total_engagement": total_engagement,
            "total_likes": sum(n["likes"] for n in networks),
            "total_comments": sum(n["comments"] for n in networks),
            "total_views": sum((n["views"] or 0) for n in networks),
            "total_shares": sum(n["shares"] for n in networks),
            "networks_count": len(networks),
            "avg_engagement": round(total_engagement / total_posts, 1) if total_posts else 0,
            "posts_transcribed": posts_transcribed,
            "contact_sheets_count": contact_sheets_count,
            "exact_metrics_count": exact_metrics_count,
        },
        "charts": {
            "engagement": {"labels": [n["network"] for n in networks], "data": [n["engagement"] for n in networks]},
            "volume": {"labels": [n["network"] for n in networks], "data": [n["posts"] for n in networks]},
        },
        "networks": networks,
        "wordcloud": [{"text": w, "weight": c} for w, c in get_top_words([f["text"] for f in feed], top_n=30)],
        "feed": feed,
    }


def run_dataframe(db: Session, run_id: str) -> pd.DataFrame:
    """DataFrame no formato da planilha executiva para uma extração salva."""
    posts = db.query(ScrapedPost).filter(ScrapedPost.run_id == run_id).order_by(ScrapedPost.id.asc()).all()
    feed = [normalize_post(p) for p in posts]
    rows = []
    for p, item in zip(posts, feed):
        rows.append({
            "Link": item["link"],
            "Data": p.post_date or (p.scraped_at.strftime("%Y-%m-%d %H:%M:%S") if p.scraped_at else ""),
            "Rede": item["network"].upper(),
            "Termo Específico": item["specific_term"],
            "Palavra-Chave": item["keyword"],
            "Autor": item["author"],
            "Texto": item["text"],
            "Curtidas": item["likes"],
            "Comentarios": item["comments"],
            "Views": item["views"],
            "Compartilhamentos": item["shares"],
            "Status Métricas": item["metrics_status"],
            "media_type": item["media_type"],
            "contact_sheet_path": item["contact_sheet_path"],
            "transcription_text": item["transcription_text"],
            "transcription_status": item["transcription_status"],
            "accessibility_caption": item["accessibility_caption"],
        })
    return pd.DataFrame(rows)


def runs_history(db: Session) -> list:
    """Histórico de extrações (usa scrape_runs quando existir e agrupa posts para runs antigas)."""
    counts = dict(db.query(ScrapedPost.run_id, func.count(ScrapedPost.id)).group_by(ScrapedPost.run_id).all())
    first_seen = dict(db.query(ScrapedPost.run_id, func.min(ScrapedPost.scraped_at)).group_by(ScrapedPost.run_id).all())
    keywords = dict(db.query(ScrapedPost.run_id, func.min(ScrapedPost.keyword)).group_by(ScrapedPost.run_id).all())
    runs = {r.run_id: r for r in db.query(ScrapeRun).all()}

    history = []
    for run_id in set(counts) | {rid for rid, r in runs.items() if r.status == "running"}:
        run = runs.get(run_id)
        started = run.started_at if run else run_started_at(run_id, first_seen.get(run_id))
        history.append({
            "run_id": run_id,
            "date": started.strftime("%d/%m/%Y %H:%M") if started else "Sem data",
            "timestamp": started.isoformat() if started else "",
            "total": counts.get(run_id, 0),
            "query": (run.query if run else keywords.get(run_id)) or "",
            "networks": run.networks if run else "",
            "origin": run.origin if run else ("agendamento" if str(run_id).startswith("cron_") else "manual"),
            "status": run.status if run else "done",
            "file_name": run.file_name if run else "",
        })
    history.sort(key=lambda h: h["timestamp"], reverse=True)
    return history
