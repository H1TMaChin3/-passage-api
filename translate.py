"""
translate.py — MODULE TRADUCTION KANTEKANT
Module partagé PASSAGE + CLONE™

Rôle :
  - Détecte la langue source (EN / ZH)
  - Supprime toutes les données fournisseur sensibles
  - Traduit en français professionnel B.E Company
  - Préserve codes produits, chiffres, unités

Appelé par :
  - main.py    (PASSAGE — mode tableau)
  - clone.py   (CLONE™  — mode blocs positionnels)
"""

import re
import anthropic
from typing import Union

# ── Client Anthropic (clé lue depuis variable d'environnement ANTHROPIC_API_KEY) ──
_client = anthropic.Anthropic()
MODEL   = "claude-sonnet-4-20250514"

# ══════════════════════════════════════════════════════════════════
# SECTION 1 — DÉTECTION DE LANGUE
# ══════════════════════════════════════════════════════════════════

def detect_language(text: str) -> str:
    """
    Détecte la langue dominante d'un texte.
    Retourne : 'ZH', 'EN', ou 'FR' (déjà en français, rien à faire)
    """
    # Détection caractères CJK (chinois, japonais, coréen)
    cjk = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]', text))
    # Détection caractères latins
    latin = len(re.findall(r'[a-zA-Z]', text))
    # Heuristique simple
    if cjk > 10:
        return 'ZH'
    # Détection si déjà majoritairement français
    fr_markers = len(re.findall(
        r'\b(le|la|les|de|du|un|une|des|et|est|sont|pour|dans|avec|sur|par)\b',
        text, re.IGNORECASE
    ))
    if fr_markers > 5 and cjk == 0:
        return 'FR'
    return 'EN'


# ══════════════════════════════════════════════════════════════════
# SECTION 2 — NETTOYAGE PRÉALABLE (regex rapides)
# ══════════════════════════════════════════════════════════════════

# Patterns à supprimer AVANT d'envoyer à Claude
_CLEAN_PATTERNS = [
    # Emails
    r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
    # URLs / sites web
    r'https?://\S+',
    r'www\.[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}\S*',
    # Téléphones (formats variés)
    r'(?:\+?[\d\s\-().]{7,20})',
    # Prix FOB explicites (ex: FOB $1,234 / FOB ¥5000 / FOB Price: USD 890)
    r'(?:FOB|EXW|CIF|CNF)\s*(?:Price|Prix|:)?\s*[A-Z]{0,3}\s*[\$¥₩€]?\s*[\d,. ]+',
    # Lignes contenant "factory price", "supplier price", "our price"
    r'(?:factory|supplier|wholesale|ex-works|ex works)\s+(?:price|prix|cost)[^\n]*',
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _CLEAN_PATTERNS]

def _pre_clean(text: str) -> str:
    """Supprime rapidement les données sensibles évidentes par regex."""
    for pattern in _COMPILED:
        text = pattern.sub('', text)
    # Nettoyer les lignes devenues vides après suppression
    lines = [l.strip() for l in text.split('\n')]
    lines = [l for l in lines if l]
    return '\n'.join(lines)


# ══════════════════════════════════════════════════════════════════
# SECTION 3 — PROMPT SYSTÈME PARTAGÉ
# ══════════════════════════════════════════════════════════════════

_SYSTEM_PROMPT = """Tu es le moteur de traduction de KANTEKANT Group, société basée en Martinique (France).

Ta mission unique : transformer des textes de catalogues fournisseurs étrangers (anglais, chinois) 
en descriptions produits françaises professionnelles, prêtes à être présentées à des clients.

RÈGLES ABSOLUES — ne jamais enfreindre :
1. SUPPRIMER toute référence au fournisseur : nom, adresse, ville, pays d'origine, email, téléphone, site web
2. SUPPRIMER tout prix source : FOB, EXW, CIF, prix usine, prix fournisseur, coûts de production
3. SUPPRIMER les mentions de marque fournisseur si elles identifient la source (ex: "Yinneng", "CHREDSUN", "RIMAN")
4. CONSERVER intacts : codes produits alphanumériques (ex: GS003, A6S, SKU-1234), dimensions, poids, unités, certifications
5. CONSERVER les chiffres techniques (puissance en W, capacité en Ah, surface en m², etc.)
6. TRADUIRE en français clair, professionnel, adapté au commerce B2B martiniquais/caribéen
7. NE PAS inventer de caractéristiques — si une info manque, ne pas la compléter
8. TON : neutre, professionnel, sans superlatifs marketing excessifs

FORMAT DE RÉPONSE : texte français uniquement, même structure que l'entrée, pas d'explications."""

# ══════════════════════════════════════════════════════════════════
# SECTION 4 — MODE PASSAGE (liste de désignations produits)
# ══════════════════════════════════════════════════════════════════

