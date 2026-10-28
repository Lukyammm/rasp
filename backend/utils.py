"""
Utilitários de texto do RASP:
- Parser booleano seguro (AND / OR / NOT / parênteses / "frases exatas" / -exclusão), sem eval().
- Extração de termos atômicos e identificação do termo mencionado em cada post.
- Conversão de métricas textuais ("1,2 mil", "39K") para inteiros.
- Interpretação de datas absolutas e relativas das redes ("há 2 dias", "3h", "Sep 8").
- Normalização de autores/handles.
"""
import math
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------

def remove_accents(input_str) -> str:
    if not isinstance(input_str, str):
        return ""
    nfkd_form = unicodedata.normalize("NFKD", input_str)
    return "".join(c for c in nfkd_form if not unicodedata.combining(c))


def normalize_text(value) -> str:
    """Minúsculas, sem acentos e com espaços colapsados (base para comparações)."""
    return re.sub(r"\s+", " ", remove_accents(str(value or "")).lower()).strip()


# ---------------------------------------------------------------------------
# Parser booleano
# ---------------------------------------------------------------------------

_OPERATORS = {"AND", "OR", "NOT"}


def _tokenize(query: str) -> List[Tuple[str, Optional[str]]]:
    tokens: List[Tuple[str, Optional[str]]] = []
    i, n = 0, len(query)
    while i < n:
        c = query[i]
        if c.isspace():
            i += 1
            continue
        if c == "(":
            tokens.append(("LP", None))
            i += 1
            continue
        if c == ")":
            tokens.append(("RP", None))
            i += 1
            continue
        if c in "\"“”":
            j = i + 1
            while j < n and query[j] not in "\"“”":
                j += 1
            phrase = query[i + 1:j].strip()
            if phrase:
                tokens.append(("PHRASE", phrase))
            i = j + 1
            continue
        if c == "'":
            m = re.match(r"'([^']+)'(?=[\s()]|$)", query[i:])
            if m:
                tokens.append(("PHRASE", m.group(1).strip()))
                i += m.end()
                continue
        j = i
        while j < n and not query[j].isspace() and query[j] not in "()\"“”":
            j += 1
        word = query[i:j]
        i = j
        upper = word.upper()
        if upper in _OPERATORS:
            tokens.append((upper, None))
        elif word == "-":
            tokens.append(("NOT", None))
        elif word.startswith("-") and len(word) > 1:
            tokens.append(("NOT", None))
            tokens.append(("TERM", word[1:]))
        else:
            tokens.append(("TERM", word))
    return tokens


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos][0] if self.pos < len(self.tokens) else None

    def next(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def parse(self):
        nodes = []
        while self.pos < len(self.tokens):
            node = self.parse_or()
            if node is not None:
                nodes.append(node)
            if self.peek() == "RP":  # parêntese solto: ignora
                self.pos += 1
            elif self.peek() in ("OR", "AND"):
                self.pos += 1
        return _combine("and", nodes)

    def parse_or(self):
        nodes = [self.parse_and()]
        while self.peek() == "OR":
            self.pos += 1
            nodes.append(self.parse_and())
        return _combine("or", [n for n in nodes if n is not None])

    def parse_and(self):
        nodes = []
        while True:
            kind = self.peek()
            if kind is None or kind in ("OR", "RP"):
                break
            if kind == "AND":
                self.pos += 1
                continue
            node = self.parse_not()
            if node is not None:
                nodes.append(node)
        return _combine("and", nodes)

    def parse_not(self):
        if self.peek() == "NOT":
            self.pos += 1
            child = self.parse_not()
            return ("not", child) if child is not None else None
        return self.parse_atom()

    def parse_atom(self):
        kind = self.peek()
        if kind is None:
            return None
        if kind == "LP":
            self.pos += 1
            node = self.parse_or()
            if self.peek() == "RP":
                self.pos += 1
            return node
        if kind in ("TERM", "PHRASE"):
            _, value = self.next()
            value = value.strip("*")
            return ("term", value, kind == "PHRASE") if value else None
        self.pos += 1
        return None


def _combine(kind, nodes):
    if not nodes:
        return None
    if len(nodes) == 1:
        return nodes[0]
    return (kind, nodes)


def _term_regex(term: str):
    norm = normalize_text(term)
    if not norm:
        return None
    pattern = r"\s+".join(re.escape(part) for part in norm.split(" "))
    # Fronteira à esquerda: impede prefixos indevidos (ex: "embate" para "debate"),
    # mas aceita sufixos de rede social como números e arrobas (ex: "lukyam72", "lukyam_oficial", "debates").
    return re.compile(r"(?<![0-9a-z_])" + pattern)


class BooleanQuery:
    """Consulta booleana compilada. Uso: BooleanQuery('(a OR b) AND "c d" NOT e').matches(texto)."""

    def __init__(self, query: str):
        self.raw = (query or "").strip()
        self.ast = _Parser(_tokenize(self.raw)).parse() if self.raw else None
        self._regex_cache = {}

    @property
    def is_empty(self) -> bool:
        return self.ast is None

    def _regex(self, term):
        if term not in self._regex_cache:
            self._regex_cache[term] = _term_regex(term)
        return self._regex_cache[term]

    def _eval(self, node, text) -> bool:
        kind = node[0]
        if kind == "term":
            rx = self._regex(node[1])
            return True if rx is None else bool(rx.search(text))
        if kind == "not":
            return not self._eval(node[1], text)
        if kind == "and":
            return all(self._eval(c, text) for c in node[1])
        return any(self._eval(c, text) for c in node[1])

    def matches(self, text: str) -> bool:
        if self.ast is None:
            return True
        return self._eval(self.ast, normalize_text(text))

    def _collect(self, node, negated, out_pos, out_neg):
        if node is None:
            return
        kind = node[0]
        if kind == "term":
            target = out_neg if negated else out_pos
            if node[1].lower() not in (t.lower() for t in target):
                target.append(node[1])
        elif kind == "not":
            self._collect(node[1], not negated, out_pos, out_neg)
        else:
            for child in node[1]:
                self._collect(child, negated, out_pos, out_neg)

    def positive_terms(self) -> List[str]:
        pos, neg = [], []
        self._collect(self.ast, False, pos, neg)
        return pos

    def negative_terms(self) -> List[str]:
        pos, neg = [], []
        self._collect(self.ast, False, pos, neg)
        return neg

    def has_excluded_term(self, text: str) -> bool:
        """True se o texto contém algum termo marcado com NOT (útil em redes cuja busca não suporta exclusão)."""
        norm = normalize_text(text)
        return any(self._regex(t) and self._regex(t).search(norm) for t in self.negative_terms())

    def to_x_query(self) -> str:
        """Converte para a sintaxe de busca do X: AND implícito, OR, "frases" e -exclusão."""
        if self.ast is None:
            return ""

        def render(node, negate=False, top=False):
            kind = node[0]
            if kind == "term":
                value = f'"{node[1]}"' if (node[2] or " " in node[1]) else node[1]
                return f"-{value}" if negate else value
            if kind == "not":
                return render(node[1], not negate)
            parts = [render(c, negate) for c in node[1]]
            is_or = (kind == "or") != negate  # De Morgan quando negado
            if is_or:
                joined = " OR ".join(parts)
                return joined if top else f"({joined})"
            return " ".join(parts)

        return render(self.ast, top=True)

    def to_plain_query(self) -> str:
        """Termos positivos separados por espaço (para redes sem suporte a operadores)."""
        return " ".join(self.positive_terms())


def check_boolean_query(query: str, text: str) -> bool:
    return BooleanQuery(query).matches(text)


def extract_atomic_terms(query: str) -> List[str]:
    """
    Termos de busca individuais (apenas os positivos — termos após NOT não são buscados).
    Ex: '"Luizianne Lins" OR "Cid Gomes"' -> ['Luizianne Lins', 'Cid Gomes']
        'mercado NOT politica' -> ['mercado']
        'ciro, fulano' -> ['ciro', 'fulano']
    """
    if not query or not str(query).strip():
        return []
    terms: List[str] = []
    for part in re.split(r"[,;\n]", str(query)):
        for t in BooleanQuery(part).positive_terms():
            if t.lower() not in (x.lower() for x in terms):
                terms.append(t)
    return terms or [str(query).strip()]


def identify_matched_terms(terms, text, author="") -> str:
    """Retorna o(s) termo(s) efetivamente mencionados no post, ex: "Cid Gomes, Capitão Wagner"."""
    if not terms:
        return "Geral"
    if len(terms) == 1:
        return terms[0]
    combined = normalize_text(f"{text} {author}")
    matched = []
    for t in terms:
        rx = _term_regex(t)
        if rx and rx.search(combined):
            matched.append(t.strip())
    return ", ".join(matched) if matched else "Geral"


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------

def parse_numeric_metric(val) -> int:
    """
    Converte representações textuais de métricas sociais para inteiro.
    "1.500" -> 1500 | "1,5 mil" / "1.5k" -> 1500 | "2,3 mi" -> 2300000 | "39K" -> 39000
    "1.234 curtidas" -> 1234 | N/A, None, "" -> 0 | IDs internos (10+ dígitos sem unidade) -> 0
    """
    if val is None:
        return 0
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, (int, float)):
        if isinstance(val, float) and math.isnan(val):
            return 0
        return int(val)

    s = str(val).strip()
    if not s or s.lower() in ("n/a", "none", "null", "-", "nan"):
        return 0

    m = re.search(r"([\d\.,]+)\s*(milh[õo]es|milh[aã]o|bilh[õo]es|bilh[aã]o|mil|mi|bi|k|m|b)?(?![a-zà-ú])", s.lower())
    if not m:
        return 0

    num_part = m.group(1).strip(".,")
    unit = (m.group(2) or "").strip()
    if not num_part:
        return 0

    digits_only = re.sub(r"\D", "", num_part)
    if not unit and len(digits_only) >= 10:
        return 0

    multiplier = 1
    if unit in ("b", "bi", "bilhão", "bilhao", "bilhões", "bilhoes"):
        multiplier = 1_000_000_000
    elif unit in ("m", "mi", "milhão", "milhao", "milhões", "milhoes"):
        multiplier = 1_000_000
    elif unit in ("k", "mil"):
        multiplier = 1_000

    if multiplier != 1:
        if "." in num_part and "," in num_part:
            cleaned = num_part.replace(".", "").replace(",", ".")
        else:
            cleaned = num_part.replace(",", ".")
        try:
            return int(round(float(cleaned) * multiplier))
        except ValueError:
            return 0

    if num_part.count(".") > 1:
        num_part = num_part.replace(".", "")
    elif num_part.count(",") > 1:
        num_part = num_part.replace(",", "")
    elif "." in num_part and "," in num_part:
        num_part = num_part.split(",")[0].replace(".", "")
    elif "." in num_part or "," in num_part:
        sep = "." if "." in num_part else ","
        left, right = num_part.split(sep)
        if len(right) in (1, 2):
            try:
                return int(float(f"{left}.{right}"))
            except ValueError:
                return 0
        num_part = left + right
    try:
        return int(float(num_part))
    except ValueError:
        return 0


