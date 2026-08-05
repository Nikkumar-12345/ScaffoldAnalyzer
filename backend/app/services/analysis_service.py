from app.services.uniprot_service import UniProtService
from app.services.chembl_service import ChEMBLService
from app.services.dataframe_service import DataFrameService
from app.services.scaffold_service import ScaffoldService


class AnalysisService:

    def __init__(self):

        self.uniprot = UniProtService()
        self.chembl = ChEMBLService()
        self.df_service = DataFrameService()
        self.scaffold = ScaffoldService()

    def analyze(self, uniprot_id):

        # ----------------------------
        # Protein Information
        # ----------------------------

        protein = self.uniprot.get_protein(
            uniprot_id
        )

        # ----------------------------
        # ChEMBL Target
        # ----------------------------

        target = self.chembl.get_target(
            uniprot_id
        )

        # ----------------------------
        # Activity Data
        # ----------------------------

        activities = self.chembl.download_activities(
            target["target_chembl_id"]
        )

        cleaned = self.df_service.clean_activity_dataframe(
            activities
        )

        # ----------------------------
        # Scaffold Analysis
        # ----------------------------

        scaffold_data = self.scaffold.generate_scaffolds(
            cleaned
        )

        # ----------------------------
        # Chart Data (Top 10)
        # ----------------------------

        chart_data = []

        for i, scaffold in enumerate(
            scaffold_data["scaffolds"][:10]
        ):

            chart_data.append({

                "name": f"SCF-{i+1}",

                "percentage": scaffold["percentage"],

                "occurrences": scaffold["occurrences"]

            })

        # ----------------------------
        # Response
        # ----------------------------

        return {

            "summary": {

                "protein":

                    protein["protein_name"],

                "gene":

                    protein["gene_name"],

                "organism":

                    protein["organism"],

                "chembl_target":

                    target["target_chembl_id"],

                "target_name":

                    target["pref_name"],

                "activity_records":

                    len(activities),

                "unique_molecules":

                    scaffold_data["total_unique_molecules"],

                "unique_scaffolds":

                    scaffold_data["unique_scaffolds"],

                "largest_scaffold_percentage":

                    scaffold_data["largest_scaffold_percentage"],

                "invalid_smiles":

                    scaffold_data["invalid_smiles"]

            },

            "chart_data":

                chart_data,

            "top_scaffolds":

                scaffold_data["scaffolds"][:10]

        }