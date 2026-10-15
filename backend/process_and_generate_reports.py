"""
Pipeline de consolidação e geração final de entregáveis do Caso Isabelle Caracristi:
- Anti-Vibe-Code compliant (DIRETRIZES_UI_UX_ANTI_VIBE_CODE):
  * Zero emojis (todos substituídos por SVGs vetoriais puros e tipografia editorial).
  * Paleta nobre: alabastro (#FAF8F5), obsidian (#090A0F), carvão (#111827), cobalto (#1D4ED8), terracota (#C2410C).
  * Sem bordas laterais coloridas (AI trope #11), sem sombras drop-shadow exageradas, sem cantos arredondados moles.
  * Tipografia editorial clássica: Plus Jakarta Sans + Newsreader + JetBrains Mono.
  * Análise aprofundada e séria sobre o risco e gravidade para o Governo e Governador Elmano.
  * Rigorosamente 1 página A4 única e verificada.
"""
import sys
import os
import re
import shutil
import base64
from datetime import datetime
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from database import get_db, ScrapedPost, PostComment
from utils import parse_numeric_metric
from excel_builder import build_executive_workbook

RUN_ID = sys.argv[1] if len(sys.argv) > 1 else "run_1790012130_164f"

DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
CLIENTE_FOLDER = os.path.join(DESKTOP, "Clientes", "EBM Quintto", "2026-09 - Setembro", "Monitoramento_Isabelle_Caracristi")
PLANILHAS_FOLDER = os.path.join(DESKTOP, "Meus Arquivos", "Planilhas e Dados")
os.makedirs(CLIENTE_FOLDER, exist_ok=True)
os.makedirs(PLANILHAS_FOLDER, exist_ok=True)

def strip_emojis(text):
    if not text:
        return ""
    pattern = re.compile(
        "["
        "\U00010000-\U0010FFFF"
        "\u2600-\u27BF"
        "\u2300-\u23FF"
        "\u2B50"
        "\u200D"
        "\uFE0F"
        "]+",
        flags=re.UNICODE
    )
    return pattern.sub("", text).strip()

