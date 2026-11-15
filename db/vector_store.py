# db/vector_store.py
from pathlib import Path
import chromadb

CHROMA_DIR = Path(__file__).resolve().parent.parent / "chroma_data"


def get_vector_collection():
    """Initializes local ChromaDB using built-in CPU ONNX embeddings."""
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(name="outreach_archetypes")

    if collection.count() == 0:
        documents = [
            (
                "High-throughput backend engineering with Python, FastAPI, and asynchronous queues. "
                "Designing fault-tolerant RESTful APIs, SQL optimization, Docker containerization, and microservices architecture.",
                {
                    "subject": "Application: {job_title} - Backend & Distributed Systems",
                    "pitch": "I specialize in designing high-throughput Python backends using FastAPI, async worker queues, and SQL performance tuning. I build resilient, low-latency microservices engineered for high concurrency."
                },
                "backend_engineering"
            ),
            (
                "Agentic AI, LLM orchestration, LangGraph, LangChain, stateful memory checkpoints, "
                "autonomous multi-agent workflows, tool-calling agents, human-in-the-loop review systems, and prompt engineering.",
                {
                    "subject": "Application: {job_title} - Agentic AI & Systems",
                    "pitch": "I architect production-ready Agentic AI systems and autonomous workflows using LangGraph and LangChain. I focus on stateful checkpointing, human-in-the-loop decision boundaries, and structured LLM tool integration."
                },
                "agentic_ai"
            ),
            (
                "Web automation, Playwright, Selenium, BeautifulSoup, crawling, ETL data pipelines, "
                "handling client-rendered SPAs, bot detection evasion, and structured data ingestion engines.",
                {
                    "subject": "Application: {job_title} - Data Automation & Scraping",
                    "pitch": "I have extensive experience architecting automated scraping engines and headless browser workflows with Playwright and BeautifulSoup, capable of bypassing client-side hydration barriers to build reliable ETL ingestion pipelines."
                },
                "scraping_automation"
            )
        ]

        collection.add(
            documents=[doc[0] for doc in documents],
            metadatas=[doc[1] for doc in documents],
            ids=[doc[2] for doc in documents]
        )

    return collection


def query_best_matching_pitch(job_description_text: str) -> dict:
    """
    Runs semantic similarity against the job description using local embeddings.
    Zero external API calls.
    """
    collection = get_vector_collection()
    results = collection.query(
        query_texts=[job_description_text[:2500]],
        n_results=1
    )

    if results and results["metadatas"] and len(results["metadatas"][0]) > 0:
        best_match = results["metadatas"][0][0]
        category_id = results["ids"][0][0]
        return {
            "category": category_id,
            "subject": best_match["subject"],
            "pitch": best_match["pitch"]
        }

    return {
        "category": "default",
        "subject": "Application: {job_title}",
        "pitch": "I am an experienced Python Developer specializing in backend scalability, automation, and AI-driven platforms."
    }