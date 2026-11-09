from fastapi import APIRouter, HTTPException

from app.services.cross_target_service import CrossTargetService
from app.services.errors import normalize_uniprot_id
from app.services.homolog_service import HomologService

router = APIRouter(
    prefix="/homolog",
    tags=["Homologous proteins"]
)

cross_target = CrossTargetService()


# --------------------------------------------------
# HOMOLOGOUS PROTEINS FOR A TARGET
# --------------------------------------------------

@router.post("/search")
def search_homologs(data: dict):

    uniprot_id = normalize_uniprot_id(data.get("uniprot_id"))

    if not uniprot_id:

        raise HTTPException(
            status_code=400,
            detail="uniprot_id is required."
        )

    if not HomologService.is_available():

        raise HTTPException(
            status_code=503,
            detail=(
                "Homologous-protein data is not installed on this "
                "server."
            )
        )

    protein = HomologService.get_protein(uniprot_id)

    if protein is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"'{uniprot_id}' is not one of the proteins in the "
                "local ChEMBL database, so no homology search has been "
                "precomputed for it."
            )
        )

    return {
        "query": protein,
        "method": HomologService.METHOD,
        "benchmark": HomologService.benchmark_info(),
        "homologs": HomologService.get_homologs(
            uniprot_id,
            limit=int(data.get("limit", 25)),
            min_identity=float(data.get("min_identity", 0)),
            min_similarity=float(data.get("min_similarity", 0)),
            with_data_only=bool(data.get("with_data_only", False))
        )
    }


# --------------------------------------------------
# SCAFFOLD SELECTIVITY ACROSS HOMOLOGS
#
# Combines the scaffold's cross-target hits with the
# sequence similarity of those targets to the protein
# being analysed:
#
#   - a scaffold shared with close homologs suggests
#     family-wide activity (selectivity risk)
#   - a scaffold shared only with unrelated proteins
#     suggests the overlap is not family driven
# --------------------------------------------------

@router.post("/scaffold-selectivity")
def scaffold_selectivity(data: dict):

    scaffold_smiles = (data.get("scaffold_smiles") or "").strip()

    uniprot_id = normalize_uniprot_id(data.get("uniprot_id"))

    if not scaffold_smiles:

        raise HTTPException(
            status_code=400,
            detail="scaffold_smiles is required."
        )

    cross = cross_target.find_other_targets(
        scaffold_smiles=scaffold_smiles,
        current_target_chembl_id=data.get("current_target_chembl_id")
    )

    targets = cross["targets"]

    identities = HomologService.identity_map(
        uniprot_id,
        [t.get("uniprot_id") for t in targets]
    )

    related = []
    unrelated = []

    for target in targets:

        match = identities.get(target.get("uniprot_id"))

        enriched = dict(target)

        if match is not None:

            enriched["identity"] = match["identity"]
            enriched["similarity"] = match["similarity"]
            enriched["bit_score"] = match["bit_score"]
            enriched["evalue"] = match["evalue"]
            enriched["is_homolog"] = True
            enriched["meets_benchmark"] = match["meets_benchmark"]

            related.append(enriched)

        else:

            enriched["identity"] = None
            enriched["similarity"] = None
            enriched["is_homolog"] = False
            enriched["meets_benchmark"] = False

            unrelated.append(enriched)

    related.sort(
        key=lambda t: t["identity"],
        reverse=True
    )

    return {
        "scaffold_smiles": scaffold_smiles,
        "query_uniprot_id": uniprot_id or None,
        "homology_available": HomologService.is_available(),
        "method": HomologService.METHOD,
        "benchmark": HomologService.benchmark_info(),
        "total_other_targets": cross["total_other_targets"],
        "homologous_targets": related,
        "unrelated_targets": unrelated,
        "homologous_count": len(related),
        "unrelated_count": len(unrelated),
        "benchmark_count": sum(
            1 for t in related if t["meets_benchmark"]
        ),
    }
