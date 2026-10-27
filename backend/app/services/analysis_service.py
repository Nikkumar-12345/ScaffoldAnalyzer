from app.services.chembl_service import ChEMBLService
from app.services.database_service import DatabaseService
from app.services.dataframe_service import DataFrameService
from app.services.scaffold_service import ScaffoldService
from app.services.errors import (
    AnalysisError,
    invalid_format_error,
    is_valid_uniprot_format,
    normalize_uniprot_id,
)


class AnalysisService:

    def __init__(self):

        # Local compact ChEMBL database
        self.database = DatabaseService()

        # ChEMBL API fallback
        self.chembl = ChEMBLService()

        self.df_service = DataFrameService()

        self.scaffold = ScaffoldService()

    def analyze(self, uniprot_id, progress=None):

        # progress (optional): callable(percent 0-100, message)
        def report(percent, message):
            if progress is not None:
                progress(percent, message)

        raw_id = (uniprot_id or "").strip()

        uniprot_id = normalize_uniprot_id(raw_id)

        if not uniprot_id:

            raise AnalysisError(
                "missing_uniprot_id",
                "Please enter a UniProt ID (for example P00533).",
                400
            )

        # ------------------------------------
        # FIRST: SEARCH LOCAL DATABASE
        # ------------------------------------

        report(1, "Looking up target in local ChEMBL database")

        print(
            f"Searching local database for "
            f"UniProt ID: {uniprot_id}"
        )

        target = self.database.get_target(
            uniprot_id
        )

        if target is None and raw_id != uniprot_id:

            # Exact text as typed (original behaviour)
            target = self.database.get_target(
                raw_id
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

                report(4, "Loading activity records")

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

                raise AnalysisError(
                    "no_activity_data",
                    f"UniProt ID '{uniprot_id}' was found "
                    f"({target['target_chembl_id']}), but no usable "
                    "IC50 activity records are available for it.",
                    422
                )

        # ------------------------------------
        # TARGET NOT FOUND LOCALLY
        # FALL BACK TO ChEMBL API
        # ------------------------------------

        else:

            # Don't query ChEMBL for text that can't be a UniProt ID
            if not is_valid_uniprot_format(uniprot_id):

                raise invalid_format_error(raw_id)

            report(2, "Not in local database - searching ChEMBL online")

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
                    target["target_chembl_id"],
                    progress=lambda fraction, message: report(
                        4 + 21 * fraction,
                        message
                    )
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

        report(26, "Cleaning activity data")

        cleaned = self.df_service.clean_activity_dataframe(
            activities
        )

        # ------------------------------------
        # VALIDATE CLEANED DATA
        # ------------------------------------

        if cleaned is None or cleaned.empty:

            raise AnalysisError(
                "no_activity_data",
                f"UniProt ID '{uniprot_id}' was found, but no valid "
                "activity records remain after data cleaning (only "
                "exact '=' IC50 measurements with structures are used).",
                422
            )

        # ------------------------------------
        # SCAFFOLD ANALYSIS
        # ------------------------------------

        scaffold_data = self.scaffold.generate_scaffolds(
            cleaned,
            progress=lambda fraction, message: report(
                28 + 69 * fraction,
                message
            )
        )

        report(97, "Preparing charts")

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