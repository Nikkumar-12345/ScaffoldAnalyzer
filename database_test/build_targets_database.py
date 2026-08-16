import sqlite3
import time
import requests


DB_PATH = "scaffold_analyzer_chembl.db"
BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"


# --------------------------------------------------
# CREATE TARGET TABLE
# --------------------------------------------------

def setup_database():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS targets (

            target_chembl_id TEXT NOT NULL,
            uniprot_id TEXT NOT NULL,

            pref_name TEXT,

            target_type TEXT,

            organism TEXT,

            PRIMARY KEY (
                target_chembl_id,
                uniprot_id
            )
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_targets_uniprot
        ON targets(uniprot_id)
    """)

    conn.commit()

    return conn


# --------------------------------------------------
# SAFE REQUEST
# --------------------------------------------------

def safe_get(session, url):

    response = session.get(
        url,
        timeout=120
    )

    response.raise_for_status()

    return response


# --------------------------------------------------
# EXTRACT UNIPROT ACCESSIONS
# --------------------------------------------------

def get_uniprot_ids(target):

    uniprot_ids = set()

    components = target.get(
        "target_components",
        []
    )

    for component in components:

        accession = component.get(
            "accession"
        )

        if accession:
            uniprot_ids.add(
                accession
            )

    return list(uniprot_ids)


# --------------------------------------------------
# DOWNLOAD AND STORE TARGETS
# --------------------------------------------------

def download_targets(conn):

    session = requests.Session()

    url = (
        BASE_URL
        + "/target.json"
        + "?target_type=SINGLE%20PROTEIN"
        + "&organism=Homo%20sapiens"
        + "&limit=500"
    )

    cursor = conn.cursor()

    page_number = 1
    total_received = 0
    total_targets_stored = 0

    print("\nDownloading human SINGLE PROTEIN targets...\n")

    try:

        while url:

            print(
                f"Downloading page {page_number}..."
            )

            response = safe_get(
                session,
                url
            )

            data = response.json()

            targets = data.get(
                "targets",
                []
            )

            total_received += len(
                targets
            )

            rows = []

            for target in targets:

                target_id = target.get(
                    "target_chembl_id"
                )

                if not target_id:
                    continue

                uniprot_ids = get_uniprot_ids(
                    target
                )

                # Skip targets without a UniProt accession
                if not uniprot_ids:
                    continue

                for uniprot_id in uniprot_ids:

                    rows.append((
                        target_id,
                        uniprot_id,
                        target.get("pref_name"),
                        target.get("target_type"),
                        target.get("organism")
                    ))

            if rows:

                cursor.executemany("""
                    INSERT OR IGNORE INTO targets (

                        target_chembl_id,
                        uniprot_id,
                        pref_name,
                        target_type,
                        organism

                    )

                    VALUES (?, ?, ?, ?, ?)
                """, rows)

                conn.commit()

                total_targets_stored += len(
                    rows
                )

            print(
                f"Page {page_number} complete | "
                f"API targets seen: {total_received} | "
                f"Target-UniProt mappings stored: "
                f"{total_targets_stored}"
            )

            page_meta = data.get(
                "page_meta",
                {}
            )

            next_page = page_meta.get(
                "next"
            )

            if next_page:

                if next_page.startswith("http"):

                    url = next_page

                else:

                    url = (
                        "https://www.ebi.ac.uk"
                        + next_page
                    )

                page_number += 1

                time.sleep(0.2)

            else:

                url = None

    finally:

        session.close()

    print("\n" + "=" * 70)
    print("TARGET DOWNLOAD COMPLETE")
    print("=" * 70)

    print(
        f"\nTotal API targets received: "
        f"{total_received}"
    )

    print(
        f"Target-UniProt mappings processed: "
        f"{total_targets_stored}"
    )


# --------------------------------------------------
# FINAL DATABASE STATISTICS
# --------------------------------------------------

def show_statistics(conn):

    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM targets
    """)

    total_mappings = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(DISTINCT target_chembl_id)
        FROM targets
    """)

    unique_targets = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(DISTINCT uniprot_id)
        FROM targets
    """)

    unique_uniprots = cursor.fetchone()[0]

    print("\n" + "=" * 70)
    print("DATABASE STATISTICS")
    print("=" * 70)

    print(
        f"\nTarget-UniProt mappings: "
        f"{total_mappings}"
    )

    print(
        f"Unique ChEMBL targets: "
        f"{unique_targets}"
    )

    print(
        f"Unique UniProt IDs: "
        f"{unique_uniprots}"
    )


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("=" * 70)
    print("SCAFFOLD ANALYZER - COMPLETE TARGET DATABASE BUILDER")
    print("=" * 70)

    print(
        f"\nDatabase: {DB_PATH}"
    )

    conn = setup_database()

    try:

        download_targets(conn)

        show_statistics(conn)

    finally:

        conn.close()

    print("\nDone.")


if __name__ == "__main__":

    main()