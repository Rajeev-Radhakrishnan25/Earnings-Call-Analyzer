"""
SEC EDGAR API client.

Handles all communication with the SEC EDGAR system:
    - Company lookup by ticker or name
    - Filing search for earnings call transcripts
    - Filing content download

SEC EDGAR requires a User-Agent header identifying who you are.
This is their fair-use policy for the free API. The header format
is: "CompanyOrAppName ContactEmail".

Rate limiting: EDGAR asks for no more than 10 requests per second.
This client enforces that with a simple async delay.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

EDGAR_BASE = "https://www.sec.gov"
EDGAR_DATA = "https://data.sec.gov"
EDGAR_EFTS = "https://efts.sec.gov/LATEST"

# Minimum delay between EDGAR requests (100ms = 10 req/sec max)
REQUEST_DELAY = 0.1


@dataclass
class EdgarCompany:
    """A company found in EDGAR's system."""

    name: str
    ticker: str
    cik: str
    exchange: str | None = None


@dataclass
class EdgarFiling:
    """Metadata for a single SEC filing."""

    accession_number: str
    form_type: str
    filing_date: str
    primary_document: str
    description: str = ""
    filing_url: str = ""


@dataclass
class EdgarSearchResult:
    """Result from EDGAR full-text search."""

    company_name: str
    cik: str
    accession_number: str
    form_type: str
    filing_date: str
    file_url: str
    description: str = ""
    matched_text: str = ""


