"""Connexion et opérations PostgreSQL pour la cvthèque."""
import json
import psycopg2
import psycopg2.extras

from config import CONFIG


def get_connection():
    """Connexion PostgreSQL.

    Utilise CONFIG["DATABASE_URL"] (ex: chaîne Supabase) si elle est définie,
    sinon la base locale de CONFIG["DB"] (Docker).
    """
    database_url = CONFIG.get("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)
    return psycopg2.connect(**CONFIG["DB"])


def inserer_cv(conn, data: dict) -> int:
    """Insère un CV. En cas de conflit sur filepath (déjà importé), met à jour."""
    sql = """
        INSERT INTO cvs (
            filename, filepath, storage_path, file_type, raw_text,
            nom_prenom, email, telephone, ville, adresse,
            diplomes, competences, experiences, statut_parsing
        ) VALUES (
            %(filename)s, %(filepath)s, %(storage_path)s, %(file_type)s, %(raw_text)s,
            %(nom_prenom)s, %(email)s, %(telephone)s, %(ville)s, %(adresse)s,
            %(diplomes)s, %(competences)s, %(experiences)s, %(statut_parsing)s
        )
        ON CONFLICT (filepath) DO UPDATE SET
            storage_path = EXCLUDED.storage_path,
            raw_text = EXCLUDED.raw_text,
            nom_prenom = EXCLUDED.nom_prenom,
            email = EXCLUDED.email,
            telephone = EXCLUDED.telephone,
            ville = EXCLUDED.ville,
            adresse = EXCLUDED.adresse,
            diplomes = EXCLUDED.diplomes,
            competences = EXCLUDED.competences,
            experiences = EXCLUDED.experiences,
            statut_parsing = EXCLUDED.statut_parsing
        RETURNING id;
    """
    data = dict(data)
    data.setdefault("storage_path", None)
    data["experiences"] = json.dumps(data.get("experiences", []), ensure_ascii=False)

    with conn.cursor() as cur:
        cur.execute(sql, data)
        cv_id = cur.fetchone()[0]
    conn.commit()
    return cv_id


def rechercher_cv(conn, ville=None, diplomes=None, competences=None, texte_libre=None, limit=100):
    """
    Recherche combinée. Chaque filtre est optionnel et cumulatif (ET logique).
    - ville: recherche floue (trigram) sur le champ ville
    - diplomes / competences: listes -> le CV doit contenir AU MOINS UN des éléments
    - texte_libre: recherche full-text (nom, ville, diplômes, compétences, texte brut)
    """
    conditions = []
    params = {}

    if ville:
        conditions.append("similarity(ville, %(ville)s) > 0.3")
        params["ville"] = ville

    if diplomes:
        conditions.append("diplomes && %(diplomes)s")
        params["diplomes"] = diplomes

    if competences:
        conditions.append("competences && %(competences)s")
        params["competences"] = competences

    if texte_libre:
        conditions.append("search_vector @@ plainto_tsquery('french', unaccent(%(texte_libre)s))")
        params["texte_libre"] = texte_libre

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    if texte_libre:
        order_clause = "ORDER BY ts_rank(search_vector, plainto_tsquery('french', unaccent(%(texte_libre)s))) DESC"
    else:
        order_clause = "ORDER BY date_import DESC"

    sql = f"""
        SELECT id, filename, filepath, nom_prenom, email, telephone,
               ville, adresse, diplomes, competences, experiences,
               statut_parsing, date_import
        FROM cvs
        WHERE {where_clause}
        {order_clause}
        LIMIT %(limit)s;
    """
    params["limit"] = limit

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def liste_valeurs_distinctes(conn, colonne_array: str) -> list[str]:
    """Utilisé pour peupler les filtres (villes, diplômes, compétences disponibles)."""
    sql = f"SELECT DISTINCT unnest({colonne_array}) AS val FROM cvs ORDER BY val;"
    with conn.cursor() as cur:
        cur.execute(sql)
        return [row[0] for row in cur.fetchall()]


def liste_villes_distinctes(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT ville FROM cvs WHERE ville IS NOT NULL ORDER BY ville;")
        return [row[0] for row in cur.fetchall()]


def mettre_a_jour_champ(conn, cv_id: int, champ: str, valeur):
    """Permet la correction manuelle d'un champ depuis l'appli de recherche."""
    champs_autorises = {"nom_prenom", "email", "telephone", "ville", "adresse", "diplomes", "competences"}
    if champ not in champs_autorises:
        raise ValueError(f"Champ non autorisé: {champ}")
    sql = f"UPDATE cvs SET {champ} = %s WHERE id = %s;"
    with conn.cursor() as cur:
        cur.execute(sql, (valeur, cv_id))
    conn.commit()
