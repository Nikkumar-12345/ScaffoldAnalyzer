import sqlite3
import pandas as pd


DB_PATH = "scaffold_analyzer_chembl.db"


def get_target(uniprot_id):

    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT
            target_chembl_id,
            uniprot_id,
            pref_name,
            target_type,
            organism
        FROM targets
        WHERE uniprot_id = ?
    """

    target = pd.read_sql_query(
        query,
        conn,
        params=(uniprot_id,)
    )

    conn.close()

    return target


def get_activities(uniprot_id):

    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT

            a.activity_id,
            a.molecule_chembl_id,
            a.canonical_smiles,
            a.standard_value,
            a.standard_units,
            a.standard_relation,
            a.standard_type,
            a.pchembl_value,
            a.assay_chembl_id,
            a.document_chembl_id

        FROM activities a

        INNER JOIN targets t
            ON a.target_chembl_id =
               t.target_chembl_id

        WHERE t.uniprot_id = ?

        AND a.standard_relation = '='

        AND a.canonical_smiles IS NOT NULL

        AND a.standard_value IS NOT NULL
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=(uniprot_id,)
    )

    conn.close()

    return df


# --------------------------------------------------
# TEST
# --------------------------------------------------

if __name__ == "__main__":

    uniprot_id = "P00533"

    print("=" * 70)
    print("LOCAL ChEMBL DATABASE QUERY TEST")
    print("=" * 70)

    print("\nSearching target...\n")

    target = get_target(uniprot_id)

    print(target)

    print("\n" + "=" * 70)
    print("ACTIVITIES")
    print("=" * 70)

    df = get_activities(uniprot_id)

    print(f"\nRecords returned: {len(df)}")

    print("\nColumns:")

    print(df.columns.tolist())

    print("\nFirst 5 records:\n")

    print(df.head())

    print("\n" + "=" * 70)
    print("MEMORY USAGE")
    print("=" * 70)

    memory_mb = (
        df.memory_usage(
            deep=True
        ).sum()
        / (1024 * 1024)
    )

    print(
        f"\nDataFrame memory: "
        f"{memory_mb:.2f} MB"
    )