# Valores fixos sintéticos que coletores legados gravavam ao falhar
PREENCHIMENTOS_FIXOS = {
    (1000, 50), (1500, 75), (1200, 60), (2500, 120), (32000, 1450), (35000, 1500)
}

RE_OG_METRICAS = re.compile(r"([\d.,]+[KkMm]?)\s+(?:likes?|curtidas?),\s*([\d.,]+[KkMm]?)\s+(?:comments?|coment[aá]rios?)", re.I)


def parse_numero_abreviado(txt: str) -> int:
    """'4,169' -> 4169; '1.2K' -> 1200; '2.5M' -> 2500000."""
    s = str(txt or "").strip().upper().replace(",", "")
    mult = 1
    if s.endswith("K"):
        mult, s = 1000, s[:-1]
    elif s.endswith("M"):
        mult, s = 1_000_000, s[:-1]
    elif s.endswith("B"):
        mult, s = 1_000_000_000, s[:-1]
    try:
        return int(round(float(s) * mult))
    except (ValueError, TypeError):
        return 0


def parse_metricas_og_description(texto: str) -> Optional[Tuple[int, int]]:
    """Extrai likes e comments de og:description do Instagram/Facebook."""
    m = RE_OG_METRICAS.search(texto or "")
    if not m:
        return None
    return parse_numero_abreviado(m.group(1)), parse_numero_abreviado(m.group(2))


