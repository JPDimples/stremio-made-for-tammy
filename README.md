# Made for Tammy with love — Stremio catalogs for Tammy

A Stremio addon with nine catalogs, built from TMDB data: rom-coms, Hallmark
movies, dramas, TV movies and stand-up specials, plus the matching series.
No horror — not even as a sub-genre. No config, no accounts needed to use it.

## Install

In Stremio, open this link (or paste the manifest URL into Addons):

    stremio://raw.githubusercontent.com/JPDimples/stremio-made-for-tammy/main/manifest.json

Manifest: `https://raw.githubusercontent.com/JPDimples/stremio-made-for-tammy/main/manifest.json`

## Catalogs (condensed 2026-11-11)

| Catalog | Type | Rule |
|---|---|---|
| Movies for Tammy | movie | Rom-coms + Hallmark + dramas + TV movies, mixed, no horror |
| Shows for Tammy | series | Rom-com + drama + comedy + Hallmark shows, English only, no horror |
| Stand-Up Specials for Tammy | movie | Comedy + "stand-up comedy", no horror |

Each catalog holds up to 100 of the most popular matching titles with IMDb
ids, so Stremio resolves posters/details through Cinemeta and streams through
whatever stream addons you already have. This addon serves catalogs only —
it provides no meta and no streams itself.

Horror is excluded twice: filtered out of every search, and every title is
checked again after fetching its details — anything with horror as a genre,
even a sub-genre, is dropped.

## How it stays fresh

`scripts/build_catalogs.py` rebuilds the catalogs from TMDB weekly
(Sundays 06:00 EST) via GitHub Actions, plus on demand from the Actions tab.
It uses only the Python standard library.

## Setup (for the repo owner)

The build needs a free TMDB API key — TMDB data is free, the key just
identifies the app:

1. Create a free account at https://www.themoviedb.org/signup, then open
   https://www.themoviedb.org/settings/api and copy the **API Key (v3 auth)**.
2. In this repo: **Settings → Secrets and variables → Actions → New
   repository secret**, name `TMDB_API_KEY`, value the key from step 1.
3. **Actions → Rebuild catalogs → Run workflow** to build the catalogs the
   first time. After that it rebuilds itself weekly.

To build locally instead: `TMDB_API_KEY=... python3 scripts/build_catalogs.py`.
