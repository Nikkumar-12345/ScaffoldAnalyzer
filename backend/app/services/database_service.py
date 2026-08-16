from pathlib import Path
import sqlite3
import pandas as pd


class DatabaseService:

    # --------------------------------------------------
    # DATABASE PATH
    # --------------------------------------------------

    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    DATABASE_PATH = (
        BASE_DIR
        / "database"
        / "scaffold_analyzer_chembl.db"
    )

    REQUIRED_COLUMNS = [
        "activity_id",
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

    # --------------------------------------------------
    # CONNECT
    # --------------------------------------------------

    def get_connection(self):

        if not self.DATABASE_PATH.exists():

            raise Exception(
                "Local ChEMBL database was not found at: "
                f"{self.DATABASE_PATH}"
            )

        return sqlite3.connect(
            str(self.DATABASE_PATH)
        )

    # --------------------------------------------------
    # GET TARGET BY UNIPROT ID
    # --------------------------------------------------

    def get_target(self, uniprot_id):

        uniprot_id = uniprot_id.strip()

        conn = self.get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    target_chembl_id,
                    uniprot_id,
                    target_name,
                    organism
                FROM targets
                WHERE uniprot_id = ?
                LIMIT 1
                """,
                (
                    uniprot_id,
                )
            )

            row = cursor.fetchone()

            if row is None:

                return None

            return {

                "target_chembl_id": row[0],

                "pref_name": row[2],

                "organism": row[3]

            }

        finally:

            conn.close()

    # --------------------------------------------------
    # CHECK WHETHER TARGET HAS ACTIVITIES
    # --------------------------------------------------

    def target_has_activities(
        self,
        target_chembl_id
    ):

        conn = self.get_connection()

        try:

            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT EXISTS(
                    SELECT 1
                    FROM activities
                    WHERE target_chembl_id = ?
                    LIMIT 1
                )
                """,
                (
                    target_chembl_id,
                )
            )

            result = cursor.fetchone()

            return bool(
                result[0]
            )

        finally:

            conn.close()

    # --------------------------------------------------
    # GET ACTIVITIES
    # --------------------------------------------------

    def get_activities(
        self,
        target_chembl_id
    ):

        conn = self.get_connection()

        try:

            query = """
            SELECT
                activity_id,
                molecule_chembl_id,
                canonical_smiles,
                standard_value,
                standard_units,
                standard_relation,
                standard_type,
                pchembl_value,
                assay_chembl_id,
                document_chembl_id
            FROM activities
            WHERE target_chembl_id = ?
            """

            dataframe = pd.read_sql_query(

                query,

                conn,

                params=(
                    target_chembl_id,
                )

            )

            return dataframe

        finally:

            conn.close()