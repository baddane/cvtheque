"""
Script principal d'ingestion des CV.

Usage:
    python ingest.py

Dépose tes fichiers (pdf, docx, images) dans CONFIG["DOSSIER_CV"], puis lance
ce script. Il traite chaque fichier, extrait le texte (avec OCR si besoin),
parse les champs, insère en base, puis déplace le fichier vers
"cv_traites" (succès) ou "cv_erreurs" (échec).

Un log CSV (CONFIG["LOG_CSV"]) permet de reprendre le traitement là où il
s'est arrêté si le script est interrompu sur un gros lot (utile pour >5000
CV) : les fichiers déjà marqués "ok" dans le log sont ignorés au relaunch.
"""
import csv
import os
import shutil
from datetime import datetime

from tqdm import tqdm

from config import CONFIG
from db import get_connection, inserer_cv
from parser import parser_cv
from extractors.pdf_extractor import extract_text_from_pdf
from extractors.docx_extractor import extract_text_from_docx
from extractors.image_extractor import extract_text_from_image


def charger_log() -> dict:
    """Charge le log CSV existant -> {filename: statut}."""
    log = {}
    if os.path.exists(CONFIG["LOG_CSV"]):
        with open(CONFIG["LOG_CSV"], newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                log[row["filename"]] = row["statut"]
    return log


def ajouter_log(filename: str, statut: str, message: str = ""):
    os.makedirs(os.path.dirname(CONFIG["LOG_CSV"]), exist_ok=True)
    fichier_existe = os.path.exists(CONFIG["LOG_CSV"])
    with open(CONFIG["LOG_CSV"], "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not fichier_existe:
            writer.writerow(["filename", "statut", "message", "date"])
        writer.writerow([filename, statut, message, datetime.now().isoformat()])


def detecter_type_et_extraire(filepath: str) -> tuple[str, str, str]:
    """Retourne (texte, methode, file_type)."""
    ext = os.path.splitext(filepath)[1].lower()

    if ext in CONFIG["EXTENSIONS_PDF"]:
        texte, methode = extract_text_from_pdf(filepath)
        return texte, methode, "pdf"

    if ext in CONFIG["EXTENSIONS_DOCX"]:
        texte, methode = extract_text_from_docx(filepath)
        return texte, methode, "docx"

    if ext in CONFIG["EXTENSIONS_IMAGE"]:
        texte, methode = extract_text_from_image(filepath)
        return texte, methode, "image"

    raise ValueError(f"Extension non supportée: {ext}")


def traiter_fichier(conn, filepath: str) -> str:
    """Traite un fichier unique. Retourne le statut final ('ok', 'ocr_faible', 'erreur')."""
    filename = os.path.basename(filepath)

    try:
        texte, methode, file_type = detecter_type_et_extraire(filepath)
    except Exception as e:
        ajouter_log(filename, "erreur", f"extraction: {e}")
        shutil.move(filepath, os.path.join(CONFIG["DOSSIER_ERREURS"], filename))
        return "erreur"

    if not texte or len(texte.strip()) < 5:
        ajouter_log(filename, "erreur", "texte vide après extraction/OCR")
        shutil.move(filepath, os.path.join(CONFIG["DOSSIER_ERREURS"], filename))
        return "erreur"

    statut_parsing = "ok"
    if len(texte.strip()) < CONFIG["SEUIL_OCR_FAIBLE"]:
        statut_parsing = "ocr_faible"

    champs = parser_cv(texte, filename)

    data = {
        "filename": filename,
        "filepath": filepath,  # chemin d'origine gardé comme identifiant unique
        "file_type": file_type,
        "raw_text": texte,
        "statut_parsing": statut_parsing,
        **champs,
    }

    try:
        inserer_cv(conn, data)
    except Exception as e:
        ajouter_log(filename, "erreur", f"insertion DB: {e}")
        shutil.move(filepath, os.path.join(CONFIG["DOSSIER_ERREURS"], filename))
        return "erreur"

    destination = os.path.join(CONFIG["DOSSIER_TRAITES"], filename)
    shutil.move(filepath, destination)
    ajouter_log(filename, statut_parsing, f"methode={methode}")
    return statut_parsing


def lister_fichiers_a_traiter() -> list[str]:
    """Retourne les noms de fichiers présents dans DOSSIER_CV qui ne sont pas
    déjà marqués 'ok' ou 'ocr_faible' dans le log CSV."""
    for dossier in [CONFIG["DOSSIER_CV"], CONFIG["DOSSIER_TRAITES"], CONFIG["DOSSIER_ERREURS"]]:
        os.makedirs(dossier, exist_ok=True)

    log_existant = charger_log()
    fichiers = [
        f for f in os.listdir(CONFIG["DOSSIER_CV"])
        if os.path.isfile(os.path.join(CONFIG["DOSSIER_CV"], f))
    ]
    return [f for f in fichiers if log_existant.get(f) not in ("ok", "ocr_faible")]


def executer_import(conn, fichiers_a_traiter: list[str] | None = None, callback=None) -> dict:
    """
    Exécute l'import pour la liste de fichiers donnée (ou tous ceux en attente
    si None). `callback(index, total, filename, statut)` est appelé après
    chaque fichier traité — utilisé par ingest.py (CLI) et search_app.py
    (interface Streamlit) pour afficher la progression.
    Retourne un dict de compteurs {statut: nombre}.
    """
    if fichiers_a_traiter is None:
        fichiers_a_traiter = lister_fichiers_a_traiter()

    compteurs = {"ok": 0, "ocr_faible": 0, "erreur": 0}
    total = len(fichiers_a_traiter)

    for i, filename in enumerate(fichiers_a_traiter, start=1):
        filepath = os.path.join(CONFIG["DOSSIER_CV"], filename)
        statut = traiter_fichier(conn, filepath)
        compteurs[statut] = compteurs.get(statut, 0) + 1
        if callback:
            callback(i, total, filename, statut)

    return compteurs


def main():
    fichiers = [
        f for f in os.listdir(CONFIG["DOSSIER_CV"])
        if os.path.isfile(os.path.join(CONFIG["DOSSIER_CV"], f))
    ] if os.path.isdir(CONFIG["DOSSIER_CV"]) else []
    fichiers_a_traiter = lister_fichiers_a_traiter()

    print(f"{len(fichiers)} fichier(s) trouvé(s), {len(fichiers_a_traiter)} à traiter "
          f"(déjà traités et ignorés: {len(fichiers) - len(fichiers_a_traiter)}).")

    if not fichiers_a_traiter:
        print("Rien à faire.")
        return

    conn = get_connection()
    barre = tqdm(total=len(fichiers_a_traiter), desc="Import CV")

    def _callback(i, total, filename, statut):
        barre.update(1)

    try:
        compteurs = executer_import(conn, fichiers_a_traiter, callback=_callback)
    finally:
        barre.close()
        conn.close()

    print("\n--- Résumé ---")
    for statut, n in compteurs.items():
        print(f"  {statut}: {n}")
    print(f"Log détaillé: {CONFIG['LOG_CSV']}")


if __name__ == "__main__":
    main()
