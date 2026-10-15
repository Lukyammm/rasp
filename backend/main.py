"""
RASP — API FastAPI (Social Listening, Web Scraping e BI da EBM Quintto).

Endpoints principais:
  POST /api/scrape                 inicia uma extração em segundo plano (logs via /ws/scrape/{client_id})
  GET  /api/jobs/{job_id}          status e logs de uma extração;  POST /api/jobs/{job_id}/cancel
  GET  /api/dashboard              dados analíticos de uma extração
  GET  /api/history/runs           histórico;  DELETE /api/history/runs/{run_id}
  GET  /api/export/excel | /api/report/pdf | /api/download/{arquivo}
  /api/accounts, /api/brands, /api/schedules
"""
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from config import (ALLOWED_ORIGINS, CONTACT_SHEETS_DIR, DOWNLOADS_DIR, FRAMES_DIR, FRONTEND_DIR,
                    LOGOS_DIR, MAX_LIMIT_PER_NETWORK, MEDIA_DIR, NETWORKS, VIDEOS_DIR, setup_logging)

setup_logging()

import analytics  # noqa: E402
import brand_logo_service  # noqa: E402
import comments_service  # noqa: E402
import scheduler_service  # noqa: E402
from database import Brand, Schedule, ScrapedPost, ScrapeRun, get_db, init_db  # noqa: E402
from excel_builder import build_executive_workbook  # noqa: E402
from exports import archive_copy  # noqa: E402
from jobs import (jobs, manager, mark_interrupted_runs, process_multimedia_enrichment_for_post,
                  run_comments_job, run_enrich_job, run_scrape_job, spawn_background,
                  start_job_in_background)
from pdf_generator import generate_pdf_report  # noqa: E402
from scrapers.login_manager import check_accounts, interactive_login  # noqa: E402
from utils import build_report_filename, unique_filename  # noqa: E402

logger = logging.getLogger("rasp.api")
APP_VERSION = "2.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    mark_interrupted_runs()
    scheduler_service.start()
    logger.info("RASP API %s iniciada.", APP_VERSION)
    yield
    for job in jobs.active():
        job.cancel_event.set()
    scheduler_service.shutdown()


