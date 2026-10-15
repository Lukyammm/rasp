"""
Camada de dados (SQLAlchemy + SQLite em modo WAL).
Tabelas: scraped_posts, post_comments, scrape_runs, brands, schedules.
As migrações são aditivas (ADD COLUMN) e idempotentes, preservando os dados existentes.
"""
import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint, create_engine, event, inspect,
                        text)
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DB_PATH, LEGACY_BRANDS_FILE

logger = logging.getLogger("rasp.db")

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30.0})


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
Base = declarative_base()


class Brand(Base):
    __tablename__ = "brands"

    name = Column(String, primary_key=True, index=True)
    x = Column(String, default="")
    tiktok = Column(String, default="")
    instagram = Column(String, default="")
    youtube = Column(String, default="")
    facebook = Column(String, default="")
    logo_svg = Column(Text, default="")
    color = Column(String, default="")

    def handles(self) -> dict:
        return {"x": self.x or "", "tiktok": self.tiktok or "", "instagram": self.instagram or "",
                "youtube": self.youtube or "", "facebook": self.facebook or ""}

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "handles": self.handles(),
            "logo_svg": self.logo_svg or "",
            "color": self.color or "",
        }


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(String, primary_key=True, index=True)
    keywords = Column(String)  # JSON (lista); registros antigos usam texto separado por vírgula
    network = Column(String)  # redes separadas por vírgula
    search_type = Column(String, default="keyword")
    cron = Column(String)
    location = Column(String, nullable=True)
    status = Column(String, default="active")
    max_posts = Column(Integer, default=50)
    created_at = Column(DateTime, default=datetime.now)
    last_run_at = Column(DateTime, nullable=True)
    last_run_id = Column(String, nullable=True)

    def keyword_list(self) -> list:
        raw = self.keywords or ""
        try:
            value = json.loads(raw)
            if isinstance(value, list):
                return [str(v) for v in value if str(v).strip()]
        except (ValueError, TypeError):
            pass
        return [k.strip() for k in raw.split(",") if k.strip()]

    def network_list(self) -> list:
        return [n.strip() for n in (self.network or "").split(",") if n.strip()]


class ScrapedPost(Base):
    __tablename__ = "scraped_posts"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, index=True)
    network = Column(String, index=True)
    keyword = Column(String, index=True)
    specific_term = Column(String, default="")
    author = Column(String)
    text = Column(Text)
    # A coluna antiga "sentiment" pode continuar existindo em bancos anteriores; ela não é mais usada.
    likes = Column(String)
    comments = Column(String)
    views = Column(String)
    shares = Column(String, default="0")
    link = Column(String)
    post_date = Column(String, default="")
    scraped_at = Column(DateTime, default=datetime.now)
    is_historical = Column(Boolean, default=False)
    # Coleta de comentários: '' (nunca tentada) | done | empty | disabled | partial | error | login
    comments_status = Column(String, default="")
    comments_collected = Column(Integer, default=0)
    comments_error = Column(String, default="")
    comments_updated_at = Column(DateTime, nullable=True)
    # Taxonomia e métricas EBM Quintto: exato | coletado | truncado | ambiguo | ausente
    metrics_status = Column(String, default="coletado")
    # Multimídia (Zero Token):
    media_type = Column(String, default="")  # video | image | carousel | text
    media_paths = Column(Text, default="")  # JSON list de caminhos de arquivo locais
    contact_sheet_path = Column(String, default="")  # Caminho da folha de contato 4x4
    scenes_detected = Column(Integer, default=0)  # Cortes de cena detectados via FFmpeg
    transcription_text = Column(Text, default="")  # Transcrição fonética via faster-whisper local
    transcription_status = Column(String, default="")  # done | no_audio | failed | pending | skipped
    transcription_json = Column(Text, default="")  # JSON completo de segmentos e confiança
    accessibility_caption = Column(Text, default="")  # Texto alternativo / acessibilidade


class PostComment(Base):
    """Comentário de um post coletado. (post_id, comment_id) é único: recoletar nunca duplica."""
    __tablename__ = "post_comments"
    __table_args__ = (UniqueConstraint("post_id", "comment_id", name="uq_post_comment"),)

    id = Column(Integer, primary_key=True)
    run_id = Column(String, index=True)
    post_id = Column(Integer, index=True)
    network = Column(String, default="")
    comment_id = Column(String, nullable=False)
    parent_id = Column(String, default="")  # preenchido quando é resposta a outro comentário
    author = Column(String, default="")
    text = Column(Text, default="")
    likes = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    comment_date = Column(String, default="")
    scraped_at = Column(DateTime, default=datetime.now)


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    run_id = Column(String, primary_key=True)
    query = Column(Text, default="")
    networks = Column(String, default="")
    search_type = Column(String, default="keyword")
    max_posts = Column(Integer, default=50)
    start_date = Column(String, default="")
    end_date = Column(String, default="")
    origin = Column(String, default="manual")  # manual | agendamento
    status = Column(String, default="running")  # running | done | error | cancelled
    total_posts = Column(Integer, default=0)
    file_name = Column(String, default="")
    error = Column(Text, default="")
    started_at = Column(DateTime, default=datetime.now)
    finished_at = Column(DateTime, nullable=True)


