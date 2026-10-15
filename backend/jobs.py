"""
Execução de extrações como jobs em segundo plano.

- O Playwright roda de forma síncrona dentro de asyncio.to_thread (isolado do event loop do FastAPI).
- Mensagens intermediárias dos scrapers chegam ao WebSocket via asyncio.run_coroutine_threadsafe.
- Cada job guarda seu histórico de logs, permitindo reconectar o painel após recarregar a página.
- Cancelamento cooperativo via threading.Event verificado pelos scrapers entre as rolagens.
"""
import asyncio
import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from fastapi import WebSocket

from config import (CONTACT_SHEETS_DIR, DOWNLOADS_DIR, FRAMES_DIR, JOB_LOG_HISTORY,
                    MAX_CONCURRENT_JOBS, MEDIA_DIR, VIDEOS_DIR)
import media_service
import video_service
import transcription_service
from database import ScrapedPost, ScrapeRun, load_brand_handles, save_post_comments, session_scope
from excel_builder import build_executive_workbook
from exports import archive_copy, friendly_path
from scrapers.base_scraper import scrape_network
from scrapers.comments import collect_network_comments, short_link
from scrapers.common import DISPLAY_NAMES
from scrapers.post_scraper import scrape_posts_by_urls
from utils import (build_report_filename, clean_author, infer_author_from_text, is_generic_author,
                   parse_numeric_metric, sanitizar_metricas_ebm, unique_filename)

logger = logging.getLogger("rasp.jobs")

EXCEL_COLUMNS = [
    "Link", "Data", "Rede", "Termo Específico", "Palavra-Chave", "Autor", "Texto", "Curtidas",
    "Comentarios", "Views", "Compartilhamentos", "Status Métricas", "media_type",
    "contact_sheet_path", "transcription_text", "transcription_status", "accessibility_caption"
]


# --------------------------------------------------------------------------- WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections.setdefault(client_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, client_id: str):
        conns = self.active_connections.get(client_id)
        if not conns:
            return
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self.active_connections.pop(client_id, None)

    async def send_personal_message(self, message: str, client_id: Optional[str]):
        for connection in list(self.active_connections.get(client_id or "", [])):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection, client_id)


manager = ConnectionManager()


# --------------------------------------------------------------------------- Jobs
@dataclass
class ScrapeJob:
    keywords: List[str]
    networks: List[str]
    search_type: str = "keyword"
    limit: int = 50
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    client_id: Optional[str] = None
    origin: str = "manual"
    schedule_id: Optional[str] = None
    scrape_comments: bool = False
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    run_id: str = field(default_factory=lambda: f"run_{int(time.time())}_{uuid.uuid4().hex[:4]}")
    status: str = "queued"  # queued | running | done | error | cancelled
    logs: List[dict] = field(default_factory=list)
    total_posts: int = 0
    total_comments: int = 0
    file_name: Optional[str] = None
    saved_path: Optional[str] = None
    error: Optional[str] = None
    steps_total: int = 0
    steps_done: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    network_results: Dict[str, int] = field(default_factory=dict)
    kind: str = "scrape"  # scrape | comments | enrich
    max_comments: int = 100
    comment_stats: Dict[str, int] = field(default_factory=dict)
    enrich_media: bool = False
    generate_contact_sheet: bool = False
    transcribe_audio: bool = False
    detect_scenes: bool = False

    @property
    def finished(self) -> bool:
        return self.status in ("done", "error", "cancelled")

    def to_dict(self, include_logs: bool = False) -> dict:
        data = {
            "job_id": self.job_id,
            "kind": self.kind,
            "max_comments": self.max_comments,
            "scrape_comments": self.scrape_comments,
            "comment_stats": self.comment_stats,
            "enrich_media": self.enrich_media,
            "generate_contact_sheet": self.generate_contact_sheet,
            "transcribe_audio": self.transcribe_audio,
            "detect_scenes": self.detect_scenes,
            "run_id": self.run_id,
            "status": self.status,
            "keywords": self.keywords,
            "networks": self.networks,
            "search_type": self.search_type,
            "limit": self.limit,
            "origin": self.origin,
            "total_posts": self.total_posts,
            "total_comments": self.total_comments,
            "network_results": self.network_results,
            "download_url": f"/api/download/{self.file_name}" if self.file_name else None,
            "file_name": self.file_name,
            "saved_folder": friendly_path(self.saved_path),
            "error": self.error,
            "progress": {"done": self.steps_done, "total": self.steps_total},
            "created_at": self.created_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }
        if include_logs:
            data["logs"] = [entry["msg"] for entry in self.logs]
        return data


