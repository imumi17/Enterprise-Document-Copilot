from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import structlog
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database.models import DocumentChunk, SourceDocument
from ingest.chunking import chunk_markdown
from ingest.embeddings import embed_texts
from ingest.html_to_markdown import html_to_markdown

logger = structlog.get_logger(__name__)

COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
}

DEFAULT_MANIFEST = (
    Path(__file__).resolve().parents[2] / "data" / "downloads" / "manifest.json"
)


def get_sync_database_url() -> str:
    url = settings.database_url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def parse_filing_date(value: str) -> date:
    return date.fromisoformat(value)


def load_existing_accessions(session: Session) -> set[str]:
    rows = session.scalars(select(SourceDocument.accession_number)).all()
    return set(rows)


def ingest_manifest(
    manifest_path: Path,
    downloads_root: Path,
    limit: int | None,
    skip_existing: bool,
) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    filings = manifest.get("filings", [])
    if limit is not None:
        filings = filings[:limit]

    engine = create_engine(get_sync_database_url())
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    documents_written = 0
    chunks_written = 0
    skipped = 0

    with session_factory() as session:
        existing_accessions = load_existing_accessions(session) if skip_existing else set()

        for filing in filings:
            accession_number = filing["accession_number"]
            if skip_existing and accession_number in existing_accessions:
                skipped += 1
                logger.info(
                    "skipped_existing_filing",
                    ticker=filing["ticker"],
                    accession=accession_number,
                )
                continue

            written = ingest_filing(session, filing, downloads_root)
            documents_written += 1
            chunks_written += written
            existing_accessions.add(accession_number)
            logger.info(
                "ingested_filing",
                ticker=filing["ticker"],
                accession=accession_number,
                chunks=written,
            )

    return {
        "documents_written": documents_written,
        "chunks_written": chunks_written,
        "skipped": skipped,
    }


def ingest_filing(session: Session, filing: dict, downloads_root: Path) -> int:
    local_path = downloads_root / filing["local_path"]
    markdown = html_to_markdown(local_path.read_bytes())

    ticker = filing["ticker"]
    accession_number = filing["accession_number"]
    fiscal_year = int((filing.get("report_date") or filing["filing_date"])[:4])
    filing_date = parse_filing_date(filing["filing_date"])

    base_metadata = {
        "ticker": ticker,
        "company_name": COMPANY_NAMES.get(ticker, ticker),
        "filing_type": filing["form"],
        "filing_date": filing["filing_date"],
        "fiscal_year": fiscal_year,
        "accession_number": accession_number,
        "source_url": filing["source_url"],
        "cik": filing.get("cik"),
        "primary_document": filing.get("primary_document"),
    }

    text_chunks = chunk_markdown(markdown, base_metadata)
    embeddings = embed_texts([chunk.text for chunk in text_chunks])

    document = session.scalar(
        select(SourceDocument).where(SourceDocument.accession_number == accession_number)
    )
    if document is None:
        document = SourceDocument(
            ticker=ticker,
            company_name=COMPANY_NAMES.get(ticker, ticker),
            filing_type=filing["form"],
            filing_date=filing_date,
            fiscal_year=fiscal_year,
            accession_number=accession_number,
            source_url=filing["source_url"],
            markdown_content=markdown,
            metadata_=base_metadata,
        )
        session.add(document)
        session.flush()
    else:
        document.markdown_content = markdown
        document.metadata_ = base_metadata
        session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
        )
        session.flush()

    for chunk, embedding in zip(text_chunks, embeddings, strict=True):
        session.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.text,
                page=None,
                section=chunk.section,
                token_count=chunk.token_count,
                metadata_=chunk.metadata,
                embedding=embedding,
            )
        )

    session.commit()
    return len(text_chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest SEC filings into Supabase")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to manifest.json from data/download.py",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only ingest the first N filings (for smoke tests)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip filings whose accession number is already in source_documents",
    )
    args = parser.parse_args()

    downloads_root = args.manifest.parent
    result = ingest_manifest(
        args.manifest,
        downloads_root,
        args.limit,
        skip_existing=args.skip_existing,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
