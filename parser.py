"""
Parsing "métier" : à partir du texte brut extrait d'un CV, on essaie de
détecter les champs structurés utiles à la recherche.

NB: l'extraction d'expériences précises est intrinsèquement difficile sur des
CV en formats libres. On adopte une approche pragmatique par mots-clés et
regex, pas du NLP lourd. Le but est de rendre les CV *cherchables*, pas
d'avoir un parsing parfait à 100%. Un champ non détecté reste vide et peut
être corrigé manuellement dans l'appli de recherche.
"""
import re
from unidecode import unidecode

from dictionaries.villes_maroc import VILLES_MAROC
from dictionaries.diplomes import DIPLOMES_KEYWORDS
from dictionaries.competences import COMPETENCES_KEYWORDS

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
TEL_RE = re.compile(r"(?:\+212|0)[\s.-]?[5-7](?:[\s.-]?\d{2}){4}")
BAC_PLUS_RE = re.compile(r"bac\s*\+?\s*(\d)", re.IGNORECASE)
ANNEE_RANGE_RE = re.compile(
    r"(\d{2}/\d{4}|\d{4})\s*(?:-|à|au|jusqu'à)\s*(\d{2}/\d{4}|\d{4}|present|présent|aujourd'hui)",
    re.IGNORECASE,
)


def _normaliser(texte: str) -> str:
    return unidecode(texte or "").lower()


def extraire_email(texte: str) -> str | None:
    m = EMAIL_RE.search(texte)
    return m.group(0) if m else None


def extraire_telephone(texte: str) -> str | None:
    m = TEL_RE.search(texte)
    if not m:
        return None
    return re.sub(r"[\s.-]", "", m.group(0))


def extraire_ville(texte: str) -> str | None:
    texte_norm = _normaliser(texte)
    for ville in VILLES_MAROC:
        if _normaliser(ville) in texte_norm:
            return ville
    return None


def extraire_adresse(texte: str) -> str | None:
    """Cherche une ligne commençant par un mot-clé d'adresse."""
    for ligne in texte.splitlines():
        ligne_norm = _normaliser(ligne)
        if any(mot in ligne_norm for mot in ["adresse", "address", "domicile", "residence"]):
            # on retire le préfixe "Adresse :" etc.
            nettoye = re.sub(r"(?i)^(adresse|address|domicile|residence)\s*[:\-]?\s*", "", ligne.strip())
            if len(nettoye) > 3:
                return nettoye
    return None


def extraire_diplomes(texte: str) -> list[str]:
    texte_norm = _normaliser(texte)
    trouves = set()

    for diplome in DIPLOMES_KEYWORDS:
        if _normaliser(diplome) in texte_norm:
            trouves.add(diplome)

    for m in BAC_PLUS_RE.finditer(texte):
        trouves.add(f"Bac+{m.group(1)}")

    return sorted(trouves)


def extraire_competences(texte: str) -> list[str]:
    texte_norm = _normaliser(texte)
    trouvees = set()
    for competence in COMPETENCES_KEYWORDS:
        if _normaliser(competence) in texte_norm:
            trouvees.add(competence)
    return sorted(trouvees)


def extraire_experiences(texte: str) -> list[dict]:
    """
    Détection heuristique de périodes d'expérience: on repère les lignes
    contenant une plage de dates (ex: "01/2019 - 03/2021") et on garde la
    ligne comme intitulé brut. Pensé pour être affiné/corrigé manuellement.
    """
    experiences = []
    for ligne in texte.splitlines():
        m = ANNEE_RANGE_RE.search(ligne)
        if m:
            experiences.append({
                "periode": m.group(0),
                "intitule_brut": ligne.strip(),
            })
    return experiences


def extraire_nom_prenom(texte: str, nom_fichier: str) -> str | None:
    """
    Heuristique simple: on prend la première ligne non vide du CV si elle
    ressemble à un nom (2-4 mots, pas de chiffres, pas trop long).
    Sinon on retombe sur le nom de fichier nettoyé.
    """
    for ligne in texte.splitlines():
        ligne = ligne.strip()
        if not ligne:
            continue
        mots = ligne.split()
        if 1 < len(mots) <= 4 and not any(c.isdigit() for c in ligne) and len(ligne) < 50:
            return ligne
        break  # on ne regarde que la toute première ligne non vide

    # fallback: nom de fichier sans extension ni underscores
    base = re.sub(r"\.\w+$", "", nom_fichier)
    return base.replace("_", " ").replace("-", " ").strip()


def parser_cv(texte: str, nom_fichier: str) -> dict:
    """Point d'entrée: transforme le texte brut en dictionnaire de champs structurés."""
    return {
        "nom_prenom": extraire_nom_prenom(texte, nom_fichier),
        "email": extraire_email(texte),
        "telephone": extraire_telephone(texte),
        "ville": extraire_ville(texte),
        "adresse": extraire_adresse(texte),
        "diplomes": extraire_diplomes(texte),
        "competences": extraire_competences(texte),
        "experiences": extraire_experiences(texte),
    }