class JobManager:
    def __init__(self):
        self.jobs: Dict[str, ScrapeJob] = {}
        self._semaphore: Optional[asyncio.Semaphore] = None

    @property
    def semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)
        return self._semaphore

    def create(self, **kwargs) -> ScrapeJob:
        job = ScrapeJob(**kwargs)
        if job.search_type == "url":
            job.steps_total = len(job.keywords)
        else:
            job.steps_total = len(job.networks) * len(job.keywords)
        self.jobs[job.job_id] = job
        self._prune()
        return job

    def get(self, job_id: str) -> Optional[ScrapeJob]:
        return self.jobs.get(job_id)

    def active(self) -> List[ScrapeJob]:
        return [j for j in self.jobs.values() if not j.finished]

    def is_run_active(self, run_id: str) -> bool:
        return any(j.run_id == run_id for j in self.active())

    def active_comments_job(self, run_id: str) -> Optional[ScrapeJob]:
        return next((j for j in self.active() if j.kind == "comments" and j.run_id == run_id), None)

    def active_enrich_job(self, run_id: str) -> Optional[ScrapeJob]:
        return next((j for j in self.active() if j.kind == "enrich" and j.run_id == run_id), None)

    def _prune(self, keep: int = 60):
        finished = sorted((j for j in self.jobs.values() if j.finished), key=lambda j: j.created_at)
        for job in finished[:-keep] if len(finished) > keep else []:
            self.jobs.pop(job.job_id, None)


jobs = JobManager()


# --------------------------------------------------------------------------- pipeline
def _record_log(job: ScrapeJob, message: str) -> None:
    job.logs.append({"t": time.time(), "msg": message})
    if len(job.logs) > JOB_LOG_HISTORY:
        del job.logs[: len(job.logs) - JOB_LOG_HISTORY]


def _wire(job: ScrapeJob, message: str) -> str:
    # Logs da coleta de comentários vão para o painel do dashboard, não para o console da extração
    return f"[CLOG] {message}" if job.kind == "comments" else message


async def _emit(job: ScrapeJob, message: str) -> None:
    _record_log(job, message)
    logger.info("[%s] %s", job.job_id, message)
    await manager.send_personal_message(_wire(job, message), job.client_id)


async def _emit_state(job: ScrapeJob) -> None:
    await manager.send_personal_message("[JOB] " + json.dumps(job.to_dict()), job.client_id)


def _postprocess(df: pd.DataFrame, keyword: str) -> pd.DataFrame:
    df = df.copy()
    df["Palavra-Chave"] = keyword

    def fix_author(row):
        author = clean_author(row.get("Autor", ""))
        if is_generic_author(author):
            author = infer_author_from_text(row.get("Texto", "")) or author or "@perfil_instagram"
        return author

    df["Autor"] = df.apply(fix_author, axis=1)
    df["Termo Específico"] = df["Termo Específico"].fillna("").replace("", "Geral")
    for col in ("Curtidas", "Comentarios", "Views", "Compartilhamentos"):
        df[col] = df[col].map(parse_numeric_metric)

    def sanitize_row(row):
        v = row.get("Views")
        l = row.get("Curtidas")
        c = row.get("Comentarios")
        s = row.get("Compartilhamentos") or 0
        status_base = row.get("metrics_status") or "coletado"
        sm = sanitizar_metricas_ebm(views=v, likes=l, comments=c, shares=s, status_base=status_base)
        return pd.Series({
            "Views": sm["views"],
            "Curtidas": sm["likes"] or 0,
            "Comentarios": sm["comments"] or 0,
            "Compartilhamentos": sm["shares"] or 0,
            "metrics_status": sm["status"],
        })

    if not df.empty:
        cleaned_metrics = df.apply(sanitize_row, axis=1)
        for c in ("Views", "Curtidas", "Comentarios", "Compartilhamentos", "metrics_status"):
            df[c] = cleaned_metrics[c]

    return df


