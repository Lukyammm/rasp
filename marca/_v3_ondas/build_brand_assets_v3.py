import os
import shutil
from PIL import Image
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MARCA_DIR = os.path.join(BASE_DIR, "marca")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Símbolo "onda raspada": barras de áudio (escuta) com o topo cortado na diagonal, como uma lâmina (raspar).
# (centro x, altura) de cada barra num quadro 400x400; a barra do meio leva a cor de destaque.
BARRAS = [(72, 100), (136, 190), (200, 280), (264, 170), (328, 90)]
BARRA_DESTAQUE = 2


def _barras_svg(cor_corpo: str, cor_destaque: str) -> str:
    meia, corte = 20, 14
    paths = []
    for i, (x, altura) in enumerate(BARRAS):
        topo, base = 200 - altura / 2, 200 + altura / 2
        d = (f"M {x - meia} {topo + corte:g} L {x + meia} {topo - corte + 8:g} V {base - meia:g} "
             f"A {meia} {meia} 0 0 1 {x - meia} {base - meia:g} Z")
        paths.append(f'<path d="{d}" fill="{cor_destaque if i == BARRA_DESTAQUE else cor_corpo}"/>')
    return "\n    ".join(paths)


# SVG 1: Símbolo Puro (Transparente)
SVG_SIMBOLO = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="100%" height="100%">
  <defs>
    <linearGradient id="bodyGrad" gradientUnits="userSpaceOnUse" x1="60" y1="360" x2="340" y2="40">
      <stop offset="0%" stop-color="#1e40af"/>
      <stop offset="45%" stop-color="#2563eb"/>
      <stop offset="100%" stop-color="#06b6d4"/>
    </linearGradient>
  </defs>
  <g>
    {_barras_svg("url(#bodyGrad)", "#06b6d4")}
  </g>
</svg>"""

# SVG 2: Ícone do App / Squircle (barras brancas, destaque ciano)
SVG_ICONE = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <linearGradient id="iconBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0b1329"/>
      <stop offset="45%" stop-color="#111c38"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>
  </defs>
  <rect width="512" height="512" rx="116" fill="url(#iconBg)" stroke="rgba(255,255,255,0.12)" stroke-width="8"/>
  <g transform="translate(68, 68) scale(0.94)">
    {_barras_svg("#ffffff", "#22d3ee")}
  </g>
</svg>"""

# Salva os arquivos SVG
with open(os.path.join(MARCA_DIR, "rasp_simbolo.svg"), "w", encoding="utf-8") as f:
    f.write(SVG_SIMBOLO)

with open(os.path.join(MARCA_DIR, "rasp_icone.svg"), "w", encoding="utf-8") as f:
    f.write(SVG_ICONE)

# O cabeçalho da interface usa o SVG (leve e nítido em qualquer resolução)
with open(os.path.join(FRONTEND_DIR, "logo.svg"), "w", encoding="utf-8") as f:
    f.write(SVG_SIMBOLO)

print("SVGs salvos.")

