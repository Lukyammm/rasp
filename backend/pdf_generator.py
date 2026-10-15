"""
Relatório PDF executivo (ReportLab, offline): KPIs, desempenho por rede, termos em alta e Top 10.
Todo texto coletado é escapado antes de ir para o Paragraph (caracteres como & e < quebravam a geração).
"""
import os
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import DOWNLOADS_DIR

NAVY = colors.HexColor("#0f172a")
INDIGO = colors.HexColor("#4f46e5")
GRID = colors.HexColor("#e2e8f0")
ZEBRA = colors.HexColor("#f8fafc")


def _fmt(n) -> str:
    return f"{int(n or 0):,}".replace(",", ".")


def _table(data, widths, header_bg=INDIGO, align_right_from=1):
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if align_right_from is not None:
        style.append(("ALIGN", (align_right_from, 1), (-1, -1), "RIGHT"))
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), ZEBRA))
    t.setStyle(TableStyle(style))
    return t


def generate_pdf_report(data: dict, filename: str, query_title: str = "") -> str:
    file_path = os.path.join(DOWNLOADS_DIR, os.path.basename(filename))
    doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=1.6 * cm, leftMargin=1.6 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm, title="Relatório RASP Analytics")
    styles = getSampleStyleSheet()
    title = ParagraphStyle("T", parent=styles["Heading1"], fontSize=20, textColor=NAVY, spaceAfter=4)
    subtitle = ParagraphStyle("S", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#64748b"), spaceAfter=14)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, textColor=INDIGO, spaceBefore=14, spaceAfter=8)
    body = ParagraphStyle("B", parent=styles["Normal"], fontSize=8.5, leading=11)

    summary = data.get("summary", {})
    elements = [
        Paragraph("RASP Analytics — Relatório Executivo", title),
        Paragraph(escape(f"EBM Quintto Comunicação • Gerado em {datetime.now():%d/%m/%Y às %H:%M}"
                         + (f" • Busca: {query_title}" if query_title else "")), subtitle),
    ]

    elements.append(Paragraph("1. Visão Geral", h2))
    kpis = [["Publicações", "Curtidas", "Comentários", "Visualizações", "Interações", "Média/Post"],
            [_fmt(summary.get("total_posts")), _fmt(summary.get("total_likes")), _fmt(summary.get("total_comments")),
             _fmt(summary.get("total_views")), _fmt(summary.get("total_engagement")),
             f"{summary.get('avg_engagement', 0):,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")]]
    elements.append(_table(kpis, [2.9 * cm] * 6, align_right_from=None))

    networks = data.get("networks") or []
    if networks:
        elements.append(Paragraph("2. Desempenho por Rede Social", h2))
        rows = [["Rede", "Posts", "Curtidas", "Comentários", "Visualizações", "Interações"]]
        for n in networks:
            rows.append([n["network"], _fmt(n["posts"]), _fmt(n["likes"]), _fmt(n["comments"]), _fmt(n["views"]), _fmt(n["engagement"])])
        elements.append(_table(rows, [3.6 * cm, 2.4 * cm, 2.7 * cm, 2.7 * cm, 3 * cm, 3 * cm]))

    sec_idx = 3
    words = data.get("wordcloud") or []
    elements.append(Paragraph(f"{sec_idx}. Principais Tópicos Comentados", h2))
    sec_idx += 1
    if words:
        formatted = ", ".join(f"{escape(str(w.get('text', '')))} ({w.get('weight', 1)})" for w in words if isinstance(w, dict))
        elements.append(Paragraph(f"<b>Termos frequentes:</b> {formatted}", body))
    else:
        elements.append(Paragraph("Nenhum tópico encontrado.", body))

    feed = sorted(data.get("feed") or [], key=lambda p: (p.get("engagement", 0), p.get("views", 0)), reverse=True)[:10]
    elements.append(Paragraph(f"{sec_idx}. Top 10 Publicações por Engajamento", h2))
    if feed:
        rows = [["#", "Rede", "Autor", "Trecho do Texto", "Interações"]]
        for i, p in enumerate(feed, start=1):
            text = str(p.get("text", ""))
            text = text if len(text) <= 160 else text[:157] + "..."
            link = str(p.get("link") or "")
            snippet = escape(text)
            if link.startswith(("http://", "https://")):
                snippet = f'<link href="{escape(link, {chr(34): "&quot;"})}" color="#4f46e5">{snippet}</link>'
            rows.append([str(i), str(p.get("network", "")).upper(), Paragraph(escape(str(p.get("author", ""))), body),
                         Paragraph(snippet, body), p.get("engagement_str") or _fmt(p.get("engagement"))])
        elements.append(_table(rows, [0.8 * cm, 2.2 * cm, 3.2 * cm, 9 * cm, 2.4 * cm], align_right_from=4))
    else:
        elements.append(Paragraph("Nenhum post registrado.", body))

    elements.append(Spacer(1, 0.4 * cm))
    doc.build(elements)
    return file_path