def _persist_posts(run_id: str, df: pd.DataFrame, network: str, keyword: str) -> int:
    with session_scope() as db:
        db.add_all([
            ScrapedPost(
                run_id=run_id,
                network=str(row.get("Rede") or network),
                keyword=keyword,
                specific_term=str(row.get("Termo Específico") or keyword),
                author=str(row.get("Autor") or ""),
                text=str(row.get("Texto") or ""),
                likes=str(int(row.get("Curtidas") or 0)),
                comments=str(int(row.get("Comentarios") or 0)),
                views=str(int(row.get("Views") or 0)) if row.get("Views") is not None and not (isinstance(row.get("Views"), float) and pd.isna(row.get("Views"))) else "",
                shares=str(int(row.get("Compartilhamentos") or 0)),
                link=str(row.get("Link") or ""),
                post_date=str(row.get("Data") or ""),
                metrics_status=str(row.get("metrics_status") or "coletado"),
                accessibility_caption=str(row.get("accessibility_caption") or ""),
            )
            for row in df.to_dict(orient="records")
        ])
    return len(df)


def _excel_filename(job: ScrapeJob) -> str:
    name = build_report_filename(job.keywords, "xlsx", job.created_at, job.search_type, job.origin)
    return unique_filename(DOWNLOADS_DIR, name)


def _upsert_run(job: ScrapeJob) -> None:
    with session_scope() as db:
        run = db.get(ScrapeRun, job.run_id) or ScrapeRun(run_id=job.run_id, started_at=job.created_at)
        run.query = " | ".join(job.keywords)
        run.networks = ",".join(job.networks)
        run.search_type = job.search_type
        run.max_posts = job.limit
        run.start_date = job.start_date or ""
        run.end_date = job.end_date or ""
        run.origin = job.origin
        run.status = job.status
        run.total_posts = job.total_posts
        run.file_name = job.file_name or ""
        run.error = job.error or ""
        run.finished_at = job.finished_at
        db.merge(run)


def mark_interrupted_runs() -> None:
    """Runs que ficaram 'running' após um desligamento abrupto do servidor."""
    with session_scope() as db:
        for run in db.query(ScrapeRun).filter(ScrapeRun.status.in_(["running", "queued"])).all():
            run.status = "error"
            run.error = "Extração interrompida (servidor reiniciado)."
            run.finished_at = run.finished_at or datetime.now()


