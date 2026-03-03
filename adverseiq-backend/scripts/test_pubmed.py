import httpx, asyncio, json

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

async def test_query(drugs, symptom):
    drug_query = " AND ".join(f'"{d}"[tiab]' for d in drugs)
    query = f"({drug_query}) AND interaction[tiab]"
    print(f"\nQuery: {query}")
    async with httpx.AsyncClient() as c:
        r = await c.get(ESEARCH, params={
            "db": "pubmed", "term": query,
            "retmax": 5, "sort": "relevance", "retmode": "json"
        }, timeout=15.0)
        res = r.json().get("esearchresult", {})
        print(f"  count={res.get('count')}  pmids={res.get('idlist', [])}")

async def main():
    await test_query(["warfarin", "fluconazole"], "bleeding")
    await test_query(["tramadol", "sertraline"], "serotonin")
    await test_query(["metformin", "st. john's wort"], "hyperglycemia")

asyncio.run(main())
