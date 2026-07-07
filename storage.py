"""
Upload optionnel des fichiers CV vers Supabase Storage (bucket privé "cvs").

Activé uniquement si SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY sont définis
(voir config.py / .env). En mode 100% local, ces fonctions ne font rien et
l'ingestion continue normalement (les CV restent sur le disque local).

On utilise l'API REST de Supabase Storage directement (via requests) pour
éviter une dépendance lourde ; le service_role contourne le RLS, ce qui
autorise l'écriture dans le bucket privé.
"""
import mimetypes
import os

import requests

from config import CONFIG


def storage_active() -> bool:
    return bool(CONFIG.get("SUPABASE_URL") and CONFIG.get("SUPABASE_SERVICE_KEY"))


def cle_objet(filename: str) -> str:
    """Clé de l'objet dans le bucket. On garde le nom de fichier d'origine."""
    return filename


def uploader_fichier(filepath: str, filename: str | None = None) -> str | None:
    """
    Envoie un fichier vers le bucket Supabase. Retourne la clé de l'objet
    stockée en base (storage_path), ou None si le Storage n'est pas configuré.
    Lève une exception en cas d'échec réseau/HTTP pour que l'appelant marque
    le CV en erreur.
    """
    if not storage_active():
        return None

    filename = filename or os.path.basename(filepath)
    objet = cle_objet(filename)
    bucket = CONFIG["SUPABASE_BUCKET"]
    url = f"{CONFIG['SUPABASE_URL']}/storage/v1/object/{bucket}/{objet}"

    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    headers = {
        "Authorization": f"Bearer {CONFIG['SUPABASE_SERVICE_KEY']}",
        "Content-Type": content_type,
        # x-upsert: réécrit l'objet s'il existe déjà (ré-ingestion d'un même CV)
        "x-upsert": "true",
    }

    with open(filepath, "rb") as f:
        resp = requests.post(url, headers=headers, data=f.read(), timeout=60)

    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Upload Storage échoué ({resp.status_code}): {resp.text[:200]}"
        )
    return objet
