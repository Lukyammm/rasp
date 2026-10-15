"""
Agendamentos recorrentes (APScheduler) persistidos na tabela schedules.
Os jobs são recarregados na inicialização do servidor e usam o mesmo pipeline das extrações manuais.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from database import Schedule, session_scope

logger = logging.getLogger("rasp.scheduler")

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = AsyncIOScheduler(job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 3600})
except ImportError:  # pragma: no cover
    scheduler = None
    CronTrigger = None
    logger.warning("APScheduler não instalado. Agendamentos desativados.")


def available() -> bool:
    return scheduler is not None


def build_trigger(cron: str):
    """Valida e converte uma expressão crontab de 5 campos (minuto hora dia mês dia-da-semana)."""
    if not CronTrigger:
        raise RuntimeError("Módulo de agendamento indisponível.")
    parts = (cron or "").split()
    if len(parts) != 5:
        raise ValueError("Use o formato crontab com 5 campos: 'minuto hora dia mês dia-da-semana'.")
    return CronTrigger.from_crontab(cron)


def next_run_time(schedule_id: str) -> Optional[str]:
    if not scheduler:
        return None
    job = scheduler.get_job(schedule_id)
    return job.next_run_time.strftime("%d/%m/%Y %H:%M") if job and job.next_run_time else None


def register(schedule: Schedule) -> None:
    if not scheduler:
        return
    if schedule.status != "active":
        unregister(schedule.id)
        return
    scheduler.add_job(run_schedule, build_trigger(schedule.cron), id=schedule.id, args=[schedule.id], replace_existing=True)


def unregister(schedule_id: str) -> None:
    if scheduler and scheduler.get_job(schedule_id):
        scheduler.remove_job(schedule_id)


async def run_schedule(schedule_id: str, force: bool = False) -> None:
    """Executa um agendamento (force=True executa mesmo se estiver pausado — botão 'Executar agora')."""
    from jobs import jobs, run_scrape_job  # import tardio evita ciclo

    def load():
        with session_scope() as db:
            s = db.get(Schedule, schedule_id)
            if not s:
                return None
            return {"keywords": s.keyword_list(), "networks": s.network_list() or ["x", "instagram", "tiktok"],
                    "search_type": s.search_type or "keyword", "limit": s.max_posts or 50, "status": s.status}

    data = await asyncio.to_thread(load)
    if not data or (data["status"] != "active" and not force) or not data["keywords"]:
        return
    logger.info("[CRON] Executando agendamento %s: %s", schedule_id, data["keywords"])
    job = jobs.create(keywords=data["keywords"], networks=data["networks"], search_type=data["search_type"],
                      limit=data["limit"], origin="agendamento", schedule_id=schedule_id)
    await run_scrape_job(job)

    def mark():
        with session_scope() as db:
            s = db.get(Schedule, schedule_id)
            if s:
                s.last_run_at = datetime.now()
                s.last_run_id = job.run_id

    await asyncio.to_thread(mark)
    logger.info("[CRON] Agendamento %s finalizado (%s posts, status %s)", schedule_id, job.total_posts, job.status)


def start() -> None:
    if not scheduler:
        return
    if not scheduler.running:
        scheduler.start()
    with session_scope() as db:
        for s in db.query(Schedule).all():
            try:
                register(s)
            except Exception as exc:
                logger.warning("Agendamento %s ignorado (cron inválido '%s'): %s", s.id, s.cron, exc)
    logger.info("Agendador iniciado com %s job(s) ativo(s).", len(scheduler.get_jobs()))


def shutdown() -> None:
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