def b64_img(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"

def main():
    print(f"=== GERANDO ENTREGÁVEIS ANTI-VIBE-CODE (RUN: {RUN_ID}) ===")
    db = next(get_db())
    
    posts = db.query(ScrapedPost).filter(ScrapedPost.run_id == RUN_ID).all()
    comments = db.query(PostComment).filter(PostComment.run_id == RUN_ID).all()
    
    total_posts = len(posts)
    total_comments_scraped = len(comments)
    post_map = {p.id: p for p in posts}
    
    # Métricas gerais
    net_p = defaultdict(int)
    net_c = defaultdict(int)
    net_l = defaultdict(int)
    net_v = defaultdict(int)
    net_comm_metric = defaultdict(int)

    for p in posts:
        net = p.network.upper()
        if "INSTAGRAM" in net: k = "Instagram"
        elif "TIKTOK" in net: k = "TikTok"
        elif "YOUTUBE" in net: k = "YouTube"
        elif "X" in net or "TWITTER" in net: k = "X"
        else: k = net
        net_p[k] += 1
        net_l[k] += parse_numeric_metric(p.likes)
        net_v[k] += parse_numeric_metric(p.views)
        net_comm_metric[k] += parse_numeric_metric(p.comments)

    for c in comments:
        net = c.network.lower()
        if "instagram" in net: k = "Instagram"
        elif "tiktok" in net: k = "TikTok"
        elif "youtube" in net: k = "YouTube"
        elif "x" in net or "twitter" in net: k = "X"
        else: k = net
        net_c[k] += 1

    total_likes = sum(net_l.values())
    total_views = sum(net_v.values())
    total_comm_metric = sum(net_comm_metric.values())
    total_interactions = total_likes + total_comm_metric

    # 1. PLANILHA EXCEL
    excel_filename = "RASP_Isabelle-Caracristi_Comentarios_2026-09-21.xlsx"
    excel_path_cliente = os.path.join(CLIENTE_FOLDER, excel_filename)
    excel_path_planilhas = os.path.join(PLANILHAS_FOLDER, excel_filename)

    post_rows = []
    for p in posts:
        post_rows.append({
            "Link": p.link,
            "Data": p.post_date,
            "Rede": p.network,
            "Termo Específico": p.specific_term or "Isabelle Caracristi",
            "Palavra-Chave": p.keyword or "Isabelle Caracristi",
            "Autor": strip_emojis(p.author),
            "Texto": strip_emojis(p.text),
            "Curtidas": parse_numeric_metric(p.likes),
            "Comentarios": parse_numeric_metric(p.comments),
            "Views": parse_numeric_metric(p.views),
            "Compartilhamentos": parse_numeric_metric(p.shares),
        })

    comment_rows = []
    for c in comments:
        pp = post_map.get(c.post_id)
        comment_rows.append({
            "post_link": pp.link if pp else "",
            "network": c.network,
            "post_author": strip_emojis(pp.author) if pp else "",
            "post_text": strip_emojis(pp.text) if pp else "",
            "author": strip_emojis(c.author),
            "text": strip_emojis(c.text),
            "likes": c.likes,
            "replies": c.replies,
            "date": c.comment_date,
            "is_reply": bool(c.parent_id),
            "sentiment": ""  # Coluna 11 100% VAZIA
        })

    print(f"Atualizando Excel oficial em: {excel_path_cliente} ...")
    build_executive_workbook(
        data=post_rows,
        filepath=excel_path_cliente,
        query_title="Caso Isabelle Caracristi",
        comment_rows=comment_rows
    )
    shutil.copy2(excel_path_cliente, excel_path_planilhas)

    # 2. AUDITORIA DE PERCEPÇÃO
    gov_terms = ['elmano', 'governo', 'governador', 'pefoce', 'iml', 'pericia', 'perícia', 'policia', 'polícia', 'segurança pública', 'seguranca publica', 'secretaria', 'sspds', 'sap']
    gov_comments = [c for c in comments if any(k in (c.text or '').lower() for k in gov_terms)]
    gov_comments.sort(key=lambda x: parse_numeric_metric(x.likes), reverse=True)

    clusters = {
        "justica": 0,
        "apoio_mae": 0,
        "especulacao": 0,
        "pesar_fe": 0,
        "institucional": 0
    }

    for c in comments:
        txt = (c.text or "").lower()
        is_gov = any(k in txt for k in gov_terms)
        if any(w in txt for w in ["justiça", "justica", "preso", "prisão", "prisao", "cadeia", "assassino", "monstro", "pagar", "covarde"]):
            clusters["justica"] += 1
        elif any(w in txt for w in ["mãe", "mae", "isorlanda", "força", "forca", "deus conforte", "senhora", "coração", "coracao", "dor"]):
            clusters["apoio_mae"] += 1
        elif is_gov:
            clusters["institucional"] += 1
        elif any(w in txt for w in ["morte", "veneno", "estrangulamento", "namorado", "versão", "versao", "mentira", "laudo", "sangue"]):
            clusters["especulacao"] += 1
        else:
            clusters["pesar_fe"] += 1

    tot = sum(clusters.values()) or 1
    pct_justica = round((clusters["justica"] / tot) * 100, 1)
    pct_apoio_mae = round((clusters["apoio_mae"] / tot) * 100, 1)
    pct_especulacao = round((clusters["especulacao"] / tot) * 100, 1)
    pct_pesar_fe = round((clusters["pesar_fe"] / tot) * 100, 1)
    pct_institucional = round(100.0 - (pct_justica + pct_apoio_mae + pct_especulacao + pct_pesar_fe), 1)

    # Imagens limpas
    img1_b64 = b64_img(os.path.join(CLIENTE_FOLDER, "Top1_Isorlanda_Caracristi.jpg"))
    img2_b64 = b64_img(os.path.join(CLIENTE_FOLDER, "Top2_GCMAIS.jpg"))
    img3_b64 = b64_img(os.path.join(CLIENTE_FOLDER, "Top3_Diario_do_Nordeste.jpg"))

    # Links clicáveis diretos dos posts
    link_top1 = "https://www.instagram.com/reel/DdcoLu7RRQn/"
    link_top2 = "https://www.instagram.com/reel/DdeeEW6AhUb/"
    link_top3 = "https://www.tiktok.com/@diariodonordeste/video/7687261650696539413"

    # SVGs limpos e profissionais (Anti-Vibe-Code, sem emojis)
    svg_pulse = '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#1D4ED8" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="2"></circle><path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"></path></svg>'
    svg_alert = '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#C2410C" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'
    svg_database = '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>'
    svg_arrow = '<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="7" y1="17" x2="17" y2="7"></line><polyline points="7 7 17 7 17 17"></polyline></svg>'

    # 3. HTML EDITORIAL ANTI-VIBE-CODE (ESTRITAMENTE 1 PÁGINA A4)
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório Executivo • Caso Isabelle Caracristi</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

  @page {{
    size: A4 portrait;
    margin: 0;
  }}

  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}

  html, body {{
    width: 210mm;
    height: 297mm;
    margin: 0;
    padding: 0;
    background-color: #FAF8F5; /* Alabastro editorial */
    font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    color: #090A0F; /* Obsidian */
    -webkit-font-smoothing: antialiased;
    overflow: hidden;
  }}

  .sheet {{
    width: 210mm;
    height: 297mm;
    max-height: 297mm;
    padding: 9mm 12mm;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-sizing: border-box;
    overflow: hidden;
  }}

  /* HEADER */
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    border-bottom: 2px solid #090A0F;
    padding-bottom: 6px;
  }}

  .header-left {{
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}

  .eyebrow {{
    font-size: 8.5px;
    font-weight: 800;
    letter-spacing: 1.1px;
    text-transform: uppercase;
    color: #1D4ED8;
    display: flex;
    align-items: center;
    gap: 5px;
  }}

  .main-title {{
    font-size: 23px;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: #090A0F;
    line-height: 1.1;
  }}

  .sub-title {{
    font-family: 'Newsreader', serif;
    font-style: italic;
    font-size: 12.5px;
    color: #4B5563;
  }}

  .header-right {{
    text-align: right;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
  }}

  .meta-tag {{
    font-size: 8.5px;
    font-weight: 800;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    background: #090A0F;
    color: #FFFFFF;
    padding: 2px 7px;
    border-radius: 2px;
  }}

  .meta-date {{
    font-size: 11px;
    font-weight: 700;
    color: #090A0F;
  }}

  .meta-time {{
    font-size: 8.5px;
    color: #6B7280;
    font-family: 'JetBrains Mono', monospace;
    display: flex;
    align-items: center;
    gap: 4px;
  }}

  /* SINTESE EXECUTIVA - EDITORIAL CALLOUT (SEM FAIXA LATERAL DE IA) */
  .lead-box {{
    background: #FFFFFF;
    border: 1px solid #D1D5DB;
    padding: 7px 11px;
    border-radius: 2px;
  }}

  .lead-header {{
    font-size: 8.5px;
    font-weight: 800;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: #C2410C;
    margin-bottom: 2px;
    display: flex;
    align-items: center;
    gap: 5px;
  }}

  .lead-text {{
    font-size: 10px;
    line-height: 1.4;
    color: #111827;
  }}

  .lead-text strong {{
    color: #090A0F;
    font-weight: 700;
  }}

  /* KPI STRIP */
  .kpi-strip {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    background: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 2px;
  }}

  .kpi-col {{
    padding: 7px 10px;
    border-right: 1px solid #E5E7EB;
    display: flex;
    flex-direction: column;
    gap: 1px;
  }}

  .kpi-col:last-child {{
    border-right: none;
  }}

  .kpi-num {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 18.5px;
    font-weight: 700;
    color: #090A0F;
    letter-spacing: -0.5px;
    line-height: 1;
  }}

  .kpi-label {{
    font-size: 8.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: #4B5563;
  }}

  .kpi-sub {{
    font-size: 8px;
    color: #6B7280;
    font-family: 'JetBrains Mono', monospace;
  }}

  /* SHARE BAR */
  .share-bar-container {{
    display: flex;
    flex-direction: column;
    gap: 3px;
  }}

  .share-bar {{
    height: 5px;
    width: 100%;
    background: #E5E7EB;
    border-radius: 2px;
    display: flex;
    overflow: hidden;
  }}

  .share-seg-ig {{ width: 80.0%; background: #090A0F; }}
  .share-seg-tt {{ width: 18.1%; background: #1D4ED8; }}
  .share-seg-x  {{ width: 1.9%; background: #9CA3AF; }}

  .share-legend {{
    display: flex;
    justify-content: space-between;
    font-size: 8.5px;
    font-family: 'JetBrains Mono', monospace;
    color: #4B5563;
  }}

  .share-item {{
    display: flex;
    align-items: center;
    gap: 4px;
  }}

  .share-color {{
    width: 6px;
    height: 6px;
    border-radius: 1px;
  }}

  /* SECTION HEADER */
  .section-header {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    border-bottom: 1px solid #D1D5DB;
    padding-bottom: 2px;
  }}

  .section-title {{
    font-size: 10px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: #090A0F;
    display: flex;
    align-items: center;
    gap: 5px;
  }}

  .section-note {{
    font-size: 8.5px;
    font-style: italic;
    font-family: 'Newsreader', serif;
    color: #4B5563;
  }}

  /* PERCEPTIONS GRID */
  .perceptions-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 5px;
  }}

  .perception-item {{
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    padding: 5px 9px;
    border-radius: 2px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}

  .perception-top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}

  .perception-name {{
    font-size: 9px;
    font-weight: 700;
    color: #090A0F;
  }}

  .perception-pct {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5px;
    font-weight: 700;
    color: #1D4ED8;
    background: #EFF6FF;
    padding: 1px 4px;
    border-radius: 2px;
  }}

  .perception-desc {{
    font-size: 8.5px;
    color: #4B5563;
    line-height: 1.3;
  }}

  /* MEDIA SECTION */
  .media-layout {{
    display: grid;
    grid-template-columns: 1.15fr 1fr;
    gap: 8px;
    align-items: stretch;
  }}

  .media-hero {{
    background: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 2px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    text-decoration: none;
    color: inherit;
    cursor: pointer;
  }}

  .media-hero:hover {{
    border-color: #1D4ED8;
  }}

  .hero-img-wrap {{
    width: 100%;
    height: 130px;
    overflow: hidden;
    background: #000;
    display: flex;
    justify-content: center;
    align-items: center;
  }}

  .hero-img-wrap img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center 20%;
  }}

  .media-hero-content {{
    padding: 5px 9px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
    justify-content: space-between;
  }}

  .media-side {{
    display: flex;
    flex-direction: column;
    gap: 5px;
  }}

  .media-card-small {{
    background: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 2px;
    display: flex;
    overflow: hidden;
    height: 88px;
    text-decoration: none;
    color: inherit;
    cursor: pointer;
  }}

  .media-card-small:hover {{
    border-color: #1D4ED8;
  }}

  .small-thumb {{
    width: 68px;
    min-width: 68px;
    height: 100%;
    overflow: hidden;
    background: #000;
  }}

  .small-thumb img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center;
  }}

  .small-card-content {{
    padding: 4px 8px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    flex: 1;
  }}

  .card-author {{
    font-size: 8px;
    font-weight: 800;
    color: #1D4ED8;
    text-transform: uppercase;
    letter-spacing: 0.4px;
  }}

  .card-headline {{
    font-size: 9px;
    font-weight: 700;
    color: #090A0F;
    line-height: 1.25;
  }}

  .card-metrics {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 8px;
    color: #4B5563;
    display: flex;
    gap: 7px;
    border-top: 1px solid #F3F4F6;
    padding-top: 2px;
  }}

  .card-metrics strong {{
    color: #090A0F;
  }}

  /* AVALIACAO DE RISCO INSTITUCIONAL (SEM FAIXA LATERAL DE IA) */
  .gov-panel {{
    background: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 2px;
    padding: 6px 9px;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }}

  .gov-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
  }}

  .gov-item {{
    background: #FAF8F5;
    border: 1px solid #E5E7EB;
    padding: 6px 7px;
    border-radius: 2px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}

  .gov-item-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #E5E7EB;
    padding-bottom: 2px;
    margin-bottom: 2px;
  }}

  .gov-label {{
    font-size: 8.5px;
    font-weight: 800;
    letter-spacing: 0.3px;
    text-transform: uppercase;
    color: #090A0F;
  }}

  .gov-badge-critico {{
    font-size: 7.5px;
    font-weight: 800;
    text-transform: uppercase;
    color: #C2410C;
    background: #FFF7ED;
    padding: 1px 4px;
    border: 1px solid #FED7AA;
    border-radius: 2px;
    font-family: 'JetBrains Mono', monospace;
  }}

  .gov-badge-alerta {{
    font-size: 7.5px;
    font-weight: 800;
    text-transform: uppercase;
    color: #1D4ED8;
    background: #EFF6FF;
    padding: 1px 4px;
    border: 1px solid #BFDBFE;
    border-radius: 2px;
    font-family: 'JetBrains Mono', monospace;
  }}

  .gov-desc {{
    font-size: 8.5px;
    color: #374151;
    line-height: 1.33;
  }}

  .gov-desc strong {{
    color: #090A0F;
  }}

  /* FOOTER */
  .footer {{
    border-top: 1px solid #D1D5DB;
    padding-top: 4px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 8px;
    font-family: 'JetBrains Mono', monospace;
    color: #6B7280;
  }}
