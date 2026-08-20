"""Research router — /research (RAG Q&A placeholder)"""

from __future__ import annotations

from fastapi import APIRouter

from models import ResearchAnswer, ResearchQuery
from services.research import answer_question

router = APIRouter(prefix="/research", tags=["Research"])


@router.post(
    "/ask",
    response_model=ResearchAnswer,
    summary="Ask a question about space mission intelligence",
    description=(
        "Placeholder RAG endpoint. Submit a natural-language question and receive an "
        "answer grounded in AstraOps mission documents. "
        "**Connect a vector store and LLM in `services/research.py` to enable real answers.**"
    ),
)
async def ask(query: ResearchQuery) -> ResearchAnswer:
    return await answer_question(query)
