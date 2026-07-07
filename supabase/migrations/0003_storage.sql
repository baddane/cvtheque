-- ============================================================
-- CVthèque — bucket de stockage des fichiers CV (privé)
-- ============================================================

-- Bucket privé : les fichiers ne sont accessibles que via une session
-- authentifiée (l'app génère des URLs signées temporaires pour le
-- téléchargement).
insert into storage.buckets (id, name, public)
values ('cvs', 'cvs', false)
on conflict (id) do nothing;

-- Lecture réservée aux utilisateurs authentifiés.
-- L'upload (ingestion locale) passe par la clé service_role, qui contourne RLS.
drop policy if exists "cvs_storage_read_authenticated" on storage.objects;
create policy "cvs_storage_read_authenticated"
    on storage.objects for select
    to authenticated
    using (bucket_id = 'cvs');
