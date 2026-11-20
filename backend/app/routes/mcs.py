from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services.errors import normalize_uniprot_id
from app.services.mcs_cache_service import MCSCacheService

router = APIRouter(
    prefix="/mcs",
    tags=["Chemical series and maximum common substructure"]
)


def resolve_target(data):

    uniprot_id = normalize_uniprot_id(data.get("uniprot_id"))

    if not uniprot_id:

        raise HTTPException(
            status_code=400,
            detail="uniprot_id is required."
        )

    if not MCSCacheService.is_available():

        raise HTTPException(
            status_code=503,
            detail=(
                "Chemical-series data is not installed on this server."
            )
        )

    target = MCSCacheService.get_target(uniprot_id)

    if target is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"No chemical-series analysis is available for "
                f"'{uniprot_id}'. It is not one of the targets with "
                "activity data in the local ChEMBL database."
            )
        )

    return uniprot_id, target


# --------------------------------------------------
# CHEMICAL SERIES FOR A TARGET (one page, largest first)
# --------------------------------------------------

@router.post("/series")
def list_series(data: dict):

    uniprot_id, target = resolve_target(data)

    total, series = MCSCacheService.get_series(
        target["target_chembl_id"],
        offset=max(int(data.get("offset", 0)), 0),
        limit=min(max(int(data.get("limit", 25)), 1), 200),
        min_size=max(int(data.get("min_size", 1)), 1),
        with_mcs_only=bool(data.get("with_mcs_only", False))
    )

    return {
        "target": {
            "uniprot_id": uniprot_id,
            "target_chembl_id": target["target_chembl_id"],
            "target_name": target["target_name"],
        },
        "summary": {
            "molecules": target["molecules"],
            "molecules_clustered": target["clustered"],
            "truncated": bool(target["truncated"]),
            "series_total": target["series_total"],
            "singletons": target["singletons"],
            "mcs_success": target["mcs_success"],
            "mcs_timeout": target["mcs_timeout"],
            "largest_series": target["largest_series"],
        },
        "parameters": MCSCacheService.parameters(),
        "matching": total,
        "offset": max(int(data.get("offset", 0)), 0),
        "series": series,
    }


# --------------------------------------------------
# ONE SERIES, WITH ITS MOLECULES AND STRUCTURE IMAGES
# --------------------------------------------------

@router.post("/series/detail")
def series_detail(data: dict):

    uniprot_id, target = resolve_target(data)

    try:
        series_no = int(data.get("series_no"))
    except (TypeError, ValueError):

        raise HTTPException(
            status_code=400,
            detail="series_no is required."
        )

    detail = MCSCacheService.get_series_detail(
        target["target_chembl_id"],
        series_no
    )

    if detail is None:

        raise HTTPException(
            status_code=404,
            detail=f"Series {series_no} was not found for {uniprot_id}."
        )

    return detail


# --------------------------------------------------
# CSV DOWNLOAD (one row per series)
# --------------------------------------------------

@router.get("/csv/{uniprot_id}")
def download_csv(uniprot_id: str):

    uniprot_id, target = resolve_target({"uniprot_id": uniprot_id})

    return Response(
        content=MCSCacheService.to_csv(target),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{uniprot_id}_MCS_by_series.csv"'
            )
        }
    )
