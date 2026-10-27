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

    # SMARTS patterns compiled once instead of on every call
    _COMPILED = None

    @classmethod
    def _compiled_patterns(cls):

        if cls._COMPILED is None:

            cls._COMPILED = [
                (name, Chem.MolFromSmarts(smarts))
                for name, smarts in cls.PATTERNS.items()
            ]

        return cls._COMPILED

    @staticmethod
    def detect(smiles, mol=None):

        # An already-parsed molecule of the same SMILES can be passed
        # to avoid parsing it twice; the result is identical.
        if mol is None:
            mol = Chem.MolFromSmiles(smiles)

        if mol is None:

            return []

        groups = []

        for name, pattern in FunctionalGroupService._compiled_patterns():

            if pattern is None:

                continue

            if mol.HasSubstructMatch(pattern):

                groups.append(name)

        return groups