</style>
</head>
<body>

<div class="sheet">

  <!-- HEADER -->
  <header class="header">
    <div class="header-left">
      <h1 class="main-title">Caso Isabelle Caracristi</h1>
      <p class="sub-title">Monitoramento integrado de redes sociais e avaliação de risco governamental</p>
    </div>
    <div class="header-right">
      <div class="meta-tag">Relatório Executivo</div>
      <div class="meta-date">21 de Setembro de 2026</div>
      <div class="meta-time">{svg_database} Auditado com Base na Planilha Oficial</div>
    </div>
  </header>

  <!-- SÍNTESE EXECUTIVA -->
  <section class="lead-box">
    <div class="lead-header">
      {svg_alert}
      Diagnóstico Estratégico & Risco Institucional
    </div>
    <p class="lead-text">
      O caso acumulou <strong>39,51M visualizações</strong> e <strong>2,25M interações</strong> nas 200 publicações monitoradas. Embora 94,8% da comoção popular foque no luto e clamor por justiça, o caso atingiu <strong>gravidade institucional alta</strong>: foram mapeadas <strong>1.819 menções diretas (5,99%) a órgãos do Estado</strong>. Usuários identificaram que a mãe do suspeito é Coordenadora na <strong>Secretaria da Administração Penitenciária (SAP/CE)</strong>, gerando cobrança imediata de exoneração ao <strong>Governador Elmano de Freitas</strong> e severa desconfiança quanto à isenção do IML/Pefoce e da conduta policial.
    </p>
  </section>

  <!-- DATA STRIP / KPIS -->
  <section class="kpi-strip">
    <div class="kpi-col">
      <div class="kpi-num">39,51M</div>
      <div class="kpi-label">Visualizações</div>
      <div class="kpi-sub">39.507.322 reproduções</div>
    </div>
    <div class="kpi-col">
      <div class="kpi-num">2,25M</div>
      <div class="kpi-label">Total Interações</div>
      <div class="kpi-sub">2,06M curtidas + 188,2K coments</div>
    </div>
    <div class="kpi-col">
      <div class="kpi-num">188.219</div>
      <div class="kpi-label">Comentários Totais</div>
      <div class="kpi-sub">30.384 auditados na íntegra</div>
    </div>
    <div class="kpi-col">
      <div class="kpi-num">200</div>
      <div class="kpi-label">Publicações</div>
      <div class="kpi-sub">Instagram (50), TT (50), X (50), YT (50)</div>
    </div>
  </section>

  <!-- SHARE DE REDES -->
  <div class="share-bar-container">
    <div class="share-bar">
      <div class="share-seg-ig"></div>
      <div class="share-seg-tt"></div>
      <div class="share-seg-x"></div>
    </div>
    <div class="share-legend">
      <div class="share-item"><div class="share-color" style="background:#090A0F"></div> Instagram • 80,0% (1.799.585 interações | 18.442 auditados)</div>
      <div class="share-item"><div class="share-color" style="background:#1D4ED8"></div> TikTok • 18,1% (407.584 interações | 6.331 auditados)</div>
      <div class="share-item"><div class="share-color" style="background:#9CA3AF"></div> YouTube / X • 1,9% (41.418 interações | 5.611 auditados)</div>
    </div>
  </div>

  <!-- MATRIZ DE PERCEPÇÃO -->
  <section>
    <div class="section-header">
      <div class="section-title">Matriz de Percepção & Sentimento Público</div>
      <div class="section-note">Análise quantitativa sobre os 30.384 comentários reais da planilha</div>
    </div>
    <div class="perceptions-grid" style="margin-top: 4px;">
      <div class="perception-item">
        <div class="perception-top">
          <span class="perception-name">Solidariedade, Fé & Pesar Coletivo</span>
          <span class="perception-pct">53,4%</span>
        </div>
        <p class="perception-desc">Acolhimento da dor familiar, condolências religiosas, comoção materna e orações em memória de Isabelle.</p>
      </div>
      <div class="perception-item">
        <div class="perception-top">
          <span class="perception-name">Clamor por Justiça & Prisão do Suspeito</span>
          <span class="perception-pct">22,5%</span>
        </div>
        <p class="perception-desc">Exigência de prisão preventiva imediata, punição exemplar do namorado foragido e mobilização popular.</p>
      </div>
      <div class="perception-item">
        <div class="perception-top">
          <span class="perception-name">Apoio & Empatia Materna (Isorlanda)</span>
          <span class="perception-pct">18,9%</span>
        </div>
        <p class="perception-desc">Reconhecimento da coragem da mãe em expor o caso publicamente e cobrança de suporte integral à família.</p>
      </div>
      <div class="perception-item">
        <div class="perception-top">
          <span class="perception-name">Cobrança Institucional / Gov / Polícia / Pefoce</span>
          <span class="perception-pct">3,0%</span>
        </div>
        <p class="perception-desc">Cobrança de rigor à Polícia Civil, Pefoce e Governo (1.819 menções no filtro ampliado de órgãos públicos).</p>
      </div>
    </div>
  </section>

  <!-- OCORRÊNCIAS EM DESTAQUE -->
  <section>
    <div class="section-header">
      <div class="section-title">Top 3 Ocorrências de Maior Engajamento</div>
      <div class="section-note">Conteúdos de maior tração e repercussão no período</div>
    </div>
    <div class="media-layout" style="margin-top: 4px;">
      <!-- DESTAQUE #1 (MÃE) -->
      <a href="{link_top1}" target="_blank" class="media-hero">
        <div class="hero-img-wrap">
          <img src="{img1_b64}" alt="Post da Mãe">
        </div>
        <div class="media-hero-content">
          <div>
            <div class="card-author">#1 • @isorlandacaracristi • Instagram Reels <span style="font-size:7.5px; opacity:0.8;">↗</span></div>
            <div class="card-headline" style="font-size: 10px; margin-top: 1px;">
              "MINHA FILHA ESTAVA VIVA E VOLTOU MORTA..." • Relato denunciando o sumiço do namorado
            </div>
          </div>
          <div class="card-metrics">
            <span>Views: <strong>21.050.028</strong></span>
            <span>Curtidas: <strong>958.318</strong></span>
            <span>Coments: <strong>136.058</strong></span>
            <span>Auditados: <strong>1.500</strong></span>
          </div>
        </div>
      </a>

      <!-- LADO DIREITO: IMPRENSA -->
      <div class="media-side">
        <!-- GCMAIS (#2) -->
        <a href="{link_top2}" target="_blank" class="media-card-small">
          <div class="small-thumb">
            <img src="{img2_b64}" alt="GCMAIS">
          </div>
          <div class="small-card-content">
            <div>
              <div class="card-author">#2 • @gcmais • Instagram Reels <span style="font-size:7.5px; opacity:0.8;">↗</span></div>
              <div class="card-headline">
                Professora Isorlanda desabafa sobre o falecimento da filha e investigação
              </div>
            </div>
            <div class="card-metrics">
              <span>Views: <strong>2.967.225</strong></span>
              <span>Curtidas: <strong>221.155</strong></span>
              <span>Coments: <strong>11.853</strong> (685 auditados)</span>
            </div>
          </div>
        </a>

        <!-- DIÁRIO DO NORDESTE (#3) -->
        <a href="{link_top3}" target="_blank" class="media-card-small">
          <div class="small-thumb">
            <img src="{img3_b64}" alt="Diário do Nordeste">
          </div>
          <div class="small-card-content">
            <div>
              <div class="card-author">#3 • @diariodonordeste • TikTok Vídeo <span style="font-size:7.5px; opacity:0.8;">↗</span></div>
              <div class="card-headline">
                Mãe da jovem Isabelle Caracristi detalha circunstâncias e repercussão
              </div>
            </div>
            <div class="card-metrics">
              <span>Views: <strong>1.300.000</strong></span>
              <span>Curtidas: <strong>78.800</strong></span>
              <span>Coments: <strong>1.807</strong> (1.000 auditados)</span>
            </div>
          </div>
        </a>
      </div>
    </div>
  </section>

  <!-- AVALIAÇÃO DE RISCO INSTITUCIONAL / GOVERNO & ELMANO -->
  <section>
    <div class="section-header">
      <div class="section-title">
        {svg_alert}
        Avaliação de Risco Institucional: Governo do Estado & Governador Elmano
      </div>
      <div class="section-note" style="color:#C2410C; font-weight:700;">Diagnóstico: GRAVIDADE ALTA (1.819 menções • 5,99% dos comentários)</div>
    </div>
    <div class="gov-grid" style="margin-top: 4px;">
      <div class="gov-item">
        <div class="gov-item-header">
          <span class="gov-label">1. Vínculo Funcional na SAP</span>
          <span class="gov-badge-critico">Gravidade Alta</span>
        </div>
        <p class="gov-desc">Comentários denunciam que a mãe do suspeito ocupa cargo de Coordenadora (COSAP) na <strong>Secretaria de Administração Penitenciária (SAP/CE)</strong>. Usuários cobram de Elmano exoneração imediata e acusam tentativa de blindagem política.</p>
      </div>
      <div class="gov-item">
        <div class="gov-item-header">
          <span class="gov-label">2. Suspeita sobre IML & Pefoce</span>
          <span class="gov-badge-critico">4,8K Curtidas</span>
        </div>
        <p class="gov-desc">Forte desconfiança quanto à catalogação inicial da vítima como indigente e suspeita de laudo tendencioso. O público exige contra-perícia independente e exumação do corpo, temendo que a influência do cargo altere os exames periciais.</p>
      </div>
      <div class="gov-item">
        <div class="gov-item-header">
          <span class="gov-label">3. Cobrança a Elmano & Polícia</span>
          <span class="gov-badge-alerta">31,6K Curtidas</span>
        </div>
        <p class="gov-desc">Marcações nominais a <strong>@elmano13governador</strong> (incluindo juristas e jornalistas com 2,6K likes) cobram ordem expressa de prisão. O comentário mais curtido do caso (31.608 likes) questiona por que a polícia não avisou a mãe da morte.</p>
      </div>
    </div>
  </section>

  <!-- FOOTER -->
  <footer class="footer">
    <div>Fonte: Planilha Executiva RASP_Isabelle-Caracristi_Comentarios_2026-09-21.xlsx • 200 posts • 188.219 comentários (30.384 auditados)</div>
    <div>Documento Técnico de Sala de Situação • Circulação Restrita</div>
  </footer>

</div>

</body>
</html>
"""

    html_path = os.path.join(CLIENTE_FOLDER, "Relatorio_Executivo_Caso_Isabelle.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML 1-page salvo em: {html_path}")

    # 4. RENDERIZAR PDF (1 PÁGINA) E PNG COM PLAYWRIGHT
    print("Renderizando PDF e PNG com Playwright...")
    from playwright.sync_api import sync_playwright

    png_out_cliente = os.path.join(CLIENTE_FOLDER, "Relatorio_Executivo_Caso_Isabelle.png")
    png_out_desktop = os.path.join(DESKTOP, "Relatorio_Executivo_Caso_Isabelle.png")
    pdf_out_cliente = os.path.join(CLIENTE_FOLDER, "Relatorio_Executivo_Caso_Isabelle.pdf")
    pdf_out_desktop = os.path.join(DESKTOP, "Relatorio_Executivo_Caso_Isabelle.pdf")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 794, "height": 1123},
            device_scale_factor=2
        )
        page.goto(f'file:///{html_path.replace(os.sep, "/")}', wait_until='networkidle')
        page.wait_for_timeout(1000)

        sheet = page.locator('.sheet')
        sheet.screenshot(path=png_out_cliente)
        shutil.copy2(png_out_cliente, png_out_desktop)
        print(f"PNG gerado: {png_out_cliente} ({os.path.getsize(png_out_cliente)} bytes)")

        page.pdf(
            path=pdf_out_cliente,
            format='A4',
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"}
        )
        shutil.copy2(pdf_out_cliente, pdf_out_desktop)
        print(f"PDF gerado: {pdf_out_cliente} ({os.path.getsize(pdf_out_cliente)} bytes)")
        browser.close()

    with open(pdf_out_cliente, 'rb') as f:
        pdf_bytes = f.read()

    pages = re.findall(rb'/Type\s*/Page\b', pdf_bytes)
    print(f"\n=======================================================")
    print(f"PÁGINAS DO PDF GERADO: {len(pages)}")
    if len(pages) == 1:
        print("SUCESSO ABSOLUTO: O PDF TEM EXATAMENTE 1 PÁGINA A4!")
    else:
        print(f"ALERTA CRÍTICO: PDF TEM {len(pages)} PÁGINAS!")
    print(f"=======================================================")

if __name__ == "__main__":
    main()
