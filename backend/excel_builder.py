"""
Planilha executiva de BI — Social Listening (EBM Quintto).

Abas:
1. Dashboard Executivo — banner, 5 KPIs, volume/interações por rede, benchmark de médias,
   distribuição por termo e Top 10 publicações (fórmulas vivas ligadas à base).
2. Share of Voice — matriz Termo × Rede (volume e interações) com participação percentual.
3. Top Autores — perfis mais influentes por interações, com médias por post.
4. Base de Posts — Link (A), Data, Rede, Termo, Palavra-Chave, Autor, Conteúdo, Curtidas, Comentários,
   Visualizações, Total de Interações (K = H + I) e Compartilhamentos.
5. Comentários — somente quando a coleta de comentários foi feita: um comentário por linha, ligado ao post.
"""
import datetime
import os
import re
from collections import defaultdict
from typing import Any, Dict, List, Union

import pandas as pd
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from utils import parse_numeric_metric, parse_social_date

# ------------------------------------------------------------------ paleta
NAVY_DEEP = "0F172A"
NAVY_HEADER = "1E293B"
TEXT_MUTED = "64748B"
BG_ZEBRA = "F8FAFC"
BG_CARD = "F1F5F9"
BORDER_LIGHT = "CBD5E1"
BORDER_DARK = "94A3B8"

POSTS_SHEET = "Base de Posts"
COMMENTS_SHEET = "Comentários"
STANDARD_NETWORKS = ["INSTAGRAM", "TIKTOK", "FACEBOOK", "X (TWITTER)", "YOUTUBE"]

THIN = Border(*(Side(style="thin", color=BORDER_LIGHT),) * 4)
TOTAL_BORDER = Border(top=Side(style="thin", color=BORDER_DARK), bottom=Side(style="double", color=NAVY_DEEP))
FILL_WHITE = PatternFill("solid", start_color="FFFFFF", end_color="FFFFFF")
FILL_ZEBRA = PatternFill("solid", start_color=BG_ZEBRA, end_color=BG_ZEBRA)
FILL_CARD = PatternFill("solid", start_color=BG_CARD, end_color=BG_CARD)
FILL_HEADER = PatternFill("solid", start_color=NAVY_HEADER, end_color=NAVY_HEADER)

F_BASE = Font(name="Calibri", size=10, color="1E293B")
F_BOLD = Font(name="Calibri", size=10, bold=True, color=NAVY_DEEP)
F_LABEL = Font(name="Calibri", size=10, bold=True, color="1E293B")
F_MUTED = Font(name="Calibri", size=10, color=TEXT_MUTED)
F_LINK = Font(name="Calibri", size=10, color="0284C7", underline="single")
F_HEADER = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
F_SECTION = Font(name="Calibri", size=11, bold=True, color=NAVY_DEEP)

LEFT = Alignment(horizontal="left", vertical="center")
RIGHT = Alignment(horizontal="right", vertical="center")
CENTER = Alignment(horizontal="center", vertical="center")
WRAP = Alignment(horizontal="left", vertical="center", wrap_text=True)

INT_FMT = "#,##0"
DEC_FMT = "#,##0.0"
PCT_FMT = "0.0%"


# ------------------------------------------------------------------ helpers
def parse_numeric(val) -> int:
    return parse_numeric_metric(val)


def normalize_network(net_str: Any) -> str:
    n = str(net_str or "").strip().upper()
    if not n:
        return "INSTAGRAM"
    if "TIKTOK" in n or "TIK TOK" in n:
        return "TIKTOK"
    if "INSTA" in n:
        return "INSTAGRAM"
    if "FACEBOOK" in n or n == "FB":
        return "FACEBOOK"
    if "YOUTUBE" in n or n == "YT":
        return "YOUTUBE"
    if "TWITTER" in n or n == "X" or n.startswith("X "):
        return "X (TWITTER)"
    return n


def clean_text(value, max_len: int = 32000) -> str:
    text = ILLEGAL_CHARACTERS_RE.sub("", str(value if value is not None else "")).strip()
    return text[:max_len]


def put(ws, row, col, value, font=F_BASE, align=LEFT, fill=None, border=THIN, fmt=None, as_text=False):
    cell = ws.cell(row=row, column=col)
    if isinstance(value, str) and not value.startswith("=") or as_text:
        value = clean_text(value)
    cell.value = value
    if as_text and isinstance(value, str) and value.startswith("="):
        cell.data_type = "s"  # impede que conteúdo coletado seja interpretado como fórmula
    cell.font = font
    cell.alignment = align
    if fill is not None:
        cell.fill = fill
    if border is not None:
        cell.border = border
    if fmt:
        cell.number_format = fmt
    return cell


