from fastapi import APIRouter

from app.services.molecule_service import MoleculeService

router = APIRouter(
    prefix="/molecule",
    tags=["Molecule"]
)


@router.post("/details")
def molecule_details(data: dict):

    return MoleculeService.create(

        chembl_id=data["chembl_id"],

        smiles=data["smiles"],

        pic50=data["pic50"]

    )