def sanitizar_metricas_ebm(
    views: Optional[int],
    likes: Optional[int],
    comments: Optional[int],
    shares: Optional[int] = 0,
    status_base: str = "coletado",
) -> dict:
    """
    Higienização e taxonomia estrita de métricas EBM Quintto (normas Dominação IA).
    - Status: 'exato', 'coletado', 'truncado', 'ambiguo', 'ausente', 'oculto' (o autor escondeu as curtidas).
    - Rejeita preenchimentos fixos/corrompidos legados.
    - Rejeita estimativas sintéticas (ex: views = likes * 15).
    """
    v = parse_numeric_metric(views) if views is not None else None
    l = parse_numeric_metric(likes) if likes is not None else None
    c = parse_numeric_metric(comments) if comments is not None else None
    s = parse_numeric_metric(shares) if shares is not None else 0

    # 1. Filtro de preenchimento fixo do coletor antigo
    if (v, l) in PREENCHIMENTOS_FIXOS and (c is None or c == 0):
        return {
            "views": None, "likes": None, "comments": None, "shares": 0,
            "status": "ausente", "motivo": "preenchimento_fixo_rejeitado",
        }

    # 2. Rejeição de views sintético (likes * 15) ou overlay de hover corrompido (views == likes)
    # E conforme diretriz de BI: ausência não é zero; se views é 0 em post público, fica ausente (None).
    if v == 0:
        v = None
    elif l and v and (v == l or v == l * 15):
        v = None

    status = status_base
    if v is None and l is None and c is None:
        status = "ausente"
    elif status_base not in ("exato", "coletado", "truncado", "ambiguo", "ausente", "oculto"):
        status = "coletado"

    return {
        "views": v,
        "likes": l,
        "comments": c,
        "shares": s,
        "status": status,
    }


