-- ============================================================
-- CVthèque — schéma de base (Supabase / PostgreSQL)
-- Reprend schema.sql à l'identique et ajoute :
--   - la colonne storage_path (clé de l'objet dans Supabase Storage)
--   - le Row Level Security (accès réservé aux utilisateurs authentifiés)
-- ============================================================

-- Extensions nécessaires.
-- Sur Supabase, unaccent et pg_trgm vivent dans le schéma "extensions".
create extension if not exists pg_trgm;
create extension if not exists unaccent;

create table if not exists public.cvs (
    id              serial primary key,
    filename        text not null,
    filepath        text not null unique,       -- chemin d'origine, clé de dédoublonnage
    storage_path    text,                        -- clé de l'objet dans le bucket "cvs"
    file_type       text,                        -- pdf, docx, image
    raw_text        text,

    nom_prenom      text,
    email           text,
    telephone       text,
    ville           text,
    adresse         text,

    diplomes        text[] default '{}',
    competences     text[] default '{}',
    experiences     jsonb  default '[]',

    statut_parsing  text default 'ok',           -- ok, ocr_faible, erreur
    date_import     timestamp default now(),
    date_maj        timestamp default now(),

    search_vector   tsvector
);

-- Index de recherche
create index if not exists idx_cvs_search       on public.cvs using gin (search_vector);
create index if not exists idx_cvs_ville_trgm    on public.cvs using gin (ville gin_trgm_ops);
create index if not exists idx_cvs_competences   on public.cvs using gin (competences);
create index if not exists idx_cvs_diplomes      on public.cvs using gin (diplomes);

-- Fonction + trigger pour maintenir le search_vector à jour automatiquement.
-- unaccent() n'étant pas IMMUTABLE, on référence explicitement le schéma
-- extensions pour rester compatible avec le search_path restreint des triggers.
create or replace function public.cvs_update_search_vector() returns trigger
set search_path = public, extensions
as $$
begin
    new.search_vector :=
        setweight(to_tsvector('french', unaccent(coalesce(new.nom_prenom, ''))), 'A') ||
        setweight(to_tsvector('french', unaccent(coalesce(new.ville, ''))), 'A') ||
        setweight(to_tsvector('french', unaccent(array_to_string(new.diplomes, ' '))), 'A') ||
        setweight(to_tsvector('french', unaccent(array_to_string(new.competences, ' '))), 'B') ||
        setweight(to_tsvector('french', unaccent(coalesce(new.raw_text, ''))), 'D');
    new.date_maj := now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_cvs_search_vector on public.cvs;
create trigger trg_cvs_search_vector
    before insert or update on public.cvs
    for each row execute function public.cvs_update_search_vector();

-- ============================================================
-- Row Level Security
-- L'ingestion locale utilise la clé "service_role" qui contourne RLS.
-- L'app web (Vercel) utilise une session utilisateur authentifiée.
-- ============================================================
alter table public.cvs enable row level security;

drop policy if exists "cvs_select_authenticated" on public.cvs;
create policy "cvs_select_authenticated"
    on public.cvs for select
    to authenticated
    using (true);

-- Correction manuelle des champs (ville, compétences...) depuis l'app.
drop policy if exists "cvs_update_authenticated" on public.cvs;
create policy "cvs_update_authenticated"
    on public.cvs for update
    to authenticated
    using (true)
    with check (true);
