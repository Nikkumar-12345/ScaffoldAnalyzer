from rdkit import Chem


class FunctionalGroupService:

    PATTERNS = {

        "Amide": "C(=O)N",

        "Hydroxyl": "[OX2H]",

        "Primary Amine": "[NX3;H2]",

        "Secondary Amine": "[NX3;H1]",

        "Tertiary Amine": "[NX3;H0]",

        "Carboxylic Acid": "C(=O)[OH]",

        "Ester": "C(=O)O",

        "Ether": "[OD2]([#6])[#6]",

        "Ketone": "[#6][CX3](=O)[#6]",

        "Aldehyde": "[CX3H1](=O)[#6]",

        "Fluorine": "[F]",

        "Chlorine": "[Cl]",

        "Bromine": "[Br]",

        "Iodine": "[I]",

        "Nitrile": "C#N",

        "Sulfonamide": "S(=O)(=O)N",

        "Sulfone": "S(=O)(=O)",

        "Thiol": "[SX2H]",

        "Phenol": "c[OH]",

        "Trifluoromethyl": "C(F)(F)F"

    }

    @staticmethod
    def detect(smiles):

        mol = Chem.MolFromSmiles(smiles)

        if mol is None:

            return []

        groups = []

        for name, smarts in FunctionalGroupService.PATTERNS.items():

            pattern = Chem.MolFromSmarts(smarts)

            if pattern is None:

                continue

            if mol.HasSubstructMatch(pattern):

                groups.append(name)

        return groups