def header_row(ws, row, start_col, headers, height=24):
    ws.row_dimensions[row].height = height
    for i, (title, align) in enumerate(headers):
        put(ws, row, start_col + i, title, font=F_HEADER, align=align, fill=FILL_HEADER)


def total_cell(ws, row, col, value, fmt=INT_FMT, align=RIGHT):
    return put(ws, row, col, value, font=F_BOLD, align=align, fill=FILL_CARD, border=TOTAL_BORDER, fmt=fmt)


def zebra(i):
    return FILL_WHITE if i % 2 == 0 else FILL_ZEBRA


def criteria(ref: str) -> str:
    """Escapa curingas (* ? ~) de uma célula usada como critério em COUNTIF/SUMIF."""
    return f'SUBSTITUTE(SUBSTITUTE(SUBSTITUTE({ref},"~","~~"),"*","~*"),"?","~?")'


def link_cell(ws, row, col, url, label, fill):
    url = str(url or "").strip()
    if url.startswith(("http://", "https://")):
        cell = put(ws, row, col, f'=HYPERLINK("{url.replace(chr(34), "%22")}", "{label}")', font=F_LINK, align=CENTER, fill=fill)
        cell.hyperlink = url
    else:
        put(ws, row, col, "-", font=F_MUTED, align=CENTER, fill=fill)


def banner(ws, title, subtitle, last_col=13):
    ws.row_dimensions[1].height = 10
    ws.row_dimensions[2].height = 30
    ws.row_dimensions[3].height = 20
    ws.row_dimensions[4].height = 12
    ws.cell(row=2, column=2, value=title).font = Font(name="Calibri", size=16, bold=True, color=NAVY_DEEP)
    ws.cell(row=3, column=2, value=subtitle).font = Font(name="Calibri", size=10, italic=True, color=TEXT_MUTED)
    for col in range(2, last_col + 1):
        ws.cell(row=4, column=col).border = Border(bottom=Side(style="thin", color=BORDER_DARK))


def _record_value(item, *keys, default=""):
    for k in keys:
        v = item.get(k)
        if v is not None and not (isinstance(v, float) and pd.isna(v)) and str(v).strip() != "":
            return v
    return default


def _terms_of(item) -> List[str]:
    raw = str(_record_value(item, "Termo Específico", "specific_term", "Termo", "Palavra-Chave", "keyword", default="Geral"))
    return [re.sub(r'[*~?"]', "", t).strip() for t in raw.split(",") if re.sub(r'[*~?"]', "", t).strip()]


# ------------------------------------------------------------------ builder
def build_executive_workbook(
    data: Union[List[Dict[str, Any]], pd.DataFrame],
    filepath: str,
    query_title: str = "Monitoramento Social Listening",
    comment_rows: Union[List[Dict[str, Any]], None] = None,
) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    records = data.to_dict(orient="records") if isinstance(data, pd.DataFrame) else list(data or [])

    rows = []
    for item in records:
        likes = parse_numeric(_record_value(item, "Curtidas", "likes", default=0))
        comments = parse_numeric(_record_value(item, "Comentarios", "Comentários", "comments", default=0))
        rows.append({
            "link": str(_record_value(item, "Link", "link")),
            "date_raw": str(_record_value(item, "Data", "post_date", "scraped_at")),
            "network": normalize_network(_record_value(item, "Rede", "network")),
            "terms": _terms_of(item),
            "term": str(_record_value(item, "Termo Específico", "specific_term", "Termo", "Palavra-Chave", "keyword", default="Geral")),
            "keyword": str(_record_value(item, "Palavra-Chave", "keyword")),
            "author": str(_record_value(item, "Autor", "author")),
            "text": str(_record_value(item, "Texto", "text")),
            "likes": likes,
            "comments": comments,
            "views": parse_numeric(_record_value(item, "Views", "views", default=0)),
            "shares": parse_numeric(_record_value(item, "Compartilhamentos", "shares", default=0)),
            "interactions": likes + comments,
            "metrics_status": str(_record_value(item, "Status Métricas", "metrics_status", default="coletado")),
            "media_type": str(_record_value(item, "media_type", default="")),
            "contact_sheet_path": str(_record_value(item, "contact_sheet_path", default="")),
            "transcription_text": str(_record_value(item, "transcription_text", default="")),
            "transcription_status": str(_record_value(item, "transcription_status", default="")),
            "accessibility_caption": str(_record_value(item, "accessibility_caption", default="")),
        })

    has_metrics_status = any(
        (item.get("Status Métricas") is not None) or (item.get("metrics_status") is not None)
        for item in records
    )

    wb = Workbook()
    ws_posts = wb.active
    ws_posts.title = POSTS_SHEET
    last_row = _build_posts_sheet(ws_posts, rows, include_metrics_status=has_metrics_status)

    ref = f"'{POSTS_SHEET}'!"
    rng = {col: f"{ref}${col}$2:${col}${last_row}" for col in "ACDFHIJKL"}
    now_str = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")
    clean_query = " ".join(str(query_title).split())
    clean_query = clean_query if len(clean_query) <= 65 else clean_query[:62] + "..."
    subtitle = f"EBM Quintto Comunicação • Monitoramento Integrado de Interações • Gerado em {now_str} • Busca: {clean_query}"

    ws_dash = wb.create_sheet(title="Dashboard Executivo", index=0)
    _build_dashboard(ws_dash, rows, rng, subtitle)
    _build_share_of_voice(wb.create_sheet(title="Share of Voice", index=1), rows, rng, subtitle)
    _build_top_authors(wb.create_sheet(title="Top Autores", index=2), rows, rng, subtitle)
    if comment_rows:
        _build_comments_sheet(wb.create_sheet(title=COMMENTS_SHEET), comment_rows)

    media_rows = [r for r in rows if r.get("transcription_text") or r.get("contact_sheet_path") or r.get("media_type") or r.get("accessibility_caption")]
    if media_rows:
        _build_transcriptions_sheet(wb.create_sheet(title="Transcrições & Mídias"), media_rows)

    wb.active = 0
    wb.save(filepath)
    return filepath


