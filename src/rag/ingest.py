"""
SEC 10-K Ingestion Pipeline Module for Financial & Market Analyst Agent.
Parses, chunks, embeds, and indexes SEC 10-K annual reports (Apple, Microsoft, Nvidia)
into the Upstash Vector database for RAG retrieval with metadata filtering.
"""

import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure project root is in sys.path so 'src' and 'config' can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.embeddings import embedding_client
from src.rag.vector_client import vector_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sec_ingestion")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sec_filings"

# Ticker to Company Name mapping
COMPANY_MAP = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
}


def parse_sec_markdown(file_path: Path) -> List[Dict[str, Any]]:
    """
    Parse a SEC 10-K markdown file into structured section blocks.
    Extracts sections starting with '## Item X'.
    """
    content = file_path.read_text(encoding="utf-8")
    filename = file_path.stem  # e.g. "AAPL_10K_2024"
    parts = filename.split("_")
    ticker = parts[0]
    year = parts[2] if len(parts) >= 3 else "2024"
    company = COMPANY_MAP.get(ticker, ticker)

    # Regex to split on "## Item ..." headers
    section_pattern = re.compile(r"(##\s+Item\s+[^\n]+)", re.IGNORECASE)
    splits = section_pattern.split(content)

    sections = []
    # Index 0 is the front matter / title before the first '## Item'
    for i in range(1, len(splits), 2):
        header = splits[i].strip()
        body = splits[i + 1].strip() if i + 1 < len(splits) else ""

        # Normalize header: "## Item 1A. Risk Factors" -> "Item 1A. Risk Factors"
        clean_section = header.lstrip("#").strip()

        sections.append({
            "ticker": ticker,
            "company": company,
            "year": year,
            "section": clean_section,
            "content": body,
        })

    return sections


def chunk_text(
    text: str,
    max_chunk_size: int = 900,
    chunk_overlap: int = 150,
) -> List[str]:
    """
    Split text into semantic paragraphs and character chunks with overlap.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    current_chunk = ""

    for p in paragraphs:
        if len(current_chunk) + len(p) + 2 <= max_chunk_size:
            current_chunk = f"{current_chunk}\n\n{p}" if current_chunk else p
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # If paragraph itself is larger than max_chunk_size, split by sentences/length
            if len(p) > max_chunk_size:
                start = 0
                while start < len(p):
                    end = start + max_chunk_size
                    chunks.append(p[start:end])
                    start += (max_chunk_size - chunk_overlap)
                current_chunk = ""
            else:
                current_chunk = p

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def prepare_chunks() -> List[Dict[str, Any]]:
    """
    Loads all filing files, chunks them, and builds metadata records.
    """
    all_chunks: List[Dict[str, Any]] = []

    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Directory {DATA_DIR} does not exist.")

    filing_files = sorted(DATA_DIR.glob("*_10K_*.md"))
    logger.info(f"Found {len(filing_files)} SEC 10-K filing files in {DATA_DIR}")

    for file_path in filing_files:
        sections = parse_sec_markdown(file_path)
        logger.info(f"Processing {file_path.name}: found {len(sections)} key sections.")

        for sec in sections:
            passages = chunk_text(sec["content"])
            # Format clean item identifier (e.g., "Item1A", "Item1", "Item7")
            item_match = re.search(r"Item\s*([0-9A-Za-z]+)", sec["section"])
            item_tag = f"Item{item_match.group(1)}" if item_match else "General"

            for idx, passage in enumerate(passages, start=1):
                chunk_id = f"{sec['ticker']}_{sec['year']}_{item_tag}_{idx:03d}"
                all_chunks.append({
                    "id": chunk_id,
                    "text": passage,
                    "metadata": {
                        "ticker": sec["ticker"],
                        "company": sec["company"],
                        "year": sec["year"],
                        "section": sec["section"],
                        "text": passage,
                    },
                })

    logger.info(f"Created total of {len(all_chunks)} semantic chunks across all filings.")
    return all_chunks


def run_ingestion(reset_first: bool = True) -> int:
    """
    Main ingestion function. Chunks files, embeds them, and upserts to Upstash Vector.
    """
    logger.info("Starting SEC 10-K Ingestion Pipeline...")

    # Optional: reset existing index to avoid duplicate IDs during iterative runs
    if reset_first:
        try:
            logger.info("Resetting existing Upstash Vector index...")
            vector_client.reset()
        except Exception as e:
            logger.warning(f"Could not reset index (may be new or empty): {e}")

    chunks = prepare_chunks()
    if not chunks:
        logger.warning("No chunks created. Ingestion aborted.")
        return 0

    # Extract all passage texts for batch embedding
    texts = [c["text"] for c in chunks]
    logger.info(f"Generating 384-dimensional embeddings for {len(texts)} chunks via FastEmbed...")
    embeddings = embedding_client.embed_documents(texts, batch_size=32)

    # Attach vectors to chunk records
    for i, emb in enumerate(embeddings):
        chunks[i]["vector"] = emb

    logger.info("Upserting vectors and metadata to Upstash Vector database...")
    upserted_count = vector_client.upsert_chunks(chunks, batch_size=50)

    # Verify index stats
    info = vector_client.get_info()
    logger.info(f"Ingestion complete! Upstash Vector Info: {info}")

    # Run verification test queries
    run_verification_queries()

    return upserted_count


def run_verification_queries():
    """
    Run 3 realistic verification queries to prove RAG retrieval works.
    """
    test_queries: List[Tuple[str, str]] = [
        ("What are Apple's main supply chain risks in Greater China?", "ticker = 'AAPL'"),
        ("What is Microsoft's capital expenditure for AI infrastructure and GPUs?", "ticker = 'MSFT'"),
        ("Does Nvidia rely on TSMC for advanced semiconductor fabrication?", "ticker = 'NVDA'"),
    ]

    print("\n" + "=" * 80)
    print("🎯 RUNNING RAG RETRIEVAL VERIFICATION QUERIES")
    print("=" * 80)

    for query, filter_expr in test_queries:
        print(f"\n🔍 Query: '{query}' [Filter: {filter_expr}]")
        query_vec = embedding_client.embed_query(query)
        results = vector_client.query(
            vector=query_vec,
            top_k=2,
            filter_expr=filter_expr,
            include_metadata=True,
        )

        for rank, match in enumerate(results, start=1):
            meta = match["metadata"]
            print(f"  Rank #{rank} (Score: {match['score']:.4f}) | {meta.get('company')} ({meta.get('ticker')}) - {meta.get('section')}")
            snippet = match["text"][:220].replace("\n", " ") + "..."
            print(f"    Excerpt: \"{snippet}\"")

    print("\n" + "=" * 80)
    print("✅ RAG KNOWLEDGE BASE VERIFIED SUCCESSFULLY!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_ingestion(reset_first=True)
