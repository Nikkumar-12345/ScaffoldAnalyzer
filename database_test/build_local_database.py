import sqlite3
import time
import requests


DB_PATH = "scaffold_analyzer_chembl.db"

BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"


# --------------------------------------------------
# DATABASE SETUP
# --------------------------------------------------

def create_database():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS targets (

            target_chembl_id TEXT PRIMARY KEY,

            uniprot_id TEXT,

            pref_name TEXT,

            target_type TEXT,

            organism TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activities (

            activity_id INTEGER PRIMARY KEY,

            target_chembl_id TEXT NOT NULL,

            molecule_chembl_id TEXT,

            canonical_smiles TEXT,

            standard_value REAL,

            standard_units TEXT,

            standard_relation TEXT,

            standard_type TEXT,

            pchembl_value REAL,

            assay_chembl_id TEXT,

            document_chembl_id TEXT,

            FOREIGN KEY (target_chembl_id)
                REFERENCES targets(target_chembl_id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_targets_uniprot
        ON targets(uniprot_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_activities_target
        ON activities(target_chembl_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_activities_molecule
        ON activities(molecule_chembl_id)
    """)

    conn.commit()

    return conn


# --------------------------------------------------
# SAFE API REQUEST
# --------------------------------------------------

def safe_get(session, url, timeout=120):

    response = session.get(
        url,
        timeout=timeout
    )

    response.raise_for_status()

    return response


# --------------------------------------------------
# FIND TARGET
# --------------------------------------------------

def get_target(session, uniprot_id):

    print("\nSearching for target...")

    url = (
        BASE_URL
        + "/target.json"
        + "?target_components__accession="
        + uniprot_id
    )

    response = safe_get(
        session,
        url,
        timeout=60
    )

    data = response.json()

    targets = data.get(
        "targets",
        []
    )

    for target in targets:

        if (
            target.get("target_type")
            == "SINGLE PROTEIN"

            and

            target.get("organism")
            == "Homo sapiens"
        ):

            print(
                "Target found:",
                target.get("target_chembl_id")
            )

            return target

    raise Exception(
        "No Human SINGLE PROTEIN target found."
    )


# --------------------------------------------------
# STORE TARGET
# --------------------------------------------------

def store_target(
    conn,
    target,
    uniprot_id
):

    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO targets (

            target_chembl_id,
            uniprot_id,
            pref_name,
            target_type,
            organism

        )

        VALUES (?, ?, ?, ?, ?)
    """, (

        target.get("target_chembl_id"),

        uniprot_id,

        target.get("pref_name"),

        target.get("target_type"),

        target.get("organism")
    ))

    conn.commit()


# --------------------------------------------------
# DOWNLOAD + STORE ACTIVITIES
# --------------------------------------------------

def download_activities(
    conn,
    session,
    target_chembl_id
):

    print("\nDownloading IC50 activities...\n")

    url = (
        BASE_URL
        + "/activity.json"
        + "?target_chembl_id="
        + target_chembl_id
        + "&standard_type=IC50"
        + "&limit=500"
    )

    cursor = conn.cursor()

    page_number = 1
    total_received = 0
    total_stored = 0

    while url:

        print(
            f"Downloading page {page_number}..."
        )

        response = safe_get(
            session,
            url,
            timeout=120
        )

        data = response.json()

        activities = data.get(
            "activities",
            []
        )

        total_received += len(
            activities
        )

        rows = []

        for activity in activities:

            activity_id = activity.get(
                "activity_id"
            )

            molecule_id = activity.get(
                "molecule_chembl_id"
            )

            smiles = activity.get(
                "canonical_smiles"
            )

            standard_value = activity.get(
                "standard_value"
            )

            standard_relation = activity.get(
                "standard_relation"
            )

            # Keep only data useful for analysis

            if not activity_id:
                continue

            if not molecule_id:
                continue

            if not smiles:
                continue

            if standard_value is None:
                continue

            if standard_relation != "=":
                continue

            rows.append((
                activity_id,
                target_chembl_id,
                molecule_id,
                smiles,
                standard_value,
                activity.get(
                    "standard_units"
                ),
                standard_relation,
                activity.get(
                    "standard_type"
                ),
                activity.get(
                    "pchembl_value"
                ),
                activity.get(
                    "assay_chembl_id"
                ),
                activity.get(
                    "document_chembl_id"
                )
            ))

        cursor.executemany("""
            INSERT OR IGNORE INTO activities (

                activity_id,
                target_chembl_id,
                molecule_chembl_id,
                canonical_smiles,
                standard_value,
                standard_units,
                standard_relation,
                standard_type,
                pchembl_value,
                assay_chembl_id,
                document_chembl_id

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)

        conn.commit()

        total_stored += len(
            rows
        )

        print(
            f"Page {page_number} complete | "
            f"Received: {total_received} | "
            f"Stored: {total_stored}"
        )

        page_meta = data.get(
            "page_meta",
            {}
        )

        next_page = page_meta.get(
            "next"
        )

        if next_page:

            if next_page.startswith(
                "http"
            ):

                url = next_page

            else:

                url = (
                    "https://www.ebi.ac.uk"
                    + next_page
                )

            page_number += 1

            time.sleep(0.3)

        else:

            url = None

    print("\nActivity download complete.")

    print(
        f"Total API records: {total_received}"
    )

    print(
        f"Total valid records stored: {total_stored}"
    )


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("=" * 70)
    print("SCAFFOLD ANALYZER - LOCAL ChEMBL DATABASE BUILDER")
    print("=" * 70)

    print(
        "\nCreating/opening SQLite database..."
    )

    conn = create_database()

    session = requests.Session()

    try:

        # ------------------------------------------
        # TEST TARGET
        # ------------------------------------------

        uniprot_id = "P00533"

        target = get_target(
            session,
            uniprot_id
        )

        target_chembl_id = target.get(
            "target_chembl_id"
        )

        store_target(
            conn,
            target,
            uniprot_id
        )

        download_activities(
            conn,
            session,
            target_chembl_id
        )

        print("\n" + "=" * 70)
        print("DATABASE BUILD SUCCESSFUL")
        print("=" * 70)

        print(
            f"\nDatabase created at:\n"
            f"{DB_PATH}"
        )

        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM targets"
        )

        target_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM activities"
        )

        activity_count = cursor.fetchone()[0]

        print(
            f"\nTargets stored: {target_count}"
        )

        print(
            f"Activities stored: {activity_count}"
        )

    finally:

        conn.close()

        session.close()


if __name__ == "__main__":

    main()