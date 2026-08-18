from rdkit import Chem
from collections import defaultdict
from itertools import combinations, count
import heapq


class SideChainService:

    # -----------------------------------------
    # SETTINGS
    # -----------------------------------------

    MIN_DELTA_PIC50 = 1.0
    TOP_PAIRS_LIMIT = 50


    # -----------------------------------------
    # GET SIDE CHAIN / SUBSTITUENT
    # -----------------------------------------

    @staticmethod
    def get_side_chain(smiles, scaffold_smiles):

        if (
            not smiles
            or not scaffold_smiles
            or scaffold_smiles == "NO_SCAFFOLD"
        ):
            return None

        mol = Chem.MolFromSmiles(smiles)
        scaffold = Chem.MolFromSmiles(scaffold_smiles)

        if mol is None or scaffold is None:
            return None

        match = mol.GetSubstructMatch(scaffold)

        if not match:
            return None

        scaffold_atoms = set(match)
        side_chain_atoms = set()

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

            if atom.GetAtomicNum() > 1:
                counts[atom.GetSymbol()] += 1

        return dict(counts)


    # -----------------------------------------
    # ANALYZE ATOM CHANGE
    # -----------------------------------------

    @staticmethod
    def analyze_atom_change_from_counts(
        counts_1,
        counts_2
    ):

        elements = set(counts_1) | set(counts_2)

        removed = []
        added = []

        for element in elements:

            difference = (
                counts_2.get(element, 0)
                - counts_1.get(element, 0)
            )

            if difference > 0:

                added.extend(
                    [element] * difference
                )

            elif difference < 0:

                removed.extend(
                    [element] * abs(difference)
                )

        # One atom addition
        if len(added) == 1 and len(removed) == 0:

            return {
                "is_one_atom_change": True,
                "change_type": "Addition",
                "structural_change":
                    f"Added {added[0]}"
            }

        # One atom removal
        if len(removed) == 1 and len(added) == 0:

            return {
                "is_one_atom_change": True,
                "change_type": "Removal",
                "structural_change":
                    f"Removed {removed[0]}"
            }

        # One atom replacement
        if len(removed) == 1 and len(added) == 1:

            return {
                "is_one_atom_change": True,
                "change_type": "Replacement",
                "structural_change":
                    f"{removed[0]} → {added[0]}"
            }

        return {
            "is_one_atom_change": False,
            "change_type": "Multiple Changes",
            "structural_change": None
        }


    # -----------------------------------------
    # ACTIVITY CLIFF CLASSIFICATION
    # -----------------------------------------

    @staticmethod
    def classify_cliff(delta_pic50):

        if delta_pic50 >= 2.0:

            return {
                "cliff_type":
                    "Strong Potential Cliff",
                "is_potential_cliff": True
            }

        if delta_pic50 >= 1.0:

            return {
                "cliff_type":
                    "Moderate Potential Cliff",
                "is_potential_cliff": True
            }

        return {
            "cliff_type": "No Strong Cliff",
            "is_potential_cliff": False
        }


    # -----------------------------------------
    # CREATE RESULT PAIR
    # -----------------------------------------

    @staticmethod
    def build_pair(
        molecule_1,
        molecule_2,
        change
    ):

        delta_pic50 = round(
            abs(
                molecule_1["pic50"]
                - molecule_2["pic50"]
            ),
            3
        )

        cliff = SideChainService.classify_cliff(
            delta_pic50
        )

        return {

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

        }


    # -----------------------------------------
    # STORE ONLY TOP PAIRS
    # -----------------------------------------

    @staticmethod
    def add_top_pair(
        heap,
        pair,
        pair_counter
    ):

        delta = pair["delta_pic50"]

        # Do not store weak differences
        if delta < SideChainService.MIN_DELTA_PIC50:
            return

        # Unique ID prevents heap from trying
        # to compare dictionaries when two pairs
        # have the same delta.
        unique_id = next(pair_counter)

        heap_item = (
            delta,
            unique_id,
            pair
        )

        # Heap has space
        if len(heap) < SideChainService.TOP_PAIRS_LIMIT:

            heapq.heappush(
                heap,
                heap_item
            )

        # Replace smallest result when the new
        # result has a larger delta.
        elif delta > heap[0][0]:

            heapq.heapreplace(
                heap,
                heap_item
            )


    # -----------------------------------------
    # MAIN ANALYSIS
    # -----------------------------------------

    @staticmethod
    def analyze(
        scaffold_smiles,
        molecules
    ):

        if (
            not scaffold_smiles
            or scaffold_smiles == "NO_SCAFFOLD"
            or len(molecules) < 2
        ):

            return {

                "total_molecules":
                    len(molecules),

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

                "stored_pairs":
                    0,

                "message":
                    "Not enough valid molecules or no valid "
                    "Murcko scaffold for one-atom analysis."

            }


        # -------------------------------------
        # PREPROCESS MOLECULES
        # -------------------------------------

        processed_molecules = []

        for molecule in molecules:

            smiles = molecule.get("smiles")
            pic50 = molecule.get("pic50")

            if (
                smiles is None
                or pic50 is None
            ):
                continue

            try:

                pic50 = float(pic50)

            except (
                TypeError,
                ValueError
            ):
                continue

            side_chain = (
                SideChainService.get_side_chain(
                    smiles,
                    scaffold_smiles
                )
            )

            if side_chain is None:
                continue

            atom_counts = (
                SideChainService.get_atom_counts(
                    side_chain
                )
            )

            processed_molecules.append(
                {

                    "chembl_id":
                        molecule.get("chembl_id"),

                    "pic50":
                        pic50,

                    "substituent":
                        side_chain,

                    "atom_counts":
                        atom_counts,

                    "atom_count":
                        sum(
                            atom_counts.values()
                        )

                }
            )


        # -------------------------------------
        # GROUP BY TOTAL ATOM COUNT
        # -------------------------------------

        grouped_by_size = defaultdict(list)

        for molecule in processed_molecules:

            grouped_by_size[
                molecule["atom_count"]
            ].append(
                molecule
            )


        # -------------------------------------
        # MEMORY-EFFICIENT RESULT STORAGE
        # -------------------------------------

        top_pairs_heap = []

        # Prevent equal delta values from causing
        # dictionary comparison errors in heapq.
        pair_counter = count()

        total_pairs_checked = 0
        valid_one_atom_pairs = 0
        replacement_pairs = 0
        addition_removal_pairs = 0
        strong_cliffs = 0
        moderate_cliffs = 0

        sizes = sorted(
            grouped_by_size.keys()
        )


        # -------------------------------------
        # CHECK PAIRS
        # -------------------------------------

        for size in sizes:

            same_size_group = (
                grouped_by_size[size]
            )


            # ---------------------------------
            # SAME SIZE → REPLACEMENT
            # ---------------------------------

            for molecule_1, molecule_2 in combinations(
                same_size_group,
                2
            ):

                total_pairs_checked += 1

                change = (
                    SideChainService
                    .analyze_atom_change_from_counts(
                        molecule_1["atom_counts"],
                        molecule_2["atom_counts"]
                    )
                )

                if (
                    not change["is_one_atom_change"]
                    or change["change_type"]
                    != "Replacement"
                ):
                    continue

                valid_one_atom_pairs += 1
                replacement_pairs += 1

                pair = (
                    SideChainService.build_pair(
                        molecule_1,
                        molecule_2,
                        change
                    )
                )

                delta = pair["delta_pic50"]

                if delta >= 2.0:

                    strong_cliffs += 1

                elif delta >= SideChainService.MIN_DELTA_PIC50:

                    moderate_cliffs += 1

                SideChainService.add_top_pair(
                    top_pairs_heap,
                    pair,
                    pair_counter
                )


            # ---------------------------------
            # SIZE DIFFERENCE OF 1
            # → ADDITION / REMOVAL
            # ---------------------------------

            next_size_group = (
                grouped_by_size.get(
                    size + 1,
                    []
                )
            )

            if not next_size_group:
                continue

            for molecule_1 in same_size_group:

                for molecule_2 in next_size_group:

                    total_pairs_checked += 1

                    change = (
                        SideChainService
                        .analyze_atom_change_from_counts(
                            molecule_1["atom_counts"],
                            molecule_2["atom_counts"]
                        )
                    )

                    if (
                        not change["is_one_atom_change"]
                        or change["change_type"]
                        not in [
                            "Addition",
                            "Removal"
                        ]
                    ):
                        continue

                    valid_one_atom_pairs += 1
                    addition_removal_pairs += 1

                    pair = (
                        SideChainService.build_pair(
                            molecule_1,
                            molecule_2,
                            change
                        )
                    )

                    delta = pair["delta_pic50"]

                    if delta >= 2.0:

                        strong_cliffs += 1

                    elif delta >= SideChainService.MIN_DELTA_PIC50:

                        moderate_cliffs += 1

                    SideChainService.add_top_pair(
                        top_pairs_heap,
                        pair,
                        pair_counter
                    )


        # -------------------------------------
        # GET TOP PAIRS
        # -------------------------------------

        one_atom_pairs = [

            item[2]

            for item in sorted(
                top_pairs_heap,
                key=lambda item: item[0],
                reverse=True
            )

        ]


        # -------------------------------------
        # CREATE MESSAGE
        # -------------------------------------

        if valid_one_atom_pairs == 0:

            message = (
                "No molecule pairs with a single atom "
                "addition, removal, or replacement were "
                "found for this scaffold."
            )

        elif strong_cliffs > 0:

            message = (
                f"{strong_cliffs} strong potential activity "
                f"cliff case(s) found among one-atom "
                f"structural modifications."
            )

        elif moderate_cliffs > 0:

            message = (
                f"{moderate_cliffs} moderate potential "
                f"activity cliff case(s) found among "
                f"one-atom structural modifications."
            )

        else:

            message = (
                f"{valid_one_atom_pairs} one-atom structural "
                f"modification pair(s) found, but no "
                f"activity difference of "
                f"{SideChainService.MIN_DELTA_PIC50} pIC50 "
                f"or greater was detected."
            )


        # -------------------------------------
        # RESPONSE
        # -------------------------------------

        return {

            "total_molecules":
                len(processed_molecules),

            "total_pairs_checked":
                total_pairs_checked,

            "valid_one_atom_pairs":
                valid_one_atom_pairs,

            "replacement_pairs":
                replacement_pairs,

            "addition_removal_pairs":
                addition_removal_pairs,

            "strong_cliffs":
                strong_cliffs,

            "moderate_cliffs":
                moderate_cliffs,

            # Maximum 50 pairs with ΔpIC50 >= 1.0
            "one_atom_pairs":
                one_atom_pairs,

            "stored_pairs":
                len(one_atom_pairs),

            "message":
                message

        }