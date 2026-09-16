import csv
import os
import shutil
import re
import requests
from datetime import datetime, timezone


# ============================================================
# CONFIGURATION
# ============================================================

INDEX = "EUAMDB10"

URL = "https://equityderivatives.natixis.com/fr/indice/euamdb10/"

SPOT_FILE = "EUAMDB10_SPOT.csv"
SPOT_OLD_FILE = "EUAMDB10_SPOT_OLD.csv"

HISTO_FILE = "EUAMDB10_HISTO.csv"
HISTO_OLD_FILE = "EUAMDB10_HISTO_OLD.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}

CSV_HEADER = [
    "date_market",
    "timestamp_utc",
    "index",
    "value",
    "source"
]


# ============================================================
# RECUPERATION NATIXIS
# ============================================================

def get_spot():

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    html = response.text

    match = re.search(
        r"seriesArray\s*=\s*(.*?);",
        html,
        flags=re.I | re.S
    )

    if not match:
        raise RuntimeError(
            "seriesArray introuvable dans la page Natixis."
        )

    series = re.findall(
        r"\[\s*(\d{12,13})\s*,\s*(-?\d+(?:[.,]\d+)?)\s*\]",
        match.group(1)
    )

    if not series:
        raise RuntimeError(
            "Aucune donnée EUAMDB10 trouvée."
        )

    timestamp = int(series[-1][0])

    value = float(
        series[-1][1].replace(",", ".")
    )

    if timestamp < 100_000_000_000:
        timestamp *= 1000

    dt = datetime.fromtimestamp(
        timestamp / 1000,
        timezone.utc
    )

    return {
        "date_market": dt.strftime("%d/%m/%Y"),
        "timestamp_utc": dt.strftime("%d/%m/%Y %H:%M:%S"),
        "index": INDEX,
        "value": f"{value:.4f}",
        "source": URL
    }


# ============================================================
# LECTURE CSV
# ============================================================

def read_csv(filename):

    with open(
        filename,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        first_line = f.readline()

        if ";" in first_line:
            delimiter = ";"

        elif "\t" in first_line:
            delimiter = "\t"

        else:
            raise RuntimeError(
                f"{filename} : séparateur CSV inconnu."
            )

        f.seek(0)

        reader = csv.DictReader(
            f,
            delimiter=delimiter
        )

        if reader.fieldnames is None:
            raise RuntimeError(
                f"{filename} : en-tête CSV absent."
            )

        reader.fieldnames = [
            field.strip()
            for field in reader.fieldnames
        ]

        missing = set(CSV_HEADER) - set(reader.fieldnames)

        if missing:
            raise RuntimeError(
                f"{filename} : colonnes manquantes : "
                f"{', '.join(sorted(missing))}\n"
                f"Colonnes trouvées : {reader.fieldnames}"
            )

        rows = []

        for row in reader:

            clean_row = {
                key.strip(): (
                    value.strip()
                    if value is not None
                    else ""
                )
                for key, value in row.items()
            }

            if not clean_row["date_market"]:
                continue

            rows.append({
                "date_market": clean_row["date_market"],
                "timestamp_utc": clean_row["timestamp_utc"],
                "index": clean_row["index"],
                "value": clean_row["value"],
                "source": clean_row["source"],
            })

    return rows


# ============================================================
# ECRITURE CSV
# ============================================================

def write_csv(filename, rows):

    with open(
        filename,
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=CSV_HEADER,
            delimiter=";",
            lineterminator="\n"
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(row)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("EUAMDB10 - DAILY BATCH V1.05")
    print("=" * 60)

    # --------------------------------------------------------
    # 1. Vérification HISTO
    # --------------------------------------------------------

    if not os.path.exists(HISTO_FILE):
        raise RuntimeError(
            f"{HISTO_FILE} est absent."
        )

    # --------------------------------------------------------
    # 2. Récupération SPOT
    # --------------------------------------------------------

    print("\nRécupération Natixis...")

    spot = get_spot()

    print(
        f"Spot : {spot['date_market']} "
        f"{spot['timestamp_utc']} "
        f"{spot['value']}"
    )

    # --------------------------------------------------------
    # 3. Lecture HISTO
    # --------------------------------------------------------

    histo = read_csv(HISTO_FILE)

    print(
        f"HISTO actuel : {len(histo)} lignes"
    )

    # --------------------------------------------------------
    # 4. Suppression de l'ancienne ligne du jour
    # --------------------------------------------------------

    histo = [
        row
        for row in histo
        if row["date_market"] != spot["date_market"]
    ]

    # --------------------------------------------------------
    # 5. AJOUT DE LA NOUVELLE LIGNE A LA FIN
    # --------------------------------------------------------

    histo.append(spot)

    print(
        f"Nouvel HISTO : {len(histo)} lignes"
    )

    # --------------------------------------------------------
    # 6. BACKUP HISTO
    # --------------------------------------------------------

    shutil.copy2(
        HISTO_FILE,
        HISTO_OLD_FILE
    )

    print(
        f"Backup : {HISTO_FILE} -> {HISTO_OLD_FILE}"
    )

    # --------------------------------------------------------
    # 7. Ecriture HISTO
    # --------------------------------------------------------

    write_csv(
        HISTO_FILE,
        histo
    )

    print(
        "Nouveau HISTO écrit."
    )

    # --------------------------------------------------------
    # 8. BACKUP SPOT
    # --------------------------------------------------------

    if os.path.exists(SPOT_FILE):

        shutil.copy2(
            SPOT_FILE,
            SPOT_OLD_FILE
        )

        print(
            f"Backup : {SPOT_FILE} -> {SPOT_OLD_FILE}"
        )

    # --------------------------------------------------------
    # 9. Nouveau SPOT
    # --------------------------------------------------------

    write_csv(
        SPOT_FILE,
        [spot]
    )

    print(
        "Nouveau SPOT écrit."
    )

    # --------------------------------------------------------
    # FIN
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("BATCH TERMINE")
    print("=" * 60)

    print(
        f"\nHISTO : {len(histo)} lignes"
    )

    print(
        f"SPOT  : {spot['date_market']} "
        f"{spot['value']}"
    )


if __name__ == "__main__":
    main()