"""Research / RAG service — Watsonx-powered retrieval-augmented generation."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

from models import ResearchAnswer, ResearchQuery, ResearchSource

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BASE_DIR = Path(__file__).resolve().parent.parent
CORPUS_DIR = _BASE_DIR / "corpus"
CHROMA_DIR = _BASE_DIR / "chroma_db"

# ---------------------------------------------------------------------------
# Lazy-initialised singletons
# ---------------------------------------------------------------------------
_vectorstore: Optional[object] = None   # langchain_chroma.Chroma
_index_built: bool = False              # True once the index has been populated


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_doc_id(source: str, chunk_index: int) -> str:
    """Stable, short document ID from source path + chunk position."""
    digest = hashlib.md5(f"{source}:{chunk_index}".encode()).hexdigest()[:8]
    return f"{Path(source).stem[:20]}-{digest}"


def _clamp_score(raw: float) -> float:
    """Chroma returns L2 distance (lower = better). Convert to [0, 1] similarity."""
    # Empirically, distances > 2.0 are essentially unrelated; clamp to [0, 1].
    similarity = max(0.0, 1.0 - raw / 2.0)
    return round(min(similarity, 1.0), 4)


def _load_corpus() -> list:
    """
    Load all PDFs and .txt files from CORPUS_DIR.
    Returns a flat list of LangChain Document objects.
    """
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain_community")
        from langchain_community.document_loaders import PyPDFLoader, TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    if not CORPUS_DIR.exists() or not any(CORPUS_DIR.iterdir()):
        logger.warning("Corpus directory '%s' is missing or empty — no documents loaded.", CORPUS_DIR)
        return []

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    all_docs: list = []

    for path in sorted(CORPUS_DIR.iterdir()):
        if path.suffix.lower() == ".pdf":
            loader = PyPDFLoader(str(path))
        elif path.suffix.lower() == ".txt":
            loader = TextLoader(str(path), encoding="utf-8")
        else:
            continue

        try:
            raw_docs = loader.load()
            chunks = splitter.split_documents(raw_docs)
            # Tag each chunk with a stable doc_id and a human-readable title
            for idx, chunk in enumerate(chunks):
                chunk.metadata.setdefault("source", str(path))
                chunk.metadata["doc_id"] = _make_doc_id(str(path), idx)
                chunk.metadata["title"] = path.stem.replace("_", " ").replace("-", " ").title()
                chunk.metadata["chunk_index"] = idx
            all_docs.extend(chunks)
            logger.info("Loaded '%s': %d chunks", path.name, len(chunks))
        except Exception as exc:
            logger.warning("Failed to load '%s': %s", path.name, exc)

    logger.info("Corpus loaded: %d total chunks from %s", len(all_docs), CORPUS_DIR)
    return all_docs


def _build_embeddings():
    """Instantiate WatsonxEmbeddings from environment variables."""
    from langchain_ibm import WatsonxEmbeddings
    from ibm_watsonx_ai.foundation_models.utils.enums import EmbeddingTypes

    api_key = os.environ.get("WATSONX_APIKEY", "")
    project_id = os.environ.get("WATSONX_PROJECT_ID", "")
    url = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

    if not api_key or not project_id:
        raise EnvironmentError(
            "WATSONX_APIKEY and WATSONX_PROJECT_ID must be set to use the RAG pipeline."
        )

    return WatsonxEmbeddings(
        model_id="ibm/slate-125m-english-rtrvr-v2",
        url=url,
        apikey=api_key,
        project_id=project_id,
    )


@lru_cache(maxsize=1)
def _get_vectorstore():
    """
    Build (or reopen) the persistent Chroma collection.
    Called lazily on first query; result is cached for the process lifetime.
    Raises if Watsonx credentials are missing.
    """
    from langchain_chroma import Chroma

    global _index_built

    embeddings = _build_embeddings()
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    # Check whether the collection already has documents
    vs = Chroma(
        collection_name="astraops_corpus",
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
    )

    existing_count = vs._collection.count()  # type: ignore[attr-defined]
    if existing_count == 0:
        logger.info("Chroma collection empty — building index from corpus …")
        docs = _load_corpus()
        if docs:
            vs.add_documents(docs)
            logger.info("Index built: %d chunks stored in Chroma.", len(docs))
        else:
            logger.warning("No documents found; index remains empty.")
    else:
        logger.info("Reusing existing Chroma index (%d chunks).", existing_count)

    _index_built = True
    return vs


def _build_llm():
    """Instantiate ChatWatsonx with Granite 4."""
    from langchain_ibm import ChatWatsonx

    api_key = os.environ.get("WATSONX_APIKEY", "")
    project_id = os.environ.get("WATSONX_PROJECT_ID", "")
    url = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

    return ChatWatsonx(
        model_id="ibm/granite-4-h-small",
        url=url,
        apikey=api_key,
        project_id=project_id,
        params={
            "max_new_tokens": 1024,
            "temperature": 0.1,
        },
    )


_SYSTEM_PROMPT = """\
You are AstraOps Research Assistant, an expert in space missions, satellite operations, \
and space weather. Answer the user's question using ONLY the retrieved context passages \
provided below. For each fact you state, cite the source filename in square brackets, \
e.g. [orbital_mechanics.pdf]. If the retrieved context does not contain enough information \
to answer the question, respond with: "I don't have enough information in the indexed \
documents to answer this question." Do not invent facts or use knowledge outside the \
provided context.\
"""


