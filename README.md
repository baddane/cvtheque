# CVthèque

Application pour parser des CV (PDF, Word, images/scans) et les rendre
cherchables par ville, diplôme, compétences, etc.

Deux modes d'utilisation :

- **Local (tout-en-un)** : interface Streamlit + PostgreSQL Docker sur ton
  poste. C'est ce que décrit ce README.
- **En ligne (Vercel + Supabase)** : l'ingestion/OCR reste locale, mais la
  base et l'interface de recherche sont hébergées (base Supabase + app Next.js
  sur Vercel). Voir **[DEPLOIEMENT.md](DEPLOIEMENT.md)**.

> Pourquoi pas Streamlit directement sur Vercel ? Streamlit a besoin d'un
> serveur persistant, incompatible avec le serverless de Vercel ; l'OCR
> (Tesseract/OpenCV/Poppler) est également trop lourd pour ce runtime. On garde
> donc l'ingestion en local et on réécrit *uniquement l'interface de recherche*
> en Next.js pour Vercel — la logique PostgreSQL (recherche full-text + floue)
> est conservée à l'identique sur Supabase.

## 1. Prérequis système (à installer une seule fois)

### PostgreSQL
Le plus simple : avec Docker Desktop installé, lance simplement :
```bash
docker compose up -d
```
Ça crée une base PostgreSQL locale avec le schéma déjà appliqué.

Si tu ne veux pas de Docker, installe PostgreSQL directement, crée la base et
lance `schema.sql` dessus :
```bash
psql -U postgres -c "CREATE DATABASE cvtheque;"
psql -U postgres -d cvtheque -f schema.sql
```
(adapte alors les identifiants dans `config.py`)

### Tesseract OCR (obligatoire pour lire les scans/images)
- **Windows** : installe depuis https://github.com/UB-Mannheim/tesseract/wiki
  puis renseigne le chemin dans `config.py` -> `TESSERACT_CMD`
  (ex: `r"C:\Program Files\Tesseract-OCR\tesseract.exe"`)
- **Mac** : `brew install tesseract tesseract-lang`
- **Linux (Ubuntu/Debian)** : `sudo apt install tesseract-ocr tesseract-ocr-fra poppler-utils`

### Poppler (nécessaire pour convertir les PDF scannés en images)
- **Windows** : télécharge https://github.com/oschwartz10612/poppler-windows,
  ajoute le dossier `bin` au PATH
- **Mac** : `brew install poppler`
- **Linux** : inclus dans la commande apt ci-dessus

## 2. Installation Python

```bash
python -m venv venv
# Windows: venv\Scripts\activate | Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```

## 3. Utilisation

Tout se passe dans une seule commande et une seule interface :

```bash
streamlit run search_app.py
```

Ça ouvre une page dans ton navigateur (http://localhost:8501) avec deux onglets :

- **📥 Import de CV** : glisse-dépose tes fichiers (pdf, docx, images —
  les CV papier doivent d'abord être scannés en image ou PDF), clique sur
  "Enregistrer", puis sur "Lancer l'import". Une barre de progression et un
  journal en direct montrent l'avancement (OCR + parsing + insertion en
  base). Le fichier `logs/import_log.csv` garde une trace de chaque CV
  (ok / ocr_faible / erreur) — si tu relances un import, les fichiers déjà
  traités sont ignorés (utile sur un gros lot de 5000+ CV traité en
  plusieurs fois). Un historique complet est consultable dans cet onglet.
- **🔍 Recherche** : filtres par ville, diplôme, compétences, recherche
  libre, avec téléchargement du CV original et correction manuelle des
  champs mal détectés.

Le script `ingest.py` reste utilisable en ligne de commande (`python
ingest.py`) si tu préfères traiter un très gros lot sans passer par le
navigateur — les deux partagent le même code, donc le résultat est
identique.

## 4. Limites connues et pistes d'amélioration

- L'extraction des **expériences professionnelles précises** (poste, société,
  dates) reste heuristique : elle repère des lignes contenant une plage de
  dates, mais ne structure pas parfaitement poste/société. C'est le point le
  plus dur à automatiser sur des CV en formats libres non normalisés.
- Les dictionnaires (`dictionaries/villes_maroc.py`, `diplomes.py`,
  `competences.py`) sont volontairement des points de départ : plus tu les
  enrichis avec les termes réels de tes CV (intitulés de diplômes marocains
  spécifiques, outils métier ANAPEC, etc.), meilleure sera la détection.
- Sur les scans de mauvaise qualité, la qualité d'OCR peut être faible : le
  champ `statut_parsing` passe à `ocr_faible` pour repérer facilement ces
  CV à vérifier/corriger manuellement dans l'appli.
- La correction manuelle (ville/compétences) est directement possible dans
  l'appli Streamlit ; tu peux étendre `mettre_a_jour_champ()` dans `db.py`
  pour permettre la correction d'autres champs (diplômes, adresse...).
