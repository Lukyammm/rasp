"""
Serviço de Automação e Sanitização XSS de Logotipos SVG de Marcas Oficiais.
Baseado nas normas estritas do Domination IA (conferir_antigravity.py):
- Bloqueio estrito de <script>, <foreignObject>, <image>, url(http), javascript:, onload, onerror.
- Bloqueio de chamadas externas via href="http...".
- Validação estrutural de árvore XML (ElementTree).
- Validação de cor hexadecimal no padrão #RRGGBB.
- Limite de peso contra traçados brutos de imagem.
"""
import logging
import os
import re
import xml.etree.ElementTree as ET
from typing import Optional, Tuple

from config import LOGOS_DIR
from database import Brand, session_scope

logger = logging.getLogger("rasp.brand_logo")

PERIGOS_SVG = (
    "<script",
    "<foreignobject",
    "<image",
    "<iframe",
    "<object",
    "<embed",
    "<applet",
    "<meta",
    "<link",
    "url(http",
    "javascript:",
    "xlink:href=\"http",
)
MAX_SVG_BYTES = 120_000  # Máximo de 120 KB para evitar traçados pesados


def sanitizar_svg(svg_conteudo: str) -> Tuple[bool, str, Optional[str]]:
    """
    Valida e sanitiza código SVG.
    Retorna (valido: bool, svg_limpo_ou_erro: str, cor_detectada: Optional[str]).
    """
    if not svg_conteudo or not svg_conteudo.strip():
        return False, "Conteúdo SVG vazio", None

    bruto = svg_conteudo.strip()
    if len(bruto.encode("utf-8")) > MAX_SVG_BYTES:
        return False, f"SVG excede o limite de {MAX_SVG_BYTES // 1000} KB (provável traçado de imagem raster)", None

    baixo = bruto.lower()
    for perigo in PERIGOS_SVG:
        if perigo in baixo:
            return False, f"SVG contém elemento ou atributo perigoso: {perigo}", None

    # Bloqueia quaisquer manipuladores de evento HTML/SVG (onload, onclick, onerror, onmouseover, etc)
    if re.search(r"\bon[a-z]+\s*=", baixo):
        return False, "SVG contém manipulador de eventos dinâmico perigoso", None

    if "<!doctype" in baixo or "<!entity" in baixo:
        return False, "SVG contém declaração DTD/ENTITY não permitida", None

    if re.search(r'(?:href|xlink:href)\s*=\s*["\']https?:', bruto, re.I):
        return False, "SVG aponta para recurso externo por href ou xlink:href", None

    try:
        raiz = ET.fromstring(bruto)
        # Remove namespace se houver para checar tag
        tag = raiz.tag.split("}")[-1] if "}" in raiz.tag else raiz.tag
        if tag.lower() != "svg":
            return False, "Elemento raiz deve ser <svg>", None
    except ET.ParseError as exc:
        return False, f"XML inválido: {exc}", None

    # Detecta ou extrai cor dominante do SVG se existir (ex.: fill="#...")
    cor_m = re.search(r'fill=["\'](#[0-9A-Fa-f]{6})["\']', bruto)
    cor = cor_m.group(1).upper() if cor_m else None

    return True, bruto, cor


def salvar_logo_marca(nome_marca: str, svg_conteudo: str, cor_hex: Optional[str] = None) -> dict:
    """Valida, sanitiza e persiste o logo SVG da marca no banco e em disco."""
    nome_marca_limpo = str(nome_marca or "").strip()
    if not nome_marca_limpo:
        raise ValueError("Nome da marca não pode ser vazio.")

    valido, resultado, cor_detectada = sanitizar_svg(svg_conteudo)
    if not valido:
        raise ValueError(resultado)

    cor_final = cor_hex or cor_detectada or ""
    if cor_final and not re.fullmatch(r"#[0-9A-Fa-f]{6}", cor_final):
        raise ValueError(f"Cor inválida: {cor_final}. Deve ser formato hexadecimal de 6 dígitos (#RRGGBB).")

    os.makedirs(LOGOS_DIR, exist_ok=True)
    slug_marca = re.sub(r"[^\w-]", "_", nome_marca_limpo.lower())
    caminho_svg = os.path.join(LOGOS_DIR, f"{slug_marca}.svg")
    with open(caminho_svg, "w", encoding="utf-8") as f:
        f.write(resultado)

    with session_scope() as db:
        brand = db.get(Brand, nome_marca)
        if not brand:
            brand = Brand(name=nome_marca)
            db.add(brand)
        brand.logo_svg = resultado
        if cor_final:
            brand.color = cor_final

    logger.info("Logo SVG salvo com sucesso para a marca '%s' (%s)", nome_marca, caminho_svg)
    return {
        "marca": nome_marca,
        "arquivo": caminho_svg,
        "cor": cor_final,
        "tamanho_bytes": len(resultado.encode("utf-8")),
    }


def obter_logo_marca(nome_marca: str) -> Optional[dict]:
    """Retorna o logo SVG e cor cadastrados para a marca."""
    with session_scope() as db:
        brand = db.get(Brand, nome_marca)
        if brand and brand.logo_svg:
            return {
                "marca": brand.name,
                "logo_svg": brand.logo_svg,
                "color": brand.color or "",
            }
    return None
