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

        # ------------------------------------
        # Protein Information
        # ------------------------------------

        protein = self.uniprot.get_protein(
            uniprot_id
        )

        # ------------------------------------
        # ChEMBL Target
        # ------------------------------------

        target = self.chembl.get_target(
            uniprot_id
        )

        # ------------------------------------
        # Activity Data
        # ------------------------------------

        activities = self.chembl.download_activities(

            target["target_chembl_id"]

        )

        cleaned = self.df_service.clean_activity_dataframe(

            activities

        )

        # ------------------------------------
        # Scaffold Analysis
        # ------------------------------------

        scaffold_data = self.scaffold.generate_scaffolds(

            cleaned

        )

        # ------------------------------------
        # Charts
        # ------------------------------------

        composition_chart = []

        potency_chart = []

        drug_chart = []

        complexity_chart = []

        for i, scaffold in enumerate(
            scaffold_data["scaffolds"][:10]
        ):

            composition_chart.append({

                "name": f"SCF-{i+1}",

                "percentage": scaffold["percentage"],

                "occurrences": scaffold["occurrences"]

            })

            potency_chart.append({

                "name": f"SCF-{i+1}",

                "median_pic50":

                    scaffold["median_pic50"]

            })

            drug_chart.append({

                "name": f"SCF-{i+1}",

                "drug_score":

                    scaffold["druglikeness"]["druglikeness_score"]

            })

            complexity_chart.append({

                "name": f"SCF-{i+1}",

                "complexity":

                    scaffold["descriptors"]["bertz_complexity"]

            })

        # ------------------------------------
        # Response
        # ------------------------------------

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

                    scaffold_data["summary"]["total_unique_molecules"],

                "unique_scaffolds":

                    scaffold_data["summary"]["unique_scaffolds"],

                "largest_scaffold_percentage":

                    scaffold_data["summary"]["largest_scaffold_percentage"],

                "invalid_smiles":

                    scaffold_data["summary"]["invalid_smiles"],

                "average_pic50":

                    scaffold_data["summary"]["average_median_pic50"],

                "dataset_median_pic50":

                    scaffold_data["summary"]["dataset_median_pic50"],

                "top_scaffold_score":

                    scaffold_data["summary"]["top_scaffold_score"]

            },

            "charts": {

                "composition":

                    composition_chart,

                "potency":

                    potency_chart,

                "druglikeness":

                    drug_chart,

                "complexity":

                    complexity_chart

            },

            "top_scaffolds":

                scaffold_data["scaffolds"][:10],

            "all_scaffolds":

                scaffold_data["scaffolds"]

        }