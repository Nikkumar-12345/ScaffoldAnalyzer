from rdkit import Chem
from rdkit.Chem import Descriptors
from rdkit.Chem import Crippen
from rdkit.Chem import QED
from rdkit.Chem import rdMolDescriptors
from rdkit.Chem import GraphDescriptors


class DescriptorService:

    @staticmethod
    def calculate(smiles: str):

        if smiles is None or smiles == "":
            return None

        mol = Chem.MolFromSmiles(smiles)

        if mol is None:
            return None

        try:

            descriptors = {

                # -------------------------
                # Physicochemical Properties
                # -------------------------

                "molecular_weight":
                    round(
                        Descriptors.MolWt(mol),
                        2
                    ),

                "logp":
                    round(
                        Crippen.MolLogP(mol),
                        2
                    ),

                "tpsa":
                    round(
                        rdMolDescriptors.CalcTPSA(mol),
                        2
                    ),

                "hba":
                    rdMolDescriptors.CalcNumHBA(mol),

                "hbd":
                    rdMolDescriptors.CalcNumHBD(mol),

                "rotatable_bonds":
                    rdMolDescriptors.CalcNumRotatableBonds(mol),

                "fsp3":
                    round(
                        rdMolDescriptors.CalcFractionCSP3(mol),
                        3
                    ),

                # -------------------------
                # Complexity
                # -------------------------

                "ring_count":
                    rdMolDescriptors.CalcNumRings(mol),

                "aromatic_rings":
                    rdMolDescriptors.CalcNumAromaticRings(mol),

                "heavy_atoms":
                    mol.GetNumHeavyAtoms(),

                "bertz_complexity":
                    round(
                        GraphDescriptors.BertzCT(mol),
                        2
                    ),

                # -------------------------
                # Drug Likeness
                # -------------------------

                "qed":
                    round(
                        QED.qed(mol),
                        3
                    )

            }

            return descriptors

        except Exception:

            return None