"""
Extraction de texte depuis un PDF.
Stratégie:
  1. Essaie d'extraire le texte natif avec pdfplumber (rapide, CV Word->PDF).
  2. Si le texte est trop court (PDF scanné = image), on convertit les pages
     en images et on passe par l'OCR (comme un CV papier scanné).
"""
import pdfplumber
from pdf2image import convert_from_path

from config import CONFIG
from extractors.image_extractor import ocr_image


def extract_text_from_pdf(filepath: str) -> tuple[str, str]:
    """
    Retourne (texte_extrait, methode) où methode vaut "pdf_natif" ou "pdf_ocr".
    """
    texte_natif = ""
    try:
        with pdfplumber.open(filepath) as pdf:
            pages_texte = []
            for page in pdf.pages:
                t = page.extract_text() or ""
                pages_texte.append(t)
            texte_natif = "\n".join(pages_texte).strip()
    except Exception as e:
        print(f"  [!] Erreur lecture PDF natif ({filepath}): {e}")

    if len(texte_natif) >= CONFIG["SEUIL_TEXTE_MIN"]:
        return texte_natif, "pdf_natif"

    # Fallback OCR: le PDF est probablement un scan (CV papier scanné en PDF)
    print("  -> Texte natif insuffisant, bascule en OCR (PDF scanné)...")
    try:
        images = convert_from_path(filepath, dpi=CONFIG["DPI_SCAN"])
    except Exception as e:
        print(f"  [!] Erreur conversion PDF->images: {e}")
        return texte_natif, "pdf_natif"

    textes_ocr = []
    for img in images:
        textes_ocr.append(ocr_image(img))
    texte_ocr = "\n".join(textes_ocr).strip()

    # On garde le plus long des deux au cas où
    if len(texte_ocr) > len(texte_natif):
        return texte_ocr, "pdf_ocr"
    return texte_natif, "pdf_natif"