def _build_transcriptions_sheet(ws, rows) -> None:
    ws.sheet_properties.tabColor = "0D9488"
    spec = [
        ("Link Original", 18, CENTER),
        ("Rede Social", 14, CENTER),
        ("Autor / Perfil", 22, LEFT),
        ("Tipo de Mídia", 14, CENTER),
        ("Status Transcrição", 18, CENTER),
        ("Status Métricas", 16, CENTER),
        ("Transcrição de Áudio", 70, LEFT),
        ("Folha de Contato 4x4", 26, LEFT),
        ("Legenda / Alt Acessibilidade", 40, LEFT),
    ]
    ws.row_dimensions[1].height = 28
    for col, (title, width, _) in enumerate(spec, start=1):
        put(ws, 1, col, title, font=Font(name="Calibri", size=11, bold=True, color="FFFFFF"), align=CENTER, fill=FILL_HEADER)
        ws.column_dimensions[get_column_letter(col)].width = width

    for idx, r in enumerate(rows, start=2):
        fill = zebra(idx)
        ws.row_dimensions[idx].height = 24
        link_cell(ws, idx, 1, r["link"], "Acessar Post", fill)
        put(ws, idx, 2, r["network"], font=Font(name="Calibri", size=10, bold=True, color="334155"), align=CENTER, fill=fill)
        put(ws, idx, 3, r["author"], fill=fill, as_text=True)
        put(ws, idx, 4, (r.get("media_type") or "Vídeo").upper(), align=CENTER, fill=fill)
        put(ws, idx, 5, (r.get("transcription_status") or "concluída").upper(), font=F_LABEL, align=CENTER, fill=fill)
        put(ws, idx, 6, (r.get("metrics_status") or "coletado").upper(), align=CENTER, fill=fill)
        put(ws, idx, 7, r.get("transcription_text") or "-", align=WRAP, fill=fill, as_text=True)
        cs_nome = os.path.basename(r.get("contact_sheet_path") or "") if r.get("contact_sheet_path") else "-"
        put(ws, idx, 8, cs_nome, fill=fill, as_text=True)
        put(ws, idx, 9, r.get("accessibility_caption") or "-", align=WRAP, fill=fill, as_text=True)

    ws.freeze_panes = "D2"
    ws.auto_filter.ref = f"A1:I{max(2, len(rows) + 1)}"


