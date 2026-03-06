from fastapi import APIRouter, Query
from app.services.pubmed_client import pubmed_client

router = APIRouter()


@router.get("/pubmed/search")
async def search_pubmed(
    drugs: str = Query(..., description="Comma-separated drug/herb names"),
    max_results: int = Query(default=5, ge=1, le=10),
):
    """
    Search PubMed for real interaction literature for the given drugs.
    Returns list of {pmid, title, abstract_snippet, year, url}.
    Results are cached per drug pair so repeated calls are instant.
    """
    drug_list = [d.strip() for d in drugs.split(",") if d.strip()]
    if not drug_list:
        return []

    results = await pubmed_client.search_and_fetch(
        drugs=drug_list,
        symptom_text="interaction adverse",
        max_results=max_results,
    )
    return results