app = FastAPI(title="RASP Analytics API", version=APP_VERSION, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def no_cache_frontend(request, call_next):
    """A interface (HTML/JS) é sempre revalidada pelo navegador, evitando rodar uma versão antiga em cache."""
    response = await call_next(request)
    if not request.url.path.startswith(("/api/", "/ws/")):
        response.headers["Cache-Control"] = "no-cache"
    return response


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# --------------------------------------------------------------------------- modelos
def _clean_networks(values: List[str]) -> List[str]:
    cleaned = []
    for v in values or []:
        n = str(v).strip().lower()
        n = "x" if n in ("twitter", "x (twitter)") else n
        if (n in NETWORKS or n == "auto") and n not in cleaned:
            cleaned.append(n)
    if not cleaned:
        raise ValueError(f"Selecione ao menos uma rede válida: {', '.join(NETWORKS)}")
    return cleaned


def _clean_keywords(values: List[str]) -> List[str]:
    cleaned = [" ".join(str(k).split()) for k in values or [] if str(k).strip()]
    if not cleaned:
        raise ValueError("Informe ao menos um termo de busca ou link.")
    if len(cleaned) > 50:
        raise ValueError("Máximo de 50 termos ou links por extração.")
    return cleaned


class ScrapeRequest(BaseModel):
    client_id: str = Field(default="", max_length=100)
    keywords: List[str]
    networks: List[str]
    search_type: Literal["keyword", "profile", "url"] = "keyword"
    limit: int = Field(default=50, ge=1, le=MAX_LIMIT_PER_NETWORK)
    scrape_comments: bool = False
    max_comments: int = Field(default=100, ge=1, le=1000)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    wait: bool = False  # True = aguarda o término e retorna o resultado final (compatibilidade com scripts)
    enrich_media: bool = False
    generate_contact_sheet: bool = False
    transcribe_audio: bool = False
    detect_scenes: bool = False

    @field_validator("networks")
    @classmethod
    def _networks(cls, v):
        return _clean_networks(v)

    @field_validator("keywords")
    @classmethod
    def _keywords(cls, v):
        return _clean_keywords(v)

    @field_validator("start_date", "end_date")
    @classmethod
    def _date(cls, v):
        if v in (None, ""):
            return None
        if not DATE_RE.match(v):
            raise ValueError("Datas devem estar no formato AAAA-MM-DD.")
        return v

    @model_validator(mode="after")
    def _range(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("A data inicial não pode ser posterior à data final.")
        return self


class CommentsRequest(BaseModel):
    client_id: str = Field(default="", max_length=100)
    run_id: str = Field(min_length=1, max_length=100)
    post_ids: Optional[List[int]] = Field(default=None, max_length=5000)
    networks: Optional[List[str]] = None
    max_per_post: int = Field(default=100, ge=1, le=1000)
    max_posts: Optional[int] = Field(default=None, ge=1, le=50000)
    mode: Literal["pending", "all"] = "pending"
    skip_zero: bool = True

    @field_validator("networks")
    @classmethod
    def _networks(cls, v):
        return _clean_networks(v) if v else None


class BrandRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    x: str = ""
    tiktok: str = ""
    instagram: str = ""
    youtube: str = ""
    facebook: str = ""
    logo_svg: Optional[str] = None
    color: Optional[str] = None


class BrandLogoRequest(BaseModel):
    svg: str = Field(min_length=10)
    color: Optional[str] = None


class EnrichRequest(BaseModel):
    client_id: str = Field(default="", max_length=100)
    enrich_media: bool = True
    generate_contact_sheet: bool = True
    transcribe_audio: bool = True
    detect_scenes: bool = False


class ScheduleRequest(BaseModel):
    keywords: List[str]
    networks: List[str] = Field(default_factory=lambda: ["x", "instagram", "tiktok"])
    network: Optional[str] = None  # compatibilidade: rede única
    search_type: Literal["keyword", "profile"] = "keyword"
    cron: str
    limit: int = Field(default=50, ge=1, le=MAX_LIMIT_PER_NETWORK)

    @field_validator("keywords")
    @classmethod
    def _keywords(cls, v):
        return _clean_keywords(v)

    @model_validator(mode="after")
    def _merge_network(self):
        self.networks = _clean_networks(self.networks + ([self.network] if self.network else []))
        return self


class ScheduleUpdate(BaseModel):
    status: Literal["active", "paused"]


# --------------------------------------------------------------------------- sistema
@app.get("/api/health")
def health():
    return {"status": "ok", "version": APP_VERSION, "active_jobs": len(jobs.active()),
            "scheduler": scheduler_service.available()}


@app.get("/api/accounts")
def get_accounts_status():
    return check_accounts()


@app.post("/api/accounts/{network}/login")
def do_interactive_login(network: str):
    if network not in NETWORKS:
        raise HTTPException(status_code=404, detail="Rede não suportada.")
    try:
        return interactive_login(network)
    except Exception as exc:
        logger.exception("Falha ao abrir login de %s", network)
        raise HTTPException(status_code=500, detail=str(exc))


@app.websocket("/ws/scrape/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, client_id)


# --------------------------------------------------------------------------- extração
@app.post("/api/scrape")
async def start_scraping(request: ScrapeRequest):
    job = jobs.create(
        keywords=request.keywords, networks=request.networks, search_type=request.search_type, limit=request.limit,
        scrape_comments=request.scrape_comments, max_comments=request.max_comments,
        start_date=request.start_date, end_date=request.end_date, client_id=request.client_id or None,
        enrich_media=request.enrich_media, generate_contact_sheet=request.generate_contact_sheet,
        transcribe_audio=request.transcribe_audio, detect_scenes=request.detect_scenes,
    )
    if request.wait:
        await run_scrape_job(job)
        if job.status == "error":
            raise HTTPException(status_code=500, detail=job.error or "Erro interno na extração.")
        return {"status": "success", "data": job.to_dict()}
    start_job_in_background(job)
    return {"status": "started", "data": job.to_dict()}


@app.get("/api/jobs")
def list_jobs(active: bool = False):
    items = jobs.active() if active else list(jobs.jobs.values())
    return {"jobs": [j.to_dict() for j in sorted(items, key=lambda j: j.created_at, reverse=True)]}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str, logs: bool = True):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Extração não encontrada (o servidor pode ter sido reiniciado).")
    return job.to_dict(include_logs=logs)


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Extração não encontrada.")
    if not job.finished:
        job.cancel_event.set()
    return {"status": "success", "data": job.to_dict()}


# --------------------------------------------------------------------------- arquivos
def _safe_download_path(filename: str) -> str:
    name = os.path.basename(filename or "")
    path = os.path.realpath(os.path.join(DOWNLOADS_DIR, name))
    if not name or not path.startswith(os.path.realpath(DOWNLOADS_DIR) + os.sep) or not name.lower().endswith((".xlsx", ".pdf")):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return path


MEDIA_TYPES = {".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".pdf": "application/pdf"}


@app.get("/api/download/{filename}")
def download_file(filename: str):
    path = _safe_download_path(filename)
    return FileResponse(path=path, filename=os.path.basename(path), media_type=MEDIA_TYPES[os.path.splitext(path)[1].lower()])


@app.get("/api/media/{filename}")
def get_media_file(filename: str):
    name = os.path.basename(filename or "")
    if not name or ".." in filename:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido.")

    target = None
    for folder in (MEDIA_DIR, CONTACT_SHEETS_DIR, VIDEOS_DIR, FRAMES_DIR, LOGOS_DIR, os.path.join(MEDIA_DIR, "carrossel")):
        cand = os.path.join(folder, name)
        if os.path.isfile(cand):
            target = cand
            break

    if not target:
        raise HTTPException(status_code=404, detail="Mídia não encontrada.")

    ext = os.path.splitext(target)[1].lower()
    media_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mkv": "video/x-matroska",
    }
    return FileResponse(path=target, media_type=media_map.get(ext, "application/octet-stream"))


def _resolve_run(db: Session, run_id: Optional[str]) -> str:
    run_id = run_id or analytics.latest_run_id(db)
    if not run_id:
        raise HTTPException(status_code=404, detail="Nenhuma extração encontrada.")
    return run_id


def _run_report_filename(db: Session, run_id: str, extension: str) -> str:
    """Mesmo padrão das planilhas das extrações: RASP_Debate-Ciro-Elmano_2026-09-12_20h07.xlsx"""
    run = db.get(ScrapeRun, run_id)
    if run:
        return build_report_filename(run.query.split(" | "), extension, run.started_at, run.search_type, run.origin)
    keywords = [k for (k,) in db.query(ScrapedPost.keyword).filter(ScrapedPost.run_id == run_id).distinct().all() if k]
    first_seen = db.query(func.min(ScrapedPost.scraped_at)).filter(ScrapedPost.run_id == run_id).scalar()
    origin = "agendamento" if run_id.startswith("cron_") else "manual"
    return build_report_filename(keywords, extension, analytics.run_started_at(run_id, first_seen), origin=origin)


def _write_report(filename: str, writer, when: Optional[datetime] = None) -> str:
    """Gera o arquivo (nome alternativo se estiver bloqueado) e guarda uma cópia na pasta do mês da Área de Trabalho."""
    try:
        path = writer(filename)
    except PermissionError:
        path = writer(unique_filename(DOWNLOADS_DIR, filename))
    archive_copy(path, when)
    return path


def _run_started(db: Session, run_id: str) -> Optional[datetime]:
    run = db.get(ScrapeRun, run_id)
    if run and run.started_at:
        return run.started_at
    first_seen = db.query(func.min(ScrapedPost.scraped_at)).filter(ScrapedPost.run_id == run_id).scalar()
    return analytics.run_started_at(run_id, first_seen)


@app.get("/api/export/excel")
def export_excel_report(run_id: Optional[str] = None, db: Session = Depends(get_db)):
    run_id = _resolve_run(db, run_id)
    df = analytics.run_dataframe(db, run_id)
    if df.empty:
        raise HTTPException(status_code=404, detail="Sem dados para exportar Excel.")
    run = db.get(ScrapeRun, run_id)
    title = (run.query if run else "") or str(df["Palavra-Chave"].iloc[0] or f"Execução {run_id}")
    comments = comments_service.excel_rows(db, run_id)
    path = _write_report(_run_report_filename(db, run_id, "xlsx"),
                         lambda name: build_executive_workbook(df, os.path.join(DOWNLOADS_DIR, name), title, comments),
                         _run_started(db, run_id))
    return FileResponse(path=path, filename=os.path.basename(path), media_type=MEDIA_TYPES[".xlsx"])


@app.get("/api/report/pdf")
def export_pdf_report(run_id: Optional[str] = None, db: Session = Depends(get_db)):
    run_id = _resolve_run(db, run_id)
    data = analytics.build_dashboard(db, run_id)
    if not data["feed"]:
        raise HTTPException(status_code=404, detail="Sem dados para gerar o PDF.")
    query = (data.get("run") or {}).get("query", "")
    try:
        path = _write_report(_run_report_filename(db, run_id, "pdf"),
                             lambda name: generate_pdf_report(data, name, query), _run_started(db, run_id))
    except Exception as exc:
        logger.exception("Falha ao gerar PDF")
        raise HTTPException(status_code=500, detail=f"Falha ao gerar PDF: {exc}")
    return FileResponse(path=path, filename=os.path.basename(path), media_type=MEDIA_TYPES[".pdf"])


# --------------------------------------------------------------------------- BI
@app.get("/api/history/runs")
def get_runs_history(db: Session = Depends(get_db)):
    return analytics.runs_history(db)


@app.delete("/api/history/runs/{run_id}")
def delete_run(run_id: str, db: Session = Depends(get_db)):
    if jobs.is_run_active(run_id):
        raise HTTPException(status_code=409, detail="Esta extração ainda está em andamento.")
    comments_service.delete_run_comments(db, run_id)
    deleted = db.query(ScrapedPost).filter(ScrapedPost.run_id == run_id).delete(synchronize_session=False)
    run = db.get(ScrapeRun, run_id)
    if run:
        db.delete(run)
    db.commit()
    if not deleted and not run:
        raise HTTPException(status_code=404, detail="Extração não encontrada.")
    return {"status": "success", "deleted_posts": deleted}


@app.get("/api/dashboard")
def get_dashboard_data(run_id: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        return analytics.build_dashboard(db, run_id)
    except Exception:
        logger.exception("Erro ao compilar dashboard")
        raise HTTPException(status_code=500, detail="Erro ao compilar dados do dashboard.")


# --------------------------------------------------------------------------- comentários
@app.post("/api/comments/scrape")
async def start_comments(request: CommentsRequest, db: Session = Depends(get_db)):
    if not db.query(ScrapedPost.id).filter(ScrapedPost.run_id == request.run_id).first():
        raise HTTPException(status_code=404, detail="Extração não encontrada ou sem publicações.")
    running = jobs.active_comments_job(request.run_id)
    if running:  # evita duas coletas simultâneas da mesma extração; o painel passa a acompanhar a existente
        if request.client_id:
            running.client_id = request.client_id
        return {"status": "already_running", "data": running.to_dict()}
    posts = comments_service.select_posts(db, request.run_id, request.post_ids, request.networks, request.mode,
                                          request.skip_zero, request.max_posts)
    total = sum(len(v) for v in posts.values())
    if not total:
        raise HTTPException(status_code=400, detail="Nenhuma publicação pendente para coletar comentários com esses filtros.")
    job = jobs.create(keywords=[], networks=list(posts), client_id=request.client_id or None, kind="comments",
                      max_comments=request.max_per_post)
    job.run_id = request.run_id
    job.steps_total = total
    spawn_background(run_comments_job(job, posts))
    return {"status": "started", "data": job.to_dict()}


@app.get("/api/comments/summary")
def get_comments_summary(run_id: Optional[str] = None, db: Session = Depends(get_db)):
    run_id = _resolve_run(db, run_id)
    data = comments_service.summary(db, run_id)
    active = jobs.active_comments_job(run_id)
    data["active_job"] = active.to_dict() if active else None
    return data


@app.get("/api/comments")
def get_comments(run_id: Optional[str] = None, post_id: Optional[int] = None, network: Optional[str] = None,
                 q: str = "", limit: int = 200, offset: int = 0, db: Session = Depends(get_db)):
    run_id = _resolve_run(db, run_id)
    return comments_service.list_comments(db, run_id, post_id, network, q[:200], limit, offset)


# --------------------------------------------------------------------------- enriquecimento multimídia
@app.get("/api/posts/{post_id}")
def get_single_post(post_id: int, db: Session = Depends(get_db)):
    post = db.get(ScrapedPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Publicação não encontrada.")
    return {"status": "success", "data": analytics.normalize_post(post)}


@app.post("/api/posts/{post_id}/enrich")
async def enrich_single_post(post_id: int, request: EnrichRequest, db: Session = Depends(get_db)):
    post = db.get(ScrapedPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Publicação não encontrada.")
    result = await asyncio.to_thread(
        process_multimedia_enrichment_for_post,
        post_id=post_id,
        enrich_media=request.enrich_media,
        generate_contact_sheet=request.generate_contact_sheet,
        transcribe_audio=request.transcribe_audio,
        detect_scenes=request.detect_scenes,
    )
    return {"status": "success", "data": result}


@app.post("/api/runs/{run_id}/enrich")
async def enrich_run_posts(run_id: str, request: EnrichRequest, db: Session = Depends(get_db)):
    run_id = _resolve_run(db, run_id)
    post_count = db.query(ScrapedPost.id).filter(ScrapedPost.run_id == run_id).count()
    if not post_count:
        raise HTTPException(status_code=404, detail="Extração não encontrada ou sem publicações.")
    active = jobs.active_enrich_job(run_id)
    if active:
        if request.client_id:
            active.client_id = request.client_id
        return {"status": "already_running", "data": active.to_dict()}

    job = jobs.create(
        keywords=[],
        networks=[],
        client_id=request.client_id or None,
        kind="enrich",
        enrich_media=request.enrich_media,
        generate_contact_sheet=request.generate_contact_sheet,
        transcribe_audio=request.transcribe_audio,
        detect_scenes=request.detect_scenes,
    )
    job.run_id = run_id
    job.steps_total = post_count
    spawn_background(run_enrich_job(job))
    return {"status": "started", "data": job.to_dict()}


# --------------------------------------------------------------------------- agendamentos
def _schedule_dict(s: Schedule) -> dict:
    return {
        "id": s.id,
        "keywords": s.keyword_list(),
        "networks": s.network_list(),
        "network": s.network,
        "search_type": s.search_type or "keyword",
        "cron": s.cron,
        "limit": s.max_posts or 50,
        "status": s.status or "active",
        "next_run": scheduler_service.next_run_time(s.id),
        "last_run_at": s.last_run_at.strftime("%d/%m/%Y %H:%M") if s.last_run_at else None,
        "last_run_id": s.last_run_id,
    }


@app.get("/api/schedules")
def get_schedules(db: Session = Depends(get_db)):
    return {"schedules": [_schedule_dict(s) for s in db.query(Schedule).order_by(Schedule.created_at.desc()).all()]}


@app.post("/api/schedules")
def create_schedule(request: ScheduleRequest, db: Session = Depends(get_db)):
    if not scheduler_service.available():
        raise HTTPException(status_code=500, detail="Módulo de agendamento não disponível.")
    try:
        scheduler_service.build_trigger(request.cron)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Expressão CRON inválida: {exc}")
    schedule = Schedule(
        id=f"job_{int(time.time() * 1000)}", keywords=json.dumps(request.keywords, ensure_ascii=False),
        network=",".join(request.networks), search_type=request.search_type, cron=request.cron.strip(),
        status="active", max_posts=request.limit, created_at=datetime.now(),
    )
    db.add(schedule)
    db.commit()
    scheduler_service.register(schedule)
    return {"status": "success", "message": "Relatório agendado com sucesso!", "job_id": schedule.id,
            "schedule": _schedule_dict(schedule)}


@app.patch("/api/schedules/{schedule_id}")
def update_schedule(schedule_id: str, request: ScheduleUpdate, db: Session = Depends(get_db)):
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    schedule.status = request.status
    db.commit()
    scheduler_service.register(schedule)
    return {"status": "success", "schedule": _schedule_dict(schedule)}


@app.post("/api/schedules/{schedule_id}/run")
async def run_schedule_now(schedule_id: str, db: Session = Depends(get_db)):
    if not db.get(Schedule, schedule_id):
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    spawn_background(scheduler_service.run_schedule(schedule_id, force=True))
    return {"status": "success", "message": "Execução iniciada. Acompanhe o resultado no Dashboard."}


@app.delete("/api/schedules/{schedule_id}")
def delete_schedule(schedule_id: str, db: Session = Depends(get_db)):
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    scheduler_service.unregister(schedule_id)
    db.delete(schedule)
    db.commit()
    return {"status": "success"}


# --------------------------------------------------------------------------- marcas
@app.get("/api/brands")
def get_brands(db: Session = Depends(get_db)):
    brands = db.query(Brand).order_by(Brand.name.asc()).all()
    return {"status": "success", "brands": {b.name: b.handles() for b in brands}}


@app.post("/api/brands")
def save_brand(brand: BrandRequest, db: Session = Depends(get_db)):
    name = " ".join(brand.name.split())
    if not name:
        raise HTTPException(status_code=400, detail="Nome da marca é obrigatório.")
    db_brand = db.get(Brand, name) or Brand(name=name)
    for net in ("x", "tiktok", "instagram", "youtube", "facebook"):
        setattr(db_brand, net, getattr(brand, net).strip().lstrip("@").strip())
    if brand.color:
        db_brand.color = brand.color
    if brand.logo_svg:
        try:
            brand_logo_service.salvar_logo_marca(name, brand.logo_svg, brand.color)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Erro no logotipo SVG: {exc}")
    db.merge(db_brand)
    db.commit()
    return {"status": "success", "message": f"Marca '{name}' salva com sucesso!"}


@app.get("/api/brands/{brand_name}/logo")
def get_brand_logo(brand_name: str, db: Session = Depends(get_db)):
    db_brand = db.get(Brand, brand_name)
    if not db_brand or not db_brand.logo_svg:
        raise HTTPException(status_code=404, detail="Logotipo da marca não encontrado.")
    return {"status": "success", "brand": brand_name, "svg": db_brand.logo_svg, "color": db_brand.color}


@app.post("/api/brands/{brand_name}/logo")
def upload_brand_logo(brand_name: str, payload: BrandLogoRequest, db: Session = Depends(get_db)):
    try:
        res = brand_logo_service.salvar_logo_marca(brand_name, payload.svg, payload.color)
        return {"status": "success", **res}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.exception("Falha ao salvar logo da marca %s", brand_name)
        raise HTTPException(status_code=500, detail=str(exc))


@app.delete("/api/brands/{brand_name}")
def delete_brand(brand_name: str, db: Session = Depends(get_db)):
    db_brand = db.get(Brand, brand_name)
    if not db_brand:
        raise HTTPException(status_code=404, detail="Marca não encontrada")
    db.delete(db_brand)
    db.commit()
    return {"status": "success"}


# --------------------------------------------------------------------------- frontend
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    @app.get("/")
    def read_root():
        return {"message": "RASP Analytics API rodando!"}
