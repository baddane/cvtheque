"""
Interface unique - lance avec:
    streamlit run search_app.py

Tout se passe ici : déposer les CV, lancer le traitement (OCR/parsing/DB),
et rechercher. Plus besoin de lancer ingest.py séparément.
"""
import os

import streamlit as st

from config import CONFIG
from db import get_connection, rechercher_cv, liste_villes_distinctes, liste_valeurs_distinctes, mettre_a_jour_champ
from ingest import lister_fichiers_a_traiter, executer_import, charger_log

st.set_page_config(page_title="CVthèque", layout="wide")
st.title("📂 CVthèque")


@st.cache_resource
def get_conn():
    return get_connection()


try:
    conn = get_conn()
except Exception as e:
    st.error(f"Impossible de se connecter à la base PostgreSQL : {e}\n\n"
             f"Vérifie que la base tourne (`docker compose up -d`) et que "
             f"`config.py` contient les bons identifiants.")
    st.stop()

onglet_import, onglet_recherche = st.tabs(["📥 Import de CV", "🔍 Recherche"])

# ============================================================
# ONGLET IMPORT
# ============================================================
with onglet_import:
    st.subheader("1. Déposer des CV")
    st.caption("PDF, Word (.docx) ou images (.jpg, .png...) — les CV papier "
               "doivent d'abord être scannés en image ou PDF.")

    fichiers_uploades = st.file_uploader(
        "Glisse-dépose ou sélectionne tes fichiers",
        type=["pdf", "docx", "doc", "jpg", "jpeg", "png", "tiff", "bmp"],
        accept_multiple_files=True,
    )

    if fichiers_uploades:
        if st.button(f"Enregistrer les {len(fichiers_uploades)} fichier(s) déposé(s)"):
            os.makedirs(CONFIG["DOSSIER_CV"], exist_ok=True)
            n_ecrits = 0
            for f in fichiers_uploades:
                destination = os.path.join(CONFIG["DOSSIER_CV"], f.name)
                with open(destination, "wb") as out:
                    out.write(f.getbuffer())
                n_ecrits += 1
            st.success(f"{n_ecrits} fichier(s) enregistré(s) dans la file d'attente. "
                       f"Passe à l'étape 2 ci-dessous.")

    st.divider()
    st.subheader("2. Lancer le traitement")

    fichiers_en_attente = lister_fichiers_a_traiter()
    st.write(f"**{len(fichiers_en_attente)}** fichier(s) en attente de traitement "
             f"dans `{CONFIG['DOSSIER_CV']}`.")

    if fichiers_en_attente:
        with st.expander("Voir la liste des fichiers en attente"):
            for f in fichiers_en_attente:
                st.write(f"- {f}")

        if st.button("▶️ Lancer l'import (OCR + parsing + base de données)", type="primary"):
            barre_progression = st.progress(0, text="Démarrage...")
            zone_log = st.empty()
            lignes_log = []

            def _callback(i, total, filename, statut):
                barre_progression.progress(i / total, text=f"{i}/{total} — {filename} ({statut})")
                lignes_log.append(f"- **{filename}** → `{statut}`")
                zone_log.markdown("\n".join(lignes_log[-15:]))

            with st.spinner("Traitement en cours..."):
                compteurs = executer_import(conn, fichiers_en_attente, callback=_callback)

            barre_progression.progress(1.0, text="Terminé.")
            st.success(
                f"Import terminé : {compteurs.get('ok', 0)} OK, "
                f"{compteurs.get('ocr_faible', 0)} OCR faible (à vérifier), "
                f"{compteurs.get('erreur', 0)} erreur(s)."
            )
            st.cache_resource.clear()
            st.rerun()
    else:
        st.info("Aucun fichier en attente. Dépose des CV ci-dessus pour commencer.")

    st.divider()
    with st.expander("📋 Historique complet des imports (log)"):
        log = charger_log()
        if log:
            st.dataframe(
                [{"fichier": k, "statut": v} for k, v in log.items()],
                use_container_width=True,
            )
        else:
            st.caption("Aucun import effectué pour l'instant.")

