from pathlib import Path
import os
import sqlite3
import pandas as pd


class DatabaseService:

    # --------------------------------------------------
    # BASE DIRECTORY
    # --------------------------------------------------

    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    # Local database location
    LOCAL_DATABASE_PATH = (
        BASE_DIR
        / "database"
        / "scaffold_analyzer_chembl.db"
    )

    # --------------------------------------------------
    # DATABASE PATH
    # --------------------------------------------------

    @classmethod
    def get_database_path(cls):

        # Check whether an environment variable is provided.
        # This will be useful on Render.
        env_database_path = os.getenv("DATABASE_PATH")

        if env_database_path:

            return Path(env_database_path)

        # Otherwise use the normal local database.
        return cls.LOCAL_DATABASE_PATH

    # --------------------------------------------------
    # REQUIRED COLUMNS
    # --------------------------------------------------

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

        database_path = self.get_database_path()

        if not database_path.exists():

            raise Exception(
                "ChEMBL database was not found at: "
                f"{database_path}"
            )

        return sqlite3.connect(
            str(database_path)
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