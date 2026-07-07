"""
Configuration centralisée - cvtheque
Modifie uniquement ce fichier pour adapter le projet à ta machine.

Les valeurs sensibles (connexion Supabase) sont lues depuis l'environnement
si présentes, ce qui permet de basculer entre une base PostgreSQL locale
(Docker) et une base Supabase hébergée sans toucher au code. Un fichier
`.env` à la racine est chargé automatiquement (voir `.env.example`).
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv est optionnel
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG = {
    # --- Base de données ---
    # Si DATABASE_URL est défini (ex: chaîne de connexion Supabase), il est
    # utilisé en priorité par db.get_connection(). Sinon on retombe sur la
    # base locale décrite dans "DB" ci-dessous.
    "DATABASE_URL": os.getenv("DATABASE_URL", ""),
    "DB": {
        "host": "localhost",
        "port": 5432,
        "dbname": "cvtheque",
        "user": "cvtheque",
        "password": "cvtheque_pwd_change_moi",
    },

    # --- Supabase Storage (upload des fichiers CV lors de l'ingestion) ---
    # Renseigne ces 2 variables (dans .env) pour envoyer les fichiers vers le
    # bucket "cvs". Laisse vide pour un fonctionnement 100% local sans upload.
    "SUPABASE_URL": os.getenv("SUPABASE_URL", ""),
    "SUPABASE_SERVICE_KEY": os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
    "SUPABASE_BUCKET": os.getenv("SUPABASE_BUCKET", "cvs"),

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
