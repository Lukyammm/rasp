"""
Serviço de Processamento de Vídeo e Varredura Visual Rápida (Zero Token).
- Geração de Folha de Contato 4x4 (Contact Sheet) em FFmpeg com carimbos de tempo embutidos (pts:hms).
- Detecção inteligente de cortes de cena via FFmpeg (scene > 0.08) para capturar quadros-chave em resolução original.
- Extração de quadros cheios com tempos distribuídos e pontos centrais de cena.
- Desduplicação temporal de texto em vídeo (OCR deduplication).
"""
import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("rasp.video")

PADRAO_QUADROS = 16
LIMIAR_CENA = 0.08  # Calibrado em Dominação IA: cortes reais sem ruído de compressão
CENA_MINIMA = 0.25  # Segundos; cortes menores são transições visuais


def _ffmpeg_bin() -> str:
    return shutil.which("ffmpeg") or "ffmpeg"


def _ffprobe_bin() -> str:
    return shutil.which("ffprobe") or "ffprobe"


def duracao_video(video_path: str) -> float:
    """Retorna a duração exata do vídeo em segundos via ffprobe."""
    if not os.path.isfile(video_path):
        return 0.0
    try:
        cmd = [
            _ffprobe_bin(),
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            video_path,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if r.returncode == 0 and r.stdout:
            data = json.loads(r.stdout)
            return float(data.get("format", {}).get("duration", 0.0))
    except Exception as exc:
        logger.warning("Falha ao ler duração de %s: %s", video_path, exc)
    return 0.0


def gerar_folha_contato_4x4(
    video_path: str,
    destino_jpg: str,
    num_quadros: int = 16,
) -> Optional[str]:
    """
    Gera uma Folha de Contato (grade 4x4, 16 quadros) com carimbos de tempo pts:hms embutidos.
    Permite leitura visual ultrarrápida do conteúdo sem reproduzir o vídeo.
    """
    if not os.path.isfile(video_path):
        return None

    os.makedirs(os.path.dirname(os.path.abspath(destino_jpg)), exist_ok=True)
    d = duracao_video(video_path)
    if d <= 0:
        d = 1.0

    fps = num_quadros / max(d, 1.0)
    filtro = (
        f"fps={fps:.5f},scale=360:-2,"
        f"drawtext=text='%{{pts\\:hms}}':x=6:y=6:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.6,"
        f"tile=4x4:padding=4:color=0x222222"
    )

    cmd = [
        _ffmpeg_bin(),
        "-v", "error",
        "-y",
        "-i", video_path,
        "-vf", filtro,
        "-frames:v", "1",
        "-update", "1",
        "-q:v", "4",
        destino_jpg,
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if os.path.isfile(destino_jpg) and os.path.getsize(destino_jpg) > 0:
            logger.info("Folha de contato 4x4 gerada: %s (%d KB)", destino_jpg, os.path.getsize(destino_jpg) // 1024)
            return destino_jpg
        logger.warning("Falha na geração da folha de contato: %s", r.stderr.strip()[:200])
    except Exception as exc:
        logger.exception("Erro ao executar ffmpeg para folha de contato: %s", exc)

    return None


def detectar_cortes_de_cena(video_path: str, limiar: float = LIMIAR_CENA) -> List[float]:
    """
    Detecta cortes e transições de cena reais no vídeo usando o filtro FFmpeg scene.
    Retorna lista ordenada de timestamps em segundos.
    """
    if not os.path.isfile(video_path):
        return []

    cmd = [
        _ffmpeg_bin(),
        "-hide_banner",
        "-i", video_path,
        "-vf", f"scale=180:-1,select='gt(scene,{limiar})',showinfo",
        "-an",
        "-f", "null",
        "-",
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        pontos = [float(m) for m in re.findall(r"pts_time:([\d.]+)", r.stderr or "")]
        logger.info("Cortes de cena detectados em %s: %d cortes", os.path.basename(video_path), len(pontos))
        return sorted(list(set(pontos)))
    except Exception as exc:
        logger.warning("Erro ao detectar cortes de cena: %s", exc)
        return []


def cenas_sem_quadro(cortes: List[float], d: float, tempos_fixos: List[float]) -> List[float]:
    """
    Identifica o instante central de cada cena em que nenhum dos tempos da grade regular caiu.
    Garante cobertura de cartões rápidos que passam despercebidos entre os 16 quadros.
    """
    limites = [0.0] + cortes + [d]
    meios = []
    for a, b in zip(limites, limites[1:]):
        if (b - a) >= CENA_MINIMA and not any(a <= t < b for t in tempos_fixos):
            meios.append((a + b) / 2.0)
    return meios


def extrair_quadros_originais(
    video_path: str,
    pasta_destino: str,
    quantos: int = PADRAO_QUADROS,
    incluir_cenas: bool = True,
) -> List[str]:
    """
    Extrai quadros no tamanho original para leitura de código, interfaces e prompts.
    Extrai os instantes regulares (q01..q16) e pontos centrais de cenas não cobertas (c01..cNN).
    """
    if not os.path.isfile(video_path):
        return []

    d = duracao_video(video_path)
    if d <= 0:
        return []

    os.makedirs(pasta_destino, exist_ok=True)
    tempos_regulares = [i * d / quantos for i in range(quantos) if (i * d / quantos) < d]
    gerados: List[str] = []

    def rotulo_tempo(s: float) -> str:
        m, seg = divmod(int(s), 60)
        return f"t{m:02d}m{seg:02d}s"

    def extrair_ponto(t: float, nome_arquivo: str):
        caminho = os.path.join(pasta_destino, nome_arquivo)
        if not os.path.exists(caminho):
            cmd = [
                _ffmpeg_bin(),
                "-v", "error",
                "-y",
                "-ss", f"{t:.3f}",
                "-i", video_path,
                "-frames:v", "1",
                "-q:v", "2",
                caminho,
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if os.path.isfile(caminho) and os.path.getsize(caminho) > 0:
            gerados.append(caminho)

    # 1. Quadros regulares (q01..qNN)
    for i, t in enumerate(tempos_regulares, 1):
        extrair_ponto(t, f"q{i:02d}_{rotulo_tempo(t)}.jpg")

    # 2. Quadros de cenas exclusivas (c01..cNN)
    if incluir_cenas:
        cortes = detectar_cortes_de_cena(video_path)
        extras = cenas_sem_quadro(cortes, d, tempos_regulares)
        for i, t in enumerate(extras, 1):
            extrair_ponto(t, f"c{i:02d}_{rotulo_tempo(t)}.jpg")

    logger.info("Extraídos %d quadros em %s", len(gerados), pasta_destino)
    return gerados


def deduplicar_linhas_ocr(quadros_ocr) -> dict:
    """
    Desduplicação temporal de texto em vídeo (baseado em Dominação IA ler_ocr.py).
    Recebe quadros com linhas de texto extraídas e elimina repetições sucessivas,
    preservando apenas texto novo que aparece pela primeira vez com seu respectivo quadro.
    Aceita tanto uma lista de quadros quanto o dicionário raiz de saída do OCR.
    """
    def chave(linha: str) -> str:
        return re.sub(r"\s+", " ", str(linha or "")).strip().lower()

    if isinstance(quadros_ocr, dict):
        quadros_lista = quadros_ocr.get("quadros", [])
        sem_texto_inicial = len(quadros_ocr.get("sem_texto", []))
    else:
        quadros_lista = quadros_ocr or []
        sem_texto_inicial = 0

    vistas = set()
    linhas_unicas = []
    quadros_relevantes = []
    sem_texto = sem_texto_inicial

    for q in quadros_lista:
        nome = q.get("arquivo", "quadro")
        linhas = q.get("texto", [])
        if not linhas:
            sem_texto += 1
            continue

        novas = [l for l in linhas if chave(l) and chave(l) not in vistas]
        if novas:
            vistas |= {chave(l) for l in novas}
            quadros_relevantes.append({"arquivo": nome, "tipo": q.get("tipo", "outro"), "novas_linhas": novas})
            linhas_unicas.extend(novas)

    return {
        "total_linhas_unicas": len(linhas_unicas),
        "quadros_relevantes": quadros_relevantes,
        "quadros_sem_texto": sem_texto,
        "texto_consolidado": "\n".join(linhas_unicas),
    }
