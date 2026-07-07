import { createClient } from "@/lib/supabase/server";
import { signOut } from "./actions";
import SearchClient from "@/components/SearchClient";
import type { FilterOptions } from "@/lib/types";

export const dynamic = "force-dynamic";

async function loadOptions(): Promise<FilterOptions> {
  const supabase = await createClient();
  const [villes, diplomes, competences] = await Promise.all([
    supabase.rpc("liste_villes"),
    supabase.rpc("liste_diplomes"),
    supabase.rpc("liste_competences"),
  ]);
  return {
    villes: (villes.data ?? []) as string[],
    diplomes: (diplomes.data ?? []) as string[],
    competences: (competences.data ?? []) as string[],
  };
}

export default async function Home() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const options = await loadOptions();

  return (
    <>
      <header className="topbar">
        <h1>📂 CVthèque</h1>
        <div className="user">
          <span>{user?.email}</span>
          <form action={signOut}>
            <button className="btn-ghost" type="submit" style={{ borderRadius: 8, padding: "0.4rem 0.8rem" }}>
              Déconnexion
            </button>
          </form>
        </div>
      </header>
      <SearchClient options={options} />
    </>
  );
}
