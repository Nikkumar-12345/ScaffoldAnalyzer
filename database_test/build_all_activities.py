import sqlite3
import time
import requests

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ==================================================
# CONFIGURATION
# ==================================================

DB_PATH = "scaffold_analyzer_chembl.db"

BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"

PAGE_SIZE = 500

DELAY_BETWEEN_PAGES = 0.2

DELAY_BETWEEN_TARGETS = 0.3


# ==================================================
# REQUIRED ACTIVITY COLUMNS
# ==================================================

REQUIRED_COLUMNS = [
    "activity_id",
    "target_chembl_id",
    "molecule_chembl_id",
    "canonical_smiles",
    "standard_value",
    "standard_units",
    "standard_relation",
    "standard_type",
    "pchembl_value",
    "assay_chembl_id",
    "document_chembl_id"
]


# ==================================================
# DATABASE SETUP
# ==================================================

def setup_database():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    # ----------------------------------------------
    # ACTIVITIES TABLE
    # ----------------------------------------------

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

            document_chembl_id TEXT
        )
    """)

    # ----------------------------------------------
    # IMPORT STATUS TABLE
    #
    # A target is added here ONLY after every page
    # for that target has been successfully processed.
    # ----------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS import_status (

            target_chembl_id TEXT PRIMARY KEY,

            status TEXT NOT NULL,

            completed_at TEXT DEFAULT CURRENT_TIMESTAMP,

            records_imported INTEGER DEFAULT 0
        )
    """)

    # ----------------------------------------------
    # INDEXES
    # ----------------------------------------------

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


# ==================================================
# CREATE ROBUST REQUEST SESSION
# ==================================================

def create_session():

    session = requests.Session()

    retry = Retry(

        total=8,

        connect=8,

        read=8,

        status=8,

        backoff_factor=2,

        status_forcelist=[
            429,
            500,
            502,
            503,
            504
        ],

        allowed_methods=["GET"],

        raise_on_status=False
    )

    adapter = HTTPAdapter(
        max_retries=retry
    )

    session.mount(
        "https://",
        adapter
    )

    session.mount(
        "http://",
        adapter
    )

    return session


# ==================================================
# SAFE GET
# ==================================================

def safe_get(session, url):

    response = session.get(
        url,
        timeout=120
    )

    if response.status_code >= 500:

        raise Exception(
            f"ChEMBL server error: "
            f"{response.status_code}"
        )

    response.raise_for_status()

    return response


# ==================================================
# LOAD ALL TARGETS
# ==================================================

def load_all_targets(conn):

    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT target_chembl_id
        FROM targets
        WHERE target_chembl_id IS NOT NULL
        ORDER BY target_chembl_id
    """)

    targets = [
        row[0]
        for row in cursor.fetchall()
    ]

    return targets


# ==================================================
# LOAD COMPLETED TARGETS
# ==================================================

def load_completed_targets(conn):

    cursor = conn.cursor()

    cursor.execute("""
        SELECT target_chembl_id
        FROM import_status
        WHERE status = 'completed'
    """)

    completed_targets = {
        row[0]
        for row in cursor.fetchall()
    }

    return completed_targets


# ==================================================
# INSERT ACTIVITY ROWS
# ==================================================

def insert_rows(conn, rows):

    if not rows:
        return 0

    cursor = conn.cursor()

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

    return len(rows)


# ==================================================
# MARK TARGET AS COMPLETED
# ==================================================

def mark_target_completed(
    conn,
    target_chembl_id,
    records_imported
):

    cursor = conn.cursor()

    cursor.execute("""

        INSERT INTO import_status (

            target_chembl_id,
            status,
            records_imported,
            completed_at

        )

        VALUES (?, 'completed', ?, CURRENT_TIMESTAMP)

        ON CONFLICT(target_chembl_id)

        DO UPDATE SET

            status = 'completed',

            records_imported =
                excluded.records_imported,

            completed_at =
                CURRENT_TIMESTAMP

    """, (

        target_chembl_id,
        records_imported

    ))

    conn.commit()


# ==================================================
# DOWNLOAD ONE TARGET
# ==================================================

def download_target(
    conn,
    session,
    target_chembl_id
):

    url = (
        BASE_URL
        + "/activity.json"
        + "?target_chembl_id="
        + target_chembl_id
        + "&standard_type=IC50"
        + f"&limit={PAGE_SIZE}"
        + "&only="
        + ",".join(REQUIRED_COLUMNS)
    )

    page_number = 1

    target_records_received = 0

    target_valid_records = 0

    print(
        f"\nDownloading target: "
        f"{target_chembl_id}"
    )

    while url:

        response = safe_get(
            session,
            url
        )

        data = response.json()

        activities = data.get(
            "activities",
            []
        )

        target_records_received += len(
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

            # ------------------------------------------
            # KEEP SAME FILTERING AS YOUR APP
            # ------------------------------------------

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

        inserted = insert_rows(
            conn,
            rows
        )

        target_valid_records += inserted

        print(
            f"  Page {page_number} | "
            f"Received: {len(activities)} | "
            f"Valid: {len(rows)}"
        )

        # ----------------------------------------------
        # GET NEXT PAGE
        # ----------------------------------------------

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

            time.sleep(
                DELAY_BETWEEN_PAGES
            )

        else:

            url = None

    print(
        f"  Completed {target_chembl_id} | "
        f"API records: {target_records_received} | "
        f"Valid records processed: {target_valid_records}"
    )

    return target_valid_records


# ==================================================
# GET DATABASE STATISTICS
# ==================================================

def get_database_stats(conn):

    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM activities
    """)

    total_activities = (
        cursor.fetchone()[0]
    )

    cursor.execute("""
        SELECT COUNT(DISTINCT target_chembl_id)
        FROM activities
    """)

    targets_with_activities = (
        cursor.fetchone()[0]
    )

    cursor.execute("""
        SELECT COUNT(*)
        FROM import_status
        WHERE status = 'completed'
    """)

    completed_targets = (
        cursor.fetchone()[0]
    )

    return (
        total_activities,
        targets_with_activities,
        completed_targets
    )


