# MODULE TRADUCTION KANTEKANT — Guide d'intégration
## translate.py + translate_router.py

---

## 1. FICHIERS À DÉPLOYER SUR RENDER (GitHub)

```
/backend/
  main.py              ← PASSAGE (existant — à modifier)
  clone.py             ← CLONE™  (existant — à modifier)
  translate.py         ← NOUVEAU module partagé
  translate_router.py  ← NOUVEAU endpoints FastAPI
  requirements.txt     ← ajouter : anthropic>=0.25.0
```

---

## 2. INTÉGRATION DANS main.py (PASSAGE)

### Ajouter en haut de main.py :
```python
from translate import translate_designations
from translate_router import router as translate_router

# Après app = FastAPI(...)
app.include_router(translate_router)
```

### Dans la fonction de traitement PDF, après extraction des produits :
```python
# Avant : désignations brutes du fournisseur
produits = extraire_produits(pdf)  # retourne list[dict] avec "designation"

# Après : désignations traduites et nettoyées
designations_brutes = [p["designation"] for p in produits]
designations_fr     = translate_designations(designations_brutes)

for i, prod in enumerate(produits):
    prod["designation"] = designations_fr[i]
```

---

## 3. INTÉGRATION DANS clone.py (CLONE™)

### Ajouter en haut de clone.py :
```python
from translate import translate_blocks
```

### Dans le pipeline CLONE, après extraction OCR :
```python
# Avant : blocs positionnels bruts
blocs = extraire_blocs_ocr(page)  
# [{"x": 72, "y": 540, "text": "Solar Panel 400W", "font_size": 12}, ...]

# Après : blocs traduits, coordonnées intactes
blocs_fr = translate_blocks(blocs)
# [{"x": 72, "y": 540, "text": "Panneau solaire 400W", "font_size": 12}, ...]

# Puis reconstruction PDF avec blocs_fr
reconstruire_pdf(blocs_fr, images, page_size)
```

---

## 4. ENDPOINTS DISPONIBLES APRÈS DÉPLOIEMENT

| Endpoint | Mode | Appelé par |
|---|---|---|
| `POST /translate/designations` | Liste produits | PASSAGE / main.py |
| `POST /translate/blocks` | Blocs positionnels | CLONE / clone.py |
| `POST /translate/text` | Texte libre | Futur usage |
| `GET /translate/detect?text=...` | Détection langue | Debug |

---

## 5. VARIABLE D'ENVIRONNEMENT REQUISE

Sur Render → Environment Variables :
```
ANTHROPIC_API_KEY = sk-ant-...
```
(Déjà présente si PASSAGE appelle déjà Claude API)

---

## 6. CE QUE LE MODULE SUPPRIME AUTOMATIQUEMENT

| Type | Exemple supprimé |
|---|---|
| Email fournisseur | sales@chredsun.com |
| Site web | www.yinneng.cn |
| Téléphone | +86 755 1234 5678 |
| Prix FOB | FOB Price: USD 890 |
| Prix usine | Factory cost: ¥5,200 |
| Nom fournisseur (si détecté) | Shenzhen CHREDSUN Co. Ltd |

## 7. CE QUE LE MODULE PRÉSERVE

| Type | Exemple conservé |
|---|---|
| Code produit | GS003, A6S, SKU-1234 |
| Dimensions | 6000×3000×2800mm |
| Puissance | 400W, 12V, 50Ah |
| Surface | 18 m², 74 m² |
| Certifications | CE, IP65, ISO 9001 |
| Chiffres purs | 2 ans garantie |

---

## 8. ARCHITECTURE FINALE

```
                    ┌─────────────────────────────┐
                    │     translate.py             │
                    │   MODULE PARTAGÉ             │
                    │                              │
                    │  detect_language()           │
                    │  _pre_clean()  (regex)       │
                    │  translate_designations()    │
                    │  translate_blocks()          │
                    │  translate_text()            │
                    └──────────┬──────────────────┘
                               │ Claude API
                    ┌──────────▼──────────────────┐
                    │   translate_router.py        │
                    │   FastAPI endpoints          │
                    │   /translate/designations    │
                    │   /translate/blocks          │
                    │   /translate/text            │
                    │   /translate/detect          │
                    └──────────┬──────────────────┘
                               │
              ┌────────────────┴───────────────────┐
              │                                     │
    ┌─────────▼──────────┐             ┌───────────▼──────────┐
    │     main.py        │             │      clone.py         │
    │     PASSAGE        │             │      CLONE™           │
    │  (tableaux PDF)    │             │  (layouts visuels)    │
    └─────────┬──────────┘             └───────────┬──────────┘
              │                                     │
    ┌─────────▼──────────┐             ┌───────────▼──────────┐
    │   index.html       │             │   clone_ui.html       │
    │   Frontend Netlify │             │   Frontend Netlify    │
    └────────────────────┘             └──────────────────────┘
```
