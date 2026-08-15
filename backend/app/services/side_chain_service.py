from rdkit import Chem
from collections import defaultdict
from itertools import combinations


class SideChainService:

    # -----------------------------------------
    # GET SIDE CHAIN / SUBSTITUENT
    # -----------------------------------------

    @staticmethod
    def get_side_chain(smiles, scaffold_smiles):

        mol = Chem.MolFromSmiles(smiles)
        scaffold = Chem.MolFromSmiles(scaffold_smiles)

        if mol is None or scaffold is None:
            return None

        match = mol.GetSubstructMatch(scaffold)

        if not match:
            return None

        scaffold_atoms = set(match)

        side_chain_atoms = set()

        # Find atoms directly connected to scaffold
        for atom_idx in scaffold_atoms:

            atom = mol.GetAtomWithIdx(atom_idx)

            for neighbor in atom.GetNeighbors():

                neighbor_idx = neighbor.GetIdx()

                if neighbor_idx not in scaffold_atoms:
                    side_chain_atoms.add(neighbor_idx)

        if not side_chain_atoms:
            return "No Side Chain"

        visited = set()
        fragments = []

        # Extract every connected fragment outside scaffold
        for start_atom in side_chain_atoms:

            if start_atom in visited:
                continue

            fragment_atoms = set()
            stack = [start_atom]

            while stack:

                atom_idx = stack.pop()

                if atom_idx in visited:
                    continue

                if atom_idx in scaffold_atoms:
                    continue

                visited.add(atom_idx)
                fragment_atoms.add(atom_idx)

                atom = mol.GetAtomWithIdx(atom_idx)

                for neighbor in atom.GetNeighbors():

                    neighbor_idx = neighbor.GetIdx()

                    if (
                        neighbor_idx not in visited
                        and neighbor_idx not in scaffold_atoms
                    ):
                        stack.append(neighbor_idx)

            if fragment_atoms:

                fragment_smiles = Chem.MolFragmentToSmiles(
                    mol,
                    atomsToUse=list(fragment_atoms),
                    canonical=True
                )

                fragments.append(fragment_smiles)

        if not fragments:
            return "No Side Chain"

        return ".".join(sorted(fragments))


    # -----------------------------------------
    # GET ATOM COUNTS
    # -----------------------------------------

    @staticmethod
    def get_atom_counts(fragment_smiles):

        if (
            fragment_smiles is None
            or fragment_smiles == "No Side Chain"
            or fragment_smiles == ""
        ):
            return {}

        mol = Chem.MolFromSmiles(fragment_smiles)

        if mol is None:
            return {}

        counts = defaultdict(int)

        for atom in mol.GetAtoms():

            # Heavy atoms only
            if atom.GetAtomicNum() > 1:

                counts[atom.GetSymbol()] += 1

        return dict(counts)


    # -----------------------------------------
    # ANALYZE STRUCTURAL CHANGE
    #
    # Supports:
    #
    # 1. Addition/removal:
    #    R-H -> R-F
    #
    # 2. Replacement:
    #    R-F -> R-Cl
    #
    # -----------------------------------------

    @staticmethod
    def analyze_atom_change(side_chain_1, side_chain_2):

        counts_1 = SideChainService.get_atom_counts(
            side_chain_1
        )

        counts_2 = SideChainService.get_atom_counts(
            side_chain_2
        )

        elements = set(counts_1.keys()) | set(counts_2.keys())

        removed = []
        added = []

        for element in elements:

            count_1 = counts_1.get(element, 0)
            count_2 = counts_2.get(element, 0)

            difference = count_2 - count_1

            if difference > 0:

                added.extend(
                    [element] * difference
                )

            elif difference < 0:

                removed.extend(
                    [element] * abs(difference)
                )


        # -------------------------------------
        # CASE 1:
        # ONE ATOM ADDED
        # -------------------------------------

        if len(added) == 1 and len(removed) == 0:

            return {

                "is_one_atom_change": True,

                "change_type": "Addition",

                "structural_change":
                    f"Added {added[0]}",

                "added_atoms": added,

                "removed_atoms": removed

            }


        # -------------------------------------
        # CASE 2:
        # ONE ATOM REMOVED
        # -------------------------------------

        if len(removed) == 1 and len(added) == 0:

            return {

                "is_one_atom_change": True,

                "change_type": "Removal",

                "structural_change":
                    f"Removed {removed[0]}",

                "added_atoms": added,

                "removed_atoms": removed

            }


        # -------------------------------------
        # CASE 3:
        # ONE ATOM REPLACED
        #
        # Example:
        # F -> Cl
        # C -> N
        # Br -> I
        # -------------------------------------

        if len(removed) == 1 and len(added) == 1:

            return {

                "is_one_atom_change": True,

                "change_type": "Replacement",

                "structural_change":
                    f"{removed[0]} → {added[0]}",

                "added_atoms": added,

                "removed_atoms": removed

            }


        # More than one atom changed
        return {

            "is_one_atom_change": False,

            "change_type": "Multiple Changes",

            "structural_change": None,

            "added_atoms": added,

            "removed_atoms": removed

        }


    # -----------------------------------------
    # ACTIVITY CLIFF CLASSIFICATION
    # -----------------------------------------

    @staticmethod
    def classify_cliff(delta_pic50):

        if delta_pic50 >= 2.0:

            return {

                "cliff_type": "Strong Potential Cliff",

                "is_potential_cliff": True

            }

        elif delta_pic50 >= 1.0:

            return {

                "cliff_type": "Moderate Potential Cliff",

                "is_potential_cliff": True

            }

        else:

            return {

                "cliff_type": "No Strong Cliff",

                "is_potential_cliff": False

            }


    # -----------------------------------------
    # MAIN ANALYSIS
    #
    # molecules passed here belong to ONE
    # scaffold only.
    # -----------------------------------------

    @staticmethod
    def analyze(scaffold_smiles, molecules):

        processed_molecules = []


        # -------------------------------------
        # PREPARE MOLECULES
        #
        # Extract side chain once only.
        # -------------------------------------

        for molecule in molecules:

            smiles = molecule.get("smiles")
            pic50 = molecule.get("pic50")

            if smiles is None or pic50 is None:
                continue

            try:
                pic50 = float(pic50)

            except (TypeError, ValueError):
                continue


            side_chain = SideChainService.get_side_chain(

                smiles=smiles,

                scaffold_smiles=scaffold_smiles

            )


            if side_chain is None:
                continue


            processed_molecules.append({

                "chembl_id":
                    molecule.get("chembl_id"),

                "smiles":
                    smiles,

                "pic50":
                    pic50,

                "substituent":
                    side_chain,

                "atom_counts":
                    SideChainService.get_atom_counts(
                        side_chain
                    )

            })


        # -------------------------------------
        # REMOVE DUPLICATE IDENTICAL MOLECULES
        # -------------------------------------

        unique_processed = {}

        for molecule in processed_molecules:

            key = (
                molecule["chembl_id"],
                molecule["smiles"]
            )

            unique_processed[key] = molecule


        processed_molecules = list(
            unique_processed.values()
        )


        # -------------------------------------
        # GROUP MOLECULES BY TOTAL
        # HEAVY ATOM COUNT
        #
        # This reduces unnecessary comparisons.
        # -------------------------------------

        grouped_by_size = defaultdict(list)

        for molecule in processed_molecules:

            total_atoms = sum(
                molecule["atom_counts"].values()
            )

            grouped_by_size[total_atoms].append(
                molecule
            )


        # -------------------------------------
        # COMPARE ONLY POSSIBLE SIZE GROUPS
        #
        # Same size:
        #     possible replacement
        #
        # Size difference of 1:
        #     possible addition/removal
        # -------------------------------------

        one_atom_pairs = []

        total_pairs_checked = 0


        sizes = sorted(
            grouped_by_size.keys()
        )


        for size in sizes:


            # =================================
            # SAME SIZE
            #
            # Check possible replacement:
            # F -> Cl, C -> N etc.
            # =================================

            same_size_group = grouped_by_size[size]

            for molecule_1, molecule_2 in combinations(
                same_size_group,
                2
            ):

                total_pairs_checked += 1

                change = (
                    SideChainService.analyze_atom_change(

                        molecule_1["substituent"],

                        molecule_2["substituent"]

                    )
                )


                if not change["is_one_atom_change"]:
                    continue


                # For same atom count, only replacement
                # should normally qualify
                if change["change_type"] != "Replacement":
                    continue


                delta_pic50 = round(

                    abs(
                        molecule_1["pic50"]
                        -
                        molecule_2["pic50"]
                    ),

                    3

                )


                cliff = SideChainService.classify_cliff(
                    delta_pic50
                )


                one_atom_pairs.append({

                    "molecule_1": {

                        "chembl_id":
                            molecule_1["chembl_id"],

                        "substituent":
                            molecule_1["substituent"],

                        "pic50":
                            molecule_1["pic50"]

                    },

                    "molecule_2": {

                        "chembl_id":
                            molecule_2["chembl_id"],

                        "substituent":
                            molecule_2["substituent"],

                        "pic50":
                            molecule_2["pic50"]

                    },

                    "change_type":
                        change["change_type"],

                    "structural_change":
                        change["structural_change"],

                    "delta_pic50":
                        delta_pic50,

                    "cliff_type":
                        cliff["cliff_type"],

                    "is_potential_cliff":
                        cliff["is_potential_cliff"]

                })


            # =================================
            # SIZE DIFFERENCE = 1
            #
            # Check addition/removal
            # =================================

            next_size_group = grouped_by_size.get(
                size + 1,
                []
            )


            for molecule_1 in same_size_group:

                for molecule_2 in next_size_group:

                    total_pairs_checked += 1


                    change = (
                        SideChainService.analyze_atom_change(

                            molecule_1["substituent"],

                            molecule_2["substituent"]

                        )
                    )


                    if not change["is_one_atom_change"]:
                        continue


                    if change["change_type"] not in [
                        "Addition",
                        "Removal"
                    ]:
                        continue


                    delta_pic50 = round(

                        abs(
                            molecule_1["pic50"]
                            -
                            molecule_2["pic50"]
                        ),

                        3

                    )


                    cliff = (
                        SideChainService.classify_cliff(
                            delta_pic50
                        )
                    )


                    one_atom_pairs.append({

                        "molecule_1": {

                            "chembl_id":
                                molecule_1["chembl_id"],

                            "substituent":
                                molecule_1["substituent"],

                            "pic50":
                                molecule_1["pic50"]

                        },

                        "molecule_2": {

                            "chembl_id":
                                molecule_2["chembl_id"],

                            "substituent":
                                molecule_2["substituent"],

                            "pic50":
                                molecule_2["pic50"]

                        },

                        "change_type":
                            change["change_type"],

                        "structural_change":
                            change["structural_change"],

                        "delta_pic50":
                            delta_pic50,

                        "cliff_type":
                            cliff["cliff_type"],

                        "is_potential_cliff":
                            cliff["is_potential_cliff"]

                    })


        # -------------------------------------
        # REMOVE DUPLICATE PAIRS
        # -------------------------------------

        unique_pairs = []

        seen_pairs = set()


        for pair in one_atom_pairs:

            molecule_1 = pair["molecule_1"]["chembl_id"]
            molecule_2 = pair["molecule_2"]["chembl_id"]

            pair_key = tuple(
                sorted([
                    str(molecule_1),
                    str(molecule_2)
                ])
            )


            if pair_key in seen_pairs:
                continue


            seen_pairs.add(pair_key)

            unique_pairs.append(pair)


        one_atom_pairs = unique_pairs


        # -------------------------------------
        # SORT BY LARGEST ACTIVITY DIFFERENCE
        # -------------------------------------

        one_atom_pairs.sort(

            key=lambda pair:
                pair["delta_pic50"],

            reverse=True

        )


        # -------------------------------------
        # SUMMARY
        # -------------------------------------

        strong_cliffs = sum(

            1

            for pair in one_atom_pairs

            if pair["delta_pic50"] >= 2.0

        )


        moderate_cliffs = sum(

            1

            for pair in one_atom_pairs

            if (
                pair["delta_pic50"] >= 1.0
                and pair["delta_pic50"] < 2.0
            )

        )


        replacement_pairs = sum(

            1

            for pair in one_atom_pairs

            if pair["change_type"] == "Replacement"

        )


        addition_removal_pairs = sum(

            1

            for pair in one_atom_pairs

            if pair["change_type"] in [
                "Addition",
                "Removal"
            ]

        )


        # -------------------------------------
        # MESSAGE
        # -------------------------------------

        if len(one_atom_pairs) == 0:

            message = (

                "No molecule pairs with a single "
                "atom addition, removal, or replacement "
                "were found for this scaffold."

            )

        elif strong_cliffs > 0:

            message = (

                f"{strong_cliffs} strong potential "
                f"activity cliff case(s) found among "
                f"one-atom structural modifications."

            )

        elif moderate_cliffs > 0:

            message = (

                f"{moderate_cliffs} moderate potential "
                f"activity cliff case(s) found among "
                f"one-atom structural modifications."

            )

        else:

            message = (

                f"{len(one_atom_pairs)} one-atom "
                f"structural modification pair(s) found, "
                f"but no large activity cliff was detected."

            )


        # -------------------------------------
        # RETURN RESULT
        # -------------------------------------

        return {

            "total_molecules":
                len(processed_molecules),

            "total_pairs_checked":
                total_pairs_checked,

            "valid_one_atom_pairs":
                len(one_atom_pairs),

            "replacement_pairs":
                replacement_pairs,

            "addition_removal_pairs":
                addition_removal_pairs,

            "strong_cliffs":
                strong_cliffs,

            "moderate_cliffs":
                moderate_cliffs,

            "one_atom_pairs":
                one_atom_pairs,

            "message":
                message

        }