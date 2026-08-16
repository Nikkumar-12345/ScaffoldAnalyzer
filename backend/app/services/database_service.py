from pathlib import Path
import os
import sqlite3
import pandas as pd
import requests


class DatabaseService:

    # --------------------------------------------------
    # BASE DIRECTORY
    # --------------------------------------------------

    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    # --------------------------------------------------
    # LOCAL DATABASE LOCATION
    # --------------------------------------------------

    LOCAL_DATABASE_PATH = (
        BASE_DIR
        / "database"
        / "scaffold_analyzer_chembl.db"
    )

    # --------------------------------------------------
    # GITHUB DATABASE DOWNLOAD URL
    # --------------------------------------------------

    DATABASE_URL = (
        "https://github.com/Nikkumar-12345/ScaffoldAnalyzer/"
        "releases/download/v1.0-db/"
        "scaffold_analyzer_chembl.db"
    )

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
    # GET DATABASE PATH
    # --------------------------------------------------

    @classmethod
    def get_database_path(cls):

        # If DATABASE_PATH is provided on Render,
        # use that location.
        env_database_path = os.getenv("DATABASE_PATH")

        if env_database_path:
            return Path(env_database_path)

        # Otherwise use the normal local location.
        return cls.LOCAL_DATABASE_PATH

    # --------------------------------------------------
    # DOWNLOAD DATABASE IF NEEDED
    # --------------------------------------------------

    @classmethod
    def ensure_database_exists(cls):

        database_path = cls.get_database_path()

        # Database already exists locally
        if database_path.exists():
            print(
                f"Using existing ChEMBL database: "
                f"{database_path}"
            )
            return database_path

        print("ChEMBL database not found locally.")
        print("Downloading database from GitHub Release...")

        # Create parent directory if needed
        database_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        # Download to a temporary file first.
        # This prevents SQLite from trying to use a
        # partially downloaded database.
        temp_path = Path(
            str(database_path) + ".download"
        )

        try:

            with requests.get(
                cls.DATABASE_URL,
                stream=True,
                timeout=300
            ) as response:

                response.raise_for_status()

                total_downloaded = 0

                with open(
                    temp_path,
                    "wb"
                ) as file:

                    for chunk in response.iter_content(
                        chunk_size=1024 * 1024
                    ):

                        if chunk:

                            file.write(chunk)

                            total_downloaded += len(chunk)

                            print(
                                f"\rDownloaded: "
                                f"{total_downloaded / (1024 * 1024):.1f} MB",
                                end=""
                            )

            print()

            # Move completed download to final location
            temp_path.replace(
                database_path
            )

            print(
                "ChEMBL database downloaded successfully."
            )

            return database_path

        except Exception as error:

            # Remove incomplete file if download fails
            if temp_path.exists():

                temp_path.unlink()

            raise Exception(
                "Failed to download ChEMBL database. "
                f"Details: {error}"
            )

    # --------------------------------------------------
    # CONNECT
    # --------------------------------------------------

    def get_connection(self):

        # Download database only if it is missing
        database_path = self.ensure_database_exists()

        return sqlite3.connect(
            str(database_path)
        )

    # --------------------------------------------------
    # GET TARGET BY UNIPROT ID
    # --------------------------------------------------

    def get_target(
        self,
        uniprot_id
    ):

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