def _build_posts_sheet(ws, rows, include_metrics_status: bool = False) -> int:
    ws.sheet_properties.tabColor = NAVY_DEEP
    spec = [
        ("Link Original", 18, CENTER), ("Data Publicação", 18, CENTER), ("Rede Social", 15, CENTER),
        ("Termo Específico", 26, LEFT), ("Palavra-Chave (Busca)", 26, LEFT), ("Autor / Perfil", 22, LEFT),
        ("Conteúdo da Publicação", 65, LEFT), ("Curtidas", 13, RIGHT), ("Comentários", 13, RIGHT),
        ("Visualizações", 14, RIGHT), ("Total Interações", 16, RIGHT), ("Compartilhamentos", 17, RIGHT),
    ]
    if include_metrics_status:
        spec.append(("Status Métricas", 16, CENTER))

    ws.row_dimensions[1].height = 28
    for col, (title, width, _) in enumerate(spec, start=1):
        put(ws, 1, col, title, font=Font(name="Calibri", size=11, bold=True, color="FFFFFF"), align=CENTER, fill=FILL_HEADER)
        ws.column_dimensions[get_column_letter(col)].width = width

    for idx, r in enumerate(rows, start=2):
        fill = zebra(idx)
        ws.row_dimensions[idx].height = 22
        link_cell(ws, idx, 1, r["link"], "Acessar Post", fill)
        dt = parse_social_date(r["date_raw"]) if r["date_raw"] else None
        if dt and re.match(r"^\d{4}-\d{2}-\d{2}", r["date_raw"]):
            put(ws, idx, 2, dt, align=CENTER, fill=fill, fmt="dd/mm/yyyy hh:mm")
        else:
            put(ws, idx, 2, r["date_raw"] or "-", align=CENTER, fill=fill)
        put(ws, idx, 3, r["network"], font=Font(name="Calibri", size=10, bold=True, color="334155"), align=CENTER, fill=fill)
        put(ws, idx, 4, r["term"], fill=fill, as_text=True)
        put(ws, idx, 5, r["keyword"], fill=fill, as_text=True)
        put(ws, idx, 6, r["author"], fill=fill, as_text=True)
        put(ws, idx, 7, r["text"], align=WRAP, fill=fill, as_text=True)
        put(ws, idx, 8, r["likes"], align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, idx, 9, r["comments"], align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, idx, 10, r["views"], align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, idx, 11, f"=H{idx}+I{idx}", font=F_BOLD, align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, idx, 12, r["shares"], align=RIGHT, fill=fill, fmt=INT_FMT)
        if include_metrics_status:
            put(ws, idx, 13, r.get("metrics_status", "coletado").upper(), font=F_LABEL, align=CENTER, fill=fill)

    last_row = max(2, len(rows) + 1)
    ws.freeze_panes = "D2"
    last_col_letter = get_column_letter(len(spec))
    ws.auto_filter.ref = f"A1:{last_col_letter}{last_row}"
    return last_row


def _build_comments_sheet(ws, comments) -> None:
    ws.sheet_properties.tabColor = "0284C7"
    spec = [
        ("Link do Post", 16, CENTER), ("Rede Social", 14, CENTER), ("Autor do Post", 22, LEFT), ("Trecho do Post", 40, LEFT),
        ("Autor do Comentário", 24, LEFT), ("Comentário", 70, LEFT), ("Curtidas", 12, RIGHT), ("Respostas", 12, RIGHT),
        ("Data do Comentário", 19, CENTER), ("Tipo", 13, CENTER), ("Sentimento", 16, CENTER),
    ]
    ws.row_dimensions[1].height = 28
    for col, (title, width, _) in enumerate(spec, start=1):
        put(ws, 1, col, title, font=Font(name="Calibri", size=11, bold=True, color="FFFFFF"), align=CENTER, fill=FILL_HEADER)
        ws.column_dimensions[get_column_letter(col)].width = width

    for idx, c in enumerate(comments, start=2):
        fill = zebra(idx)
        post_text = str(c.get("post_text") or "")
        date_raw = str(c.get("date") or "")
        link_cell(ws, idx, 1, c.get("post_link"), "Ver Post", fill)
        put(ws, idx, 2, normalize_network(c.get("network")), font=Font(name="Calibri", size=10, bold=True, color="334155"),
            align=CENTER, fill=fill)
        put(ws, idx, 3, c.get("post_author") or "", fill=fill, as_text=True)
        put(ws, idx, 4, post_text if len(post_text) <= 120 else post_text[:117] + "...", fill=fill, as_text=True)
        put(ws, idx, 5, c.get("author") or "", fill=fill, as_text=True)
        put(ws, idx, 6, c.get("text") or "", align=WRAP, fill=fill, as_text=True)
        put(ws, idx, 7, parse_numeric(c.get("likes")), align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, idx, 8, parse_numeric(c.get("replies")), align=RIGHT, fill=fill, fmt=INT_FMT)
        dt = parse_social_date(date_raw) if re.match(r"^\d{4}-\d{2}-\d{2}", date_raw) else None
        if dt:
            put(ws, idx, 9, dt, align=CENTER, fill=fill, fmt="dd/mm/yyyy hh:mm")
        else:
            put(ws, idx, 9, date_raw or "-", align=CENTER, fill=fill, as_text=True)  # ex.: "há 2 dias" (YouTube)
        put(ws, idx, 10, "Resposta" if c.get("is_reply") else "Comentário", font=F_MUTED, align=CENTER, fill=fill)
        put(ws, idx, 11, c.get("sentiment") or "", font=F_BOLD, align=CENTER, fill=fill, as_text=True)

    ws.freeze_panes = "E2"
    ws.auto_filter.ref = f"A1:K{max(2, len(comments) + 1)}"


