"""
Infraestrutura compartilhada pelos scrapers:
- ScrapeContext: parâmetros da busca, filtros (data, exclusões), deduplicação, limite, progresso e cancelamento.
- ResponseCollector: interceptação de respostas JSON da rede (sem chamadas Playwright por elemento).
- Helpers de JSON e rolagem.
"""
import itertools
import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Iterator, List, Optional

from utils import BooleanQuery, extract_atomic_terms, format_date, identify_matched_terms

logger = logging.getLogger("rasp.scraper")

DISPLAY_NAMES = {"x": "X", "tiktok": "TikTok", "instagram": "Instagram", "youtube": "YouTube", "facebook": "Facebook"}
POST_COLUMNS = ["Rede", "Palavra-Chave", "Termo Específico", "Autor", "Texto", "Curtidas", "Comentarios",
                "Views", "Compartilhamentos", "Link", "Data"]
# Opcionais por rede: formato (imagem | carrossel | reel | video) e status das métricas (ex.: "oculto")
EXTRA_COLUMNS = ["post_format", "metrics_status"]


def _parse_day(value: Optional[str], end: bool = False) -> Optional[datetime]:
    if not value:
        return None
    try:
        day = datetime.strptime(str(value)[:10], "%Y-%m-%d")
    except ValueError:
        return None
    return day + timedelta(hours=23, minutes=59, seconds=59) if end else day


@dataclass
class ScrapeContext:
    network: str
    keyword: str
    limit: int
    search_type: str = "keyword"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    brand_handles: dict = field(default_factory=dict)
    progress_callback: Optional[Callable[[str], None]] = None
    cancel_event: Optional[threading.Event] = None
    time_budget: Optional[float] = None

    def __post_init__(self):
        self.keyword = (self.keyword or "").strip()
        self.limit = max(1, int(self.limit or 1))
        self.query = BooleanQuery(self.keyword)
        self.atomic_terms = extract_atomic_terms(self.keyword) or [self.keyword]
        self.start_dt = _parse_day(self.start_date)
        self.end_dt = _parse_day(self.end_date, end=True)
        self.started_at = time.monotonic()
        if self.time_budget is None:
            self.time_budget = min(900.0, 120.0 + self.limit * 2.0)
        self.results: List[dict] = []
        self._seen = set()  # aceitos ou descartados pelo período (decisão definitiva)
        self._rejected = {}  # chave -> texto avaliado; reavaliado se o post voltar com texto diferente
        self._last_report = 0.0
        self.skipped_by_date = 0
        self.login_required = False
        self.authenticated = False
        self._timeout_warned = False

    # ---------------- estado ----------------
    @property
    def name(self) -> str:
        return DISPLAY_NAMES.get(self.network, self.network.upper())

    @property
    def full(self) -> bool:
        return len(self.results) >= self.limit

    def cancelled(self) -> bool:
        return bool(self.cancel_event and self.cancel_event.is_set())

    def time_exceeded(self) -> bool:
        return (time.monotonic() - self.started_at) > self.time_budget

    def should_stop(self) -> bool:
        if self.full or self.cancelled():
            return True
        if self.time_exceeded():
            if not self._timeout_warned:
                self._timeout_warned = True
                self.log(f"{self.name}: tempo máximo da busca atingido ({int(self.time_budget)}s). "
                         f"Encerrando com {len(self.results)} posts.", "WARN")
            return True
        return False

    # ---------------- comunicação ----------------
    def log(self, message: str, level: str = "INFO") -> None:
        logger.log(logging.WARNING if level in ("WARN", "ERROR") else logging.INFO, message)
        if self.progress_callback:
            try:
                self.progress_callback(f"[{level}] {message}")
            except Exception:
                pass

    def report(self, force: bool = False) -> None:
        now = time.monotonic()
        if force or now - self._last_report >= 1.5:
            self._last_report = now
            self.log(f"{self.name}: {min(len(self.results), self.limit)}/{self.limit} posts coletados...")

    # ---------------- busca ----------------
    def profile_handle(self) -> str:
        """Handle do perfil: busca a marca cadastrada (sem diferenciar maiúsculas) ou usa o texto digitado."""
        key = self.keyword.lower()
        for brand, handles in (self.brand_handles or {}).items():
            if brand.lower() == key:
                handle = str((handles or {}).get(self.network, "") or "").strip()
                if handle:
                    return handle.lstrip("@").strip("/")
        return self.keyword.lstrip("@").strip().strip("/")

    def search_variants(self, max_variants: int = 8) -> List[List[tuple]]:
        """
        Expande a consulta em variantes AND (forma normal disjuntiva, ignorando NOT) para redes sem
        operadores booleanos. '(a OR b) AND c' -> [[a, c], [b, c]]. Cada termo é (texto, é_frase).
        """
        def dnf(node):
            if node is None:
                return [[]]
            kind = node[0]
            if kind == "term":
                return [[(node[1], node[2])]]
            if kind == "not":
                return [[]]
            if kind == "or":
                return list(itertools.chain.from_iterable(dnf(c) for c in node[1]))
            combos = [[]]
            for child in node[1]:
                combos = [a + b for a in combos for b in dnf(child)]
                if len(combos) > max_variants:
                    raise OverflowError
            return combos

        try:
            variants = [v for v in dnf(self.query.ast) if v]
        except OverflowError:
            variants = []
        if not variants or len(variants) > max_variants:
            variants = [[(t, " " in t)] for t in self.atomic_terms]
        unique, seen = [], set()
        for v in variants:
            key = tuple(sorted(t.lower() for t, _ in v))
            if key not in seen:
                seen.add(key)
                unique.append(v)
        return unique

    @staticmethod
    def render_variant(variant, quote_phrases: bool = False) -> str:
        # Aspas só em frases de várias palavras: '"Ciro"' literal zera a busca do Instagram
        return " ".join(f'"{t}"' if (quote_phrases and phrase and " " in t) else t for t, phrase in variant)

    # ---------------- posts ----------------
    def matched_term(self, text: str, author: str, fallback: str = "") -> str:
        term = identify_matched_terms(self.atomic_terms, text, author)
        if len(self.atomic_terms) > 1:  # pela regra do filtro, que também reconhece 'termo*'
            term = ", ".join(self.query.matched_terms(f"{text} {author}")) or term
        if term == "Geral" and fallback:
            return fallback
        return term

    def has_seen(self, key: str) -> bool:
        return key in self._seen or key in self._rejected

    def add_post(self, *, key: str, author: str, text: str, link: str, date: Optional[datetime],
                 likes=0, comments=0, views=0, shares=0, term_fallback: str = "",
                 match_text: Optional[str] = None, require_match: bool = True,
                 post_format: str = "", metrics_status: str = "") -> bool:
        """Adiciona um post aplicando deduplicação, limite, período e exclusões. Retorna True se entrou."""
        if self.full or not key or key in self._seen:
            return False
        haystack = f"{match_text if match_text is not None else text} {author}"
        if self._rejected.get(key) == haystack:
            return False
        if self.search_type != "profile" and (
                (require_match and not self.query.matches(haystack)) or self.query.has_excluded_term(haystack)):
            # Não é definitivo: o mesmo post pode reaparecer com mais texto (tweet citado, "Ver mais" do Facebook)
            self._rejected[key] = haystack
            return False
        self._seen.add(key)
        self._rejected.pop(key, None)
        if date is not None and ((self.start_dt and date < self.start_dt) or (self.end_dt and date > self.end_dt)):
            self.skipped_by_date += 1
            return False
        self.results.append({
            "Rede": {"x": "X (Twitter)"}.get(self.network, self.network.upper()),
            "Palavra-Chave": self.keyword,
            "Termo Específico": self.matched_term(haystack, "", term_fallback),
            "Autor": author,
            "Texto": " ".join(str(text or "").split()),
            "Curtidas": str(likes if likes not in (None, "") else 0),
            "Comentarios": str(comments if comments not in (None, "") else 0),
            "Views": str(views if views not in (None, "") else 0),
            "Compartilhamentos": str(shares if shares not in (None, "") else 0),
            "Link": link,
            "Data": format_date(date),
            "post_format": post_format,
            "metrics_status": metrics_status,
        })
        return True