async def run_scrape_job(job: ScrapeJob) -> ScrapeJob:
    loop = asyncio.get_running_loop()

    def notify_progress(message: str) -> None:
        _record_log(job, message)
        try:
            asyncio.run_coroutine_threadsafe(manager.send_personal_message(message, job.client_id), loop)
        except Exception:
            pass

    if jobs.semaphore.locked():
        await _emit(job, "[INFO] Aguardando outra extração terminar para iniciar...")
    async with jobs.semaphore:
        job.status = "running"
        try:
            await asyncio.to_thread(_upsert_run, job)
            await _emit_state(job)
            await _emit(job, f"[START] Iniciando extração para: {', '.join(job.keywords)} nas redes "
                             f"{', '.join(n.upper() for n in job.networks)}")
            brand_handles = await asyncio.to_thread(load_brand_handles) if job.search_type == "profile" else {}
            frames = []

            if job.search_type == "url":
                target_network = job.networks[0] if job.networks and job.networks[0] != "auto" else None
                await _emit(job, f"[START] Iniciando extração de {len(job.keywords)} publicações específicas por link...")
                started = time.monotonic()
                try:
                    df, posts, comments = await asyncio.to_thread(
                        scrape_posts_by_urls,
                        urls=job.keywords,
                        network=target_network,
                        progress_callback=notify_progress,
                        cancel_event=job.cancel_event,
                    )
                except Exception as exc:
                    logger.exception("Falha na extração de posts específicos")
                    await _emit(job, f"[ERROR] Falha na extração por URL: {str(exc).splitlines()[0]}")
                    df, posts, comments = pd.DataFrame(), 0, 0

                job.steps_done = len(job.keywords)
                if not df.empty:
                    df = await asyncio.to_thread(_postprocess, df, "Post Específico")
                    await asyncio.to_thread(_persist_posts, job.run_id, df, target_network or "Social", "Post Específico")
                    frames.append(df)
                    job.total_posts += posts
                    job.total_comments += comments
                    for _, row in df.iterrows():
                        net_val = str(row.get("Rede", "")).lower()
                        job.network_results[net_val] = job.network_results.get(net_val, 0) + 1
                    await _emit(job, f"[SUCCESS] Extraídas {posts} publicações com sucesso em {time.monotonic() - started:.0f}s.")
                elif not job.cancel_event.is_set():
                    await _emit(job, "[WARN] Nenhuma publicação pôde ser extraída a partir dos links informados.")
                await _emit_state(job)
            else:
                for network in job.networks:
                    for keyword in job.keywords:
                        if job.cancel_event.is_set():
                            break
                        await _emit(job, f"[INFO] Configurando motor de busca para '{keyword}' na rede {network.upper()}...")
                        started = time.monotonic()
                        try:
                            df, posts, comments = await asyncio.to_thread(
                                scrape_network,
                                network=network, keyword=keyword, limit=job.limit, scrape_comments=False,
                                start_date=job.start_date, end_date=job.end_date, search_type=job.search_type,
                                progress_callback=notify_progress, cancel_event=job.cancel_event, brand_handles=brand_handles,
                            )
                        except Exception as exc:
                            logger.exception("Falha em %s/%s", network, keyword)
                            await _emit(job, f"[ERROR] {network.upper()}: falha na extração de '{keyword}': {str(exc).splitlines()[0]}")
                            df, posts, comments = pd.DataFrame(), 0, 0

                        job.steps_done += 1
                        if not df.empty:
                            df = await asyncio.to_thread(_postprocess, df, keyword)
                            await asyncio.to_thread(_persist_posts, job.run_id, df, network, keyword)
                            frames.append(df)
                            job.total_posts += posts
                            job.total_comments += comments
                            job.network_results[network] = job.network_results.get(network, 0) + posts
                            await _emit(job, f"[SUCCESS] {network.upper()}: Extraídos {posts} posts para '{keyword}' "
                                             f"em {time.monotonic() - started:.0f}s.")
                        elif not job.cancel_event.is_set():
                            await _emit(job, f"[WARN] {network.upper()}: Nenhum resultado encontrado para '{keyword}'.")
                        await _emit_state(job)
                    if job.cancel_event.is_set():
                        break

            if job.scrape_comments and frames and not job.cancel_event.is_set():
                await _emit(job, f"[INFO] Coletando comentários das publicações extraídas (até {job.max_comments} por post)...")
                posts_by_network = {}
                with session_scope() as db:
                    db_posts = db.query(ScrapedPost).filter(ScrapedPost.run_id == job.run_id).all()
                    for p in db_posts:
                        p_dict = {
                            "id": p.id,
                            "link": p.link,
                            "network": p.network,
                            "author": p.author,
                            "comments": p.comments,
                        }
                        net_key = p.network.lower()
                        if "instagram" in net_key:
                            net_key = "instagram"
                        elif "tiktok" in net_key:
                            net_key = "tiktok"
                        elif "youtube" in net_key:
                            net_key = "youtube"
                        elif "facebook" in net_key:
                            net_key = "facebook"
                        else:
                            net_key = "x"
                        posts_by_network.setdefault(net_key, []).append(p_dict)

                for net, posts_list in posts_by_network.items():
                    if job.cancel_event.is_set():
                        break
                    def on_result(post, status, items, message, net=net):
                        _save_comments_with_retry(post["id"], job.run_id, net, items, status, message)
                        job.total_comments += len(items)
                    def comment_log(msg, level="INFO"):
                        notify_progress(f"[{level}] {msg}")
                    try:
                        await asyncio.to_thread(collect_network_comments, net, posts_list, job.max_comments, on_result, comment_log, job.cancel_event)
                    except Exception as exc:
                        logger.exception("Falha na coleta de comentários")
                        await _emit(job, f"[WARN] Falha ao coletar comentários de {net}: {exc}")

            if frames and not job.cancel_event.is_set() and (job.enrich_media or job.generate_contact_sheet or job.transcribe_audio or job.detect_scenes):
                await _emit(job, "[INFO] Processando enriquecimento multimídia (mídias, folhas de contato e transcrições)...")
                with session_scope() as db:
                    run_post_ids = [p.id for p in db.query(ScrapedPost.id).filter(ScrapedPost.run_id == job.run_id).all()]
                for idx, pid in enumerate(run_post_ids, start=1):
                    if job.cancel_event.is_set():
                        break
                    await asyncio.to_thread(
                        process_multimedia_enrichment_for_post,
                        post_id=pid,
                        enrich_media=job.enrich_media,
                        generate_contact_sheet=job.generate_contact_sheet,
                        transcribe_audio=job.transcribe_audio,
                        detect_scenes=job.detect_scenes,
                        progress_callback=notify_progress,
                    )
                    await _emit(job, f"[MEDIA] Enriquecido post {idx}/{len(run_post_ids)}")

            if frames:
                await _emit(job, "[INFO] Gerando planilha Excel executiva...")
                import analytics
                with session_scope() as db:
                    final_df = analytics.run_dataframe(db, job.run_id)
                if final_df.empty:
                    final_df = pd.concat(frames, ignore_index=True)
                    final_df = final_df[[c for c in EXCEL_COLUMNS if c in final_df.columns]]
                file_name = _excel_filename(job)
                file_path = os.path.join(DOWNLOADS_DIR, file_name)
                await asyncio.to_thread(build_executive_workbook, final_df, file_path, " ".join(job.keywords))
                job.file_name = file_name
                job.saved_path = await asyncio.to_thread(archive_copy, file_path, job.created_at)
                if job.saved_path:
                    await _emit(job, f"[INFO] Planilha salva em: {friendly_path(job.saved_path)}")

            if job.cancel_event.is_set():
                job.status = "cancelled"
                await _emit(job, f"[WARN] Extração cancelada. {job.total_posts} posts coletados até o momento foram salvos.")
            else:
                job.status = "done"
                await _emit(job, f"[DONE] Extração concluída! Total de {job.total_posts} posts agregados.")
        except Exception as exc:
            logger.exception("Job %s falhou", job.job_id)
            job.status = "error"
            job.error = str(exc)
            await _emit(job, f"[ERROR] Falha crítica durante a extração: {exc}")
        finally:
            job.finished_at = datetime.now()
            try:
                await asyncio.to_thread(_upsert_run, job)
            except Exception:
                logger.exception("Não foi possível atualizar o registro da extração %s", job.run_id)
            await _emit_state(job)
    return job


