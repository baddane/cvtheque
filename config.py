"""
Configuration centralisée - cvtheque
Modifie uniquement ce fichier pour adapter le projet à ta machine.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG = {
    # --- Base de données ---
    "DB": {
        "host": "localhost",
        "port": 5432,
        "dbname": "cvtheque",
        "user": "cvtheque",
        "password": "cvtheque_pwd_change_moi",
    },

    # --- Dossiers ---
    "DOSSIER_CV": os.path.join(BASE_DIR, "cv_a_traiter"),     # dépose les nouveaux CV ici
    "DOSSIER_TRAITES": os.path.join(BASE_DIR, "cv_traites"),  # déplacés après succès
    "DOSSIER_ERREURS": os.path.join(BASE_DIR, "cv_erreurs"),  # déplacés si échec
    "LOG_CSV": os.path.join(BASE_DIR, "logs", "import_log.csv"),

    # --- OCR (Tesseract) ---
    # Laisse vide sur Linux/Mac si tesseract est dans le PATH.
    # Sur Windows, mets par ex: r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    "TESSERACT_CMD": "",
    "OCR_LANG": "fra",       # "fra" = français, "fra+ara" si tu veux aussi l'arabe
    "DPI_SCAN": 300,         # résolution de conversion PDF -> image pour l'OCR

    # --- Seuils de qualité ---
    "SEUIL_TEXTE_MIN": 40,   # si le texte extrait fait moins de N caractères -> OCR de secours (PDF)
    "SEUIL_OCR_FAIBLE": 60,  # si le texte OCR final fait moins de N caractères -> statut "ocr_faible"

    # --- Extensions supportées ---
    "EXTENSIONS_PDF": [".pdf"],
    "EXTENSIONS_DOCX": [".docx", ".doc"],
    "EXTENSIONS_IMAGE": [".jpg", ".jpeg", ".png", ".tiff", ".bmp"],
}
