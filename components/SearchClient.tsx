"use client";

import { useState } from "react";
import {
  searchCvs,
  getDownloadUrl,
  updateVille,
  updateCompetences,
} from "@/app/actions";
import type { Cv, FilterOptions } from "@/lib/types";

export default function SearchClient({ options }: { options: FilterOptions }) {
  const [texteLibre, setTexteLibre] = useState("");
  const [ville, setVille] = useState("");
  const [diplomes, setDiplomes] = useState<string[]>([]);
  const [competences, setCompetences] = useState<string[]>([]);

  const [results, setResults] = useState<Cv[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggle(list: string[], value: string): string[] {
    return list.includes(value)
      ? list.filter((v) => v !== value)
      : [...list, value];
  }

  async function runSearch(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await searchCvs({ texteLibre, ville, diplomes, competences });
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de recherche.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="layout">
      <aside className="panel filters">
        <h2>Filtres de recherche</h2>
        <form onSubmit={runSearch}>
          <div className="field">
            <label htmlFor="q">Recherche libre</label>
            <input
              id="q"
              type="text"
              placeholder="nom, texte du CV…"
              value={texteLibre}
              onChange={(e) => setTexteLibre(e.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor="ville">Ville</label>
            <select
              id="ville"
              value={ville}
              onChange={(e) => setVille(e.target.value)}
            >
              <option value="">— Toutes —</option>
              {options.villes.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </div>

          <ChecklistField
            label="Diplôme(s)"
            options={options.diplomes}
            selected={diplomes}
            onToggle={(v) => setDiplomes((s) => toggle(s, v))}
          />

          <ChecklistField
            label="Compétence(s)"
            options={options.competences}
            selected={competences}
            onToggle={(v) => setCompetences((s) => toggle(s, v))}
          />

          <button className="btn" type="submit" disabled={loading} style={{ width: "100%" }}>
            {loading ? "Recherche…" : "🔍 Rechercher"}
          </button>
          <p className="hint" style={{ marginTop: "0.7rem" }}>
            Les filtres se cumulent (ET logique). La recherche libre utilise le
            texte complet du CV.
          </p>
        </form>
      </aside>

      <section>
        {error && <p className="error">{error}</p>}
        {results === null ? (
          <div className="panel empty-state">
            Utilise les filtres puis clique sur <strong>Rechercher</strong>.
          </div>
        ) : results.length === 0 ? (
          <div className="panel empty-state">Aucun résultat.</div>
        ) : (
          <>
            <p className="result-count">{results.length} résultat(s)</p>
            {results.map((cv) => (
              <CvCard key={cv.id} cv={cv} />
            ))}
          </>
        )}
      </section>
    </div>
  );
}

function ChecklistField({
  label,
  options,
  selected,
  onToggle,
}: {
  label: string;
  options: string[];
  selected: string[];
  onToggle: (v: string) => void;
}) {
  return (
    <div className="field">
      <label>
        {label}
        {selected.length > 0 ? ` (${selected.length})` : ""}
      </label>
      {options.length === 0 ? (
        <div className="checklist empty">Aucune valeur disponible.</div>
      ) : (
        <div className="checklist">
          {options.map((opt) => (
            <label key={opt}>
              <input
                type="checkbox"
                checked={selected.includes(opt)}
                onChange={() => onToggle(opt)}
              />
              {opt}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

function CvCard({ cv }: { cv: Cv }) {
  const [open, setOpen] = useState(false);
  const [ville, setVille] = useState(cv.ville ?? "");
  const [comp, setComp] = useState((cv.competences ?? []).join(", "));
  const [savedVille, setSavedVille] = useState(false);
  const [savedComp, setSavedComp] = useState(false);
  const [downloading, setDownloading] = useState(false);

  async function download() {
    if (!cv.storage_path) return;
    setDownloading(true);
    const url = await getDownloadUrl(cv.storage_path);
    setDownloading(false);
    if (url) window.open(url, "_blank");
  }

  async function saveVille() {
    await updateVille(cv.id, ville);
    setSavedVille(true);
    setTimeout(() => setSavedVille(false), 2000);
  }

  async function saveComp() {
    const liste = comp
      .split(",")
      .map((c) => c.trim())
      .filter(Boolean);
    await updateCompetences(cv.id, liste);
    setSavedComp(true);
    setTimeout(() => setSavedComp(false), 2000);
  }

  return (
    <div className="cv-card">
      <div className="cv-head" onClick={() => setOpen((o) => !o)}>
        <span className="name">{cv.nom_prenom || cv.filename}</span>
        <span className="city">{cv.ville || "ville inconnue"}</span>
      </div>

      {open && (
        <div className="cv-body">
          <dl className="kv">
            <dt>Fichier</dt>
            <dd>{cv.filename}</dd>
            <dt>Email</dt>
            <dd>{cv.email || "—"}</dd>
            <dt>Téléphone</dt>
            <dd>{cv.telephone || "—"}</dd>
            <dt>Adresse</dt>
            <dd>{cv.adresse || "—"}</dd>
            <dt>Diplômes</dt>
            <dd>
              {cv.diplomes && cv.diplomes.length ? (
                <div className="chips">
                  {cv.diplomes.map((d) => (
                    <span className="chip" key={d}>
                      {d}
                    </span>
                  ))}
                </div>
              ) : (
                "—"
              )}
            </dd>
            <dt>Compétences</dt>
            <dd>
              {cv.competences && cv.competences.length ? (
                <div className="chips">
                  {cv.competences.map((c) => (
                    <span className="chip" key={c}>
                      {c}
                    </span>
                  ))}
                </div>
              ) : (
                "—"
              )}
            </dd>
            {cv.experiences && cv.experiences.length > 0 && (
              <>
                <dt>Expériences</dt>
                <dd>
                  {cv.experiences.map((exp, i) => (
                    <div key={i}>
                      {exp.periode ? `${exp.periode} — ` : ""}
                      {exp.intitule_brut}
                    </div>
                  ))}
                </dd>
              </>
            )}
          </dl>

          <div style={{ display: "flex", gap: "0.7rem", alignItems: "center", flexWrap: "wrap" }}>
            {cv.storage_path ? (
              <button className="btn" type="button" onClick={download} disabled={downloading}>
                {downloading ? "…" : "⬇️ Télécharger le CV"}
              </button>
            ) : (
              <span className="hint" style={{ margin: 0 }}>
                Fichier non disponible en ligne.
              </span>
            )}
            {cv.statut_parsing && cv.statut_parsing !== "ok" && (
              <span className="badge-warn">statut : {cv.statut_parsing}</span>
            )}
          </div>

          <div className="correct">
            <p className="hint">Corriger un champ (si le parsing s'est trompé)</p>
            <div className="row">
              <div className="field" style={{ margin: 0 }}>
                <label>Ville</label>
                <input
                  type="text"
                  value={ville}
                  onChange={(e) => setVille(e.target.value)}
                />
              </div>
              <button className="btn-ghost" type="button" onClick={saveVille} style={{ borderRadius: 8, padding: "0.5rem 0.8rem" }}>
                Enregistrer
              </button>
            </div>
            {savedVille && <span className="saved">✓ Ville mise à jour</span>}

            <div className="row">
              <div className="field" style={{ margin: 0 }}>
                <label>Compétences (séparées par des virgules)</label>
                <input
                  type="text"
                  value={comp}
                  onChange={(e) => setComp(e.target.value)}
                />
              </div>
              <button className="btn-ghost" type="button" onClick={saveComp} style={{ borderRadius: 8, padding: "0.5rem 0.8rem" }}>
                Enregistrer
              </button>
            </div>
            {savedComp && <span className="saved">✓ Compétences mises à jour</span>}
          </div>
        </div>
      )}
    </div>
  );
}
