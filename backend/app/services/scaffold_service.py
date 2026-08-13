
from collections import defaultdict
from app.services.side_chain_service import SideChainService

import numpy as np
import pandas as pd
from app.services.functional_group_service import FunctionalGroupService

from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
from rdkit.Chem.Draw import rdMolDraw2D

from app.services.descriptor_service import DescriptorService
from app.services.druglikeness_service import DrugLikenessService
from app.services.ranking_service import RankingService


class ScaffoldService:

    @staticmethod
    def generate_scaffolds(df: pd.DataFrame):

        # ---------------------------------------
        # Remove duplicate molecules
        # ---------------------------------------

        unique_df = df.drop_duplicates(
            subset=["molecule_chembl_id"]
        ).copy()

        scaffold_dict = {}

        invalid_smiles = 0

        total_unique_molecules = len(unique_df)

        # ---------------------------------------
        # Iterate over every molecule
        # ---------------------------------------

        for _, row in unique_df.iterrows():

            smiles = row["canonical_smiles"]

            molecule_id = row["molecule_chembl_id"]

            pchembl = row.get("pchembl_value", None)

            mol = Chem.MolFromSmiles(smiles)

            if mol is None:

                invalid_smiles += 1

                continue

            scaffold = MurckoScaffold.GetScaffoldForMol(mol)

            if scaffold is None:

                continue

            scaffold_smiles = Chem.MolToSmiles(

                scaffold,

                canonical=True

            )

            if scaffold_smiles == "":

                scaffold_smiles = "NO_SCAFFOLD"

            # ---------------------------------------
            # Create scaffold entry
            # ---------------------------------------

            if scaffold_smiles not in scaffold_dict:

                drawer = rdMolDraw2D.MolDraw2DSVG(

                    300,

                    220

                )

                drawer.DrawMolecule(scaffold)

                drawer.FinishDrawing()

                svg = drawer.GetDrawingText()

                descriptors = DescriptorService.calculate(
                    scaffold_smiles
                )

                druglikeness = DrugLikenessService.evaluate(
                    descriptors
                )

                scaffold_dict[scaffold_smiles] = {
                    "scaffold_smiles": scaffold_smiles,
                    "svg": svg,
                    "molecules": [],
                    "pic50_values": [],
                    "descriptors": descriptors,
                    "druglikeness": druglikeness,
                    "functional_groups":
                        FunctionalGroupService.detect(
                            scaffold_smiles
                        )
                }

            scaffold_dict[
    scaffold_smiles
]["molecules"].append(

    {

        "chembl_id": molecule_id,

        "smiles": smiles,

        "pic50": (
            float(pchembl)
            if (
                pchembl is not None
                and pchembl != ""
                and not pd.isna(pchembl)
            )
            else None
        )

    }

)

            if (

                pchembl is not None

                and pchembl != ""

                and not pd.isna(pchembl)

            ):

                try:

                    scaffold_dict[
                        scaffold_smiles
                    ]["pic50_values"].append(

                        float(pchembl)

                    )

                except:

                    pass

        # ---------------------------------------
        # Maximum occurrence
        # ---------------------------------------

        if len(scaffold_dict) == 0:

            return {

                "total_unique_molecules": 0,

                "invalid_smiles": invalid_smiles,

                "unique_scaffolds": 0,

                "largest_scaffold_percentage": 0,

                "scaffolds": []

            }

        max_occurrences = max(

            len(

                scaffold["molecules"]

            )

            for scaffold in scaffold_dict.values()

        )

        scaffold_list = []

        scaffold_id = 1

        # ---------------------------------------
        # Generate statistics
        # ---------------------------------------

        for scaffold in scaffold_dict.values():
            side_chain_analysis = SideChainService.analyze(
    scaffold["scaffold_smiles"],
    scaffold["molecules"]
)

            pic50 = scaffold["pic50_values"]

            occurrences = len(

                scaffold["molecules"]

            )

            percentage = round(

                occurrences

                * 100

                / total_unique_molecules,

                2

            )   
            if len(pic50) > 0:

                max_pic50 = round(

                    max(pic50),

                    3

                )

                min_pic50 = round(

                    min(pic50),

                    3

                )

                mean_pic50 = round(

                    float(np.mean(pic50)),

                    3

                )

                median_pic50 = round(

                    float(np.median(pic50)),

                    3

                )

                std_pic50 = round(

                    float(np.std(pic50)),

                    3

                )

            else:

                max_pic50 = None

                min_pic50 = None

                mean_pic50 = None

                median_pic50 = None

                std_pic50 = None

            # ---------------------------------------
            # Descriptor Information
            # ---------------------------------------

            descriptors = scaffold["descriptors"]

            druglikeness = scaffold["druglikeness"]

            # ---------------------------------------
            # Ranking
            # ---------------------------------------

            ranking = RankingService.calculate(

                median_pic50=median_pic50,

                occurrences=occurrences,

                descriptors=descriptors,

                druglikeness=druglikeness,

                max_occurrences=max_occurrences

            )
            # ---------------------------------------
            # Side Chain Analysis
            # ---------------------------------------

            side_chain_analysis = SideChainService.analyze(
                scaffold_smiles=scaffold["scaffold_smiles"],
                molecules=scaffold["molecules"]
            )

            scaffold_list.append(

                {

                    "id": scaffold_id,
                    "side_chain_analysis": side_chain_analysis,

                    "scaffold_smiles":

                        scaffold["scaffold_smiles"],

                    "svg":

                        scaffold["svg"],

                    "occurrences":

                        occurrences,

                    "percentage":

                        percentage,

                    "activity_records":

                        len(pic50),

                    "unique_molecules":

                        occurrences,

                    "max_pic50":

                        max_pic50,

                    "mean_pic50":

                        mean_pic50,

                    "median_pic50":

                        median_pic50,

                    "min_pic50":

                        min_pic50,

                    "std_pic50":

                        std_pic50,

                    "descriptors":

                        descriptors,

                    "druglikeness":

                        druglikeness,
                    "functional_groups":

    scaffold["functional_groups"],

                    "ranking":

                        ranking,

                    "molecules":

                        scaffold["molecules"]

                }

            )

            scaffold_id += 1        # ---------------------------------------
        # Sort Scaffolds
        # ---------------------------------------

        # Primary sort:
        # 1. Overall ranking score
        # 2. Median pIC50
        # 3. Occurrences

        scaffold_list.sort(

            key=lambda x: (

                x["ranking"]["overall_score"]
                if x["ranking"] is not None
                else 0,

                x["median_pic50"]
                if x["median_pic50"] is not None
                else 0,

                x["occurrences"]

            ),

            reverse=True

        )

        # ---------------------------------------
        # Reassign ranks
        # ---------------------------------------

        for rank, scaffold in enumerate(

            scaffold_list,

            start=1

        ):

            scaffold["rank"] = rank

            if scaffold["ranking"] is not None:

                scaffold["ranking"]["rank"] = rank

        # ---------------------------------------
        # Top Scaffold Summary
        # ---------------------------------------

        if len(scaffold_list) > 0:

            top_scaffold = scaffold_list[0]

            top_percentage = top_scaffold["percentage"]

            top_score = top_scaffold["ranking"]["overall_score"]

        else:

            top_percentage = 0

            top_score = 0
                    # ---------------------------------------
        # Global Statistics
        # ---------------------------------------

        total_activity_records = sum(

            scaffold["activity_records"]

            for scaffold in scaffold_list

        )

        valid_pic50 = []

        for scaffold in scaffold_list:

            if scaffold["median_pic50"] is not None:

                valid_pic50.append(

                    scaffold["median_pic50"]

                )

        if len(valid_pic50) > 0:

            average_pic50 = round(

                float(np.mean(valid_pic50)),

                3

            )

            median_dataset_pic50 = round(

                float(np.median(valid_pic50)),

                3

            )

        else:

            average_pic50 = None

            median_dataset_pic50 = None

        # ---------------------------------------
        # Final Response
        # ---------------------------------------

        return {

            "summary": {

                "total_unique_molecules":
                    total_unique_molecules,

                "unique_scaffolds":
                    len(scaffold_list),

                "invalid_smiles":
                    invalid_smiles,

                "total_activity_records":
                    total_activity_records,

                "largest_scaffold_percentage":
                    top_percentage,

                "top_scaffold_score":
                    top_score,

                "average_median_pic50":
                    average_pic50,

                "dataset_median_pic50":
                    median_dataset_pic50

            },

            "scaffolds":

                scaffold_list

        }