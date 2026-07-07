# Déploiement de la CVthèque sur Vercel + Supabase

Cette application a été pensée à l'origine comme un outil **local** (Streamlit
+ PostgreSQL Docker + OCR Tesseract). Pour la rendre accessible en ligne, on
sépare les deux responsabilités :

| Partie | Où ça tourne | Pourquoi |
|--------|--------------|----------|
| **Ingestion / OCR** (extraction, parsing) | **Local**, sur ton poste | Tesseract, OpenCV et Poppler sont des binaires lourds, impossibles à exécuter en serverless. C'est un traitement par lot ponctuel. |
| **Base de données + recherche full-text** | **Supabase** (PostgreSQL hébergé) | Même moteur PostgreSQL, mêmes extensions (`pg_trgm`, `unaccent`), donc **la logique de recherche est conservée à l'identique**. |
| **Fichiers CV originaux** | **Supabase Storage** (bucket privé) | Volume important (5000+ fichiers), liens de téléchargement signés et temporaires. |
| **Interface de recherche** | **Vercel** (app Next.js) | Streamlit ne tourne pas sur Vercel (serveur persistant) ; l'interface est réécrite en Next.js. |

```
   Poste local                         Cloud
┌──────────────────┐        ┌───────────────────────────┐
│ ingest.py (OCR)  │  ───►  │ Supabase                  │
│  + Storage upload│        │  • PostgreSQL (table cvs) │
└──────────────────┘        │  • Storage (bucket cvs)   │
                            │  • Auth (utilisateurs RH)  │
                            └────────────┬──────────────┘
                                         │ (anon key + session)
                                ┌────────▼─────────┐
                                │ Vercel (Next.js) │  ◄── navigateur RH
                                │  app de recherche│
                                └──────────────────┘
```

---

## 1. Créer le projet Supabase

1. Crée un projet sur [supabase.com](https://supabase.com).
2. Applique les migrations SQL du dossier [`supabase/migrations/`](supabase/migrations/),
   **dans l'ordre**, via **SQL Editor** (copier-coller) ou la CLI Supabase :

   ```bash
   # option CLI (depuis la racine du repo)
   supabase link --project-ref <ref-du-projet>
   supabase db push
   ```

   Les trois fichiers créent : la table `cvs` + index + trigger `search_vector`
   (`0001`), les fonctions de recherche RPC + RLS (`0002`), le bucket privé
   `cvs` (`0003`).

3. **Crée un utilisateur RH** : *Authentication > Users > Add user* (email +
   mot de passe). C'est ce compte qui servira à se connecter à l'app.
   > Astuce : dans *Authentication > Providers*, laisse "Email" activé et
   > désactive "Enable email confirmations" si tu veux créer des comptes sans
   > vérification par mail.

---

## 2. Alimenter la base depuis ton poste (ingestion)

L'OCR reste local. On configure juste où écrire.

1. Copie `.env.example` en `.env` à la racine et renseigne :

   ```env
   DATABASE_URL=postgresql://postgres.xxxx:MOT_DE_PASSE@aws-0-...pooler.supabase.com:5432/postgres
   SUPABASE_URL=https://xxxx.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...   # clé "service_role" (secrète !)
   SUPABASE_BUCKET=cvs
   ```

   - `DATABASE_URL` : *Project Settings > Database > Connection string > URI*
     (utilise de préférence le **Session pooler**, port 5432).
   - `SUPABASE_SERVICE_ROLE_KEY` : *Project Settings > API*. **Ne jamais
     l'exposer côté web / la committer.**

2. Installe les prérequis OCR locaux (voir `README.md`) et les dépendances :

   ```bash
   pip install -r requirements.txt
   ```

3. Dépose tes CV dans `cv_a_traiter/` puis lance l'ingestion :

   ```bash
   python ingest.py
   ```

   Chaque CV est extrait/parsé, **le fichier est uploadé dans le bucket
   Supabase** et la ligne est insérée dans la table `cvs`. Le log
   `logs/import_log.csv` permet de reprendre un gros lot interrompu.

   > Sans les variables Supabase, `ingest.py` fonctionne toujours en 100 %
   > local (base Docker + fichiers sur disque), exactement comme avant.

---

## 3. Déployer l'interface sur Vercel

1. Pousse ce repo sur GitHub (déjà le cas).
2. Sur [vercel.com](https://vercel.com) : *Add New > Project*, importe le repo.
3. **Important** — dans la configuration du projet :
   - **Root Directory** : `web`
   - Framework preset : *Next.js* (détecté automatiquement)
4. **Environment Variables** (Settings > Environment Variables) :

   | Nom | Valeur |
   |-----|--------|
   | `NEXT_PUBLIC_SUPABASE_URL` | `https://xxxx.supabase.co` |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | clé `anon` publique (*Project Settings > API*) |

   > On utilise uniquement la clé **anon** (publique) côté Vercel. La sécurité
   > repose sur l'authentification Supabase + le RLS : un visiteur non
   > connecté ne peut rien lire.

5. Déploie. L'URL Vercel affiche une page de connexion ; connecte-toi avec le
   compte créé à l'étape 1.3.

---

## 4. Développement local de l'interface (optionnel)

```bash
cd web
cp .env.example .env.local   # renseigne les 2 variables NEXT_PUBLIC_*
npm install
npm run dev                  # http://localhost:3000
```

---

## Sécurité — points clés

- Bucket `cvs` **privé** : les téléchargements passent par des URLs signées
  valables 2 minutes, générées seulement pour une session authentifiée.
- **RLS activé** sur la table `cvs` : lecture/mise à jour réservées au rôle
  `authenticated`.
- La clé `service_role` (tous pouvoirs) ne vit **que** dans ton `.env` local
  d'ingestion, jamais sur Vercel ni dans le navigateur.
- Pour ajouter/retirer un accès RH : gère les comptes dans *Supabase >
  Authentication > Users*.
