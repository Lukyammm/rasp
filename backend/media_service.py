"""
Serviço de Download Híbrido de Mídias e Carrosséis (Zero Token).
- Download híbrido de mídias: yt-dlp como primeira linha com fallback para Playwright com sessão logada
  (interceptando manifesto DASH/BaseURL e requisições .mp4).
- Download leve de imagens de carrosséis via HTTP direto com captura de accessibility_caption (alt text).
"""
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from typing import Dict, List, Optional, Tuple

from config import SESSIONS_DIR, session_dir_path, session_json_path

logger = logging.getLogger("rasp.media")

UA_GOOGLEBOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
UA_BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"


def _slug_from_url(url: str) -> str:
    clean = url.rstrip("/").split("?")[0]
    return clean.split("/")[-1]


def baixar_arquivo_http(url: str, destino: str, user_agent: str = UA_GOOGLEBOT, timeout: int = 60) -> bool:
    """Baixa um arquivo binário via HTTP com cabeçalhos apropriados."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": user_agent})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        os.makedirs(os.path.dirname(os.path.abspath(destino)), exist_ok=True)
        with open(destino, "wb") as f:
            f.write(data)
        return os.path.isfile(destino) and os.path.getsize(destino) > 0
    except Exception as exc:
        logger.warning("Falha ao baixar HTTP de %s: %s", url[:80], exc)
        return False


def _extrair_json_balanceado(texto: str, inicio: int):
    """Extrai um objeto ou array JSON balanceado a partir do caractere em texto[inicio]."""
    abre = texto[inicio]
    fecha = {"[": "]", "{": "}"}.get(abre)
    if not fecha:
        raise ValueError("Início não corresponde a [ ou {")
    nivel, em_string, escape = 0, False, False
    for i in range(inicio, len(texto)):
        c = texto[i]
        if em_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                em_string = False
        elif c == '"':
            em_string = True
        elif c in "[{":
            nivel += 1
        elif c in "]}":
            nivel -= 1
            if nivel == 0:
                return json.loads(texto[inicio:i + 1])
    raise ValueError("JSON sem fechamento balanceado")


def baixar_imagens_carrossel(url: str, pasta_destino: str, prefixo: str) -> List[dict]:
    """
    Download leve de imagens de posts/carrosséis sem abrir navegador (HTTP direto).
    Lê o JSON embutido na página pública (carousel_media ou image_versions2) e salva as imagens,
    capturando também o texto alternativo (accessibility_caption).
    """
    os.makedirs(pasta_destino, exist_ok=True)
    slug = _slug_from_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": UA_GOOGLEBOT})

    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            pagina = r.read().decode("utf-8", "replace")
    except Exception as exc:
        logger.warning("Carrossel: falha na requisição pública de %s: %s", url, exc)
        return []

    pos_code = pagina.find(f'"code":"{slug}"')
    janela_ini = max(0, pos_code - 200_000) if pos_code >= 0 else 0
    janela_fim = min(len(pagina), (pos_code if pos_code >= 0 else 0) + 400_000)
    trecho = pagina[janela_ini:janela_fim]

    itens = []
    k_carrossel = trecho.find('"carousel_media":[')
    if k_carrossel >= 0:
        try:
            itens = _extrair_json_balanceado(trecho, k_carrossel + len('"carousel_media":'))
        except Exception:
            itens = []

    if not itens:
        k_img = trecho.find('"image_versions2":{')
        if k_img >= 0:
            try:
                single_img = _extrair_json_balanceado(trecho, k_img + len('"image_versions2":'))
                itens = [{"image_versions2": single_img, "accessibility_caption": ""}]
            except Exception:
                itens = []

    arquivos_salvos = []
    for idx, it in enumerate(itens, 1):
        cands = (it.get("image_versions2") or {}).get("candidates") or []
        if not cands:
            continue
        # Escolhe a versão com maior resolução
        maior = max(cands, key=lambda c: (c.get("width") or 0) * (c.get("height") or 0))
        img_url = maior.get("url")
        alt = it.get("accessibility_caption") or ""
        is_video = bool(it.get("video_versions"))
        if not img_url:
            continue

        nome = f"{prefixo}_{slug}.{idx:02d}.jpg"
        destino = os.path.join(pasta_destino, nome)
        if baixar_arquivo_http(img_url, destino):
            arquivos_salvos.append({
                "arquivo": destino,
                "nome": nome,
                "alt": alt,
                "era_video": is_video,
                "url_origem": img_url,
            })

    logger.info("Carrossel baixado: %d imagens em %s", len(arquivos_salvos), pasta_destino)
    return arquivos_salvos


def _baixar_via_yt_dlp(url: str, pasta_destino: str, prefixo: str) -> List[str]:
    """Tenta baixar via yt-dlp diretamente."""
    os.makedirs(pasta_destino, exist_ok=True)
    slug = _slug_from_url(url)
    output_tmpl = os.path.join(pasta_destino, f"{prefixo}_{slug}.%(autonumber)s.%(ext)s")

    yt_dlp_bin = shutil.which("yt-dlp")
    cmd_base = [yt_dlp_bin] if yt_dlp_bin else [sys.executable, "-m", "yt_dlp"]
    cmd = cmd_base + [
        "--no-warnings",
        "--yes-playlist",
        "-f", "mp4/best",
        "-o", output_tmpl,
        url,
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        gerados = [
            os.path.join(pasta_destino, f)
            for f in os.listdir(pasta_destino)
            if f.startswith(f"{prefixo}_{slug}") and f.endswith((".mp4", ".mkv", ".webm"))
        ]
        if gerados:
            # Se for um único arquivo, renomeia para padrão simples
            if len(gerados) == 1 and ".1." in gerados[0]:
                final = os.path.join(pasta_destino, f"{prefixo}_{slug}.mp4")
                if not os.path.exists(final):
                    os.rename(gerados[0], final)
                gerados = [final]
            return gerados
    except Exception as exc:
        logger.warning("yt-dlp falhou para %s: %s", url, exc)
    return []


def _baixar_via_sessao_playwright(url: str, pasta_destino: str, prefixo: str) -> List[str]:
    """
    Fallback: Baixa mídias do Instagram/TikTok interceptando sessão logada e manifesto DASH/BaseURL.
    Reutiliza a infraestrutura de navegação e sessões do RASP com lock de concorrência.
    """
    os.makedirs(pasta_destino, exist_ok=True)
    slug = _slug_from_url(url)
    destino_mp4 = os.path.join(pasta_destino, f"{prefixo}_{slug}.mp4")

    # Identifica rede para pegar a sessão certa
    rede = "instagram" if "instagram" in url else ("tiktok" if "tiktok" in url else "facebook")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        try:
            from patchright.sync_api import sync_playwright
        except ImportError:
            logger.warning("Playwright/Patchright indisponível para fallback de mídia.")
            return []

    try:
        from scrapers.browser import network_lock, open_page

        with network_lock(rede):
            with sync_playwright() as pw:
                with open_page(pw, rede) as (page, mode):
                    capturadas = []
                    page.on("response", lambda r: capturadas.append(r.url) if ".mp4" in r.url.split("?")[0] else None)

                    page.goto(url, timeout=40000, wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)

                    # Clica no vídeo se necessário para forçar carregamento
                    try:
                        page.locator("video").first.click(timeout=3000)
                    except Exception:
                        pass
                    page.wait_for_timeout(3000)

                    # Busca URL do vídeo via DOM / regex / DASH BaseURL
                    js_src = """() => {
                        const v = [...document.querySelectorAll('video')].find(v => v.src && !v.src.startsWith('blob:'));
                        if (v) return v.src;
                        const m = document.documentElement.innerHTML.match(/"video_url":"([^"]+)"/);
                        if (m) return m[1].replace(/\\\\u0026/g, '&').replace(/\\\\\\//g, '/');
                        const base = document.documentElement.innerHTML.match(/<BaseURL>([^<]+)<\\/BaseURL>/);
                        if (base) return base[1].replace(/&amp;/g, '&');
                        return null;
                    }"""
                    src = page.evaluate(js_src) or next((u for u in capturadas if "_n.mp4" in u or ".mp4" in u), None)

                    if src:
                        ctx = page.context
                        resp = ctx.request.get(src, headers={"Referer": url})
                        if resp.status == 200:
                            with open(destino_mp4, "wb") as f:
                                f.write(resp.body())
                            if os.path.isfile(destino_mp4) and os.path.getsize(destino_mp4) > 0:
                                logger.info("Vídeo salvo com sucesso via sessão Playwright (%s): %s", mode, destino_mp4)
                                return [destino_mp4]
    except Exception as exc:
        logger.warning("Fallback Playwright falhou para %s: %s", url, exc)

    return []


def baixar_midia_hibrida(url: str, pasta_destino: str, prefixo: str = "post") -> List[str]:
    """
    Download híbrido: yt-dlp -> fallback Playwright com sessão logada e manifesto DASH/BaseURL.
    Retorna lista de caminhos de arquivos de vídeo/áudio baixados localmente.
    """
    gerados = _baixar_via_yt_dlp(url, pasta_destino, prefixo)
    if gerados:
        return gerados

    logger.info("yt-dlp não obteve mídia direta para %s. Acionando fallback com sessão...", url)
    gerados = _baixar_via_sessao_playwright(url, pasta_destino, prefixo)
    return gerados