def format_int_br(value) -> str:
    if value is None:
        return "-"
    return f"{int(value or 0):,}".replace(",", ".")


# ---------------------------------------------------------------------------
# Datas
# ---------------------------------------------------------------------------

_MONTHS = {
    "jan": 1, "janeiro": 1, "january": 1,
    "fev": 2, "fevereiro": 2, "feb": 2, "february": 2,
    "mar": 3, "marco": 3, "march": 3,
    "abr": 4, "abril": 4, "apr": 4, "april": 4,
    "mai": 5, "maio": 5, "may": 5,
    "jun": 6, "junho": 6, "june": 6,
    "jul": 7, "julho": 7, "july": 7,
    "ago": 8, "agosto": 8, "aug": 8, "august": 8,
    "set": 9, "setembro": 9, "sep": 9, "sept": 9, "september": 9,
    "out": 10, "outubro": 10, "oct": 10, "october": 10,
    "nov": 11, "novembro": 11, "november": 11,
    "dez": 12, "dezembro": 12, "dec": 12, "december": 12,
}

_RELATIVE_UNITS = [
    (r"segundos?|secs?|seconds?|seg|s", "seconds"),
    (r"minutos?|minutes?|mins?|m", "minutes"),
    (r"horas?|hours?|hrs?|h", "hours"),
    (r"dias?|days?|d", "days"),
    (r"semanas?|weeks?|sem|w", "weeks"),
    (r"meses|mes|months?|mo", "months"),
    (r"anos?|years?|yrs?|y", "years"),
]
_RELATIVE_RE = re.compile(
    r"(\d+)\s*(?:de\s+)?(" + "|".join(p for p, _ in _RELATIVE_UNITS) + r")(?![a-z])"
)


def _unit_for(token: str) -> Optional[str]:
    for pattern, unit in _RELATIVE_UNITS:
        if re.fullmatch(pattern, token):
            return unit
    return None


