from fastapi import APIRouter, Query
from app.services.drug_lookup import drug_lookup

router = APIRouter()


@router.get("/drugs/search")
async def search_drugs(
    q: str = Query(default="", min_length=1)
):
    results = drug_lookup.search_drugs(q, limit=10)

    return [
        {
            "id": r["generic"].replace(" ", "-"),
            "displayName": r["display"],
            "genericName": r["generic"],
            "isHerb": r["is_herb"],
        }
        for r in results
    ]