COMMENT_STATUS_LABELS = {"done": "concluída", "empty": "sem comentários", "disabled": "comentários desativados",
                         "partial": "parcial", "error": "falha", "login": "sessão necessária"}


def _save_comments_with_retry(post_id: int, run_id: str, network: str, items: list, status: str, message: str) -> bool:
    """Grava o resultado de um post; tenta de novo se o banco estiver ocupado. Nunca derruba a coleta."""
    for attempt in range(4):
        try:
            save_post_comments(post_id, run_id, network, items, status, message)
            return True
        except Exception:
            logger.exception("Falha ao gravar comentários do post %s (tentativa %s)", post_id, attempt + 1)
            time.sleep(1.5 * (attempt + 1))
    return False


async def run_comments_job(job: ScrapeJob, posts_by_network: Dict[str, List[dict]]) -> ScrapeJob:
    loop = asyncio.get_running_loop()

    def push(message: str) -> None:
        _record_log(job, message)
        try:
            asyncio.run_coroutine_threadsafe(manager.send_personal_message(_wire(job, message), job.client_id), loop)
        except Exception:
            pass

    def push_state() -> None:
        try:
            asyncio.run_coroutine_threadsafe(_emit_state(job), loop)
        except Exception:
            pass

    if jobs.semaphore.locked():
        await _emit(job, "[INFO] Aguardando outra extração terminar para iniciar...")
    async with jobs.semaphore:
        job.status = "running"
        try:
            await _emit_state(job)
            nets = ", ".join(DISPLAY_NAMES.get(n, n) for n in posts_by_network)
            await _emit(job, f"[START] Coletando comentários de {job.steps_total} publicações ({nets}) — "
                             f"até {job.max_comments} por publicação.")
            for network, posts in posts_by_network.items():
                if job.cancel_event.is_set():
                    break
                name = DISPLAY_NAMES.get(network, network)

                def on_result(post, status, items, message, network=network, name=name):
                    saved = _save_comments_with_retry(post["id"], job.run_id, network, items, status, message)
                    job.steps_done += 1
                    if not saved:
                        status, message = "error", "não foi possível gravar no banco (tente novamente)"
                    else:
                        job.total_comments += len(items)
                        job.network_results[network] = job.network_results.get(network, 0) + len(items)
                    job.comment_stats[status] = job.comment_stats.get(status, 0) + 1
                    push_state()
                    if status == "login" or message.startswith("Coleta interrompida"):
                        return  # o coletor já registrou um aviso único para a rede inteira
                    level = "WARN" if status in ("error", "partial") else "INFO"
                    detail = f" — {message}" if message else ""
                    push(f"[{level}] {name} {job.steps_done}/{job.steps_total}: {len(items)} comentários "
                         f"({COMMENT_STATUS_LABELS.get(status, status)}) • {short_link(post['link'])}{detail}")

                def log(message, level="INFO"):
                    push(f"[{level}] {message}")

                await _emit(job, f"[INFO] {name}: abrindo navegador para {len(posts)} publicações...")
                try:
                    await asyncio.to_thread(collect_network_comments, network, posts, job.max_comments, on_result, log,
                                            job.cancel_event)
                except Exception as exc:  # proteção final: uma rede com problema não interrompe as outras
                    logger.exception("Coleta de comentários falhou em %s", network)
                    await _emit(job, f"[ERROR] {name}: coleta interrompida ({str(exc).splitlines()[0][:160]}). "
                                     f"As publicações não processadas continuam pendentes.")

            stats = ", ".join(f"{v} {COMMENT_STATUS_LABELS.get(k, k)}" for k, v in job.comment_stats.items())
            if job.cancel_event.is_set():
                job.status = "cancelled"
                await _emit(job, f"[WARN] Coleta cancelada. {job.total_comments} comentários salvos; "
                                 f"as publicações restantes continuam pendentes.")
            else:
                job.status = "done"
                await _emit(job, f"[DONE] Coleta de comentários concluída: {job.total_comments} comentários"
                                 f"{' (' + stats + ')' if stats else ''}.")
        except Exception as exc:
            logger.exception("Job de comentários %s falhou", job.job_id)
            job.status = "error"
            job.error = str(exc)
            await _emit(job, f"[ERROR] Falha na coleta de comentários: {exc}. O que já foi coletado está salvo.")
        finally:
            job.finished_at = datetime.now()
            await _emit_state(job)
    return job