# ============================================================
# ONGLET RECHERCHE
# ============================================================
with onglet_recherche:
    st.sidebar.header("Filtres de recherche")

    texte_libre = st.sidebar.text_input("Recherche libre (nom, texte du CV...)")

    try:
        villes_dispo = liste_villes_distinctes(conn)
        diplomes_dispo = liste_valeurs_distinctes(conn, "diplomes")
        competences_dispo = liste_valeurs_distinctes(conn, "competences")
    except Exception as e:
        st.error(f"Erreur de connexion à la base : {e}")
        st.stop()

    ville = st.sidebar.selectbox("Ville", options=[""] + villes_dispo)
    diplomes_choisis = st.sidebar.multiselect("Diplôme(s)", options=diplomes_dispo)
    competences_choisies = st.sidebar.multiselect("Compétence(s)", options=competences_dispo)

    lancer_recherche = st.sidebar.button("🔍 Rechercher", type="primary", use_container_width=True)

    st.sidebar.divider()
    st.sidebar.caption("Astuce : combine les filtres pour affiner (ET logique). "
                        "La recherche libre utilise le texte complet du CV.")

    if lancer_recherche or "resultats" in st.session_state:
        if lancer_recherche:
            resultats = rechercher_cv(
                conn,
                ville=ville or None,
                diplomes=diplomes_choisis or None,
                competences=competences_choisies or None,
                texte_libre=texte_libre or None,
            )
            st.session_state["resultats"] = resultats
        else:
            resultats = st.session_state["resultats"]

        st.subheader(f"{len(resultats)} résultat(s)")

        for cv in resultats:
            with st.expander(f"**{cv['nom_prenom'] or cv['filename']}** — {cv['ville'] or 'ville inconnue'}"):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.write(f"**Fichier :** {cv['filename']}")
                    st.write(f"**Email :** {cv['email'] or '—'}")
                    st.write(f"**Téléphone :** {cv['telephone'] or '—'}")
                    st.write(f"**Adresse :** {cv['adresse'] or '—'}")
                    st.write(f"**Diplômes :** {', '.join(cv['diplomes']) if cv['diplomes'] else '—'}")
                    st.write(f"**Compétences :** {', '.join(cv['competences']) if cv['competences'] else '—'}")
                    if cv["experiences"]:
                        st.write("**Expériences détectées :**")
                        for exp in cv["experiences"]:
                            st.write(f"- {exp.get('periode', '')} — {exp.get('intitule_brut', '')}")
                    if cv["statut_parsing"] != "ok":
                        st.warning(f"Statut parsing : {cv['statut_parsing']} (à vérifier / corriger)")

                with col2:
                    if os.path.exists(cv["filepath"]):
                        with open(cv["filepath"], "rb") as f:
                            st.download_button(
                                "⬇️ Télécharger le CV",
                                data=f.read(),
                                file_name=cv["filename"],
                                key=f"dl_{cv['id']}",
                            )
                    else:
                        st.caption("Fichier introuvable sur disque (déplacé/supprimé ?)")

                st.divider()
                st.caption("Corriger un champ (si le parsing s'est trompé)")
                c1, c2 = st.columns(2)
                with c1:
                    nouvelle_ville = st.text_input("Ville corrigée", value=cv["ville"] or "", key=f"ville_{cv['id']}")
                    if st.button("Enregistrer la ville", key=f"save_ville_{cv['id']}"):
                        mettre_a_jour_champ(conn, cv["id"], "ville", nouvelle_ville)
                        st.success("Ville mise à jour.")
                with c2:
                    nouvelles_competences = st.text_input(
                        "Compétences corrigées (séparées par des virgules)",
                        value=", ".join(cv["competences"]) if cv["competences"] else "",
                        key=f"comp_{cv['id']}",
                    )
                    if st.button("Enregistrer les compétences", key=f"save_comp_{cv['id']}"):
                        liste = [c.strip() for c in nouvelles_competences.split(",") if c.strip()]
                        mettre_a_jour_champ(conn, cv["id"], "competences", liste)
                        st.success("Compétences mises à jour.")
    else:
        st.info("Utilise les filtres à gauche puis clique sur **Rechercher**.")