def epoch_to_local(ts) -> Optional[datetime]:
    try:
        ts = float(ts)
        if ts > 1e12:
            ts /= 1000.0
        if ts <= 0:
            return None
        return datetime.fromtimestamp(ts)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def parse_social_date(date_str, now: Optional[datetime] = None) -> Optional[datetime]:
    """Interpreta datas absolutas (ISO, dd/mm/aaaa, "8 de set.", "Sep 8, 2025") e relativas ("há 2 dias", "3h")."""
    if date_str is None or date_str == "":
        return None
    if isinstance(date_str, datetime):
        return date_str
    now = now or datetime.now()
    raw = str(date_str).strip()
    s = normalize_text(raw)
    if not s or s in ("none", "null", "n/a", "nan"):
        return None

    iso = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})(?:[t ](\d{1,2}):(\d{2})(?::(\d{2}))?)?", s)
    if iso:
        try:
            y, mo, d = int(iso.group(1)), int(iso.group(2)), int(iso.group(3))
            hh, mm, ss = int(iso.group(4) or 0), int(iso.group(5) or 0), int(iso.group(6) or 0)
            dt = datetime(y, mo, d, hh, mm, ss)
            if raw.endswith("Z") or re.search(r"[+-]00:?00$", raw):
                dt = dt.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
            return dt
        except ValueError:
            pass

    br = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b", s)
    if br:
        try:
            year = int(br.group(3))
            year = year + 2000 if year < 100 else year
            return datetime(year, int(br.group(2)), int(br.group(1)))
        except ValueError:
            pass

    if re.fullmatch(r"\d{1,2}-\d{1,2}", s):  # formato "M-D" do TikTok
        mo, d = (int(x) for x in s.split("-"))
        try:
            dt = datetime(now.year, mo, d)
            return dt.replace(year=now.year - 1) if dt > now else dt
        except ValueError:
            pass

    if any(k in s for k in ("agora", "just now", "now")) and not re.search(r"\d", s):
        return now
    if "ontem" in s or "yesterday" in s:
        return now - timedelta(days=1)
    if s in ("hoje", "today"):
        return now

    rel = _RELATIVE_RE.search(s)
    if rel:
        num, unit = int(rel.group(1)), _unit_for(rel.group(2))
        if unit == "months":
            return now - timedelta(days=30 * num)
        if unit == "years":
            return now - timedelta(days=365 * num)
        if unit:
            return now - timedelta(**{unit: num})

    # "8 de set. de 2025", "8 set", "Sep 8, 2025", "setembro 8"
    words = re.findall(r"[a-z]+|\d+", s)
    for idx, w in enumerate(words):
        month = _MONTHS.get(w)
        if not month:
            continue
        numbers = [int(x) for x in words[max(0, idx - 2):idx + 4] if x.isdigit()]
        day = next((x for x in numbers if 1 <= x <= 31), None)
        year = next((x for x in numbers if x > 1900), now.year)
        if day:
            try:
                dt = datetime(year, month, day)
                if year == now.year and dt > now + timedelta(days=1) and not any(x > 1900 for x in numbers):
                    dt = dt.replace(year=now.year - 1)
                return dt
            except ValueError:
                return None
    return None


def format_date(dt: Optional[datetime]) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""


def decode_instagram_shortcode(code: str) -> Optional[int]:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    try:
        media_id = 0
        for char in code:
            media_id = media_id * 64 + alphabet.index(char)
        return media_id
    except ValueError:
        return None


def decode_instagram_date(link_or_code) -> Optional[str]:
    match = re.search(r"/(?:p|reel|reels|tv)/([\w\-]+)", str(link_or_code))
    code = match.group(1) if match else str(link_or_code)
    media_id = decode_instagram_shortcode(code[:11])
    if not media_id:
        return None
    epoch_ms = (media_id >> 23) + 1314220800000
    dt = epoch_to_local(epoch_ms)
    return format_date(dt) if dt and dt.year >= 2010 else None


# ---------------------------------------------------------------------------
# Autores
# ---------------------------------------------------------------------------

_GENERIC_AUTHORS = {"@perfil_instagram", "perfil_instagram", "@instagram_user", "instagram user", "n/a", "", "@", "desconhecido"}
_NOT_A_HANDLE = {"foto", "video", "vídeo", "reel", "post", "imagem", "apenas", "este", "debate", "a", "o", "atlas"}


def clean_author(author, network: str = "") -> str:
    """Normaliza o autor para '@handle'. Ex: '@Wagner Mendes | @reportermendes | · | Sep 8' -> '@reportermendes'."""
    raw = str(author or "").strip()
    if not raw:
        return ""
    if "|" in raw or "\n" in raw:
        handles = re.findall(r"@[\w\.]{2,}", raw)
        if handles:
            return handles[-1]
        raw = re.split(r"[|\n]", raw)[0].strip()
    if not raw.startswith("@"):
        raw = "@" + raw
    return raw


def is_generic_author(author) -> bool:
    return str(author or "").strip().lower() in _GENERIC_AUTHORS or "não extraído" in str(author or "").lower()


