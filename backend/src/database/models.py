"""
Database models for the Earnings Call Analyzer.

Three core tables:
    - companies: Company metadata (ticker, CIK, sector)
    - transcripts: Individual earnings call documents
    - chunks: Speaker-turn chunks with vector embeddings
"""

import enum
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

from src.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    pass


class SectionType(str, enum.Enum):
    PREPARED_REMARKS = "prepared_remarks"
    QA = "qa"
    UNKNOWN = "unknown"


class SpeakerRole(str, enum.Enum):
    CEO = "ceo"
    CFO = "cfo"
    COO = "coo"
    CTO = "cto"
    EXECUTIVE = "executive"
    ANALYST = "analyst"
    OPERATOR = "operator"
    UNKNOWN = "unknown"


class IngestionStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cik_number: Mapped[str] = mapped_column(String(20), nullable=True)
    sector: Mapped[str] = mapped_column(String(100), nullable=True)
    exchange: Mapped[str] = mapped_column(String(20), nullable=True)
    is_sp500: Mapped[bool] = mapped_column(default=False)
    ingestion_status: Mapped[IngestionStatus] = mapped_column(
        Enum(IngestionStatus), default=IngestionStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    transcripts: Mapped[list["Transcript"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Company {self.ticker}: {self.name}>"


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    quarter: Mapped[str] = mapped_column(String(5), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    filing_date: Mapped[str] = mapped_column(String(20), nullable=True)
    filing_url: Mapped[str] = mapped_column(Text, nullable=True)
    filing_type: Mapped[str] = mapped_column(String(20), nullable=True)
    raw_content: Mapped[str] = mapped_column(Text, nullable=True)
    parsed_content: Mapped[str] = mapped_column(Text, nullable=True)
    speaker_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    company: Mapped["Company"] = relationship(back_populates="transcripts")
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="transcript", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_transcript_company_quarter", "company_id", "year", "quarter"),
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transcript_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    speaker_name: Mapped[str] = mapped_column(String(255), nullable=True)
    speaker_role: Mapped[SpeakerRole] = mapped_column(
        Enum(SpeakerRole), default=SpeakerRole.UNKNOWN
    )
    section_type: Mapped[SectionType] = mapped_column(
        Enum(SectionType), default=SectionType.UNKNOWN
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dimension), nullable=True
    )
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    transcript: Mapped["Transcript"] = relationship(back_populates="chunks")

    __table_args__ = (
        Index("idx_chunk_transcript", "transcript_id"),
        Index("idx_chunk_speaker_role", "speaker_role"),
        Index("idx_chunk_section_type", "section_type"),
    )