def _add_missing_columns():
    """Migração aditiva: cria colunas novas em bancos antigos sem perder dados."""
    wanted = {
        "brands": {
            "youtube": "VARCHAR DEFAULT ''",
            "logo_svg": "TEXT DEFAULT ''",
            "color": "VARCHAR DEFAULT ''",
        },
        "scraped_posts": {
            "post_date": "VARCHAR DEFAULT ''",
            "specific_term": "VARCHAR DEFAULT ''",
            "shares": "VARCHAR DEFAULT '0'",
            "comments_status": "VARCHAR DEFAULT ''",
            "comments_collected": "INTEGER DEFAULT 0",
            "comments_error": "VARCHAR DEFAULT ''",
            "comments_updated_at": "DATETIME",
            "metrics_status": "VARCHAR DEFAULT 'coletado'",
            "media_type": "VARCHAR DEFAULT ''",
            "media_paths": "TEXT DEFAULT ''",
            "contact_sheet_path": "VARCHAR DEFAULT ''",
            "scenes_detected": "INTEGER DEFAULT 0",
            "transcription_text": "TEXT DEFAULT ''",
            "transcription_status": "VARCHAR DEFAULT ''",
            "transcription_json": "TEXT DEFAULT ''",
            "accessibility_caption": "TEXT DEFAULT ''",
        },
        "schedules": {
            "max_posts": "INTEGER DEFAULT 50",
            "created_at": "DATETIME",
            "last_run_at": "DATETIME",
            "last_run_id": "VARCHAR",
        },
    }
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, columns in wanted.items():
            existing = {c["name"] for c in insp.get_columns(table)}
            for col, ddl in columns.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))
                    logger.info("Migração: coluna %s.%s criada", table, col)
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_scraped_posts_run_network ON scraped_posts (run_id, network)"))


def _import_legacy_brands():
    """Importa o antigo brands.json para a tabela brands (apenas marcas que ainda não existem)."""
    if not os.path.exists(LEGACY_BRANDS_FILE):
        return
    try:
        with open(LEGACY_BRANDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return
    if not isinstance(data, dict):
        return
    with session_scope() as db:
        for name, handles in data.items():
            if not isinstance(handles, dict) or db.get(Brand, name):
                continue
            db.add(Brand(name=name, **{k: str(handles.get(k, "") or "").lstrip("@") for k in ("x", "tiktok", "instagram", "youtube", "facebook")}))
            logger.info("Marca '%s' importada do brands.json", name)
    # Importa uma única vez: marcas excluídas pela interface não devem reaparecer ao reiniciar
    try:
        os.replace(LEGACY_BRANDS_FILE, LEGACY_BRANDS_FILE + ".importado")
    except OSError:
        pass


def init_db():
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()
    _import_legacy_brands()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    """Sessão transacional para uso em threads/background (commit automático, rollback em erro)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def save_post_comments(post_id: int, run_id: str, network: str, comments: list, status: str, error: str = "") -> int:
    """
    Grava os comentários de um post e atualiza o status dele numa única transação.
    Comentários já existentes são ignorados (INSERT OR IGNORE). Retorna o total de comentários do post no banco.
    """
    now = datetime.now()
    with session_scope() as db:
        rows = [{
            "run_id": run_id, "post_id": post_id, "network": network, "comment_id": str(c["id"])[:200],
            "parent_id": str(c.get("parent_id") or "")[:200], "author": str(c.get("author") or "")[:300],
            "text": str(c.get("text") or ""), "likes": int(c.get("likes") or 0), "replies": int(c.get("replies") or 0),
            "comment_date": str(c.get("date") or ""), "scraped_at": now,
        } for c in comments if c.get("id")]
        for start in range(0, len(rows), 500):
            db.execute(sqlite_insert(PostComment).values(rows[start:start + 500]).on_conflict_do_nothing(
                index_elements=["post_id", "comment_id"]))
        total = db.query(PostComment).filter(PostComment.post_id == post_id).count()
        post = db.get(ScrapedPost, post_id)
        if post is not None:
            # Uma recoleta que falhou não apaga o sucesso anterior: os comentários já salvos continuam valendo
            if status in ("error", "login") and total > 0:
                status = "partial"
            elif status == "empty" and total > 0:
                status = "done"
            post.comments_status = status
            post.comments_collected = total
            post.comments_error = (error or "")[:500]
            post.comments_updated_at = now
    return total


def load_brand_handles() -> dict:
    """{nome_da_marca: {rede: handle}} a partir do banco."""
    with session_scope() as db:
        return {b.name: b.handles() for b in db.query(Brand).all()}
