"""
Script para extrair TODOS os comentários de TODAS as publicações da extração do Caso Isabelle Caracristi (run_1789851028_c6cf).
Compatível com Windows utf-8 e com a arquitetura do RASP.
"""
import sys
import io
import os
import time
import logging

# Forçar stdout para UTF-8 no Windows
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rasp.batch_comments")

from database import get_db, ScrapedPost, PostComment, save_post_comments
from scrapers.comments import collect_network_comments, SUPPORTED_NETWORKS
from utils import parse_numeric_metric

RUN_ID = sys.argv[1] if len(sys.argv) > 1 else "run_1789851028_c6cf"

def get_posts_by_network():
    db = next(get_db())
    posts = db.query(ScrapedPost).filter(ScrapedPost.run_id == RUN_ID).all()
    
    by_network = {"instagram": [], "tiktok": [], "youtube": [], "x": []}
    
    for p in posts:
        net = p.network.lower()
        if "instagram" in net:
            key = "instagram"
        elif "tiktok" in net:
            key = "tiktok"
        elif "youtube" in net:
            key = "youtube"
        elif "x" in net or "twitter" in net:
            key = "x"
        else:
            continue
            
        link = (p.link or "").strip()
        if not link.startswith(("http://", "https://")):
            continue
            
        metric = parse_numeric_metric(p.comments)
        by_network[key].append({
            "id": p.id,
            "link": link,
            "author": p.author,
            "comments": metric,
            "text": (p.text or "")[:60]
        })
        
    # Ordenar pelos mais comentados primeiro
    for k in by_network:
        by_network[k].sort(key=lambda x: x["comments"], reverse=True)
        
    return by_network

def main():
    print(f"=== INICIANDO COLETA TOTAL DE COMENTÁRIOS PARA RUN {RUN_ID} ===")
    posts_by_network = get_posts_by_network()
    
    total_posts = sum(len(p) for p in posts_by_network.values())
    print(f"Total de publicações elegíveis: {total_posts}")
    for net, plist in posts_by_network.items():
        print(f"  - {net.upper()}: {len(plist)} posts (soma métricas: {sum(p['comments'] for p in plist):,} comentários)")

    limits = {
        "instagram": 1500,  # Até 1500 comentários nos posts gigantes, 100% nos demais
        "tiktok": 1000,     # Até 1000 comentários nos maiores, 100% nos demais
        "youtube": 500,     # Até 500 comentários por vídeo
        "x": 200            # Até 200 respostas por tweet
    }

    # Ordem de execução: youtube -> tiktok -> instagram -> x
    exec_order = ["youtube", "tiktok", "instagram", "x"]
    
    overall_stats = {}
    
    for network in exec_order:
        all_plist = posts_by_network.get(network, [])
        if not all_plist:
            continue
            
        limit = limits.get(network, 500)
        
        # Separar posts que já têm 0 comentários confirmados (exceto YouTube onde métrica vem 0 da busca)
        if network == "youtube":
            to_scrape = all_plist
            zero_posts = []
        else:
            to_scrape = [p for p in all_plist if p["comments"] > 0]
            zero_posts = [p for p in all_plist if p["comments"] == 0]
            
        print(f"\n=======================================================")
        print(f"--> PROCESSANDO REDE: {network.upper()} ({len(all_plist)} posts total: {len(to_scrape)} para raspar, {len(zero_posts)} com 0 comentários)")
        print(f"=======================================================")
        
        # Registrar diretamente os posts com 0 comentários
        for zp in zero_posts:
            save_post_comments(zp["id"], RUN_ID, network, [], "empty", "")
            
        results_in_net = []
        
        def on_result(post, status, items, message):
            saved_count = save_post_comments(post["id"], RUN_ID, network, items, status, message)
            results_in_net.append((post["id"], status, len(items), saved_count))
            msg_part = f" | {message}" if message else ""
            print(f"  [{network.upper()} #{post['id']}] {post['author']} - {len(items)} comentários coletados (Total no banco: {saved_count}) | status={status}{msg_part}")
            
        def log_cb(msg, lvl="INFO"):
            print(f"  [{lvl}] {msg}")
            
        if to_scrape:
            try:
                collect_network_comments(
                    network=network,
                    posts=to_scrape,
                    limit=limit,
                    on_result=on_result,
                    log=log_cb
                )
            except Exception as exc:
                print(f"  [ERRO GERAL EM {network.upper()}]: {exc}")
                
        overall_stats[network] = results_in_net
        print(f"Fim da rede {network.upper()}: {len(results_in_net)}/{len(to_scrape)} raspados (+ {len(zero_posts)} com zero).")
        time.sleep(1)

    print("\n=== RESUMO FINAL DA COLETA ===")
    db = next(get_db())
    total_comments_in_db = db.query(PostComment).filter(PostComment.run_id == RUN_ID).count()
    print(f"TOTAL DE COMENTÁRIOS NO BANCO PARA O CASO ISABELLE: {total_comments_in_db}")
    
    # Detalhar por rede
    from sqlalchemy import func
    net_counts = db.query(PostComment.network, func.count(PostComment.id)).filter(PostComment.run_id == RUN_ID).group_by(PostComment.network).all()
    for net, count in net_counts:
        print(f"  - {net.upper()}: {count:,} comentários")

if __name__ == "__main__":
    main()
