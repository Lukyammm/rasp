import base64
import io
import os
import shutil

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MARCA_DIR = os.path.join(BASE_DIR, "marca")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Logo v4 (12/10/2026): placa cobalto em isométrico com a ponta descascando e o verso terracota.
# O símbolo é uma imagem gerada no Antigravity sobre fundo magenta (marca/fonte/rasp_simbolo_chroma.png);
# este script tira o magenta, monta ícone, lockups e .ico. A v3 (barras) está em marca/_v3_ondas/.
FONTE = os.path.join(MARCA_DIR, "fonte", "rasp_simbolo_chroma.png")
OBSIDIAN = "#090A0F"
ALABASTRO = "#FAF8F5"
LADO = 2048


def tirar_magenta(caminho):
    """Fundo magenta vira transparente; na borda, desfaz a mistura com o magenta."""
    rgb = np.asarray(Image.open(caminho).convert("RGB")).astype(np.float32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    # Magenta tem R e B altos e G zero: min(R,B)-G vale ~255 no fundo e fica negativo no azul e no terracota.
    m = np.minimum(r, b) - g
    # O magenta gerado não é puro (#FE17F9 nos cantos): o limiar e a cor de fundo saem da borda da imagem.
    borda = np.concatenate([rgb[:40].reshape(-1, 3), rgb[-40:].reshape(-1, 3)])
    m_borda = np.concatenate([m[:40].ravel(), m[-40:].ravel()])
    limiar = np.percentile(m_borda, 0.5) - 6.0
    alfa = np.clip((limiar - m) / (limiar + 40.0), 0.0, 1.0)
    magenta = np.median(borda, axis=0)
    a = np.maximum(alfa, 1e-3)[..., None]
    cor = np.clip((rgb - (1.0 - a) * magenta) / a, 0, 255)
    rgba = np.dstack([cor, alfa * 255.0]).astype(np.uint8)
    im = Image.fromarray(rgba, "RGBA")
    return im.crop(im.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox())


def no_quadro(simbolo, lado, ocupa):
    """Centraliza o símbolo num quadro transparente, com a largura em `ocupa` do lado."""
    w = int(lado * ocupa)
    h = round(simbolo.height * w / simbolo.width)
    quadro = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    quadro.alpha_composite(simbolo.resize((w, h), Image.Resampling.LANCZOS), ((lado - w) // 2, (lado - h) // 2))
    return quadro


def icone(simbolo, lado):
    # Sem fundo (pedido do Lukyam, 12/10/2026): só a placa, ocupando quase toda a largura para render em 16px.
    return no_quadro(simbolo, lado, 0.98)


def png_b64(im, lado=None):
    if lado:
        im = im.resize((lado, lado), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def svg_com_png(im, lado):
    # Não é vetor: o símbolo tem volume e foi gerado como imagem. O SVG só embala o PNG.
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {lado} {lado}" width="{lado}" height="{lado}">'
            f'<image width="{lado}" height="{lado}" href="data:image/png;base64,{png_b64(im, lado)}"/></svg>')


simbolo = tirar_magenta(FONTE)
img_simbolo = no_quadro(simbolo, LADO, 0.92)
img_icone = icone(simbolo, LADO)

simbolo_png = os.path.join(MARCA_DIR, "rasp_simbolo_1024.png")
icone_png = os.path.join(MARCA_DIR, "rasp_icone_1024.png")
img_simbolo.save(simbolo_png)
img_icone.save(icone_png)

with open(os.path.join(MARCA_DIR, "rasp_simbolo.svg"), "w", encoding="utf-8") as f:
    f.write(svg_com_png(img_simbolo, 1024))
with open(os.path.join(MARCA_DIR, "rasp_icone.svg"), "w", encoding="utf-8") as f:
    f.write(svg_com_png(img_icone, 1024))
with open(os.path.join(FRONTEND_DIR, "logo.svg"), "w", encoding="utf-8") as f:
    f.write(svg_com_png(img_simbolo, 256))

SIMB = "data:image/png;base64," + png_b64(img_simbolo, 512)
ICON = "data:image/png;base64," + png_b64(img_icone, 512)

HTML_RENDER = f"""<html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@800&display=swap" rel="stylesheet">
<style>
body{{margin:0;background:#777;font-family:'Plus Jakarta Sans',sans-serif}}
.lock{{display:inline-flex;align-items:center;gap:18px;padding:36px 48px}}
.lock img{{width:110px;height:110px}}
.lock b{{font-size:84px;font-weight:800;letter-spacing:-.025em;line-height:1}}
#logo-escuro{{background:{OBSIDIAN};color:{ALABASTRO}}}
#logo-claro{{background:{ALABASTRO};color:{OBSIDIAN}}}
#apresentacao{{width:1440px;height:900px;background:{OBSIDIAN};display:grid;grid-template-columns:1fr 1fr}}
#apresentacao .esq{{display:flex;align-items:center;justify-content:center}}
#apresentacao .esq img{{width:560px;height:560px}}
#apresentacao .dir{{display:flex;flex-direction:column;justify-content:center;gap:40px;padding-right:96px}}
.tam{{display:flex;align-items:flex-end;gap:28px}}
.tile{{background:{ALABASTRO};border-radius:8px;display:flex;justify-content:center}}
</style></head><body>
<div><div class="lock" id="logo-escuro"><img src="{SIMB}"><b>RASP</b></div></div>
<div><div class="lock" id="logo-claro"><img src="{SIMB}"><b>RASP</b></div></div>
<div id="apresentacao">
  <div class="esq"><img src="{SIMB}"></div>
  <div class="dir">
    <div class="lock" style="padding:0;color:{ALABASTRO}"><img src="{SIMB}"><b>RASP</b></div>
    <div class="tile"><div class="lock" style="color:{OBSIDIAN}"><img src="{SIMB}"><b>RASP</b></div></div>
    <div class="tam">
      <img src="{ICON}" width="128" height="128"><img src="{ICON}" width="64" height="64">
      <img src="{ICON}" width="32" height="32"><img src="{ICON}" width="16" height="16">
    </div>
  </div>
</div>
</body></html>"""

render_html_path = os.path.join(MARCA_DIR, "_render_temp.html")
with open(render_html_path, "w", encoding="utf-8") as f:
    f.write(HTML_RENDER)

print("Iniciando renderização Playwright...")
with sync_playwright() as p:
    try:
        browser = p.chromium.launch(channel="chrome")
    except Exception:
        browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=2)
    page.goto("file:///" + os.path.abspath(render_html_path).replace(os.sep, "/"))
    page.wait_for_timeout(1500)
    for el, nome in (("#logo-escuro", "rasp_logo_escuro.png"), ("#logo-claro", "rasp_logo_claro.png"),
                     ("#apresentacao", "rasp_logo_apresentacao.png")):
        page.locator(el).screenshot(path=os.path.join(MARCA_DIR, nome))
        print(f"{nome} gerado.")
    browser.close()

os.remove(render_html_path)

print("Gerando arquivos do frontend e .ico...")
shutil.copy(simbolo_png, os.path.join(FRONTEND_DIR, "logo.png"))
img_icone.resize((256, 256), Image.Resampling.LANCZOS).save(os.path.join(FRONTEND_DIR, "favicon.png"), format="PNG")

ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
ico_marca = os.path.join(MARCA_DIR, "rasp_icon.ico")
img_icone.resize((256, 256), Image.Resampling.LANCZOS).save(ico_marca, format="ICO", sizes=ico_sizes)
shutil.copy(ico_marca, os.path.join(FRONTEND_DIR, "favicon.ico"))
shutil.copy(ico_marca, os.path.join(BASE_DIR, "rasp_icon.ico"))
# O atalho da área de trabalho aponta para rasp_icon_v5.ico: nome novo para o Windows não mostrar o ícone do cache.
# Se o ícone mudar de novo, trocar o número aqui e no atalho (Desktop\RASP.lnk).
shutil.copy(ico_marca, os.path.join(BASE_DIR, "rasp_icon_v5.ico"))

print("Todos os ícones e arquivos .ico gerados com sucesso!")
