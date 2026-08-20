"""Research / RAG service — placeholder for vector-search Q&A."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from models import ResearchAnswer, ResearchQuery, ResearchSource

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Placeholder implementation
#
# Replace the body of `answer_question` with a real RAG pipeline, e.g.:
#   1. Embed `query.question` with an embedding model (OpenAI, sentence-transformers…)
#   2. Query a vector store (Pinecone, pgvector, Chroma…) for top-k chunks
#   3. Build a prompt with retrieved context and call an LLM
#   4. Return the answer + source attributions
# ---------------------------------------------------------------------------

_PLACEHOLDER_SOURCES: list[ResearchSource] = [
    ResearchSource(
        document_id="doc-001",
        title="Introduction to Two-Line Element Sets",
        excerpt=(
            "TLE (Two-Line Element) sets encode the orbital parameters of an Earth-orbiting "
            "object at a specific epoch and are used by SGP4/SDP4 propagators."
        ),
        score=0.91,
    ),
    ResearchSource(
        document_id="doc-002",
        title="NASA DONKI Space Weather Glossary",
        excerpt=(
            "A coronal mass ejection (CME) is a significant release of plasma and magnetic field "
            "from the solar corona. They can cause geomagnetic storms when directed at Earth."
        ),
        score=0.85,
    ),
]


async def answer_question(query: ResearchQuery) -> ResearchAnswer:
    """
    Placeholder RAG endpoint.

    Returns a canned response indicating the pipeline is not yet connected.
    Replace the internals with real retrieval + generation logic.
    """
    logger.info(
        "Research query received (RAG not yet connected): '%s'", query.question[:80]
    )

    answer_text = (
        "The RAG pipeline is not yet configured. "
        "Connect a vector store and an LLM in services/research.py to enable "
        "question answering over AstraOps mission intelligence documents."
    )

    return ResearchAnswer(
        question=query.question,
        answer=answer_text,
        sources=_PLACEHOLDER_SOURCES[: query.top_k],
        model_used="placeholder",
        answered_at=datetime.now(timezone.utc),
    )
