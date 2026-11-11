#!/usr/bin/env python3
"""Build the "Made for Tammy with love" Stremio addon catalogs from TMDB.

Movies (5) and Series (4), each split by genre. Horror is excluded TWICE:
once in every discover query (without_genres=27) and again per title after
fetching details (any title with genre id 27 is dropped, even as a sub-genre).

Catalogs:
  movie  rom-coms           Comedy AND Romance, no Horror
  movie  hallmark-movies    Hallmark companies (Media/Entertainment/Productions)
  movie  dramas             Drama, no Horror
  movie  tv-movies          Lifetime productions, no Horror
  movie  stand-up-specials  Comedy + "stand-up comedy" keyword, no Horror
  series rom-com-shows      Comedy AND Romance, no Horror
  series drama-shows        Drama, no Horror
  series comedy-shows       Comedy, no Horror
  series hallmark-shows     Hallmark Channel network, no Horror

Only items with an IMDb id (tt...) and a poster are kept, so Stremio can
resolve meta through Cinemeta and streams through the user's own addons.
This addon serves catalogs ONLY (resources: ["catalog"]) — no meta, no streams.

Pagination: Stremio keeps requesting pages while they come back non-empty,
advancing skip by the number received; a short page is NOT the last one and
a 404 is not an empty page. So every catalog also ships skip=0 (full page)
and skip=100 (empty array) files.

Usage:  TMDB_API_KEY=... python3 scripts/build_catalogs.py
Output: catalog/{type}/{id}.json + skip variants, under the repo root.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/w500"
OUT = Path(__file__).resolve().parent.parent
KEY = os.environ.get("TMDB_API_KEY", "")
PER_PAGE = 20
TARGET = 100
HORROR = 27

MOVIE_CATALOGS = [
    ("rom-coms", {
        "with_genres": "35,10749",
        "without_genres": "27",
        "vote_count.gte": "50",
        "sort_by": "popularity.desc",
        "include_adult": "false",
    }),
    ("hallmark-movies", {
        "with_companies": "53015|4056|6435",
        "without_genres": "27",
        "sort_by": "popularity.desc",
        "include_adult": "false",
    }),
    ("dramas", {
        "with_genres": "18",
        "without_genres": "27",
        "vote_count.gte": "50",
        "sort_by": "popularity.desc",
        "include_adult": "false",
    }),
    ("tv-movies", {
        "with_companies": "3431",
        "without_genres": "27",
        "sort_by": "popularity.desc",
        "include_adult": "false",
    }),
    ("stand-up-specials", {
        "with_genres": "35",
        "with_keywords": "9716",
        "without_genres": "27",
        "sort_by": "popularity.desc",
        "include_adult": "false",
    }),
]

TV_CATALOGS = [
    ("rom-com-shows", {
        "with_genres": "35,10749",
        "without_genres": "27",
        "sort_by": "popularity.desc",
        "include_adult": "false",
    }),
    ("drama-shows", {
        "with_genres": "18",
        "without_genres": "27",
        "sort_by": "popularity.desc",
        "include_adult": "false",
    }),
    ("comedy-shows", {
        "with_genres": "35",
        "without_genres": "27",
        "sort_by": "popularity.desc",
        "include_adult": "false",
    }),
    ("hallmark-shows", {
        "with_networks": "384",
        "without_genres": "27",
        "sort_by": "popularity.desc",
        "include_adult": "false",
    }),
]


def get_json(path, params):
    params = dict(params)
    params["api_key"] = KEY
    params["language"] = "en-US"
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"GET {path} failed after retries")


def rate_limited():
    time.sleep(0.25)


def poster(path):
    return IMG + path if path else None


def has_horror(d):
    return any(g.get("id") == HORROR for g in d.get("genres", []))


def movie_meta(d):
    if has_horror(d) or not d.get("imdb_id") or not d.get("poster_path"):
        return None
    return {
        "id": d["imdb_id"],
        "type": "movie",
        "name": d.get("title") or d.get("original_title"),
        "poster": poster(d["poster_path"]),
        "posterShape": "poster",
        "releaseInfo": (d.get("release_date") or "")[:4],
        "genres": [g["name"] for g in d.get("genres", [])][:3],
    }


def tv_meta(d):
    ext = d.get("external_ids") or {}
    if has_horror(d) or not ext.get("imdb_id") or not d.get("poster_path"):
        return None
    return {
        "id": ext["imdb_id"],
        "type": "series",
        "name": d.get("name") or d.get("original_name"),
        "poster": poster(d["poster_path"]),
        "posterShape": "poster",
        "releaseInfo": (d.get("first_air_date") or "")[:4],
        "genres": [g["name"] for g in d.get("genres", [])][:3],
    }


def build_movies(catalog_id, params):
    metas, seen = [], set()
    page = 1
    while len(metas) < TARGET and page <= 8:
        res = get_json("/discover/movie", dict(params, page=page))
        rate_limited()
        for item in res.get("results", []):
            if len(metas) >= TARGET:
                break
            d = get_json(f"/movie/{item['id']}", {})
            rate_limited()
            m = movie_meta(d)
            if m and m["id"] not in seen:
                seen.add(m["id"])
                metas.append(m)
        page += 1
    return metas


def build_tv(catalog_id, params):
    metas, seen = [], set()
    page = 1
    while len(metas) < TARGET and page <= 30:
        res = get_json("/discover/tv", dict(params, page=page))
        rate_limited()
        for item in res.get("results", []):
            if len(metas) >= TARGET:
                break
            d = get_json(f"/tv/{item['id']}", {
                "append_to_response": "external_ids",
            })
            rate_limited()
            m = tv_meta(d)
            if m and m["id"] not in seen:
                seen.add(m["id"])
                metas.append(m)
        page += 1
    return metas


def write_catalog(ctype, catalog_id, metas):
    d = OUT / "catalog" / ctype
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{catalog_id}.json").write_text(json.dumps({"metas": metas}, indent=1))
    sub = d / catalog_id
    sub.mkdir(parents=True, exist_ok=True)
    (sub / "skip=0.json").write_text(json.dumps({"metas": metas}, indent=1))
    (sub / "skip=100.json").write_text(json.dumps({"metas": []}, indent=1))
    print(f"  {ctype}/{catalog_id}: {len(metas)} items")


def main():
    if not KEY:
        print("TMDB_API_KEY is not set. Get a free key at https://www.themoviedb.org/settings/api")
        return 1
    print("Building Made for Tammy catalogs from TMDB...")
    for catalog_id, params in MOVIE_CATALOGS:
        write_catalog("movie", catalog_id, build_movies(catalog_id, params))
    for catalog_id, params in TV_CATALOGS:
        write_catalog("series", catalog_id, build_tv(catalog_id, params))
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