class EdgarClient:
    """
    Async client for the SEC EDGAR API.

    Usage:
        async with EdgarClient() as client:
            companies = await client.search_company("Apple")
            filings = await client.find_transcript_filings(cik="0000320193")
            html = await client.download_filing(url)
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._last_request_time: float = 0
        self._company_tickers: dict[str, EdgarCompany] | None = None

    async def __aenter__(self) -> "EdgarClient":
        self._client = httpx.AsyncClient(
            headers={
                "User-Agent": settings.edgar_user_agent,
                "Accept-Encoding": "gzip, deflate",
            },
            timeout=30.0,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client:
            await self._client.aclose()

    async def _rate_limit(self) -> None:
        """Enforce EDGAR's rate limit of 10 requests per second."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        if elapsed < REQUEST_DELAY:
            await asyncio.sleep(REQUEST_DELAY - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    async def _get(self, url: str) -> httpx.Response:
        """Make a rate-limited GET request."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with EdgarClient()' context.")
        await self._rate_limit()
        logger.debug("EDGAR GET: %s", url)
        response = await self._client.get(url)
        response.raise_for_status()
        return response

    async def _load_company_tickers(self) -> dict[str, EdgarCompany]:
        """
        Load the master company-to-ticker mapping from EDGAR.

        This JSON file contains every company with a ticker symbol
        that has filed with the SEC. We cache it after first load.
        """
        if self._company_tickers is not None:
            return self._company_tickers

        url = f"{EDGAR_BASE}/files/company_tickers.json"
        response = await self._get(url)
        data = response.json()

        tickers: dict[str, EdgarCompany] = {}
        for entry in data.values():
            ticker = str(entry.get("ticker", "")).upper()
            if ticker:
                cik = str(entry.get("cik_str", ""))
                name = str(entry.get("title", ""))
                tickers[ticker] = EdgarCompany(
                    name=name,
                    ticker=ticker,
                    cik=cik.zfill(10),
                )

        self._company_tickers = tickers
        logger.info("Loaded %d company tickers from EDGAR", len(tickers))
        return tickers

    async def search_company(self, query: str) -> list[EdgarCompany]:
        """
        Search for a company by ticker symbol or name.

        First tries exact ticker match, then falls back to
        name-based search across the full company listing.

        Args:
            query: A ticker symbol (e.g. "AAPL") or partial company name

        Returns:
            List of matching EdgarCompany objects, up to 20 results
        """
        tickers = await self._load_company_tickers()
        query_upper = query.upper().strip()
        results: list[EdgarCompany] = []

        # Exact ticker match
        if query_upper in tickers:
            results.append(tickers[query_upper])

        # Fuzzy name search
        query_lower = query.lower()
        for company in tickers.values():
            if company in results:
                continue
            if (
                query_lower in company.name.lower()
                or query_lower in company.ticker.lower()
            ):
                results.append(company)
            if len(results) >= 20:
                break

        return results

    async def get_company_filings(
        self,
        cik: str,
        form_types: list[str] | None = None,
    ) -> list[EdgarFiling]:
        """
        Get all filings for a company by CIK number.

        Uses EDGAR's submissions API which returns filing history
        in reverse chronological order.

        Args:
            cik: SEC Central Index Key (zero-padded to 10 digits)
            form_types: Filter by form types (e.g. ["8-K", "6-K"])

        Returns:
            List of EdgarFiling objects
        """
        cik_padded = cik.zfill(10)
        url = f"{EDGAR_DATA}/submissions/CIK{cik_padded}.json"

        response = await self._get(url)
        data = response.json()

        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        descriptions = recent.get("primaryDocDescription", [])

        filings: list[EdgarFiling] = []
        for i in range(len(forms)):
            if form_types and forms[i] not in form_types:
                continue

            accession_clean = accessions[i].replace("-", "")
            filing_url = (
                f"{EDGAR_BASE}/Archives/edgar/data/{cik_padded}"
                f"/{accession_clean}/{primary_docs[i]}"
            )

            filings.append(
                EdgarFiling(
                    accession_number=accessions[i],
                    form_type=forms[i],
                    filing_date=dates[i],
                    primary_document=primary_docs[i],
                    description=descriptions[i] if i < len(descriptions) else "",
                    filing_url=filing_url,
                )
            )

        logger.info(
            "Found %d filings for CIK %s (filtered: %s)",
            len(filings), cik_padded, form_types,
        )
        return filings

    async def find_transcript_filings(
        self,
        cik: str,
        max_results: int = 20,
    ) -> list[EdgarSearchResult]:
        """
        Search for earnings call transcript filings for a specific company.

        Uses EDGAR's Full-Text Search System (EFTS) to find filings
        that contain earnings call language. Searches across 8-K and
        6-K filings (the common form types for earnings materials).

        Args:
            cik: SEC Central Index Key
            max_results: Maximum number of results to return

        Returns:
            List of EdgarSearchResult objects with filing URLs
        """
        search_terms = [
            '"earnings call transcript"',
            '"conference call transcript"',
            '"earnings conference call"',
        ]

        all_results: list[EdgarSearchResult] = []
        seen_accessions: set[str] = set()

        for term in search_terms:
            if len(all_results) >= max_results:
                break

            params = {
                "q": term,
                "dateRange": "custom",
                "startdt": "2022-01-01",
                "enddt": datetime.now().strftime("%Y-%m-%d"),
                "forms": "8-K,6-K",
                "from": "0",
                "size": str(min(max_results, 40)),
            }

            # Add entity filter if CIK is provided
            if cik:
                params["q"] = f'{term} AND entityCik:"{cik.lstrip("0")}"'

            try:
                url = f"{EDGAR_EFTS}/search-index"
                response = await self._get(f"{url}?{'&'.join(f'{k}={v}' for k, v in params.items())}")
                data = response.json()

                hits = data.get("hits", {}).get("hits", [])
                for hit in hits:
                    source = hit.get("_source", {})
                    accession = source.get("file_num", source.get("accession_no", ""))

                    if accession in seen_accessions:
                        continue
                    seen_accessions.add(accession)

                    file_url = source.get("file_url", "")
                    if not file_url and source.get("root_form_url"):
                        file_url = f"{EDGAR_BASE}{source['root_form_url']}"

                    all_results.append(
                        EdgarSearchResult(
                            company_name=source.get("entity_name", ""),
                            cik=source.get("entity_cik", cik),
                            accession_number=accession,
                            form_type=source.get("form_type", ""),
                            filing_date=source.get("file_date", ""),
                            file_url=file_url,
                            description=source.get("display_names", [""])[0]
                            if source.get("display_names")
                            else "",
                        )
                    )
            except httpx.HTTPStatusError as exc:
                logger.warning("EFTS search failed for term '%s': %s", term, exc)
                continue

        logger.info("Found %d transcript filings for CIK %s", len(all_results), cik)
        return all_results[:max_results]

    async def download_filing(self, url: str) -> str:
        """
        Download the raw HTML content of a filing.

        Args:
            url: Full URL to the filing document

        Returns:
            Raw HTML content as a string
        """
        response = await self._get(url)
        return response.text

    async def get_filing_documents(self, cik: str, accession_number: str) -> list[dict]:
        """
        Get the list of documents within a filing (index page).

        Filings often contain multiple documents. Earnings call
        transcripts are typically in EX-99.1 exhibits.

        Args:
            cik: Company CIK number
            accession_number: Filing accession number

        Returns:
            List of document metadata dicts with name, type, and URL
        """
        cik_padded = cik.zfill(10)
        accession_clean = accession_number.replace("-", "")
        url = f"{EDGAR_DATA}/submissions/{accession_clean}.json"

        try:
            response = await self._get(url)
            data = response.json()
        except (httpx.HTTPStatusError, Exception):
            # Fall back to the filing index page
            index_url = (
                f"{EDGAR_BASE}/Archives/edgar/data/{cik_padded}"
                f"/{accession_clean}/index.json"
            )
            response = await self._get(index_url)
            data = response.json()

        documents = []
        items = data.get("directory", {}).get("item", [])
        for item in items:
            name = item.get("name", "")
            doc_url = (
                f"{EDGAR_BASE}/Archives/edgar/data/{cik_padded}"
                f"/{accession_clean}/{name}"
            )
            documents.append({
                "name": name,
                "type": item.get("type", ""),
                "size": item.get("size", ""),
                "url": doc_url,
            })

        return documents
