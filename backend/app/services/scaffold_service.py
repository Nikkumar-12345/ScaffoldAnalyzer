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
from app.services.precomputed_service import PrecomputedService


class ScaffoldService:

    # Scaffold images are only drawn for the top-ranked scaffolds,
    # which are the ones the dashboard displays. Any other scaffold's
    # image can be requested on demand via POST /scaffold/svg.
    SVG_TOP_N = 10

    # ---------------------------------------
    # Murcko scaffold of one molecule
    # (identical to the original inline logic)
    #
    # Returns (status, scaffold_smiles, scaffold_mol)
    # ---------------------------------------

    @staticmethod
    def compute_scaffold(smiles):

        mol = Chem.MolFromSmiles(smiles)

        if mol is None:
            return PrecomputedService.STATUS_INVALID, None, None

        try:

            scaffold = MurckoScaffold.GetScaffoldForMol(
                mol
            )

        except Exception:

            return PrecomputedService.STATUS_INVALID, None, None

        if (
            scaffold is None
            or scaffold.GetNumAtoms() == 0
        ):

            return PrecomputedService.STATUS_NO_SCAFFOLD, None, None

        scaffold_smiles = Chem.MolToSmiles(
            scaffold,
            canonical=True
        )

        if not scaffold_smiles:

            return PrecomputedService.STATUS_NO_SCAFFOLD, None, None

        return PrecomputedService.STATUS_OK, scaffold_smiles, scaffold

    # ---------------------------------------
    # Scaffold image
    # ---------------------------------------

    @staticmethod
    def draw_scaffold_svg(scaffold_mol):

        drawer = rdMolDraw2D.MolDraw2DSVG(
            300,
            220
        )

        drawer.DrawMolecule(scaffold_mol)

        drawer.FinishDrawing()

        return drawer.GetDrawingText()

    @staticmethod
    def svg_for_molecule_scaffold(smiles):
        """
        Draws the scaffold exactly as the original pipeline did: from the
        scaffold object derived from the first molecule that produced it.
        """

        status, _, scaffold_mol = ScaffoldService.compute_scaffold(smiles)

        if status != PrecomputedService.STATUS_OK:
            return None

        return ScaffoldService.draw_scaffold_svg(scaffold_mol)

    @staticmethod
    def svg_for_scaffold_smiles(scaffold_smiles):

        scaffold_mol = Chem.MolFromSmiles(scaffold_smiles)

        if scaffold_mol is None:
            return None

        return ScaffoldService.draw_scaffold_svg(scaffold_mol)

    # ---------------------------------------
    # Main analysis
    #
    # progress (optional): callable(fraction 0..1, message)
    # ---------------------------------------

    @staticmethod
    def generate_scaffolds(df: pd.DataFrame, progress=None):

        def report(fraction, message):
            if progress is not None:
                progress(min(max(fraction, 0.0), 1.0), message)

        # ---------------------------------------
        # Remove duplicate molecules
        # ---------------------------------------

        unique_df = df.drop_duplicates(
            subset=["molecule_chembl_id"]
        )

        scaffold_dict = {}

        invalid_smiles = 0

        total_unique_molecules = len(unique_df)

        # Plain Python lists are much faster to iterate than iterrows()
        smiles_column = unique_df["canonical_smiles"].tolist()

        id_column = unique_df["molecule_chembl_id"].tolist()

        if "pchembl_value" in unique_df.columns:
            pchembl_column = unique_df["pchembl_value"].tolist()
        else:
            pchembl_column = [None] * total_unique_molecules

        # ---------------------------------------
        # Precomputed scaffolds / side chains
        # ---------------------------------------

        report(0.02, "Looking up precomputed scaffolds")

        cached = PrecomputedService.lookup_molecules(
            [s for s in set(smiles_column) if isinstance(s, str) and s]
        )

        # smiles -> side chain (None = no match) for SideChainService
        side_chains = {}

        # scaffold_smiles -> SMILES of the first molecule with it
        first_molecule_smiles = {}

        live_computed = 0

        # ---------------------------------------
        # Iterate over every molecule
        # ---------------------------------------

        for index, (smiles, molecule_id, pchembl) in enumerate(
            zip(smiles_column, id_column, pchembl_column)
        ):

            if index % 500 == 0:
                report(
                    0.05 + 0.25 * index / max(total_unique_molecules, 1),
                    f"Generating Murcko scaffolds "
                    f"({index:,}/{total_unique_molecules:,} molecules)"
                )

            if not smiles:
                invalid_smiles += 1
                continue

            hit = cached.get(smiles)

            if hit is not None:

                status, scaffold_smiles, has_side_chain, side_chain = hit

                if has_side_chain or status == PrecomputedService.STATUS_OK:
                    side_chains[smiles] = (
                        side_chain if has_side_chain else None
                    )

            else:

                live_computed += 1

                status, scaffold_smiles, _ = (
                    ScaffoldService.compute_scaffold(smiles)
                )

            if status == PrecomputedService.STATUS_INVALID:

                invalid_smiles += 1

                continue

            if status != PrecomputedService.STATUS_OK:

                continue

            # ---------------------------------------
            # Create scaffold entry
            # ---------------------------------------

            if scaffold_smiles not in scaffold_dict:

                first_molecule_smiles[scaffold_smiles] = smiles

                scaffold_dict[scaffold_smiles] = {

                    "scaffold_smiles": scaffold_smiles,

                    "svg": None,

                    "molecules": [],

                    "pic50_values": [],

                    "descriptors": None,

                    "druglikeness": None,

                    "functional_groups": []
                }

            # ---------------------------------------
            # Add molecule to its SAME scaffold
            # ---------------------------------------

            molecule_pic50 = None

            if (
                pchembl is not None
                and pchembl != ""
                and not pd.isna(pchembl)
            ):

                try:

                    molecule_pic50 = float(
                        pchembl
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    molecule_pic50 = None

            scaffold_dict[
                scaffold_smiles
            ]["molecules"].append(

                {

                    "chembl_id": molecule_id,

                    "smiles": smiles,

                    "pic50": molecule_pic50

                }

            )

            if molecule_pic50 is not None:

                scaffold_dict[
                    scaffold_smiles
                ]["pic50_values"].append(
                    molecule_pic50
                )

        if live_computed:
            print(f"Computed {live_computed} scaffold(s) live "
                  "(not in precomputed cache).")

        # ---------------------------------------
        # Scaffold descriptors / drug-likeness /
        # functional groups
        # ---------------------------------------

        report(0.30, "Calculating scaffold descriptors")

        scaffold_props = PrecomputedService.lookup_scaffolds(
            list(scaffold_dict.keys())
        )

        total_scaffolds = len(scaffold_dict)

        for position, (scaffold_smiles, scaffold) in enumerate(
            scaffold_dict.items()
        ):

            props = scaffold_props.get(scaffold_smiles)

            if props is not None:

                descriptors, groups = props

            else:

                if position % 50 == 0:
                    report(
                        0.30 + 0.10 * position / max(total_scaffolds, 1),
                        f"Calculating scaffold descriptors "
                        f"({position:,}/{total_scaffolds:,})"
                    )

                descriptors = DescriptorService.calculate(
                    scaffold_smiles
                )

                groups = FunctionalGroupService.detect(
                    scaffold_smiles
                )

            scaffold["descriptors"] = descriptors

            scaffold["druglikeness"] = DrugLikenessService.evaluate(
                descriptors
            )

            scaffold["functional_groups"] = groups

        # ---------------------------------------
        # Release DataFrame memory
        # ---------------------------------------

        unique_df = None
        df = None

        # ---------------------------------------
        # Maximum occurrence
        # ---------------------------------------

        if len(scaffold_dict) == 0:

            return {

                "summary": {

                    "total_unique_molecules": 0,

                    "unique_scaffolds": 0,

                    "invalid_smiles": invalid_smiles,

                    "total_activity_records": 0,

                    "largest_scaffold_percentage": 0,

                    "top_scaffold_score": 0,

                    "average_median_pic50": None,

                    "dataset_median_pic50": None

                },

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

        # Progress for the one-atom analysis is weighted by molecule
        # count, since that is where the time goes.
        molecules_total = sum(
            len(s["molecules"]) for s in scaffold_dict.values()
        )

        molecules_done = 0

        # ---------------------------------------
        # Generate statistics
        # ---------------------------------------

        for scaffold in scaffold_dict.values():

            pic50 = scaffold["pic50_values"]

            occurrences = len(
                scaffold["molecules"]
            )

            if scaffold_id % 100 == 1 or occurrences >= 50:
                report(
                    0.40 + 0.52 * molecules_done / max(molecules_total, 1),
                    f"One-atom difference analysis "
                    f"(scaffold {scaffold_id:,}/{total_scaffolds:,})"
                )

            molecules_done += occurrences

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
            #
            # IMPORTANT:
            # molecules here belong ONLY to this
            # particular Murcko scaffold.
            #
            # Skip analysis when fewer than two
            # molecules are available because no pair
            # can possibly be formed.
            # ---------------------------------------

            if occurrences >= 2:

                side_chain_analysis = (
                    SideChainService.analyze(
                        scaffold_smiles=
                            scaffold["scaffold_smiles"],

                        molecules=
                            scaffold["molecules"],

                        side_chains=
                            side_chains
                    )
                )

            else:

                side_chain_analysis = {

                    "total_molecules":
                        occurrences,

                    "total_pairs_checked":
                        0,

                    "valid_one_atom_pairs":
                        0,

                    "replacement_pairs":
                        0,

                    "addition_removal_pairs":
                        0,

                    "strong_cliffs":
                        0,

                    "moderate_cliffs":
                        0,

                    "one_atom_pairs":
                        [],

                    "message": (
                        "At least two molecules are "
                        "required for one-atom "
                        "comparison."
                    )

                }

            # ---------------------------------------
            # Add complete scaffold result
            # ---------------------------------------

            scaffold_list.append(

                {

                    "id": scaffold_id,

                    "side_chain_analysis":
                        side_chain_analysis,

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

            scaffold_id += 1

        scaffold_dict = None

        report(0.93, "Ranking scaffolds")

        # ---------------------------------------
        # Sort Scaffolds
        #
        # Primary sort:
        # 1. Overall ranking score
        # 2. Median pIC50
        # 3. Occurrences
        # ---------------------------------------

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
        # Scaffold images for the top scaffolds
        # ---------------------------------------

        report(0.95, "Drawing top scaffold structures")

        for scaffold in scaffold_list[:ScaffoldService.SVG_TOP_N]:

            scaffold["svg"] = ScaffoldService.svg_for_molecule_scaffold(
                first_molecule_smiles[scaffold["scaffold_smiles"]]
            )

        # ---------------------------------------
        # Top Scaffold Summary
        # ---------------------------------------

        if len(scaffold_list) > 0:

            top_scaffold = scaffold_list[0]

            top_percentage = (
                top_scaffold["percentage"]
            )

            if (
                top_scaffold["ranking"]
                is not None
            ):

                top_score = (
                    top_scaffold["ranking"]
                    .get("overall_score", 0)
                )

            else:

                top_score = 0

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

            if (
                scaffold["median_pic50"]
                is not None
            ):

                valid_pic50.append(

                    scaffold["median_pic50"]

                )

        if len(valid_pic50) > 0:

            average_pic50 = round(

                float(
                    np.mean(valid_pic50)
                ),

                3

            )

            median_dataset_pic50 = round(

                float(
                    np.median(valid_pic50)
                ),

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
