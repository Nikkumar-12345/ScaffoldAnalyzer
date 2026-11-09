from fastapi import APIRouter, HTTPException

from app.services.cross_target_service import CrossTargetService
from app.services.homolog_service import HomologService
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

    result = cross_target.find_other_targets(

        scaffold_smiles=
            request["scaffold_smiles"],

        current_target_chembl_id=
            request.get(
                "current_target_chembl_id"
            )

    )

    # ----------------------------------------------
    # OPTIONAL: ANNOTATE WITH SEQUENCE SIMILARITY
    #
    # When the caller passes the UniProt ID of the
    # protein being analysed, each cross-target is
    # marked with how similar its sequence is to that
    # protein. Existing callers that do not pass it
    # get exactly the same response as before.
    # ----------------------------------------------

    query_uniprot_id = request.get("query_uniprot_id")

    if not query_uniprot_id:

        return result

    identities = HomologService.identity_map(

        query_uniprot_id,

        [
            target.get("uniprot_id")
            for target in result["targets"]
        ]

    )

    homologous = 0

    for target in result["targets"]:

        match = identities.get(
            target.get("uniprot_id")
        )

        if match is None:

            target["identity"] = None

            target["similarity"] = None

            target["is_homolog"] = False

            target["meets_benchmark"] = False

        else:

            target["identity"] = match["identity"]

            target["similarity"] = match["similarity"]

            target["bit_score"] = match["bit_score"]

            target["evalue"] = match["evalue"]

            target["is_homolog"] = True

            target["meets_benchmark"] = match["meets_benchmark"]

            homologous += 1

    result["homology_available"] = (
        HomologService.is_available()
    )

    result["homologous_count"] = homologous

    result["benchmark_count"] = sum(
        1
        for target in result["targets"]
        if target.get("meets_benchmark")
    )

    result["benchmark"] = (
        HomologService.benchmark_info()
    )

    return result


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