def _build_prompt(question: str, chunks: list) -> str:
    context_blocks = []
    for i, (doc, _score) in enumerate(chunks, 1):
        source_name = Path(doc.metadata.get("source", "unknown")).name
        context_blocks.append(f"[{i}] Source: {source_name}\n{doc.page_content.strip()}")
    context_text = "\n\n".join(context_blocks)
    return (
        f"{_SYSTEM_PROMPT}\n\n"
        f"### Retrieved Context\n\n{context_text}\n\n"
        f"### Question\n\n{question}\n\n"
        f"### Answer"
    )


def _docs_to_sources(chunks: list) -> list[ResearchSource]:
    sources: list[ResearchSource] = []
    seen: set[str] = set()
    for doc, raw_score in chunks:
        doc_id = doc.metadata.get("doc_id", "unknown")
        if doc_id in seen:
            continue
        seen.add(doc_id)
        sources.append(
            ResearchSource(
                document_id=doc_id,
                title=doc.metadata.get("title", Path(doc.metadata.get("source", "")).stem),
                excerpt=doc.page_content[:300].strip(),
                score=_clamp_score(raw_score),
            )
        )
    return sources


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def answer_question(query: ResearchQuery) -> ResearchAnswer:
    """
    Retrieve top-k relevant chunks from the local corpus and generate an answer
    with IBM Granite 4 via Watsonx. Builds and persists the Chroma index on first
    call; subsequent calls reuse the cached collection.
    """
    logger.info("Research query: '%s'", query.question[:120])

    # ── 1. Validate credentials are present before doing any work ────────────
    if not os.environ.get("WATSONX_APIKEY") or not os.environ.get("WATSONX_PROJECT_ID"):
        logger.warning("Watsonx credentials missing — returning configuration notice.")
        return ResearchAnswer(
            question=query.question,
            answer=(
                "The RAG pipeline is not configured. "
                "Set WATSONX_APIKEY and WATSONX_PROJECT_ID in your environment "
                "to enable question answering."
            ),
            sources=[],
            model_used="unavailable",
            answered_at=datetime.now(timezone.utc),
        )

    # ── 2. Initialise / reuse vector store ───────────────────────────────────
    try:
        vs = await asyncio.to_thread(_get_vectorstore)
    except EnvironmentError as exc:
        logger.error("Vectorstore init failed: %s", exc)
        return ResearchAnswer(
            question=query.question,
            answer=str(exc),
            sources=[],
            model_used="unavailable",
            answered_at=datetime.now(timezone.utc),
        )
    except Exception as exc:
        logger.error("Unexpected error initialising vectorstore: %s", exc)
        return ResearchAnswer(
            question=query.question,
            answer="Failed to initialise the vector index. Check server logs for details.",
            sources=[],
            model_used="unavailable",
            answered_at=datetime.now(timezone.utc),
        )

    # ── 3. Check corpus is not empty ─────────────────────────────────────────
    try:
        doc_count = vs._collection.count()  # type: ignore[attr-defined]
    except Exception:
        doc_count = 0

    if doc_count == 0:
        logger.warning("Corpus is empty — no documents are indexed.")
        return ResearchAnswer(
            question=query.question,
            answer=(
                "No documents are currently indexed. "
                f"Add PDF or text files to the '{CORPUS_DIR.name}/' directory "
                "and restart the server to build the search index."
            ),
            sources=[],
            model_used="unavailable",
            answered_at=datetime.now(timezone.utc),
        )

    # ── 4. Similarity search ──────────────────────────────────────────────────
    try:
        search_kwargs: dict = {"k": query.top_k}
        if query.context_filter:
            # Use Chroma metadata filtering when a domain filter is provided
            search_kwargs["filter"] = {"domain": query.context_filter}

        chunks_with_scores = await asyncio.to_thread(
            vs.similarity_search_with_score,
            query.question,
            **search_kwargs,
        )
    except Exception as exc:
        logger.error("Similarity search failed: %s", exc)
        return ResearchAnswer(
            question=query.question,
            answer="Retrieval failed. Check server logs for details.",
            sources=[],
            model_used="unavailable",
            answered_at=datetime.now(timezone.utc),
        )

    sources = _docs_to_sources(chunks_with_scores)

    # ── 5. Generate answer ────────────────────────────────────────────────────
    from langchain_core.messages import HumanMessage

    answer_text = None
    last_exc = None
    for attempt in range(3):
        try:
            llm = _build_llm()
            prompt = _build_prompt(query.question, chunks_with_scores)
            response = await asyncio.to_thread(llm.invoke, [HumanMessage(content=prompt)])
            answer_text = response.content.strip()
            break
        except Exception as exc:
            last_exc = exc
            text = str(exc)
            transient = ("429" in text or "consumption_limit" in text
                         or "timeout" in text.lower())
            if transient and attempt < 2:
                wait = 2 ** attempt
                logger.warning("Granite busy (attempt %d/3); retrying in %ds",
                               attempt + 1, wait)
                await asyncio.sleep(wait)
                continue
            logger.error("LLM generation failed: %s", exc)
            break

    if answer_text is None:
        text = str(last_exc)
        if "429" in text or "consumption_limit" in text:
            answer_text = (
                "The watsonx free tier hit its concurrent-request limit for this model. "
                "The passages below are the sources this answer would have been drawn "
                "from — ask again in a few seconds for the written answer."
            )
        else:
            answer_text = (
                "Answer generation is unavailable right now. "
                "The retrieved sources below may still be helpful."
            )

    return ResearchAnswer(
        question=query.question,
        answer=answer_text,
        sources=sources,
        model_used="ibm/granite-4-h-small",
        answered_at=datetime.now(timezone.utc),
    )
