from fastapi import APIRouter

from app.services.cross_target_service import CrossTargetService
from app.services.molecule_service import MoleculeService


router = APIRouter(
    prefix="/scaffold",
    tags=["Scaffold"]
)


# --------------------------------------------------
# CROSS-TARGET SERVICE
# --------------------------------------------------

cross_target = CrossTargetService()


# --------------------------------------------------
# FIND OTHER TARGETS CONTAINING SAME SCAFFOLD
# --------------------------------------------------

@router.post("/cross-targets")
def find_cross_targets(request: dict):

    return cross_target.find_other_targets(

        scaffold_smiles=
            request["scaffold_smiles"],

        current_target_chembl_id=
            request.get(
                "current_target_chembl_id"
            )

    )


# --------------------------------------------------
# GET MOLECULE DETAILS FOR A SCAFFOLD
# --------------------------------------------------

@router.post("/details")
def scaffold_details(data: dict):

    molecules = []

    for molecule in data["molecules"]:

        details = MoleculeService.create(

            chembl_id=molecule["chembl_id"],

            smiles=molecule["smiles"],

            pic50=molecule["pic50"]

        )

        if details is not None:

            molecules.append(details)

    return {

        "molecules": molecules

    }