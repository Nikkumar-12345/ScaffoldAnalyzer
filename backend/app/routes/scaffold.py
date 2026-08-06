from fastapi import APIRouter

from app.services.molecule_service import MoleculeService

router = APIRouter(
    prefix="/scaffold",
    tags=["Scaffold"]
)


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