"""
Consultas da coleta de comentários: escolha dos posts a processar, resumo por rede, listagem e linhas do Excel.
"""
from collections import defaultdict
from typing import Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from analytics import canonical_network, normalize_post
from database import PostComment, ScrapedPost
from scrapers.comments import SUPPORTED_NETWORKS
from utils import parse_numeric_metric

FINAL_STATUSES = ("done", "empty", "disabled")  # não precisam ser coletados de novo
# Redes em que a métrica de comentários da busca é confiável para pular posts sem comentários
RELIABLE_COUNT_NETWORKS = ("x", "tiktok", "instagram")
NETWORK_ORDER = ("youtube", "tiktok", "instagram", "x", "facebook")


def network_key(raw: str) -> str:
    net = canonical_network(raw)
    return "x" if net == "X (TWITTER)" else net.lower()


def select_posts(db: Session, run_id: str, post_ids: Optional[List[int]] = None, networks: Optional[List[str]] = None,
                 mode: str = "pending", skip_zero: bool = True, max_posts: Optional[int] = None) -> Dict[str, List[dict]]:
    """
    Posts a processar, agrupados por rede e ordenados pelos mais comentados.
    mode 'pending' ignora os já concluídos (done/empty/disabled); 'all' recoleta tudo (sem duplicar comentários).
    Posts escolhidos individualmente (post_ids) são sempre processados.
    Quando max_posts for informado, o limite é distribuído de forma equilibrada entre as redes participantes
    (ou aplicado à rede selecionada), evitando que redes com grandes volumes de comentários monopolizem as vagas.
    """
    query = db.query(ScrapedPost).filter(ScrapedPost.run_id == run_id)
    if post_ids:
        query = query.filter(ScrapedPost.id.in_(post_ids))
    candidates = []
    target_nets = {network_key(n) for n in networks} if networks else None
    for p in query.all():
        net = network_key(p.network)
        link = (p.link or "").strip()
        if net not in SUPPORTED_NETWORKS or not link.startswith(("http://", "https://")):
            continue
        if target_nets and net not in target_nets:
            continue
        metric = max(parse_numeric_metric(p.comments), int(p.comments_collected or 0))
        likes = parse_numeric_metric(p.likes)
        if not post_ids:
            if mode == "pending" and (p.comments_status or "") in FINAL_STATUSES:
                continue
            if skip_zero and net in RELIABLE_COUNT_NETWORKS and metric == 0:
                continue
        candidates.append((net, {"id": p.id, "link": link, "comments": metric, "likes": likes}))

    by_net: Dict[str, List[dict]] = defaultdict(list)
    for net, post in candidates:
        by_net[net].append(post)

    for net in by_net:
        by_net[net].sort(key=lambda c: (c["comments"], c["likes"]), reverse=True)

    if max_posts and not post_ids:
        selected_by_net: Dict[str, List[dict]] = defaultdict(list)
        total_selected = 0
        net_priority = sorted(by_net.keys(), key=lambda n: (by_net[n][0]["comments"], by_net[n][0]["likes"]), reverse=True)
        idx = {n: 0 for n in net_priority}
        while total_selected < max_posts:
            advanced = False
            for n in net_priority:
                if idx[n] < len(by_net[n]):
                    selected_by_net[n].append(by_net[n][idx[n]])
                    idx[n] += 1
                    total_selected += 1
                    advanced = True
                    if total_selected >= max_posts:
                        break
            if not advanced:
                break
        by_net = selected_by_net

    grouped: Dict[str, List[dict]] = {}
    for net in NETWORK_ORDER:
        items = by_net.get(net)
        if items:
            grouped[net] = items
    return grouped


