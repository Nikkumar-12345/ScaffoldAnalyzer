from fastapi import APIRouter, HTTPException

from app.services.cross_target_service import CrossTargetService
from app.services.molecule_service import MoleculeService
from app.services.scaffold_service import ScaffoldService


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

# --------------------------------------------------
# SCAFFOLD IMAGE ON DEMAND
#
# The analysis draws images only for the top-ranked
# scaffolds (the ones shown on the dashboard). Any other
# scaffold's image can be requested here.
# --------------------------------------------------

@router.post("/svg")
def scaffold_svg(data: dict):

    scaffold_smiles = (data.get("scaffold_smiles") or "").strip()

    if not scaffold_smiles:

        raise HTTPException(
            status_code=400,
            detail="scaffold_smiles is required."
        )

    svg = ScaffoldService.svg_for_scaffold_smiles(scaffold_smiles)

    if svg is None:

        raise HTTPException(
            status_code=400,
            detail=f"'{scaffold_smiles}' is not a valid scaffold SMILES."
        )

    return {
        "scaffold_smiles": scaffold_smiles,
        "svg": svg
    }