def _build_dashboard(ws, rows, rng, subtitle):
    ws.sheet_properties.tabColor = "2563EB"
    for col, width in {"A": 4, "B": 24, "C": 16, "D": 16, "E": 16, "F": 16, "G": 18, "H": 18, "I": 4,
                       "J": 22, "K": 18, "L": 18, "M": 18}.items():
        ws.column_dimensions[col].width = width
    banner(ws, "RELATÓRIO EXECUTIVO DE SOCIAL LISTENING & MÉTRICAS DE ENGAJAMENTO", subtitle)
    has_rows = bool(rows)

    # KPIs (linhas 6 a 8)
    for r, h in ((5, 8), (6, 18), (7, 32), (8, 18), (9, 16)):
        ws.row_dimensions[r].height = h
    kpis = [
        (2, 3, "TOTAL DE PUBLICAÇÕES", f"=COUNTA({rng['A']})", "Volume Coletado", "1E3A8A"),
        (4, 5, "TOTAL DE CURTIDAS", f"=SUM({rng['H']})", "Reações Diretas", "E11D48"),
        (6, 7, "TOTAL DE COMENTÁRIOS", f"=SUM({rng['I']})", "Discussões & Respostas", "2563EB"),
        (8, 9, "TOTAL DE VISUALIZAÇÕES", f"=SUM({rng['J']})", "Alcance & Reproduções", "7C3AED"),
        (10, 12, "TOTAL DE INTERAÇÕES", f"=SUM({rng['K']})", "Engajamento Consolidado", "059669"),
    ]
    for cs, ce, title, formula, sub, accent in kpis:
        for r in (6, 7, 8):
            ws.merge_cells(start_row=r, start_column=cs, end_row=r, end_column=ce)
        for r in range(6, 9):
            for c in range(cs, ce + 1):
                ws.cell(row=r, column=c).fill = FILL_CARD
                ws.cell(row=r, column=c).border = Border(
                    left=Side(style="thin", color=BORDER_DARK) if c == cs else None,
                    right=Side(style="thin", color=BORDER_DARK) if c == ce else None,
                    top=Side(style="medium", color=accent) if r == 6 else None,
                    bottom=Side(style="thin", color=BORDER_DARK) if r == 8 else None,
                )
        put(ws, 6, cs, title, font=Font(name="Calibri", size=9, bold=True, color=accent), align=CENTER, fill=FILL_CARD, border=None)
        put(ws, 7, cs, formula if has_rows else 0, font=Font(name="Calibri", size=20, bold=True, color=NAVY_DEEP),
            align=CENTER, fill=FILL_CARD, border=None, fmt=INT_FMT)
        put(ws, 8, cs, sub, font=Font(name="Calibri", size=8, italic=True, color=TEXT_MUTED), align=CENTER, fill=FILL_CARD, border=None)

    # Tabela 1 — Rede
    networks = STANDARD_NETWORKS + sorted({r["network"] for r in rows} - set(STANDARD_NETWORKS))
    start_r = 12
    tot_r1 = start_r + len(networks)
    ws.cell(row=10, column=2, value="1. VOLUME & INTERAÇÕES CONSOLIDADAS POR REDE SOCIAL").font = F_SECTION
    header_row(ws, 11, 2, [("Rede Social", LEFT), ("Publicações (Vol)", RIGHT), ("Share Vol (%)", RIGHT),
                            ("Curtidas", RIGHT), ("Comentários", RIGHT), ("Visualizações", RIGHT), ("Total Interações", RIGHT)])
    for i, net in enumerate(networks):
        r, fill = start_r + i, zebra(i)
        ws.row_dimensions[r].height = 20
        put(ws, r, 2, net, font=F_LABEL, fill=fill)
        put(ws, r, 3, f"=COUNTIF({rng['C']}, B{r})", align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, r, 4, f"=IFERROR(C{r}/$C${tot_r1}, 0)", align=RIGHT, fill=fill, fmt=PCT_FMT)
        put(ws, r, 5, f"=SUMIF({rng['C']}, B{r}, {rng['H']})", align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, r, 6, f"=SUMIF({rng['C']}, B{r}, {rng['I']})", align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, r, 7, f"=SUMIF({rng['C']}, B{r}, {rng['J']})", align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, r, 8, f"=E{r}+F{r}", font=F_BOLD, align=RIGHT, fill=fill, fmt=INT_FMT)
    ws.row_dimensions[tot_r1].height = 24
    total_cell(ws, tot_r1, 2, "TOTAL CONSOLIDADO", fmt=None, align=LEFT)
    for col in range(3, 9):
        letter = get_column_letter(col)
        total_cell(ws, tot_r1, col, f"=SUM({letter}{start_r}:{letter}{tot_r1 - 1})", fmt=PCT_FMT if col == 4 else INT_FMT)

    # Tabela 2 — Benchmark de médias
    ws.cell(row=10, column=10, value="2. BENCHMARK DE MÉDIAS POR POST").font = F_SECTION
    header_row(ws, 11, 10, [("Rede Social", LEFT), ("Média Curtidas/Post", RIGHT), ("Média Comentários/Post", RIGHT),
                             ("Média Interações/Post", RIGHT)])
    for i, net in enumerate(networks):
        r, fill = start_r + i, zebra(i)
        put(ws, r, 10, net, font=F_LABEL, fill=fill)
        put(ws, r, 11, f"=IFERROR(ROUND(E{r}/C{r}, 1), 0)", align=RIGHT, fill=fill, fmt=DEC_FMT)
        put(ws, r, 12, f"=IFERROR(ROUND(F{r}/C{r}, 1), 0)", align=RIGHT, fill=fill, fmt=DEC_FMT)
        put(ws, r, 13, f"=IFERROR(ROUND(H{r}/C{r}, 1), 0)", font=F_BOLD, align=RIGHT, fill=fill, fmt=DEC_FMT)
    total_cell(ws, tot_r1, 10, "MÉDIA GERAL CONSOLIDADA", fmt=None, align=LEFT)
    for col, src in ((11, "E"), (12, "F"), (13, "H")):
        total_cell(ws, tot_r1, col, f"=IFERROR(ROUND({src}{tot_r1}/C{tot_r1}, 1), 0)", fmt=DEC_FMT)

    # Tabela 3 — Termos
    term_counts = defaultdict(int)
    for r in rows:
        for t in r["terms"]:
            term_counts[t] += 1
    top_terms = [t for t, _ in sorted(term_counts.items(), key=lambda x: x[1], reverse=True)[:12]] or ["Geral"]
    start_t3 = tot_r1 + 3
    tot_r3 = start_t3 + 1 + len(top_terms)
    ws.cell(row=start_t3 - 1, column=2, value="3. DISTRIBUIÇÃO DE INTERAÇÃO POR TERMO ESPECÍFICO / ENTIDADE").font = F_SECTION
    header_row(ws, start_t3, 2, [("Termo / Entidade Específica", LEFT), ("Publicações (Vol)", RIGHT), ("Share Vol (%)", RIGHT),
                                  ("Curtidas Totais", RIGHT), ("Comentários Totais", RIGHT), ("Visualizações Totais", RIGHT),
                                  ("Interações Consolidadas", RIGHT)])
    for i, term in enumerate(top_terms):
        r, fill = start_t3 + 1 + i, zebra(i)
        ws.row_dimensions[r].height = 20
        crit = f'"*" & B{r} & "*"'
        put(ws, r, 2, term, font=F_LABEL, fill=fill, as_text=True)
        put(ws, r, 3, f"=COUNTIF({rng['D']}, {crit})", align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, r, 4, f"=IFERROR(C{r}/$C${tot_r3}, 0)", align=RIGHT, fill=fill, fmt=PCT_FMT)
        put(ws, r, 5, f"=SUMIF({rng['D']}, {crit}, {rng['H']})", align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, r, 6, f"=SUMIF({rng['D']}, {crit}, {rng['I']})", align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, r, 7, f"=SUMIF({rng['D']}, {crit}, {rng['J']})", align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, r, 8, f"=E{r}+F{r}", font=F_BOLD, align=RIGHT, fill=fill, fmt=INT_FMT)
    ws.row_dimensions[tot_r3].height = 24
    total_cell(ws, tot_r3, 2, "TOTAL TOP TERMOS", fmt=None, align=LEFT)
    for col in range(3, 9):
        letter = get_column_letter(col)
        total_cell(ws, tot_r3, col, f"=SUM({letter}{start_t3 + 1}:{letter}{tot_r3 - 1})", fmt=PCT_FMT if col == 4 else INT_FMT)

    # Tabela 4 — Top 10
    start_t4 = tot_r3 + 3
    ws.cell(row=start_t4 - 1, column=2, value="4. DESTAQUES EXECUTIVOS — TOP 10 PUBLICAÇÕES POR ENGAJAMENTO").font = F_SECTION
    header_row(ws, start_t4, 2, [("Rank", CENTER), ("Rede", CENTER), ("Autor / Perfil", LEFT), ("Termo", LEFT),
                                  ("Conteúdo em Destaque", LEFT), ("Curtidas", RIGHT), ("Comentários", RIGHT),
                                  ("Visualizações", RIGHT), ("Total Interações", RIGHT), ("Acesso Direto", CENTER)])
    top = sorted(rows, key=lambda x: (x["interactions"], x["views"]), reverse=True)[:10]
    for i, item in enumerate(top):
        r, fill = start_t4 + 1 + i, zebra(i)
        ws.row_dimensions[r].height = 22
        text = item["text"] if len(item["text"]) <= 60 else item["text"][:57] + "..."
        put(ws, r, 2, f"#{i + 1}", font=Font(name="Calibri", size=10, bold=True, color="475569"), align=CENTER, fill=fill)
        put(ws, r, 3, item["network"], font=F_LABEL, align=CENTER, fill=fill)
        put(ws, r, 4, item["author"], fill=fill, as_text=True)
        put(ws, r, 5, item["term"], fill=fill, as_text=True)
        put(ws, r, 6, text, fill=fill, as_text=True)
        put(ws, r, 7, item["likes"], align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, r, 8, item["comments"], align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, r, 9, item["views"], align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, r, 10, item["interactions"], font=F_BOLD, align=RIGHT, fill=fill, fmt=INT_FMT)
        link_cell(ws, r, 11, item["link"], "Ver Post", fill)


