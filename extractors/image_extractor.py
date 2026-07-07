"""
Extraction de texte depuis une image (CV papier scanné puis pris en photo/scanné).
Prétraitement simple avec OpenCV pour améliorer la qualité OCR:
  - passage en niveaux de gris
  - seuillage adaptatif (binarisation)
  - léger débruitage
"""
import cv2
import numpy as np
import pytesseract
from PIL import Image

from config import CONFIG

if CONFIG["TESSERACT_CMD"]:
    pytesseract.pytesseract.tesseract_cmd = CONFIG["TESSERACT_CMD"]


def _pretraiter_image(pil_image: Image.Image) -> Image.Image:
    """Améliore la lisibilité du scan avant OCR."""
    img = np.array(pil_image.convert("RGB"))
    gris = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gris = cv2.fastNlMeansDenoising(gris, h=10)
    seuil = cv2.adaptiveThreshold(
        gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )
    return Image.fromarray(seuil)


def ocr_image(pil_image: Image.Image) -> str:
    """OCR d'une image PIL déjà chargée (utilisé aussi pour les pages de PDF scannés)."""
    try:
        image_traitee = _pretraiter_image(pil_image)
        texte = pytesseract.image_to_string(image_traitee, lang=CONFIG["OCR_LANG"])
        return texte.strip()
    except Exception as e:
        print(f"  [!] Erreur OCR: {e}")
        return ""


def extract_text_from_image(filepath: str) -> tuple[str, str]:
    """Retourne (texte_extrait, methode) pour un fichier image sur disque."""
    try:
        img = Image.open(filepath)
        texte = ocr_image(img)
        return texte, "image_ocr"
    except Exception as e:
        print(f"  [!] Erreur ouverture image ({filepath}): {e}")
        return "", "image_ocr"
