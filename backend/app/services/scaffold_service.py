from collections import defaultdict

import numpy as np
import pandas as pd

from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
from rdkit.Chem.Draw import rdMolDraw2D


class ScaffoldService:

    @staticmethod
    def generate_scaffolds(df: pd.DataFrame):

        # -----------------------------
        # Keep only unique molecules
        # -----------------------------
        unique_df = df.drop_duplicates(
            subset=["molecule_chembl_id"]
        ).copy()

        scaffold_dict = {}

        invalid_smiles = 0

        total_unique_molecules = len(unique_df)

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

            # Empty scaffold (acyclic molecules)
            if scaffold_smiles == "":
                scaffold_smiles = "NO_SCAFFOLD"

            # ---------------- SVG ----------------

            if scaffold_smiles not in scaffold_dict:

                drawer = rdMolDraw2D.MolDraw2DSVG(
                    300,
                    220
                )

                drawer.DrawMolecule(scaffold)

                drawer.FinishDrawing()

                svg = drawer.GetDrawingText()

                scaffold_dict[scaffold_smiles] = {

                    "scaffold_smiles": scaffold_smiles,

                    "svg": svg,

                    "molecules": [],

                    "pic50_values": []

                }

            scaffold_dict[
                scaffold_smiles
            ]["molecules"].append(molecule_id)

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

        # ------------------------------------------
        # Final statistics
        # ------------------------------------------

        scaffold_list = []

        scaffold_id = 1

        for scaffold in scaffold_dict.values():

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

            scaffold_list.append({

                "id": scaffold_id,

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

                "molecules":
                    scaffold["molecules"]

            })

            scaffold_id += 1

        scaffold_list.sort(

            key=lambda x: x["occurrences"],

            reverse=True

        )

        return {

            "total_unique_molecules":
                total_unique_molecules,

            "invalid_smiles":
                invalid_smiles,

            "unique_scaffolds":
                len(scaffold_list),

            "largest_scaffold_percentage":
                scaffold_list[0]["percentage"]
                if scaffold_list
                else 0,

            "scaffolds":
                scaffold_list

        }