class ResponseCollector:
    """Guarda (url, corpo) das respostas cuja URL contém algum marcador. Os corpos são lidos no handler."""

    def __init__(self, page, markers: List[str]):
        self.page = page
        self.markers = markers
        self.queue: deque = deque()
        self.total = 0
        page.on("response", self._on_response)

    def _on_response(self, response):
        url = response.url
        if not any(m in url for m in self.markers):
            return
        try:
            if response.status >= 400:
                return
            body = response.text()
        except Exception:
            return
        self.queue.append((url, body))
        self.total += 1

    def drain(self):
        items = list(self.queue)
        self.queue.clear()
        return items

    def wait(self, timeout_ms: int = 6000, step_ms: int = 250) -> bool:
        waited = 0
        while not self.queue and waited < timeout_ms:
            self.page.wait_for_timeout(step_ms)
            waited += step_ms
        return bool(self.queue)

    def detach(self):
        try:
            self.page.remove_listener("response", self._on_response)
        except Exception:
            pass


def loads_lenient(body: str):
    """JSON tolerante: remove prefixos anti-XSSI e aceita múltiplos objetos por linha."""
    if not body:
        return []
    text = body.lstrip()
    for prefix in ("for (;;);", ")]}'"):
        if text.startswith(prefix):
            text = text[len(prefix):].lstrip()
    try:
        return [json.loads(text)]
    except ValueError:
        pass
    docs = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                docs.append(json.loads(line))
            except ValueError:
                continue
    return docs


def iter_dicts(obj) -> Iterator[dict]:
    """Percorre iterativamente todos os dicionários de uma estrutura JSON."""
    stack = [obj]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            yield current
            stack.extend(v for v in current.values() if isinstance(v, (dict, list)))
        elif isinstance(current, list):
            stack.extend(v for v in current if isinstance(v, (dict, list)))


def scroll(page, pixels: int = 2500, pause_ms: int = 900) -> bool:
    try:
        page.evaluate(f"window.scrollBy(0, {int(pixels)})")
        page.mouse.move(640, 480)
        page.mouse.wheel(0, pixels)
        page.wait_for_timeout(pause_ms)
        return True
    except Exception:
        return False


def text_runs(value) -> str:
    """Texto de objetos {simpleText} / {runs:[{text}]} / {content} usados pelo YouTube."""
    if not value:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if "simpleText" in value:
            return str(value["simpleText"])
        if "content" in value:
            return str(value["content"])
        if "runs" in value:
            return "".join(str(r.get("text", "")) for r in value["runs"] if isinstance(r, dict))
    return ""
