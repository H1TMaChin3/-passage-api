"""
translate_router.py — Endpoint FastAPI du MODULE TRADUCTION
À intégrer dans main.py de PASSAGE (Render)

Usage dans main.py :
    from translate_router import router as translate_router
    app.include_router(translate_router)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from translate import translate_designations, translate_blocks, translate_text, detect_language

router = APIRouter(prefix="/translate", tags=["Traduction"])


# ── Schémas d'entrée ──

class TranslateDesignationsRequest(BaseModel):
    """Mode PASSAGE : liste de désignations produit à traduire."""
    designations: list[str]

class TranslateBlocksRequest(BaseModel):
    """Mode CLONE : blocs texte positionnels à traduire."""
    blocks: list[dict]  # [{"x": float, "y": float, "text": str, ...}]

class TranslateTextRequest(BaseModel):
    """Mode texte libre."""
    text: str
    context: Optional[str] = None  # Ex: "fiche technique", "description produit"


# ── Schémas de sortie ──

class TranslateDesignationsResponse(BaseModel):
    designations_fr: list[str]
    langue_detectee: str
    count: int

class TranslateBlocksResponse(BaseModel):
    blocks: list[dict]
    langue_detectee: str
    blocs_traduits: int
    blocs_total: int

class TranslateTextResponse(BaseModel):
    text_fr: str
    langue_detectee: str


# ══════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@router.post("/designations", response_model=TranslateDesignationsResponse)
async def endpoint_translate_designations(req: TranslateDesignationsRequest):
    """
    MODE PASSAGE — Traduit une liste de désignations produit.
    Appelé par main.py après extraction des produits du PDF fournisseur.
    
    Exemple :
        POST /translate/designations
        {"designations": ["Solar Emergency Light GS003", "LED 600W Panel"]}
    
    Retour :
        {"designations_fr": ["Luminaire de secours solaire GS003", "Panneau LED 600W"], ...}
    """
    if not req.designations:
        raise HTTPException(status_code=400, detail="Liste de désignations vide")
    if len(req.designations) > 200:
        raise HTTPException(status_code=400, detail="Maximum 200 désignations par appel")

    try:
        sample = next((d for d in req.designations if d.strip()), '')
        lang   = detect_language(sample)
        result = translate_designations(req.designations)

        return TranslateDesignationsResponse(
            designations_fr=result,
            langue_detectee=lang,
            count=len(result)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de traduction : {str(e)}")


@router.post("/blocks", response_model=TranslateBlocksResponse)
async def endpoint_translate_blocks(req: TranslateBlocksRequest):
    """
    MODE CLONE — Traduit des blocs texte positionnels.
    Appelé par clone.py après extraction OCR du PDF source.
    Les coordonnées (x, y, font_size, etc.) sont préservées intactes.
    
    Exemple :
        POST /translate/blocks
        {"blocks": [{"x": 72, "y": 540, "text": "Solar Panel 400W", "font_size": 12}]}
    """
    if not req.blocks:
        raise HTTPException(status_code=400, detail="Liste de blocs vide")
    if len(req.blocks) > 5000:
        raise HTTPException(status_code=400, detail="Maximum 5000 blocs par appel")

    try:
        sample_text = ' '.join(b.get('text','') for b in req.blocks[:10])
        lang        = detect_language(sample_text)

        # Compter les blocs qui seront réellement traduits
        import re
        translatable = sum(
            1 for b in req.blocks
            if len(b.get('text','').strip()) >= 3
            and not re.fullmatch(r'[\d\s\-/.,:%°]+', b.get('text','').strip())
            and not re.fullmatch(r'[A-Z0-9\-_]{1,15}', b.get('text','').strip())
        )

        result = translate_blocks(req.blocks)

        return TranslateBlocksResponse(
            blocks=result,
            langue_detectee=lang,
            blocs_traduits=translatable,
            blocs_total=len(req.blocks)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de traduction : {str(e)}")


@router.post("/text", response_model=TranslateTextResponse)
async def endpoint_translate_text(req: TranslateTextRequest):
    """
    MODE TEXTE LIBRE — Traduit un bloc de texte brut.
    Pour descriptions longues, fiches techniques, etc.
    """
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Texte vide")

    try:
        lang   = detect_language(req.text)
        result = translate_text(req.text)

        return TranslateTextResponse(
            text_fr=result,
            langue_detectee=lang
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de traduction : {str(e)}")


@router.get("/detect")
async def endpoint_detect_language(text: str):
    """
    Détecte la langue d'un texte (GET rapide, pas de traduction).
    Utile pour debug ou pré-vérification.
    """
    lang = detect_language(text)
    labels = {'EN': 'Anglais', 'ZH': 'Chinois', 'FR': 'Français (déjà traduit)'}
    return {"langue": lang, "label": labels.get(lang, lang)}