# Template HTML para renderizar com Playwright
HTML_RENDER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Inter', -apple-system, sans-serif; background: transparent; }

  /* Render Containers */
  #simbolo-1024 { width: 1024px; height: 1024px; display: flex; align-items: center; justify-content: center; background: transparent; }
  #icone-1024 { width: 1024px; height: 1024px; display: flex; align-items: center; justify-content: center; background: transparent; }

  /* Logo Lockup Horizontal */
  .logo-box {
    display: inline-flex;
    align-items: center;
    gap: 28px;
    padding: 36px 48px;
  }
  .logo-box.escuro {
    background: #0b0f19;
  }
  .logo-box.claro {
    background: #ffffff;
  }
  .brand-title {
    font-size: 68px;
    font-weight: 900;
    line-height: 0.95;
    letter-spacing: -0.04em;
  }
  .escuro .brand-title { color: #ffffff; }
  .claro .brand-title { color: #090d16; }

  .brand-badge-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 8px;
  }
  .badge {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    padding: 4px 10px;
    border-radius: 6px;
  }
  .escuro .badge {
    background: rgba(6, 182, 212, 0.15);
    color: #22d3ee;
    border: 1px solid rgba(6, 182, 212, 0.35);
  }
  .claro .badge {
    background: #ecfeff;
    color: #0e7490;
    border: 1px solid #a5f3fc;
  }
  .sub-tag {
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }
  .escuro .sub-tag { color: #64748b; }
  .claro .sub-tag { color: #64748b; }

  /* Sheet de Apresentação */
  #apresentacao {
    width: 1440px;
    height: 900px;
    background: #070a11;
    padding: 50px 70px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }
  .apres-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    padding-bottom: 24px;
  }
  .apres-header h1 {
    font-size: 32px;
    font-weight: 900;
    letter-spacing: -0.03em;
    color: #ffffff;
  }
  .apres-header p {
    color: #06b6d4;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
  }
  .apres-grid {
    display: grid;
    grid-template-columns: 1.2fr 1fr;
    gap: 30px;
    flex: 1;
    margin: 30px 0;
  }
  .apres-card {
    border-radius: 20px;
    padding: 36px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    border: 1px solid rgba(255,255,255,0.08);
  }
  .apres-card.c-dark { background: #0f172a; }
  .apres-card.c-light { background: #ffffff; }
  .card-tag {
    position: absolute;
    top: 20px;
    left: 24px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }
  .c-dark .card-tag { color: #64748b; }
  .c-light .card-tag { color: #94a3b8; }
  
  .apres-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #0f172a;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 18px 32px;
  }
  .footer-item {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .footer-label {
    font-size: 13px;
    font-weight: 600;
    color: #94a3b8;
  }
</style>
</head>
<body>

  <!-- 1. Simbolo 1024 -->
  <div id="simbolo-1024">
    <div style="width: 860px; height: 860px;">
      """ + SVG_SIMBOLO + """
    </div>
  </div>

  <!-- 2. Icone 1024 -->
  <div id="icone-1024">
    <div style="width: 1024px; height: 1024px;">
      """ + SVG_ICONE + """
    </div>
  </div>

  <!-- 3. Logo Escuro -->
  <div id="logo-escuro" class="logo-box escuro">
    <div style="width: 110px; height: 110px;">
      """ + SVG_SIMBOLO + """
    </div>
    <div>
      <div class="brand-title">RASP</div>
      <div class="brand-badge-row">
        <span class="badge">SOCIAL LISTENING &amp; BI</span>
      </div>
    </div>
  </div>

  <!-- 4. Logo Claro -->
  <div id="logo-claro" class="logo-box claro">
    <div style="width: 110px; height: 110px;">
      """ + SVG_SIMBOLO + """
    </div>
    <div>
      <div class="brand-title">RASP</div>
      <div class="brand-badge-row">
        <span class="badge">SOCIAL LISTENING &amp; BI</span>
      </div>
    </div>
  </div>

  <!-- 5. Folha de Apresentacao -->
  <div id="apresentacao">
    <div class="apres-header">
      <div>
        <h1>RASP</h1>
        <p>Sistema de Social Listening, Web Scraping e Business Intelligence</p>
      </div>
      <div style="text-align: right; color: #64748b; font-size: 12px; font-weight: 600;">
        EBM QUINTTO COMUNICAÇÃO<br>IDENTIDADE VISUAL V3.0
      </div>
    </div>

    <div class="apres-grid">
      <!-- Dark Version -->
      <div class="apres-card c-dark">
        <div class="card-tag">Tema Escuro (Primário)</div>
        <div class="logo-box escuro" style="background: transparent; padding: 0;">
          <div style="width: 120px; height: 120px;">""" + SVG_SIMBOLO + """</div>
          <div>
            <div class="brand-title" style="font-size: 64px;">RASP</div>
            <div class="brand-badge-row">
              <span class="badge">SOCIAL LISTENING &amp; BI</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Light Version -->
      <div class="apres-card c-light">
        <div class="card-tag">Tema Claro (Secundário)</div>
        <div class="logo-box claro" style="background: transparent; padding: 0;">
          <div style="width: 120px; height: 120px;">""" + SVG_SIMBOLO + """</div>
          <div>
            <div class="brand-title" style="font-size: 64px;">RASP</div>
            <div class="brand-badge-row">
              <span class="badge">SOCIAL LISTENING &amp; BI</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer com Icones de Sistema -->
    <div class="apres-footer">
      <div class="footer-item">
        <div style="width: 60px; height: 60px;">""" + SVG_ICONE + """</div>
        <div>
          <div class="footer-label" style="color: #ffffff; font-weight: 700;">Ícone do Aplicativo</div>
          <div class="footer-label" style="font-size: 11px;">Desktop Windows (.ico) & macOS Squircle</div>
        </div>
      </div>

      <div class="footer-item">
        <div style="width: 44px; height: 44px;">""" + SVG_ICONE + """</div>
        <div>
          <div class="footer-label" style="color: #ffffff; font-weight: 700;">Atalho RASP</div>
          <div class="footer-label" style="font-size: 11px;">Barra de Tarefas & Desktop (48px)</div>
        </div>
      </div>

      <div class="footer-item">
        <div style="width: 32px; height: 32px;">""" + SVG_ICONE + """</div>
        <div>
          <div class="footer-label" style="color: #ffffff; font-weight: 700;">Favicon Web</div>
          <div class="footer-label" style="font-size: 11px;">Guia do Navegador (32px / 16px)</div>
        </div>
      </div>
    </div>
  </div>

</body>
</html>"""

render_html_path = os.path.join(BASE_DIR, "render_assets.html")
with open(render_html_path, "w", encoding="utf-8") as f:
    f.write(HTML_RENDER)

print("Iniciando renderização Playwright...")
with sync_playwright() as p:
    try:
        browser = p.chromium.launch(channel="chrome")
    except Exception:
        browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=2)
    page.goto("file://" + os.path.abspath(render_html_path))
    page.wait_for_timeout(1000)

    # 1. Simbolo 1024x1024
    simbolo_el = page.locator("#simbolo-1024")
    simbolo_png = os.path.join(MARCA_DIR, "rasp_simbolo_1024.png")
    simbolo_el.screenshot(path=simbolo_png, omit_background=True)
    print("rasp_simbolo_1024.png gerado.")

    # 2. Icone 1024x1024
    icone_el = page.locator("#icone-1024")
    icone_png = os.path.join(MARCA_DIR, "rasp_icone_1024.png")
    icone_el.screenshot(path=icone_png, omit_background=True)
    print("rasp_icone_1024.png gerado.")

    # 3. Logo Escuro
    escuro_el = page.locator("#logo-escuro")
    escuro_png = os.path.join(MARCA_DIR, "rasp_logo_escuro.png")
    escuro_el.screenshot(path=escuro_png)
    print("rasp_logo_escuro.png gerado.")

    # 4. Logo Claro
    claro_el = page.locator("#logo-claro")
    claro_png = os.path.join(MARCA_DIR, "rasp_logo_claro.png")
    claro_el.screenshot(path=claro_png)
    print("rasp_logo_claro.png gerado.")

    # 5. Folha de Apresentacao
    apres_el = page.locator("#apresentacao")
    apres_png = os.path.join(MARCA_DIR, "rasp_logo_apresentacao.png")
    apres_el.screenshot(path=apres_png)
    print("rasp_logo_apresentacao.png gerado.")

    browser.close()

os.remove(render_html_path)

# Geração dos arquivos para o Frontend e .ICO do Windows
print("Gerando arquivos do frontend e .ico...")

# Copia simbolo para frontend/logo.png
shutil.copy(simbolo_png, os.path.join(FRONTEND_DIR, "logo.png"))

# Gera favicon.png (256x256)
img_icone = Image.open(icone_png)
img_favicon_png = img_icone.resize((256, 256), Image.Resampling.LANCZOS)
img_favicon_png.save(os.path.join(FRONTEND_DIR, "favicon.png"), format="PNG")

# Gera .ICO multi-resolução
ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
ico_marca = os.path.join(MARCA_DIR, "rasp_icon.ico")
ico_front = os.path.join(FRONTEND_DIR, "favicon.ico")
ico_base = os.path.join(BASE_DIR, "rasp_icon.ico")

img_icone.save(ico_marca, format="ICO", sizes=ico_sizes)
shutil.copy(ico_marca, ico_front)
shutil.copy(ico_marca, ico_base)

print("Todos os ícones e arquivos .ico gerados com sucesso!")
