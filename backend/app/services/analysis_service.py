from app.services.chembl_service import ChEMBLService
from app.services.database_service import DatabaseService
from app.services.dataframe_service import DataFrameService
from app.services.scaffold_service import ScaffoldService


class AnalysisService:

    def __init__(self):

        # Local compact ChEMBL database
        self.database = DatabaseService()

        # ChEMBL API fallback
        self.chembl = ChEMBLService()

        self.df_service = DataFrameService()

        self.scaffold = ScaffoldService()

    def analyze(self, uniprot_id):

        uniprot_id = uniprot_id.strip()

        # ------------------------------------
        # FIRST: SEARCH LOCAL DATABASE
        # ------------------------------------

        print(
            f"Searching local database for "
            f"UniProt ID: {uniprot_id}"
        )

        target = self.database.get_target(
            uniprot_id
        )

        # ------------------------------------
        # TARGET FOUND LOCALLY
        # ------------------------------------

        if target is not None:

            print(
                "Target found in local database: "
                f"{target['target_chembl_id']}"
            )

            has_activities = (
                self.database.target_has_activities(
                    target["target_chembl_id"]
                )
            )

            # --------------------------------
            # LOCAL ACTIVITIES AVAILABLE
            # --------------------------------

            if has_activities:

                print(
                    "Loading activities from "
                    "local database..."
                )

                activities = (
                    self.database.get_activities(
                        target["target_chembl_id"]
                    )
                )

                print(
                    f"Loaded {len(activities)} "
                    "activity records locally."
                )

            # --------------------------------
            # TARGET EXISTS BUT HAS NO DATA
            # --------------------------------

            else:

                raise Exception(
                    "Target was found in the local "
                    "ChEMBL database, but no usable "
                    "IC50 activity records are available."
                )

        # ------------------------------------
        # TARGET NOT FOUND LOCALLY
        # FALL BACK TO ChEMBL API
        # ------------------------------------

        else:

            print(
                "Target not found locally. "
                "Using ChEMBL API fallback..."
            )

            target = self.chembl.get_target(
                uniprot_id
            )

            print(
                f"Target found through API: "
                f"{target['target_chembl_id']}"
            )

            activities = (
                self.chembl.download_activities(
                    target["target_chembl_id"]
                )
            )

            print(
                f"Downloaded {len(activities)} "
                "activity records from API."
            )

        # ------------------------------------
        # PROTEIN INFORMATION
        # FROM LOCAL/API TARGET DATA
        # ------------------------------------

        protein = {

            "protein_name":
                target.get("pref_name", ""),

            # Gene name is not stored in
            # the current local database.
            "gene_name": "",

            "organism":
                target.get("organism", "")

        }

        # ------------------------------------
        # CLEAN ACTIVITY DATA
        # ------------------------------------

        cleaned = self.df_service.clean_activity_dataframe(
            activities
        )

        # ------------------------------------
        # VALIDATE CLEANED DATA
        # ------------------------------------

        if cleaned is None or cleaned.empty:

            raise Exception(
                "No valid activity records remain "
                "after data cleaning."
            )

        # ------------------------------------
        # SCAFFOLD ANALYSIS
        # ------------------------------------

        scaffold_data = self.scaffold.generate_scaffolds(
            cleaned
        )

        # ------------------------------------
        # CHARTS
        # ------------------------------------

        composition_chart = []

        potency_chart = []

        drug_chart = []

        complexity_chart = []

        for i, scaffold in enumerate(
            scaffold_data["scaffolds"][:10]
        ):

            composition_chart.append({

                "name": f"SCF-{i + 1}",

                "percentage": scaffold["percentage"],

                "occurrences": scaffold["occurrences"]

            })

            potency_chart.append({

                "name": f"SCF-{i + 1}",

                "median_pic50":
                    scaffold["median_pic50"]

            })

            drug_chart.append({

                "name": f"SCF-{i + 1}",

                "drug_score":
                    scaffold["druglikeness"][
                        "druglikeness_score"
                    ]

            })

            complexity_chart.append({

                "name": f"SCF-{i + 1}",

                "complexity":
                    scaffold["descriptors"][
                        "bertz_complexity"
                    ]

            })

        # ------------------------------------
        # RESPONSE
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
                    scaffold_data["summary"][
                        "total_unique_molecules"
                    ],

                "unique_scaffolds":
                    scaffold_data["summary"][
                        "unique_scaffolds"
                    ],

                "largest_scaffold_percentage":
                    scaffold_data["summary"][
                        "largest_scaffold_percentage"
                    ],

                "invalid_smiles":
                    scaffold_data["summary"][
                        "invalid_smiles"
                    ],

                "average_pic50":
                    scaffold_data["summary"][
                        "average_median_pic50"
                    ],

                "dataset_median_pic50":
                    scaffold_data["summary"][
                        "dataset_median_pic50"
                    ],

                "top_scaffold_score":
                    scaffold_data["summary"][
                        "top_scaffold_score"
                    ]

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