def process_multimedia_enrichment_for_post(
    post_id: int,
    enrich_media: bool = True,
    generate_contact_sheet: bool = True,
    transcribe_audio: bool = True,
    detect_scenes: bool = False,
    progress_callback = None,
) -> dict:
    """
    Enriquece um post com mídias baixadas, folha de contato 4x4, detecção de cortes de cena e transcrição fonética local.
    Zero tokens de IA pagos. 100% determinístico e auditável.
    """
    with session_scope() as db:
        post = db.get(ScrapedPost, post_id)
        if not post:
            return {"status": "error", "error": f"Post {post_id} não encontrado"}
        url = post.link or ""
        media_type = post.media_type or ""
        media_paths_raw = post.media_paths or ""
        sheet_path = post.contact_sheet_path or ""
        scenes_cnt = post.scenes_detected or 0
        transcript_text = post.transcription_text or ""
        transcript_status = post.transcription_status or ""
        transcript_json = post.transcription_json or ""
        caption = post.accessibility_caption or ""

    if not url:
        return {"status": "skipped", "message": "Sem link associado ao post"}

    media_paths = []
    if media_paths_raw:
        try:
            media_paths = json.loads(media_paths_raw) if isinstance(media_paths_raw, str) else list(media_paths_raw)
        except Exception:
            media_paths = []
    media_paths = [p for p in media_paths if os.path.isfile(p)]

    # 1. Download de mídias se necessário
    if not media_paths and (enrich_media or generate_contact_sheet or transcribe_audio or detect_scenes):
        if progress_callback:
            progress_callback(f"[MEDIA] Baixando mídia para post {post_id} ({short_link(url)})...")
        try:
            downloaded = media_service.baixar_midia_hibrida(url, pasta_destino=VIDEOS_DIR, prefixo=f"post_{post_id}")
            if downloaded:
                media_paths = downloaded
                media_type = "video"
            else:
                carrossel = media_service.baixar_imagens_carrossel(url, pasta_destino=os.path.join(MEDIA_DIR, "carrossel"), prefixo=f"post_{post_id}")
                if carrossel:
                    media_paths = [c["arquivo"] for c in carrossel]
                    media_type = "carrossel"
                    alts = [c["alt"] for c in carrossel if c.get("alt")]
                    if alts and not caption:
                        caption = " | ".join(alts)
                else:
                    media_type = "desconhecido"
        except Exception as exc:
            logger.warning("Falha ao baixar mídia para post %s: %s", post_id, exc)

    # 2. Folha de contato, cortes de cena e transcrição para vídeos
    video_file = next((p for p in media_paths if p.lower().endswith((".mp4", ".mkv", ".webm", ".avi", ".mov"))), None)

    if video_file:
        media_type = "video"
        if generate_contact_sheet and (not sheet_path or not os.path.isfile(sheet_path)):
            if progress_callback:
                progress_callback(f"[FFMPEG] Gerando folha de contato 4x4 para post {post_id}...")
            sheet_dest = os.path.join(CONTACT_SHEETS_DIR, f"contact_{post_id}.jpg")
            res_sheet = video_service.gerar_folha_contato_4x4(video_file, sheet_dest)
            if res_sheet and os.path.isfile(res_sheet):
                sheet_path = res_sheet

        if detect_scenes and not scenes_cnt:
            if progress_callback:
                progress_callback(f"[FFMPEG] Detectando cortes de cena para post {post_id}...")
            cortes = video_service.detectar_cortes_de_cena(video_file)
            scenes_cnt = len(cortes)

        if transcribe_audio and (not transcript_text or transcript_status in ("pending", "failed", "")):
            if progress_callback:
                progress_callback(f"[WHISPER] Verificando áudio via ffprobe para post {post_id}...")
            if transcription_service.tem_audio(video_file):
                if progress_callback:
                    progress_callback(f"[WHISPER] Transcrevendo áudio para post {post_id}...")
                t_res = transcription_service.transcrever_audio_local(video_file)
                transcript_text = t_res.get("texto", "")
                transcript_status = t_res.get("status", "done")
                transcript_json = json.dumps(t_res.get("segmentos", []), ensure_ascii=False)
            else:
                transcript_status = "no_audio"
                transcript_text = ""
                transcript_json = "[]"

    # 3. Persistir de volta no banco
    with session_scope() as db:
        p = db.get(ScrapedPost, post_id)
        if p:
            if media_type:
                p.media_type = media_type
            if media_paths:
                p.media_paths = json.dumps(media_paths, ensure_ascii=False)
            if sheet_path:
                p.contact_sheet_path = sheet_path
            if detect_scenes:
                p.scenes_detected = scenes_cnt
            if transcribe_audio:
                p.transcription_status = transcript_status
                p.transcription_text = transcript_text
                p.transcription_json = transcript_json
            if caption:
                p.accessibility_caption = caption

    return {
        "status": "success",
        "post_id": post_id,
        "media_type": media_type,
        "media_paths": media_paths,
        "contact_sheet_path": sheet_path,
        "scenes_detected": scenes_cnt,
        "transcription_status": transcript_status,
        "transcription_text": transcript_text[:120] if transcript_text else "",
        "accessibility_caption": caption[:120] if caption else "",
    }


