"use server";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import type { Cv, SearchFilters } from "@/lib/types";

const COLUMNS =
  "id, filename, storage_path, file_type, nom_prenom, email, telephone, " +
  "ville, adresse, diplomes, competences, experiences, statut_parsing, date_import";

/** Recherche combinée (RPC PostgreSQL rechercher_cv). */
export async function searchCvs(filters: SearchFilters): Promise<Cv[]> {
  const supabase = await createClient();

  // .select(COLUMNS) limite les colonnes renvoyées (on évite de rapatrier
  // raw_text, potentiellement volumineux, inutile pour l'affichage).
  const { data, error } = await supabase
    .rpc("rechercher_cv", {
      p_ville: filters.ville || null,
      p_diplomes:
        filters.diplomes && filters.diplomes.length ? filters.diplomes : null,
      p_competences:
        filters.competences && filters.competences.length
          ? filters.competences
          : null,
      p_texte_libre: filters.texteLibre || null,
      p_limit: 100,
    })
    .select(COLUMNS);

  if (error) throw new Error(error.message);
  return (data ?? []) as unknown as Cv[];
}

/** Correction manuelle d'un champ texte (ville). */
export async function updateVille(id: number, ville: string): Promise<void> {
  const supabase = await createClient();
  const { error } = await supabase
    .from("cvs")
    .update({ ville: ville.trim() || null })
    .eq("id", id);
  if (error) throw new Error(error.message);
}

/** Correction manuelle des compétences (tableau). */
export async function updateCompetences(
  id: number,
  competences: string[],
): Promise<void> {
  const supabase = await createClient();
  const { error } = await supabase
    .from("cvs")
    .update({ competences })
    .eq("id", id);
  if (error) throw new Error(error.message);
}

/** URL signée temporaire pour télécharger le CV original (bucket privé). */
export async function getDownloadUrl(
  storagePath: string,
): Promise<string | null> {
  const supabase = await createClient();
  const { data, error } = await supabase.storage
    .from("cvs")
    .createSignedUrl(storagePath, 120, { download: true });
  if (error) return null;
  return data?.signedUrl ?? null;
}

export async function signOut(): Promise<void> {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/login");
}