# ==================================================
# MAIN IMPORT FUNCTION
# ==================================================

def build_database():

    print("=" * 70)
    print("SCAFFOLD ANALYZER")
    print("RESUMABLE HUMAN IC50 DATABASE IMPORT")
    print("=" * 70)

    conn = setup_database()

    session = create_session()

    start_time = time.time()

    try:

        # ----------------------------------------------
        # LOAD TARGETS
        # ----------------------------------------------

        all_targets = load_all_targets(
            conn
        )

        completed_targets = (
            load_completed_targets(
                conn
            )
        )

        pending_targets = [

            target

            for target in all_targets

            if target not in completed_targets

        ]

        print(
            f"\nTotal Human SINGLE PROTEIN targets: "
            f"{len(all_targets):,}"
        )

        print(
            f"Already completed targets: "
            f"{len(completed_targets):,}"
        )

        print(
            f"Targets remaining: "
            f"{len(pending_targets):,}"
        )

        (
            total_activities,
            targets_with_activities,
            completed_count
        ) = get_database_stats(conn)

        print(
            f"\nExisting activities in database: "
            f"{total_activities:,}"
        )

        print(
            f"Existing targets with activities: "
            f"{targets_with_activities:,}"
        )

        # ----------------------------------------------
        # IMPORT PENDING TARGETS
        # ----------------------------------------------

        total_targets = len(
            all_targets
        )

        completed_before_start = len(
            completed_targets
        )

        for index, target_chembl_id in enumerate(
            pending_targets,
            start=1
        ):

            overall_number = (
                completed_before_start
                + index
            )

            print(
                "\n"
                + "=" * 70
            )

            print(
                f"TARGET "
                f"{overall_number}/{total_targets}"
            )

            print(
                f"ChEMBL ID: "
                f"{target_chembl_id}"
            )

            print(
                "=" * 70
            )

            try:

                records_imported = (
                    download_target(
                        conn,
                        session,
                        target_chembl_id
                    )
                )

                # IMPORTANT:
                # We reach here only after ALL pages
                # for this target completed successfully.

                mark_target_completed(
                    conn,
                    target_chembl_id,
                    records_imported
                )

                elapsed = (
                    time.time()
                    - start_time
                )

                print(
                    f"\n✓ Target completed: "
                    f"{target_chembl_id}"
                )

                print(
                    f"Progress: "
                    f"{overall_number}/{total_targets}"
                )

                print(
                    f"Elapsed: "
                    f"{elapsed / 60:.2f} minutes"
                )

                # --------------------------------------
                # CURRENT DATABASE STATS
                # --------------------------------------

                (
                    current_activities,
                    current_targets,
                    current_completed
                ) = get_database_stats(
                    conn
                )

                print(
                    f"Database activities: "
                    f"{current_activities:,}"
                )

                print(
                    f"Targets with activities: "
                    f"{current_targets:,}"
                )

                print(
                    f"Targets marked completed: "
                    f"{current_completed:,}"
                )

                time.sleep(
                    DELAY_BETWEEN_TARGETS
                )

            except KeyboardInterrupt:

                print(
                    "\n\n"
                    + "=" * 70
                )

                print(
                    "IMPORT STOPPED BY USER"
                )

                print(
                    "=" * 70
                )

                print(
                    "\nThe current target was NOT "
                    "marked as completed."
                )

                print(
                    "All previously committed records "
                    "remain safely in the database."
                )

                print(
                    "\nRun this script again to resume."
                )

                break

            except Exception as e:

                print(
                    f"\nERROR FOR TARGET "
                    f"{target_chembl_id}:"
                )

                print(
                    str(e)
                )

                print(
                    "\nThis target was NOT marked "
                    "completed."
                )

                print(
                    "The importer will continue with "
                    "the next target."
                )

                continue

        # ----------------------------------------------
        # FINAL STATISTICS
        # ----------------------------------------------

        (
            total_activities,
            targets_with_activities,
            completed_count
        ) = get_database_stats(
            conn
        )

        elapsed = (
            time.time()
            - start_time
        )

        print(
            "\n"
            + "=" * 70
        )

        print(
            "CURRENT IMPORT STATUS"
        )

        print(
            "=" * 70
        )

        print(
            f"\nTotal activities stored: "
            f"{total_activities:,}"
        )

        print(
            f"Targets with activities: "
            f"{targets_with_activities:,}"
        )

        print(
            f"Targets fully completed: "
            f"{completed_count:,}"
        )

        print(
            f"Targets still remaining: "
            f"{len(all_targets) - completed_count:,}"
        )

        print(
            f"Time for this run: "
            f"{elapsed / 60:.2f} minutes"
        )

        print(
            f"\nDatabase file: "
            f"{DB_PATH}"
        )

        print(
            "\nRun the same script again anytime "
            "to continue importing unfinished targets."
        )

    finally:

        conn.close()

        session.close()


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    build_database()