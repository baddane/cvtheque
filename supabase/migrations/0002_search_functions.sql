-- ============================================================
-- CVthèque — fonctions de recherche exposées à l'app web via RPC
-- Reprennent exactement la logique de db.py (recherche combinée,
-- floue sur la ville, chevauchement de tableaux, full-text pondéré).
-- ============================================================

-- Recherche combinée. Chaque filtre est optionnel et cumulatif (ET logique).
--   p_ville         : recherche floue (trigram) sur le champ ville
--   p_diplomes      : le CV doit contenir AU MOINS UN des diplômes
--   p_competences   : le CV doit contenir AU MOINS UNE des compétences
--   p_texte_libre   : recherche full-text pondérée (nom, ville, diplômes, compétences, texte brut)
create or replace function public.rechercher_cv(
    p_ville         text    default null,
    p_diplomes      text[]  default null,
    p_competences   text[]  default null,
    p_texte_libre   text    default null,
    p_limit         int     default 100
)
returns setof public.cvs
language sql
stable
security invoker
set search_path = public, extensions
as $$
    select *
    from public.cvs
    where (p_ville is null or similarity(ville, p_ville) > 0.3)
      and (p_diplomes is null or diplomes && p_diplomes)
      and (p_competences is null or competences && p_competences)
      and (p_texte_libre is null
           or search_vector @@ plainto_tsquery('french', unaccent(p_texte_libre)))
    order by
        case
            when p_texte_libre is not null
            then ts_rank(search_vector, plainto_tsquery('french', unaccent(p_texte_libre)))
            else 0
        end desc,
        date_import desc
    limit greatest(1, least(p_limit, 500));
$$;

-- Valeurs distinctes pour peupler les filtres de l'interface.
create or replace function public.liste_villes()
returns setof text
language sql
stable
security invoker
set search_path = public
as $$
    select distinct ville
    from public.cvs
    where ville is not null
    order by ville;
$$;

create or replace function public.liste_diplomes()
returns setof text
language sql
stable
security invoker
set search_path = public
as $$
    select distinct unnest(diplomes) as val
    from public.cvs
    order by val;
$$;

create or replace function public.liste_competences()
returns setof text
language sql
stable
security invoker
set search_path = public
as $$
    select distinct unnest(competences) as val
    from public.cvs
    order by val;
$$;

-- Les fonctions sont appelées avec la session de l'utilisateur authentifié.
grant execute on function public.rechercher_cv(text, text[], text[], text, int) to authenticated;
grant execute on function public.liste_villes()      to authenticated;
grant execute on function public.liste_diplomes()    to authenticated;
grant execute on function public.liste_competences() to authenticated;