def translate_designations(designations: list[str]) -> list[str]:
    """
    Mode PASSAGE — traduit une liste de désignations produit.
    
    Input  : ['Solar Emergency Light GS003', 'LED Panel 600W', ...]
    Output : ['Luminaire de secours solaire GS003', 'Panneau LED 600W', ...]
    """
    if not designations:
        return []

    # Pré-nettoyage
    cleaned = [_pre_clean(d) for d in designations]

    # Détecter la langue du premier texte non vide
    sample = next((d for d in cleaned if d.strip()), '')
    lang   = detect_language(sample)

    if lang == 'FR':
        return cleaned  # Déjà en français, rien à traduire

    # Construction du prompt utilisateur — format JSON numéroté pour parsing fiable
    numbered = '\n'.join(f'{i+1}. {d}' for i, d in enumerate(cleaned))

    user_prompt = f"""Voici {len(cleaned)} désignations produit en {'chinois' if lang == 'ZH' else 'anglais'}.
Traduis chacune en français professionnel en respectant les règles.
Réponds UNIQUEMENT avec la liste numérotée traduite, même format, rien d'autre.

{numbered}"""

    response = _client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )

    raw = response.content[0].text.strip()

    # Parser les lignes numérotées
    result = []
    for line in raw.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Retirer le préfixe "1. ", "2. " etc.
        match = re.match(r'^\d+\.\s*(.+)$', line)
        if match:
            result.append(match.group(1).strip())

    # Sécurité : si le parsing échoue, retourner les originaux nettoyés
    if len(result) != len(cleaned):
        return cleaned

    return result


# ══════════════════════════════════════════════════════════════════
# SECTION 5 — MODE CLONE (blocs texte positionnels)
# ══════════════════════════════════════════════════════════════════

def translate_blocks(blocks: list[dict]) -> list[dict]:
    """
    Mode CLONE™ — traduit une liste de blocs texte positionnels.
    
    Input  : [{"x": 72, "y": 540, "text": "Solar Panel 400W", "font_size": 12}, ...]
    Output : [{"x": 72, "y": 540, "text": "Panneau solaire 400W", "font_size": 12}, ...]
    
    Les coordonnées et métadonnées sont préservées intactes.
    Seul le champ "text" est traduit.
    """
    if not blocks:
        return []

    # Séparer les blocs à traduire des blocs à ignorer
    # (codes purs, chiffres seuls, très courts — inutile d'appeler l'API)
    translatable_idx = []
    for i, b in enumerate(blocks):
        txt = b.get('text', '').strip()
        if len(txt) < 3:
            continue  # Trop court, ignorer
        if re.fullmatch(r'[\d\s\-/.,:%°]+', txt):
            continue  # Que des chiffres/symboles, ignorer
        if re.fullmatch(r'[A-Z0-9\-_]{1,15}', txt):
            continue  # Code produit pur (ex: GS003, SKU-1A), ignorer
        translatable_idx.append(i)

    if not translatable_idx:
        return blocks

    # Détecter la langue sur un échantillon
    sample_text = ' '.join(blocks[i].get('text','') for i in translatable_idx[:5])
    lang = detect_language(sample_text)

    if lang == 'FR':
        return blocks  # Déjà en français

    # Pré-nettoyage uniquement sur les blocs sélectionnés
    texts_to_translate = [_pre_clean(blocks[i].get('text','')) for i in translatable_idx]

    # Envoi à Claude — groupé pour réduire les appels API
    BATCH_SIZE = 50  # blocs par appel
    translated_texts = []

    for start in range(0, len(texts_to_translate), BATCH_SIZE):
        batch = texts_to_translate[start:start + BATCH_SIZE]
        numbered = '\n'.join(f'{j+1}. {t}' for j, t in enumerate(batch))

        user_prompt = f"""Voici {len(batch)} fragments de texte extraits d'un catalogue produit en {'chinois' if lang == 'ZH' else 'anglais'}.
Traduis chacun en français professionnel en respectant les règles.
Réponds UNIQUEMENT avec la liste numérotée, même format, rien d'autre.

{numbered}"""

        response = _client.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )

        raw = response.content[0].text.strip()
        for line in raw.split('\n'):
            line = line.strip()
            if not line:
                continue
            match = re.match(r'^\d+\.\s*(.+)$', line)
            if match:
                translated_texts.append(match.group(1).strip())

    # Reconstruction des blocs avec textes traduits
    result_blocks = [b.copy() for b in blocks]  # Copie profonde légère

    # Sécurité : si nombre de résultats ne correspond pas, garder originaux
    if len(translated_texts) == len(translatable_idx):
        for k, idx in enumerate(translatable_idx):
            result_blocks[idx]['text'] = translated_texts[k]

    return result_blocks


# ══════════════════════════════════════════════════════════════════
# SECTION 6 — MODE TEXTE LIBRE (pour futures extensions)
# ══════════════════════════════════════════════════════════════════

def translate_text(text: str) -> str:
    """
    Mode texte libre — traduit un bloc de texte brut.
    Utile pour descriptions longues, fiches techniques, etc.
    """
    if not text or not text.strip():
        return text

    cleaned = _pre_clean(text)
    lang    = detect_language(cleaned)

    if lang == 'FR':
        return cleaned

    user_prompt = f"""Traduis ce texte de catalogue produit ({'chinois' if lang == 'ZH' else 'anglais'}) en français professionnel.
Respecte toutes les règles de suppression des données fournisseur.

{cleaned}"""

    response = _client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )

    return response.content[0].text.strip()
