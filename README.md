# Earnings Call Analyzer

A RAG-based financial analysis tool that enables natural language queries across SEC EDGAR earnings call transcripts, with cited answers, temporal comparison, and multi-quarter sentiment analysis.

## Features

- **Natural language queries** across 50+ earnings call transcripts from S&P 500 companies
- **Dynamic company ingestion** for any SEC-filing company via EDGAR API
- **Source-grounded citations** linking every answer to the specific speaker, quarter, and section
- **Temporal comparison** tracking how management narratives evolve across 8+ quarters
- **Multi-quarter sentiment analysis** detecting shifts in executive tone and confidence
- **Cross-company analysis** comparing strategies and performance across multiple companies
- **Voice input** for hands-free query submission
- **Sub-5 second query response times** via optimized hybrid retrieval

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI |
| Vector Database | PostgreSQL + pgvector |
| LLM | Claude Opus 4.6 (Anthropic API) |
| Embeddings | all-MiniLM-L6-v2 (sentence-transformers) |
| Frontend | React, Vite |
| Containerization | Docker, Docker Compose |

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/earnings-call-analyzer.git
cd earnings-call-analyzer

# Set up environment variables
cp .env.example .env
# Edit .env with your Anthropic API key and EDGAR user agent

# Start the database
docker-compose up -d

# Install backend dependencies
cd backend
poetry install

# Create database tables
cd ..
python -m scripts.setup_db

# Seed the database with sample transcripts
python -m scripts.generate_seed_data
# Then seed via the API: POST /api/companies/seed

# Start the backend
cd backend
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, start the frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## Architecture

```
User Query (text or voice)
        |
        v
   FastAPI Backend
        |
        v
  Hybrid Retrieval (pgvector cosine similarity + SQL metadata filtering)
        |
        v
  Context Assembly (relevant chunks with metadata)
        |
        v
  Claude Opus 4.6 (answer generation with citations)
        |
        v
  Structured Response (answer + citations + sentiment)
```

## Project Structure

```
earnings-call-analyzer/
├── backend/
│   ├── src/
│   │   ├── api/            # FastAPI routes and schemas
│   │   ├── ingestion/      # SEC EDGAR client and transcript parser
│   │   ├── chunking/       # Speaker-aware transcript chunking
│   │   ├── embedding/      # Sentence-transformers embedding generation
│   │   ├── retrieval/      # Hybrid vector + metadata search
│   │   ├── generation/     # Claude API integration and prompt templates
│   │   ├── analysis/       # Sentiment analysis and temporal comparison
│   │   ├── database/       # SQLAlchemy models and connection
│   │   └── config.py       # Environment-based configuration
│   ├── tests/
│   └── pyproject.toml
├── frontend/               # React + Vite application
├── scripts/                # Database setup and data seeding
├── data/                   # Sample transcript data
├── docker-compose.yml      # PostgreSQL + pgvector container
└── .env.example
```

## License

MIT
