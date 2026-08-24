from app.services.database_service import DatabaseService


class CrossTargetService:

    def __init__(self):

        self.database = DatabaseService()

    def find_other_targets(
        self,
        scaffold_smiles,
        current_target_chembl_id=None
    ):

        conn = self.database.get_connection()

        try:

            cursor = conn.cursor()

            # --------------------------------------------------
            # FIND TARGETS CONTAINING THIS SCAFFOLD
            # --------------------------------------------------

            query = """
            SELECT
                si.target_chembl_id,
                t.target_name,
                t.uniprot_id,
                t.organism,
                COUNT(
                    DISTINCT si.molecule_chembl_id
                ) AS molecule_count

            FROM scaffold_index si

            LEFT JOIN targets t
                ON si.target_chembl_id =
                   t.target_chembl_id

            WHERE si.scaffold_smiles = ?
            """

            params = [
                scaffold_smiles
            ]

            # --------------------------------------------------
            # EXCLUDE CURRENT TARGET
            # --------------------------------------------------

            if current_target_chembl_id:

                query += """
                AND si.target_chembl_id != ?
                """

                params.append(
                    current_target_chembl_id
                )

            # --------------------------------------------------
            # GROUP BY TARGET
            # --------------------------------------------------

            query += """
            GROUP BY
                si.target_chembl_id,
                t.target_name,
                t.uniprot_id,
                t.organism

            ORDER BY
                molecule_count DESC
            """

            cursor.execute(
                query,
                params
            )

            rows = cursor.fetchall()

            # --------------------------------------------------
            # FORMAT RESPONSE
            # --------------------------------------------------

            targets = []

            for row in rows:

                targets.append({

                    "target_chembl_id":
                        row[0],

                    "target_name":
                        row[1],

                    "uniprot_id":
                        row[2],

                    "organism":
                        row[3],

                    "molecule_count":
                        row[4]

                })

            return {

                "scaffold_smiles":
                    scaffold_smiles,

                "total_other_targets":
                    len(targets),

                "targets":
                    targets

            }

        finally:

            conn.close()