from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services.errors import normalize_uniprot_id
from app.services.stereo_cache_service import StereoCacheService

router = APIRouter(
    prefix="/stereo",
    tags=["Stereochemistry"]
)


def resolve_target(data):

    uniprot_id = normalize_uniprot_id(data.get("uniprot_id"))

    if not uniprot_id:

        raise HTTPException(
            status_code=400,
            detail="uniprot_id is required."
        )

    if not StereoCacheService.is_available():

        raise HTTPException(
            status_code=503,
            detail="Stereochemistry data is not installed on this server."
        )

    target = StereoCacheService.get_target(uniprot_id)

    if target is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"No stereochemistry analysis is available for "
                f"'{uniprot_id}'. It is not one of the targets with "
                "activity data in the local ChEMBL database."
            )
        )

    return uniprot_id, target


# --------------------------------------------------
# STEREOISOMER GROUPS FOR A TARGET (one page)
# --------------------------------------------------

@router.post("/groups")
def list_groups(data: dict):

    uniprot_id, target = resolve_target(data)

    offset = max(int(data.get("offset", 0)), 0)

    total, groups = StereoCacheService.get_groups(
        target["target_chembl_id"],
        offset=offset,
        limit=min(max(int(data.get("limit", 25)), 1), 200),
        min_delta=float(data.get("min_delta", 0.0)),
        relationship=data.get("relationship") or None
    )

    molecules = target["molecules"] or 0

    return {
        "target": {
            "uniprot_id": uniprot_id,
            "target_chembl_id": target["target_chembl_id"],
            "target_name": target["target_name"],
        },
        "summary": {
            "molecules": molecules,
            "with_stereocentres": target["with_stereocentres"],
            "fully_specified": target["fully_specified"],
            "partly_specified": target["partly_specified"],
            "groups_total": target["groups_total"],
            "groups_with_activity": target["groups_with_activity"],
            "enantiomer_pairs": target["enantiomer_pairs"],
            "cliffs_moderate": target["cliffs_moderate"],
            "cliffs_strong": target["cliffs_strong"],
            "max_delta": target["max_delta"],
        },
        "relationships": StereoCacheService.relationship_counts(
            target["target_chembl_id"]
        ),
        "parameters": StereoCacheService.parameters(),
        "matching": total,
        "offset": offset,
        "groups": groups,
    }


# --------------------------------------------------
# ONE GROUP, EVERY ISOMER DRAWN WITH ITS POTENCY
# --------------------------------------------------

@router.post("/groups/detail")
def group_detail(data: dict):

    uniprot_id, target = resolve_target(data)

    try:
        group_no = int(data.get("group_no"))
    except (TypeError, ValueError):

        raise HTTPException(
            status_code=400,
            detail="group_no is required."
        )

    detail = StereoCacheService.get_group_detail(
        target["target_chembl_id"],
        group_no
    )

    if detail is None:

        raise HTTPException(
            status_code=404,
            detail=f"Group {group_no} was not found for {uniprot_id}."
        )

    return detail


# --------------------------------------------------
# CSV DOWNLOAD (one row per group)
# --------------------------------------------------

@router.get("/csv/{uniprot_id}")
def download_csv(uniprot_id: str):

    uniprot_id, target = resolve_target({"uniprot_id": uniprot_id})

    return Response(
        content=StereoCacheService.to_csv(target),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{uniprot_id}_stereoisomers.csv"'
            )
        }
    )
