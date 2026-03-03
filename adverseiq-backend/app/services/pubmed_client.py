import json
import logging
import re
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Absolute path so it works regardless of working directory
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "pubmed_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class PubMedClient:
    async def search_and_fetch(
        self,
        drugs: list[str],
        symptom_text: str,
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Search PubMed for drug interaction literature, fetch abstracts.
        Returns list of {pmid, title, abstract_snippet, year, source: 'literature'}.
        """
        # Build query: each drug as a [tiab] term, plus interaction keyword
        # Format: ("warfarin"[tiab] AND "fluconazole"[tiab]) AND interaction[tiab]
        drug_terms = " AND ".join(f'"{d}"[tiab]' for d in drugs[:3])
        query = f"({drug_terms}) AND interaction[tiab]"

        # Check cache
        cache_key = (
            "_".join(sorted(drugs[:2]))
            .replace(" ", "_")
            .replace("'", "")
        )
        cache_file = CACHE_DIR / f"{cache_key}.json"

        if cache_file.exists():
            logger.info(f"PubMed cache hit: {cache_key}")
            return json.loads(cache_file.read_text(encoding="utf-8"))

        try:
            async with httpx.AsyncClient() as client:
                # Search for PMIDs
                search_r = await client.get(
                    ESEARCH_URL,
                    params={
                        "db": "pubmed",
                        "term": query,
                        "retmax": max_results,
                        "sort": "relevance",
                        "retmode": "json",
                    },
                    timeout=15.0,
                )
                search_r.raise_for_status()

                pmids = (
                    search_r.json()
                    .get("esearchresult", {})
                    .get("idlist", [])
                )

                if not pmids:
                    return []

                # Fetch abstracts
                fetch_r = await client.get(
                    EFETCH_URL,
                    params={
                        "db": "pubmed",
                        "id": ",".join(pmids),
                        "rettype": "abstract",
                        "retmode": "text",
                    },
                    timeout=15.0,
                )
                fetch_r.raise_for_status()

                raw_text = fetch_r.text
                results = self._parse_abstracts(pmids, raw_text)

                # Cache result
                cache_file.write_text(
                    json.dumps(results, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

                return results

        except Exception as e:
            logger.warning(f"PubMed fetch failed: {e}")
            return []

    def _parse_abstracts(self, pmids: list[str], raw_text: str) -> list[dict[str, Any]]:
        """
        Parse PubMed plain-text output into structured snippets.
        Extracts title and first 3 sentences of abstract.
        """
        results: list[dict[str, Any]] = []

        # Split by record separator (efetch text often uses blank blocks)
        records = raw_text.split("\n\n\n")

        for i, record in enumerate(records[: len(pmids)]):
            lines = [l.strip() for l in record.split("\n") if l.strip()]
            if not lines:
                continue

            title = lines[0] if lines else "Unknown title"

            # Find abstract — look for line after "Abstract" or just body text
            abstract_lines: list[str] = []
            in_abstract = False

            for line in lines[1:]:
                if line.lower().startswith("abstract"):
                    in_abstract = True
                    continue

                if in_abstract or (len(line) > 50 and not line[:1].isdigit()):
                    abstract_lines.append(line)

                if len(abstract_lines) >= 5:
                    break

            abstract_text = " ".join(abstract_lines)

            # Take first 3 sentences
            sentences = re.split(r"(?<=[.!?])\s+", abstract_text)
            snippet = " ".join(sentences[:3]).strip()

            # Try to extract year
            year_match = re.search(r"\b(19|20)\d{2}\b", record)
            year = year_match.group(0) if year_match else "Unknown"

            pmid = pmids[i] if i < len(pmids) else "unknown"

            results.append(
                {
                    "pmid": pmid,
                    "title": title[:200],
                    "abstract_snippet": snippet[:500],
                    "year": year,
                    "source": "literature",
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                }
            )

        return results

    async def pre_cache_demo_cases(self) -> None:
        """Pre-download and cache PubMed abstracts for all three demo cases."""
        cases = [
            {
                "drugs": ["warfarin", "fluconazole"],
                "symptom": "bruising bleeding coagulation",
            },
            {
                "drugs": ["metformin", "st. john's wort"],
                "symptom": "hyperglycemia blood sugar diabetes",
            },
            {
                "drugs": ["tramadol", "sertraline"],
                "symptom": "fever confusion muscle rigidity serotonin",
            },
        ]

        for case in cases:
            result = await self.search_and_fetch(
                drugs=case["drugs"],
                symptom_text=case["symptom"],
                max_results=5,
            )
            print(f"Cached {len(result)} PubMed records for {case['drugs']}")


pubmed_client = PubMedClient()