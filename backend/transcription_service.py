"""
Serviço de Transcrição Fonética Local (Zero Token) via faster-whisper.
- Validação pre-flight de áudio via ffprobe (tem_audio) antes de acionar transcrição.
- faster-whisper em CPU int8 com 4 threads e filtro VAD.
- Filtro determinístico anti-alucinação por regex e logprob.
"""
import json
import logging
import os
import re
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("rasp.transcription")

ALUCINACOES = re.compile(
    r"(amara\.org|legendas pela comunidade|obrigad[oa] por assistir|inscreva-se no canal|"
    r"thanks? for watching|subtitles by|legendado por|tradução e legendas|deixe seu like|"
    r"compartilhe esse v[ií]deo)",
    re.I,
)

_MODEL_CACHE: Dict[str, object] = {}


def _ffprobe_bin() -> str:
    return shutil.which("ffprobe") or "ffprobe"


def tem_audio(caminho_midia: str) -> bool:
    """Verifica com ffprobe se o arquivo de mídia possui faixa de áudio válida."""
    if not os.path.isfile(caminho_midia):
        return False
    try:
        cmd = [
            _ffprobe_bin(),
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_type",
            "-of", "default=nw=1:nk=1",
            caminho_midia,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return "audio" in (res.stdout or "").strip().lower()
    except Exception as exc:
        logger.warning("Falha ao checar áudio com ffprobe em %s: %s", caminho_midia, exc)
        return False


def _get_whisper_model(modelo_nome: str = "large-v3-turbo", cpu_threads: int = 4):
    """Carrega ou reutiliza o modelo do Whisper em cache na memória."""
    global _MODEL_CACHE
    key = f"{modelo_nome}_cpu_{cpu_threads}"
    if key not in _MODEL_CACHE:
        from faster_whisper import WhisperModel
        logger.info("Carregando modelo faster-whisper '%s' (CPU int8, %d threads)...", modelo_nome, cpu_threads)
        _MODEL_CACHE[key] = WhisperModel(modelo_nome, device="cpu", compute_type="int8", cpu_threads=cpu_threads)
    return _MODEL_CACHE[key]


def transcrever_audio_local(
    caminho_midia: str,
    modelo_nome: str = "large-v3-turbo",
    cpu_threads: int = 4,
    fallback_model: str = "base",
) -> dict:
    """
    Executa transcrição fonética local de vídeo/áudio sem gasto de tokens de IA.
    Retorna dicionário com status, texto, segmentos e metadados.
    """
    if not os.path.isfile(caminho_midia):
        return {
            "status": "failed",
            "erro": f"Arquivo não encontrado: {caminho_midia}",
            "texto": "",
            "segmentos": [],
            "descartados": [],
            "duracao_s": 0.0,
        }

    if not tem_audio(caminho_midia):
        logger.info("Pre-flight ffprobe: %s não possui faixa de áudio. Transcrição dispensada.", os.path.basename(caminho_midia))
        return {
            "status": "no_audio",
            "texto": "",
            "segmentos": [],
            "descartados": [],
            "duracao_s": 0.0,
            "motivo": "Mídia sem faixa de áudio",
        }

    # Tenta com o modelo especificado; se falhar por memória/download, tenta modelo leve de fallback
    modelos_para_tentar = [modelo_nome]
    if fallback_model and fallback_model != modelo_nome:
        modelos_para_tentar.append(fallback_model)

    ultimo_erro = None
    for mod in modelos_para_tentar:
        try:
            modelo = _get_whisper_model(mod, cpu_threads=cpu_threads)
            segmentos_iter, info = modelo.transcribe(
                caminho_midia,
                beam_size=5,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
                condition_on_previous_text=False,
            )

            saida: List[dict] = []
            descartados: List[dict] = []
            for s in segmentos_iter:
                texto = (s.text or "").strip()
                # Filtro logprob e probabilidade de silêncio/música
                duvidoso = getattr(s, "no_speech_prob", 0.0) > 0.6 and getattr(s, "avg_logprob", 0.0) < -0.8
                if not texto or ALUCINACOES.search(texto) or duvidoso:
                    descartados.append({
                        "inicio": round(float(s.start or 0.0), 1),
                        "fim": round(float(s.end or 0.0), 1),
                        "texto": texto,
                        "motivo": "alucinacao_provavel" if (ALUCINACOES.search(texto) or duvidoso) else "vazio",
                    })
                    continue

                saida.append({
                    "inicio": round(float(s.start or 0.0), 1),
                    "fim": round(float(s.end or 0.0), 1),
                    "texto": texto,
                    "confianca_media": round(float(getattr(s, "avg_logprob", 0.0) or 0.0), 2),
                })

            texto_completo = " ".join(s["texto"] for s in saida).strip()
            return {
                "status": "done",
                "modelo": f"faster-whisper {mod} (int8, CPU)",
                "duracao_s": round(float(info.duration or 0.0), 1),
                "idioma": str(info.language or "pt"),
                "prob_idioma": round(float(info.language_probability or 1.0), 2),
                "segmentos": saida,
                "descartados": descartados,
                "texto": texto_completo,
            }
        except Exception as exc:
            logger.warning("Falha ao transcrever com modelo '%s': %s", mod, exc)
            ultimo_erro = exc

    return {
        "status": "failed",
        "erro": str(ultimo_erro),
        "texto": "",
        "segmentos": [],
        "descartados": [],
        "duracao_s": 0.0,
    }
