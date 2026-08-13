from rdkit import Chem
from collections import defaultdict
import statistics


class SideChainService:

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

        # Find atoms directly attached to scaffold
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

        # Extract complete fragments outside the scaffold
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


    @staticmethod
    def analyze(scaffold_smiles, molecules):

        side_chain_data = defaultdict(list)

        highest_molecule = None
        lowest_molecule = None

        # ----------------------------------
        # Group molecules by side chain
        # ----------------------------------

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
                smiles,
                scaffold_smiles
            )

            if side_chain is None:
                side_chain = "Unknown"

            molecule_data = {

                "chembl_id": molecule.get("chembl_id"),

                "smiles": smiles,

                "pic50": pic50,

                "side_chain": side_chain

            }

            side_chain_data[side_chain].append(
                molecule_data
            )

            # Overall highest activity molecule
            if (
                highest_molecule is None
                or pic50 > highest_molecule["pic50"]
            ):

                highest_molecule = molecule_data

            # Overall lowest activity molecule
            if (
                lowest_molecule is None
                or pic50 < lowest_molecule["pic50"]
            ):

                lowest_molecule = molecule_data


        # ----------------------------------
        # Calculate side-chain statistics
        # ----------------------------------

        side_chains = []

        for side_chain, group in side_chain_data.items():

            values = [

                molecule["pic50"]

                for molecule in group

            ]

            # Highest and lowest molecule
            # belonging to this side chain
            max_molecule = max(
                group,
                key=lambda x: x["pic50"]
            )

            min_molecule = min(
                group,
                key=lambda x: x["pic50"]
            )

            side_chains.append({

                "side_chain": side_chain,

                "count": len(group),

                "max_pic50": round(
                    max(values),
                    3
                ),

                "mean_pic50": round(
                    statistics.mean(values),
                    3
                ),

                "min_pic50": round(
                    min(values),
                    3
                ),

                "max_molecule": max_molecule,

                "min_molecule": min_molecule

            })


        # Sort highest potency side chains first
        side_chains.sort(

            key=lambda x: x["max_pic50"],

            reverse=True

        )


        # ----------------------------------
        # Activity Cliff Analysis
        # Compare DIFFERENT side chains
        # ----------------------------------

        activity_difference = None

        possible_activity_cliff = False

        cliff_type = "None"

        cliff_side_chain_1 = None
        cliff_side_chain_2 = None

        cliff_molecule_high = None
        cliff_molecule_low = None

        cliff_message = (
            "Not enough different side chains for "
            "activity cliff analysis."
        )


        # Need at least 2 different side chains
        if len(side_chains) >= 2:

            largest_difference = -1

            # Compare every side chain with every
            # other side chain
            for i in range(len(side_chains)):

                for j in range(i + 1, len(side_chains)):

                    chain_1 = side_chains[i]
                    chain_2 = side_chains[j]

                    # Compare the strongest molecule
                    # from each side-chain group
                    difference = abs(

                        chain_1["max_pic50"]
                        -
                        chain_2["max_pic50"]

                    )

                    if difference > largest_difference:

                        largest_difference = difference

                        activity_difference = round(
                            difference,
                            3
                        )

                        # Determine which chain is higher
                        if (
                            chain_1["max_pic50"]
                            >=
                            chain_2["max_pic50"]
                        ):

                            cliff_side_chain_1 = (
                                chain_1["side_chain"]
                            )

                            cliff_side_chain_2 = (
                                chain_2["side_chain"]
                            )

                            cliff_molecule_high = (
                                chain_1["max_molecule"]
                            )

                            cliff_molecule_low = (
                                chain_2["max_molecule"]
                            )

                        else:

                            cliff_side_chain_1 = (
                                chain_2["side_chain"]
                            )

                            cliff_side_chain_2 = (
                                chain_1["side_chain"]
                            )

                            cliff_molecule_high = (
                                chain_2["max_molecule"]
                            )

                            cliff_molecule_low = (
                                chain_1["max_molecule"]
                            )


            # ----------------------------------
            # Cliff Thresholds
            # ----------------------------------

            if activity_difference >= 2.0:

                possible_activity_cliff = True

                cliff_type = "Strong"

                cliff_message = (

                    f"Possible strong activity cliff detected. "
                    f"The largest difference between two different "
                    f"side chains is {activity_difference} pIC50 units. "

                    f"The higher-activity side chain is "
                    f"'{cliff_side_chain_1}', while the lower-activity "
                    f"side chain is '{cliff_side_chain_2}'."

                )

            elif activity_difference >= 1.0:

                possible_activity_cliff = True

                cliff_type = "Moderate"

                cliff_message = (

                    f"Possible moderate activity cliff detected. "
                    f"The largest difference between two different "
                    f"side chains is {activity_difference} pIC50 units. "

                    f"This suggests that side-chain modification may "
                    f"significantly affect biological activity."

                )

            else:

                cliff_type = "None"

                cliff_message = (

                    f"No significant activity cliff detected between "
                    f"different side chains. The largest observed "
                    f"difference is {activity_difference} pIC50 units."

                )


        # ----------------------------------
        # Return Analysis
        # ----------------------------------

        return {

            "side_chains": side_chains,

            "highest_activity": highest_molecule,

            "lowest_activity": lowest_molecule,

            "activity_difference": activity_difference,

            "possible_activity_cliff": possible_activity_cliff,

            "cliff_type": cliff_type,

            "high_activity_side_chain": cliff_side_chain_1,

            "low_activity_side_chain": cliff_side_chain_2,

            "high_activity_molecule": cliff_molecule_high,

            "low_activity_molecule": cliff_molecule_low,

            "message": cliff_message

        }