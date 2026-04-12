import logging
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class FeedbackRequest(BaseModel):
    type: str                    # "positive" | "negative"
    category: Optional[str]      # error category, negative only
    comment: str
    message_content: str         # first 100 chars of the AI message


@router.post("/feedback")
async def submit_feedback(payload: FeedbackRequest):
    logger.info(
        "feedback received: type=%s category=%s comment=%r message_content=%r",
        payload.type,
        payload.category,
        payload.comment[:200] if payload.comment else "",
        payload.message_content[:100],
    )
    # TODO(future): forward to remote server here
    return {"ok": True}
