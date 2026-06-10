"""Pydantic schemas for API request and response validation."""

from datetime import datetime
from pydantic import BaseModel, Field


class CompanyBase(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")
    name: str = Field(..., description="Full company name")
    sector: str | None = Field(None)
    exchange: str | None = Field(None)
    is_sp500: bool = Field(False)


class CompanyCreate(CompanyBase):
    cik_number: str | None = Field(None)


class CompanyResponse(CompanyBase):
    id: int
    cik_number: str | None
    ingestion_status: str
    transcript_count: int = 0
    created_at: datetime
    model_config = {"from_attributes": True}


class CompanySearchResult(BaseModel):
    name: str
    ticker: str
    cik_number: str
    exchange: str | None = None
    already_loaded: bool = False


class TranscriptResponse(BaseModel):
    id: int
    company_ticker: str
    company_name: str
    quarter: str
    year: int
    filing_date: str | None
    speaker_count: int
    chunk_count: int
    model_config = {"from_attributes": True}


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3)
    company_tickers: list[str] | None = Field(None)
    quarters: list[str] | None = Field(None)
    years: list[int] | None = Field(None)
    section_type: str | None = Field(None)
    speaker_roles: list[str] | None = Field(None)
    enable_temporal_comparison: bool = Field(False)
    enable_sentiment: bool = Field(False)
    top_k: int = Field(10, ge=1, le=50)


class Citation(BaseModel):
    company: str
    ticker: str
    quarter: str
    year: int
    speaker: str
    speaker_role: str
    section: str
    excerpt: str
    relevance_score: float


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    query_time_ms: int
    chunks_retrieved: int
    companies_searched: list[str]


class SentimentDataPoint(BaseModel):
    quarter: str
    year: int
    score: float = Field(..., ge=-1.0, le=1.0)
    label: str
    summary: str


class SentimentResponse(BaseModel):
    company: str
    ticker: str
    data_points: list[SentimentDataPoint]
    overall_trend: str
    analysis: str


class StatsResponse(BaseModel):
    total_transcripts: int
    total_companies: int
    total_chunks: int
    quarters_covered: int
    sp500_companies: int
    other_companies: int
    oldest_quarter: str | None
    newest_quarter: str | None