def _build_share_of_voice(ws, rows, rng, subtitle):
    ws.sheet_properties.tabColor = "7C3AED"
    banner(ws, "SHARE OF VOICE — TERMOS × REDES SOCIAIS", subtitle, last_col=12)
    networks = [n for n in STANDARD_NETWORKS if any(r["network"] == n for r in rows)] or ["INSTAGRAM"]
    networks += sorted({r["network"] for r in rows} - set(STANDARD_NETWORKS))
    term_counts = defaultdict(int)
    for r in rows:
        for t in r["terms"]:
            term_counts[t] += 1
    terms = [t for t, _ in sorted(term_counts.items(), key=lambda x: x[1], reverse=True)[:15]] or ["Geral"]

    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 30
    for c in range(3, 3 + len(networks) + 3):
        ws.column_dimensions[get_column_letter(c)].width = 16

    def matrix(title, start_row, value_formula, total_label):
        ws.cell(row=start_row - 1, column=2, value=title).font = F_SECTION
        headers = [("Termo / Entidade", LEFT)] + [(n, RIGHT) for n in networks] + [("Total", RIGHT), ("Share of Voice (%)", RIGHT)]
        header_row(ws, start_row, 2, headers)
        first, last = start_row + 1, start_row + len(terms)
        total_r = last + 1
        total_col = 3 + len(networks)
        for i, term in enumerate(terms):
            r, fill = first + i, zebra(i)
            put(ws, r, 2, term, font=F_LABEL, fill=fill, as_text=True)
            for j, _ in enumerate(networks):
                col_letter = get_column_letter(3 + j)
                put(ws, r, 3 + j, value_formula(f"$B{r}", f"{col_letter}${start_row}"), align=RIGHT, fill=fill, fmt=INT_FMT)
            tl = get_column_letter(total_col)
            put(ws, r, total_col, f"=SUM(C{r}:{get_column_letter(total_col - 1)}{r})", font=F_BOLD, align=RIGHT, fill=fill, fmt=INT_FMT)
            put(ws, r, total_col + 1, f"=IFERROR({tl}{r}/${tl}${total_r}, 0)", align=RIGHT, fill=fill, fmt=PCT_FMT)
        total_cell(ws, total_r, 2, total_label, fmt=None, align=LEFT)
        for col in range(3, total_col + 2):
            letter = get_column_letter(col)
            total_cell(ws, total_r, col, f"=SUM({letter}{first}:{letter}{last})", fmt=PCT_FMT if col == total_col + 1 else INT_FMT)
        return total_r

    end1 = matrix("1. VOLUME DE MENÇÕES POR TERMO E REDE", 7,
                  lambda term, net: f'=COUNTIFS({rng["D"]}, "*" & {term} & "*", {rng["C"]}, {net})', "TOTAL DE MENÇÕES")
    end2 = matrix("2. INTERAÇÕES (CURTIDAS + COMENTÁRIOS) POR TERMO E REDE", end1 + 4,
                  lambda term, net: f'=SUMIFS({rng["K"]}, {rng["D"]}, "*" & {term} & "*", {rng["C"]}, {net})', "TOTAL DE INTERAÇÕES")
    note = ws.cell(row=end2 + 2, column=2,
                   value="Obs.: um post que cita mais de um termo é contado em cada termo; o Share of Voice é calculado sobre a soma das menções.")
    note.font = Font(name="Calibri", size=9, italic=True, color=TEXT_MUTED)


