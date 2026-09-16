#!/usr/bin/env python3
"""
Génère data/euamdb10.json à partir des CSV bruts SPOT et HISTO.

Ce script ne modifie JAMAIS les CSV sources : lecture seule.
Il s'exécute APRÈS le script de récupération (SPOT + HISTO) dans le
workflow GitHub Actions, jamais avant.

Entrées attendues (chemins relatifs à la racine du repo — voir note
sur les chemins en bas de fichier) :
  - data/EUAMDB10_SPOT.csv    : dernière valeur connue (1 ligne de données)
  - data/EUAMDB10_HISTO.csv   : historique complet, append-only
  - data/EUAMDB10_PARAMS.csv  : paramètres contractuels MIN/MAX, fixés
                                 manuellement, censés ne pas changer

Format SPOT/HISTO (séparateur ';') :
  date_market;timestamp_utc;index;value;source
  HISTO a une colonne supplémentaire #num en position 2, ignorée ici
  car reconstructible depuis l'ordre des lignes si jamais nécessaire.

Format PARAMS (séparateur ';') :
  param;value
  MIN;3.10
  MAX;4.20

Sortie : data/euamdb10.json
{
  "spot": {
    "label": "SPOT",
    "value": 3.6,
    "date": "16.09.2026",
    "last_update": "16/09/2026 07:12:27 UTC"
  },
  "params": {
    "min": 3.1,
    "max": 4.2
  },
  "history": [
    {"date": "2017-07-15", "value": 0.3},
    ...
    {"date": "2026-09-16", "value": 3.6}
  ]
}

Points de fragilité connus (à relire avant modification) :
  - Suppose un format de date strict d/m/Y, celui observé dans les CSV
    fournis le 16/09/2026. Un changement de format côté script amont
    casse ce script sans avertissement autre qu'une ValueError.
  - Ne déduplique PAS l'historique par date : si le script amont écrit
    deux lignes pour le même jour, les deux se retrouvent dans le
    JSON et le graphe affichera un doublon. La garantie d'unicité par
    jour doit venir du script SPOT/HISTO en amont, pas d'ici.
  - Aucune détection de valeur aberrante : une valeur de saisie
    erronée dans HISTO.csv se propage telle quelle dans le JSON.
  - "last_update" est repris tel quel du timestamp_utc du SPOT — si ce
    champ est absent ou mal formé côté source, il est recopié sans
    validation.

Non testé : comportement si HISTO.csv contient une ligne d'en-tête
différente (BOM, ordre de colonnes changé) — seul le format observé
au 16/09/2026 a été vérifié.

  - PARAMS.csv est traité comme contractuel : si le fichier est
    absent ou incomplet (MIN ou MAX manquant), le script s'arrête en
    erreur plutôt que de générer un JSON sans ces valeurs — une page
    affichée sans ses seuils contractuels serait une régression
    silencieuse plus grave qu'un échec de build visible.
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

# --- Configuration -----------------------------------------------------
# Chemins RELATIFS à la racine du repo, volontairement (et non absolus) :
# dans un runner GitHub Actions, le chemin absolu du workspace change à
# chaque exécution, donc "chemin absolu et stable" au sens habituel n'a
# pas de sens ici. La stabilité vient du fait que le script est toujours
# lancé avec cwd = racine du repo (garanti par le workflow, voir tâche 5).
SPOT_PATH = Path("data/EUAMDB10_SPOT.csv")
HISTO_PATH = Path("data/EUAMDB10_HISTO.csv")
PARAMS_PATH = Path("data/EUAMDB10_PARAMS.csv")
OUTPUT_PATH = Path("data/euamdb10.json")
# Copie supplémentaire : GitHub Pages sert uniquement le contenu de /docs,
# pas /data à la racine du repo. Le HTML dans docs/ fait donc
# fetch('data/euamdb10.json') en relatif, ce qui résout vers ce chemin-ci
# une fois le site publié. data/euamdb10.json (ci-dessus) reste la source
# de référence pour l'audit et pour tout futur script qui en aurait besoin.
DOCS_OUTPUT_PATH = Path("docs/data/euamdb10.json")
# -------------------------------------------------------------------------


def read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        print(f"ERREUR : fichier introuvable : {path}", file=sys.stderr)
        sys.exit(1)
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def parse_date_market(raw: str) -> datetime:
    return datetime.strptime(raw.strip(), "%d/%m/%Y")


def build_spot(rows: list[dict]) -> dict:
    if not rows:
        print("ERREUR : SPOT.csv ne contient aucune donnée", file=sys.stderr)
        sys.exit(1)
    last = rows[-1]  # une seule ligne attendue ; on prend la dernière par sécurité
    d = parse_date_market(last["date_market"])
    return {
        "label": "SPOT",
        "value": round(float(last["value"]), 4),
        "date": d.strftime("%d.%m.%Y"),
        "last_update": last["timestamp_utc"].strip() + " UTC",
    }


def build_params(rows: list[dict]) -> dict:
    values = {}
    for row in rows:
        key = row["param"].strip().upper()
        values[key] = float(row["value"])
    missing = {"MIN", "MAX"} - values.keys()
    if missing:
        print(
            f"ERREUR : paramètre(s) contractuel(s) manquant(s) dans PARAMS.csv : "
            f"{', '.join(sorted(missing))}",
            file=sys.stderr,
        )
        sys.exit(1)
    return {"min": values["MIN"], "max": values["MAX"]}


def build_history(rows: list[dict]) -> list[dict]:
    history = []
    for row in rows:
        d = parse_date_market(row["date_market"])
        history.append(
            {"date": d.strftime("%Y-%m-%d"), "value": round(float(row["value"]), 4)}
        )
    history.sort(key=lambda x: x["date"])
    return history


def main() -> None:
    spot_rows = read_csv_rows(SPOT_PATH)
    histo_rows = read_csv_rows(HISTO_PATH)
    params_rows = read_csv_rows(PARAMS_PATH)

    payload = {
        "spot": build_spot(spot_rows),
        "params": build_params(params_rows),
        "history": build_history(histo_rows),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    DOCS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DOCS_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(
        f"OK : {len(payload['history'])} points d'historique, "
        f"spot={payload['spot']['value']} au {payload['spot']['date']} "
        f"— écrit dans {OUTPUT_PATH} et {DOCS_OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