def summary(db: Session, run_id: str) -> dict:
    rows = db.query(ScrapedPost.id, ScrapedPost.network, ScrapedPost.link, ScrapedPost.comments,
                    ScrapedPost.comments_status, ScrapedPost.comments_collected, ScrapedPost.comments_error) \
        .filter(ScrapedPost.run_id == run_id).all()
    by_net = {}
    statuses = {}
    for pid, raw_net, link, metric, status, collected, error in rows:
        net = network_key(raw_net)
        supported = net in SUPPORTED_NETWORKS and str(link or "").startswith(("http://", "https://"))
        agg = by_net.setdefault(net, defaultdict(int, network=net))
        agg["posts"] += 1
        if not supported:
            continue
        status = status or ""
        agg["supported"] += 1
        agg["comments"] += int(collected or 0)
        agg[status or "never"] += 1
        if status not in FINAL_STATUSES:
            zero = net in RELIABLE_COUNT_NETWORKS and max(parse_numeric_metric(metric), int(collected or 0)) == 0
            agg["pending_zero" if zero else "pending"] += 1
        if status:
            statuses[pid] = [status, int(collected or 0), error or ""]
    networks = [dict(by_net[n]) for n in NETWORK_ORDER if n in by_net]
    totals = defaultdict(int)
    for n in networks:
        for key in ("posts", "supported", "comments", "done", "empty", "disabled", "partial", "error", "login", "pending", "pending_zero"):
            totals[key] += n.get(key, 0)
    return {"run_id": run_id, "networks": networks, "totals": dict(totals), "statuses": statuses}


def list_comments(db: Session, run_id: str, post_id: Optional[int] = None, network: Optional[str] = None,
                  search: str = "", limit: int = 200, offset: int = 0) -> dict:
    query = db.query(PostComment, ScrapedPost).join(ScrapedPost, ScrapedPost.id == PostComment.post_id) \
        .filter(PostComment.run_id == run_id)
    if post_id:
        query = query.filter(PostComment.post_id == post_id)
    if network:
        query = query.filter(PostComment.network == network)
    search = (search or "").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(or_(PostComment.text.ilike(like), PostComment.author.ilike(like)))
    total = query.count()
    rows = query.order_by(PostComment.post_id.asc(), PostComment.likes.desc(), PostComment.id.asc()) \
        .offset(max(0, offset)).limit(max(1, min(limit, 1000))).all()
    posts_cache = {}
    items = []
    for c, p in rows:
        if p.id not in posts_cache:
            norm = normalize_post(p)
            posts_cache[p.id] = {"id": p.id, "author": norm["author"], "text": norm["text"][:280], "link": norm["link"],
                                 "network": norm["network"], "date": norm["date"]}
        items.append({"id": c.id, "post_id": c.post_id, "network": c.network, "author": c.author, "text": c.text,
                      "likes": c.likes or 0, "replies": c.replies or 0, "date": c.comment_date or "",
                      "parent_id": c.parent_id or "", "post": posts_cache[p.id]})
    return {"total": total, "offset": offset, "items": items}


def excel_rows(db: Session, run_id: str) -> List[dict]:
    rows = db.query(PostComment, ScrapedPost).join(ScrapedPost, ScrapedPost.id == PostComment.post_id) \
        .filter(PostComment.run_id == run_id) \
        .order_by(PostComment.post_id.asc(), PostComment.likes.desc(), PostComment.id.asc()).all()
    posts_cache = {}
    out = []
    for c, p in rows:
        if p.id not in posts_cache:
            posts_cache[p.id] = normalize_post(p)
        post = posts_cache[p.id]
        out.append({
            "post_link": post["link"], "network": post["network"].upper(), "post_author": post["author"],
            "post_text": post["text"], "author": c.author or "", "text": c.text or "", "likes": c.likes or 0,
            "replies": c.replies or 0, "date": c.comment_date or "", "is_reply": bool(c.parent_id),
        })
    return out


def delete_run_comments(db: Session, run_id: str) -> int:
    return db.query(PostComment).filter(PostComment.run_id == run_id).delete(synchronize_session=False)
