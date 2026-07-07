-- Extensions nécessaires
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE TABLE IF NOT EXISTS cvs (
    id              SERIAL PRIMARY KEY,
    filename        TEXT NOT NULL,
    filepath        TEXT NOT NULL UNIQUE,
    file_type       TEXT,                       -- pdf, docx, image
    raw_text        TEXT,

    nom_prenom      TEXT,
    email           TEXT,
    telephone       TEXT,
    ville           TEXT,
    adresse         TEXT,

    diplomes        TEXT[] DEFAULT '{}',
    competences     TEXT[] DEFAULT '{}',
    experiences     JSONB DEFAULT '[]',

    statut_parsing  TEXT DEFAULT 'ok',           -- ok, ocr_faible, erreur
    date_import     TIMESTAMP DEFAULT now(),
    date_maj        TIMESTAMP DEFAULT now(),

    search_vector   tsvector
);

-- Index de recherche
CREATE INDEX IF NOT EXISTS idx_cvs_search        ON cvs USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_cvs_ville_trgm     ON cvs USING GIN (ville gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_cvs_competences    ON cvs USING GIN (competences);
CREATE INDEX IF NOT EXISTS idx_cvs_diplomes       ON cvs USING GIN (diplomes);

-- Fonction + trigger pour maintenir le search_vector à jour automatiquement
CREATE OR REPLACE FUNCTION cvs_update_search_vector() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('french', unaccent(coalesce(NEW.nom_prenom, ''))), 'A') ||
        setweight(to_tsvector('french', unaccent(coalesce(NEW.ville, ''))), 'A') ||
        setweight(to_tsvector('french', unaccent(array_to_string(NEW.diplomes, ' '))), 'A') ||
        setweight(to_tsvector('french', unaccent(array_to_string(NEW.competences, ' '))), 'B') ||
        setweight(to_tsvector('french', unaccent(coalesce(NEW.raw_text, ''))), 'D');
    NEW.date_maj := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_cvs_search_vector ON cvs;
CREATE TRIGGER trg_cvs_search_vector
    BEFORE INSERT OR UPDATE ON cvs
    FOR EACH ROW EXECUTE FUNCTION cvs_update_search_vector();
