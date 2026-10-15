"""
Pipeline de atualização completa do monitoramento do Caso Isabelle Caracristi (até 21/09/2026 14h34).
Etapa 1: Scraping atualizado dos posts nas redes (Instagram, TikTok, YouTube, X).
"""
import sys
import os
import asyncio
import time
import logging

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rasp.refresh")

from jobs import jobs, run_scrape_job
from database import get_db, ScrapedPost, ScrapeRun

async def run():
    print("=== ETAPA 1: INICIANDO EXTRAÇÃO DE POSTS ATUALIZADOS (ATÉ 21/09/2026) ===")
    job = jobs.create(
        keywords=["Isabelle Caracristi"],
        networks=["instagram", "tiktok", "youtube", "x"],
        limit=50,
        search_type="keyword"
    )
    print(f"Job ID: {job.job_id}")
    print(f"Run ID: {job.run_id}")
    
    await run_scrape_job(job)
    
    print("\n=== RESULTADO DO SCRAPE DE POSTS ===")
    print(f"Status do Job: {job.status}")
    print(f"Total de posts: {job.total_posts}")
    print(f"Resultados por rede: {job.network_results}")
    if job.error:
        print(f"Erro: {job.error}")

    db = next(get_db())
    posts = db.query(ScrapedPost).filter(ScrapedPost.run_id == job.run_id).all()
    print(f"Posts gravados no banco para run_id '{job.run_id}': {len(posts)}")
    for p in posts[:10]:
        print(f"  [{p.network}] {p.author} | Likes: {p.likes} | Comments: {p.comments} | Views: {p.views} | {p.link}")

if __name__ == "__main__":
    asyncio.run(run())
