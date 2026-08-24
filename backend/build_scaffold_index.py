import sqlite3
from pathlib import Path

from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold


# ============================================================
# DATABASE PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATABASE_PATH = (
    BASE_DIR
    / "database"
    / "scaffold_analyzer_chembl.db"
)


# ============================================================
# SETTINGS
# ============================================================

BATCH_SIZE = 5000


# ============================================================
# GET MURCKO SCAFFOLD
# ============================================================

def get_scaffold_smiles(smiles):

    if not smiles:
        return None

    try:

        mol = Chem.MolFromSmiles(smiles)

        if mol is None:
            return None

        scaffold = (
            MurckoScaffold.GetScaffoldForMol(
                mol
            )
        )

        if (
            scaffold is None
            or scaffold.GetNumAtoms() == 0
        ):
            return None

        scaffold_smiles = Chem.MolToSmiles(
            scaffold,
            canonical=True
        )

        if not scaffold_smiles:
            return None

        return scaffold_smiles

    except Exception:

        return None


# ============================================================
# MAIN
# ============================================================

def build_index():

    print("=" * 60)
    print("BUILDING SCAFFOLD INDEX")
    print("=" * 60)

    print(
        f"Database: {DATABASE_PATH}"
    )

    if not DATABASE_PATH.exists():

        raise Exception(
            f"Database not found: {DATABASE_PATH}"
        )

    conn = sqlite3.connect(
        str(DATABASE_PATH)
    )

    cursor = conn.cursor()

    # --------------------------------------------------------
    # Create scaffold index table
    # --------------------------------------------------------

    print("\nCreating scaffold_index table...")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS scaffold_index (

            scaffold_smiles TEXT NOT NULL,

            molecule_chembl_id TEXT NOT NULL,

            target_chembl_id TEXT NOT NULL,

            PRIMARY KEY (
                scaffold_smiles,
                molecule_chembl_id,
                target_chembl_id
            )

        )
        """
    )

    conn.commit()

    # --------------------------------------------------------
    # Clear old index
    # --------------------------------------------------------

    print("Clearing previous scaffold index...")

    cursor.execute(
        "DELETE FROM scaffold_index"
    )

    conn.commit()

    # --------------------------------------------------------
    # Count unique molecules
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT DISTINCT
                molecule_chembl_id
            FROM activities
            WHERE
                molecule_chembl_id IS NOT NULL
                AND canonical_smiles IS NOT NULL
        )
        """
    )

    total_molecules = cursor.fetchone()[0]

    print(
        f"Unique molecules to process: "
        f"{total_molecules:,}"
    )

    # --------------------------------------------------------
    # Process molecules
    # --------------------------------------------------------

    offset = 0

    processed = 0

    valid_scaffolds = 0

    invalid_smiles = 0

    inserted = 0

    while True:

        print(
            f"\nProcessing molecules "
            f"{offset + 1:,} - "
            f"{offset + BATCH_SIZE:,}"
        )

        cursor.execute(
            """
            SELECT
                molecule_chembl_id,
                canonical_smiles
            FROM activities
            WHERE
                molecule_chembl_id IS NOT NULL
                AND canonical_smiles IS NOT NULL
            GROUP BY
                molecule_chembl_id
            LIMIT ?
            OFFSET ?
            """,
            (
                BATCH_SIZE,
                offset
            )
        )

        molecules = cursor.fetchall()

        if not molecules:

            break

        # ----------------------------------------------------
        # Calculate scaffold for each molecule
        # ----------------------------------------------------

        molecule_scaffolds = []

        for molecule_id, smiles in molecules:

            scaffold_smiles = (
                get_scaffold_smiles(
                    smiles
                )
            )

            processed += 1

            if scaffold_smiles is None:

                invalid_smiles += 1

                continue

            valid_scaffolds += 1

            molecule_scaffolds.append(
                (
                    scaffold_smiles,
                    molecule_id
                )
            )

        # ----------------------------------------------------
        # Get targets for molecules in this batch
        # ----------------------------------------------------

        for (
            scaffold_smiles,
            molecule_id
        ) in molecule_scaffolds:

            cursor.execute(
                """
                SELECT DISTINCT
                    target_chembl_id
                FROM activities
                WHERE
                    molecule_chembl_id = ?
                    AND target_chembl_id IS NOT NULL
                """,
                (
                    molecule_id,
                )
            )

            targets = cursor.fetchall()

            for (target_id,) in targets:

                cursor.execute(
                    """
                    INSERT OR IGNORE INTO
                    scaffold_index
                    (
                        scaffold_smiles,
                        molecule_chembl_id,
                        target_chembl_id
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        scaffold_smiles,
                        molecule_id,
                        target_id
                    )
                )

                inserted += cursor.rowcount

        # ----------------------------------------------------
        # Commit this batch
        # ----------------------------------------------------

        conn.commit()

        offset += BATCH_SIZE

        print(
            f"Processed: {processed:,} / "
            f"{total_molecules:,}"
        )

        print(
            f"Valid scaffolds: "
            f"{valid_scaffolds:,}"
        )

        print(
            f"Invalid SMILES: "
            f"{invalid_smiles:,}"
        )

        print(
            f"Relationships inserted: "
            f"{inserted:,}"
        )

    # ========================================================
    # CREATE INDEXES
    # ========================================================

    print("\nCreating SQLite indexes...")

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_scaffold_index_scaffold
        ON scaffold_index (
            scaffold_smiles
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_scaffold_index_target
        ON scaffold_index (
            target_chembl_id
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_scaffold_index_molecule
        ON scaffold_index (
            molecule_chembl_id
        )
        """
    )

    conn.commit()

    # ========================================================
    # FINAL STATISTICS
    # ========================================================

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM scaffold_index
        """
    )

    total_relationships = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT COUNT(DISTINCT scaffold_smiles)
        FROM scaffold_index
        """
    )

    total_scaffolds = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT COUNT(DISTINCT target_chembl_id)
        FROM scaffold_index
        """
    )

    total_targets = cursor.fetchone()[0]

    print("\n" + "=" * 60)
    print("SCAFFOLD INDEX COMPLETE")
    print("=" * 60)

    print(
        f"Unique molecules processed : "
        f"{processed:,}"
    )

    print(
        f"Valid scaffold molecules   : "
        f"{valid_scaffolds:,}"
    )

    print(
        f"Invalid SMILES             : "
        f"{invalid_smiles:,}"
    )

    print(
        f"Scaffold-target relationships: "
        f"{total_relationships:,}"
    )

    print(
        f"Unique scaffolds            : "
        f"{total_scaffolds:,}"
    )

    print(
        f"Unique targets              : "
        f"{total_targets:,}"
    )

    print(
        "\nScaffold index successfully "
        "created."
    )

    conn.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    build_index()