def _build_top_authors(ws, rows, rng, subtitle):
    ws.sheet_properties.tabColor = "059669"
    banner(ws, "TOP AUTORES — PERFIS MAIS INFLUENTES POR INTERAÇÕES", subtitle, last_col=11)
    for col, width in {"A": 4, "B": 8, "C": 30, "D": 15, "E": 14, "F": 14, "G": 14, "H": 16, "I": 16, "J": 18, "K": 16}.items():
        ws.column_dimensions[col].width = width

    placeholders = {"@perfil_instagram", "@facebook_user", "@desconhecido", "@canal_youtube", "@instagram_user"}
    grouped = defaultdict(lambda: {"posts": 0, "interactions": 0, "views": 0})
    for r in rows:
        if not r["author"] or r["author"].lower() in placeholders:
            continue
        g = grouped[(r["author"], r["network"])]
        g["posts"] += 1
        g["interactions"] += r["interactions"]
        g["views"] += r["views"]
    ranking = sorted(grouped.items(), key=lambda kv: (kv[1]["interactions"], kv[1]["views"], kv[1]["posts"]), reverse=True)[:30]

    start = 6
    header_row(ws, start, 2, [("Rank", CENTER), ("Autor / Perfil", LEFT), ("Rede", CENTER), ("Publicações", RIGHT),
                               ("Curtidas", RIGHT), ("Comentários", RIGHT), ("Visualizações", RIGHT),
                               ("Total Interações", RIGHT), ("Média Interações/Post", RIGHT), ("Share Interações", RIGHT)])
    total_r = start + 1 + len(ranking)
    for i, ((author, network), _) in enumerate(ranking):
        r, fill = start + 1 + i, zebra(i)
        a_crit, n_ref = criteria(f"$C{r}"), f"$D{r}"
        put(ws, r, 2, f"#{i + 1}", font=Font(name="Calibri", size=10, bold=True, color="475569"), align=CENTER, fill=fill)
        put(ws, r, 3, author, font=F_LABEL, fill=fill, as_text=True)
        put(ws, r, 4, network, align=CENTER, fill=fill)
        put(ws, r, 5, f"=COUNTIFS({rng['F']}, {a_crit}, {rng['C']}, {n_ref})", align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, r, 6, f"=SUMIFS({rng['H']}, {rng['F']}, {a_crit}, {rng['C']}, {n_ref})", align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, r, 7, f"=SUMIFS({rng['I']}, {rng['F']}, {a_crit}, {rng['C']}, {n_ref})", align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, r, 8, f"=SUMIFS({rng['J']}, {rng['F']}, {a_crit}, {rng['C']}, {n_ref})", align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, r, 9, f"=F{r}+G{r}", font=F_BOLD, align=RIGHT, fill=fill, fmt=INT_FMT)
        put(ws, r, 10, f"=IFERROR(ROUND(I{r}/E{r}, 1), 0)", align=RIGHT, fill=fill, fmt=DEC_FMT)
        put(ws, r, 11, f"=IFERROR(I{r}/SUM({rng['K']}), 0)", align=RIGHT, fill=fill, fmt=PCT_FMT)
    if ranking:
        total_cell(ws, total_r, 2, "", fmt=None)
        total_cell(ws, total_r, 3, f"TOTAL TOP {len(ranking)}", fmt=None, align=LEFT)
        total_cell(ws, total_r, 4, "", fmt=None)
        for col in range(5, 10):
            letter = get_column_letter(col)
            total_cell(ws, total_r, col, f"=SUM({letter}{start + 1}:{letter}{total_r - 1})")
        total_cell(ws, total_r, 10, f"=IFERROR(ROUND(I{total_r}/E{total_r}, 1), 0)", fmt=DEC_FMT)
        total_cell(ws, total_r, 11, f"=SUM(K{start + 1}:K{total_r - 1})", fmt=PCT_FMT)
    ws.freeze_panes = f"A{start + 1}"
