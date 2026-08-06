from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D
from app.services.functional_group_service import FunctionalGroupService

from app.services.descriptor_service import DescriptorService
from app.services.druglikeness_service import DrugLikenessService


class MoleculeService:

    @staticmethod
    def create(
        chembl_id,
        smiles,
        pic50
    ):

        if smiles is None or smiles == "":
            return None

        mol = Chem.MolFromSmiles(smiles)

        if mol is None:
            return None

        # -----------------------------
        # SVG
        # -----------------------------

        drawer = rdMolDraw2D.MolDraw2DSVG(
            220,
            160
        )

        drawer.DrawMolecule(mol)

        drawer.FinishDrawing()

        svg = drawer.GetDrawingText()

        # -----------------------------
        # Descriptors
        # -----------------------------

        descriptors = DescriptorService.calculate(
            smiles
        )

        # -----------------------------
        # Drug Likeness
        # -----------------------------

        druglikeness = DrugLikenessService.evaluate(
            descriptors
        )

        return {

    "chembl_id": chembl_id,

    "smiles": smiles,

    "svg": svg,

    "pic50": pic50,

    "descriptors": descriptors,

    "druglikeness": druglikeness,

    "functional_groups":
        FunctionalGroupService.detect(
            smiles
        )

}