async def run_enrich_job(job: ScrapeJob) -> ScrapeJob:
    """Executa job de enriquecimento multimídia em lote para uma extração inteira."""
    loop = asyncio.get_running_loop()

    def notify_progress(message: str) -> None:
        _record_log(job, message)
        try:
            asyncio.run_coroutine_threadsafe(manager.send_personal_message(message, job.client_id), loop)
        except Exception:
            pass

    async with jobs.semaphore:
        job.status = "running"
        try:
            await _emit_state(job)
            await _emit(job, f"[START] Iniciando enriquecimento multimídia da extração {job.run_id}...")

            with session_scope() as db:
                posts = db.query(ScrapedPost).filter(ScrapedPost.run_id == job.run_id).all()
                post_ids = [p.id for p in posts]

            job.steps_total = len(post_ids)
            for idx, pid in enumerate(post_ids, start=1):
                if job.cancel_event.is_set():
                    break
                await asyncio.to_thread(
                    process_multimedia_enrichment_for_post,
                    post_id=pid,
                    enrich_media=job.enrich_media,
                    generate_contact_sheet=job.generate_contact_sheet,
                    transcribe_audio=job.transcribe_audio,
                    detect_scenes=job.detect_scenes,
                    progress_callback=notify_progress,
                )
                job.steps_done = idx
                await _emit_state(job)
                await _emit(job, f"[INFO] Post {idx}/{len(post_ids)} enriquecido com sucesso.")

            if job.cancel_event.is_set():
                job.status = "cancelled"
                await _emit(job, "[WARN] Enriquecimento multimídia cancelado pelo usuário.")
            else:
                job.status = "done"
                await _emit(job, f"[DONE] Enriquecimento concluído para {job.steps_done} publicações.")
        except Exception as exc:
            logger.exception("Job de enriquecimento %s falhou", job.job_id)
            job.status = "error"
            job.error = str(exc)
            await _emit(job, f"[ERROR] Falha no enriquecimento multimídia: {exc}")
        finally:
            job.finished_at = datetime.now()
            await _emit_state(job)
    return job


_background_tasks = set()


def spawn_background(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)  # mantém referência forte até o término
    task.add_done_callback(_background_tasks.discard)
    return task


def start_job_in_background(job: ScrapeJob) -> asyncio.Task:
    return spawn_background(run_scrape_job(job))