def infer_author_from_text(text: str) -> str:
    """Heurística para posts legados do Instagram salvos sem autor (texto do modal 'usuario • Seguir ...')."""
    txt = str(text or "").strip()
    m = re.search(r"([\w\.\-]+)\s*•\s*(?:Seguir|Follow|Seguindo)", txt, re.IGNORECASE)
    if m and m.group(1).lower() not in _NOT_A_HANDLE:
        return "@" + m.group(1).lstrip("@")
    m = re.search(r"@([\w\.\-]+)", txt)
    if m:
        return "@" + m.group(1)
    m = re.search(r"(?:Foto|Vídeo|Reel|Post) de ([\w\.\-]+)", txt, re.IGNORECASE)
    if m:
        return "@" + m.group(1)
    m = re.search(r"^([\w\.\-]+)\s*(?:•|e outros|é|na|no|com)", txt, re.IGNORECASE)
    if m and m.group(1).lower() not in _NOT_A_HANDLE:
        return "@" + m.group(1)
    return ""


_UI_NOISE_PATTERNS = [
    r"\b\d+\s*(?:sem|d|h|min|m)\s*(?:\d+)?\s*(?:curtidas?|likes?)?\s*Responder\b",
    r"curtidas?responder|semresponder|\bresponder\b|\brespostas\b|\bpostar\b",
    r"Ver respostas\s*\(\d+\)",
    r"\d+\s+de\s+(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)",
    r"Adicione um comentário\.{3}",
    r"^[\w\.\-]+\s*•\s*(?:Seguir|Follow)?\s*(?:Áudio|Audio)?\s*original?\s*[\d\.,\s]+(?:mil|k|m)?\s*curtidas\s*[\w\.\-]*\s*",
    r"Este (?:reel|post) tem [\d\.,\s]+ comentários.*$",
]


def clean_ui_noise(text: str) -> str:
    """Remove ruídos de interface capturados em extrações antigas do Instagram."""
    t = str(text or "")
    for pattern in _UI_NOISE_PATTERNS:
        t = re.sub(pattern, " ", t, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", t).strip()


def safe_filename(value: str, max_len: int = 60) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", remove_accents(str(value or ""))).strip("_")
    return cleaned[:max_len] or "extracao"


def _slug(text: str, max_len: int = 40) -> str:
    """'"Ciro Gomes" AND Ceará' -> 'Ciro-Gomes-Ceara' (sem acentos/símbolos, cortado em palavra inteira)."""
    words = re.findall(r"[A-Za-z0-9]+", remove_accents(str(text or "")))
    slug = ""
    for word in words:
        candidate = f"{slug}-{word}" if slug else word
        if len(candidate) > max_len:
            break
        slug = candidate
    return slug or (words[0][:max_len] if words else "")


def build_report_filename(keywords, extension: str, started_at: Optional[datetime] = None,
                          search_type: str = "keyword", origin: str = "manual") -> str:
    """
    Nome legível para planilhas e relatórios:
      RASP_Debate-Ciro-Elmano_2026-09-12_20h07.xlsx
      RASP_Perfil_Netflix_2026-09-12_20h07.xlsx
      RASP_Agendado_Debate-Ciro-Elmano_2026-09-12_08h00.pdf
    """
    if isinstance(keywords, str):
        keywords = [keywords]
    terms: List[str] = []
    if search_type == "url":
        terms = ["Posts-Especificos"]
    else:
        for keyword in keywords or []:
            found = [str(keyword).lstrip("@")] if search_type == "profile" else extract_atomic_terms(keyword)
            for term in found:
                if term.lower() not in (t.lower() for t in terms):
                    terms.append(term)
    parts = ["RASP"]
    if origin == "agendamento":
        parts.append("Agendado")
    if search_type == "profile":
        parts.append("Perfil")
    elif search_type == "url":
        parts.append("Post-Especifico")
    parts.append(_slug(" ".join(terms)) or "Extracao")
    parts.append((started_at or datetime.now()).strftime("%Y-%m-%d_%Hh%M"))
    return "_".join(parts) + "." + extension.lstrip(".")


def unique_filename(directory: str, filename: str) -> str:
    """Acrescenta _2, _3... se já existir um arquivo com o mesmo nome na pasta."""
    base, ext = os.path.splitext(filename)
    candidate, n = filename, 2
    while os.path.exists(os.path.join(directory, candidate)):
        candidate, n = f"{base}_{n}{ext}", n + 1
    return candidate
