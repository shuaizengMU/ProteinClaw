import logging
from typing import Literal, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


class FeedbackRequest(BaseModel):
    feedback_type: Literal["positive", "negative"]
    category: Optional[str] = None
    comment: str = Field(default="", max_length=500)
    message_content: str = Field(max_length=500)


@router.post("/feedback")
async def submit_feedback(payload: FeedbackRequest):
    logger.info(
        "feedback received: type=%s category=%s comment=%r message_content=%r",
        payload.feedback_type,
        payload.category,
        payload.comment[:200],
        payload.message_content[:100],
    )
    # TODO(future): forward to remote server here
    return {"ok": True}
