export type Experience = {
  periode?: string;
  intitule_brut?: string;
};

export type Cv = {
  id: number;
  filename: string;
  storage_path: string | null;
  file_type: string | null;
  nom_prenom: string | null;
  email: string | null;
  telephone: string | null;
  ville: string | null;
  adresse: string | null;
  diplomes: string[] | null;
  competences: string[] | null;
  experiences: Experience[] | null;
  statut_parsing: string | null;
  date_import: string | null;
};

export type SearchFilters = {
  texteLibre?: string;
  ville?: string;
  diplomes?: string[];
  competences?: string[];
};

export type FilterOptions = {
  villes: string[];
  diplomes: string[];
  competences: string[];
};
